"""Capture every read route's payload from the webapp backend, or compare two captures (workplan M5).

READ-ONLY against DSS: it calls the route handlers in-process (no HTTP layer, no server) with each
Query default filled, so nothing is deployed and nothing is written. The sources routes (an
external search, and a cache write on a miss) and the assistant (an LLM POST) are left out.
Captures go under data/webapp_payloads/, which is never committed.

    cd webapp && PROJECT_KEY=DEMO_TARGET_IDENTIFICATION .venv/bin/python ../tools/capture_webapp_payloads.py \\
        capture ../data/webapp_payloads/<date>.json
    python3 tools/capture_webapp_payloads.py compare data/webapp_payloads/A.json data/webapp_payloads/B.json

Run the capture with the webapp's own environment (`webapp/.venv`), from `webapp/`, after
`eval "$(dku auth export-env)"`.

The compare matches list rows by their ids (gene_index, disease_index, family ids) rather than by
position, takes numbers as equal within 1e-9 relative (3 and 3.0 are equal), and reports apart the
fields the shortlist's ranking with ties is predicted to move (DEC-MEAS-005): `rank_in_disease`
and `rank_percentile`. It also checks every candidate list is ordered by rank, then gene name.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import sys
import time

MOVED = {"rank_in_disease", "rank_percentile"}
IDS = ("gene_index", "disease_index", "family_id", "disease_family_id", "act3_family", "disease_a",
       "disease_b", "subtype", "gene", "label", "quintile", "split")
RTOL = 1e-9


def capture(out_path: str) -> int:
    from fastapi import HTTPException

    from backend.routes import calibration, candidates, evidence, families, system

    results, failures = {}, []

    def call(label, fn, **given):
        kwargs = {}
        for name, p in inspect.signature(fn).parameters.items():
            if name in given:
                kwargs[name] = given[name]
            elif p.default is not inspect.Parameter.empty:
                kwargs[name] = getattr(p.default, "default", p.default)
        key = label + ("?" + "&".join("%s=%s" % kv for kv in sorted(given.items())) if given else "")
        t = time.time()
        try:
            body, status = fn(**kwargs), 200
        except HTTPException as e:
            body, status = e.detail, e.status_code
        except Exception as e:  # noqa: BLE001
            body, status = "%s: %s" % (type(e).__name__, e), 500
        body = json.loads(json.dumps(body, default=str))
        results[key] = {"status": status, "seconds": round(time.time() - t, 2), "body": body,
                        "sha256": hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]}
        if status != 200:
            failures.append("%s -> %s %s" % (key, status, str(body)[:200]))
        return body if status == 200 else None

    call("/api/system/health", system.health)
    call("/api/evidence", evidence.evidence)
    call("/api/calibration", calibration.calibration)
    fams = call("/api/families", families.families) or []
    for f in fams:
        fid = f.get("family_id", f.get("disease_family_id", f.get("id")))
        if fid is not None:
            call("/api/families/%s" % fid, families.family, family_id=fid)
    diseases = call("/api/candidates/diseases", candidates.diseases) or []
    genes = set()
    for d in diseases:
        di = d.get("disease_index")
        rows = call("/api/candidates", candidates.candidates, disease=di) or []
        call("/api/candidates", candidates.candidates, disease=di, novel_only=True, tractable_only=True,
             exclude_secreted=True)
        rows = rows if isinstance(rows, list) else rows.get("candidates", rows.get("rows", []))
        for row in rows[:3]:
            g = row.get("gene_index")
            genes.add(g)
            call("/api/candidates/gene", candidates.gene_detail, disease=di, gene=g)
            call("/api/candidates/drugs", candidates.pair_drugs, disease=di, gene=g)
            call("/api/candidates/drivers", candidates.pair_drivers, disease=di, gene=g)
    for g in sorted(genes):
        call("/api/candidates/identity", candidates.gene_identity, gene=g)

    json.dump(results, open(out_path, "w"), indent=1, sort_keys=True)
    print("routes called: %d, families %d, diseases %d, genes %d" % (len(results), len(fams), len(diseases), len(genes)))
    print("non-200: %d" % len(failures))
    for f in failures:
        print("  " + f)
    return 1 if failures else 0


def row_id(row):
    return tuple((k, row[k]) for k in IDS if isinstance(row, dict) and k in row)


def diff(a, b, path, out, moved):
    """Append (path, a, b) for each difference; predicted rank moves go to `moved`."""
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            out.append((path, a, b))
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if not (a == b or (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b))
                or math.isclose(a, b, rel_tol=RTOL)):
            (moved if path.rsplit(".", 1)[-1] in MOVED else out).append((path, a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(("%s.%s" % (path, k), a.get(k, "<absent>"), b.get(k, "<absent>")))
            else:
                diff(a[k], b[k], "%s.%s" % (path, k), out, moved)
    elif isinstance(a, list) and isinstance(b, list):
        if a and all(isinstance(x, dict) and row_id(x) for x in a + b):
            ka, kb = {row_id(x): x for x in a}, {row_id(x): x for x in b}
            if len(ka) == len(a) and len(kb) == len(b):
                for k in sorted(set(ka) | set(kb), key=str):
                    if k not in ka or k not in kb:
                        out.append(("%s[%s]" % (path, dict(k)), "<absent>" if k not in ka else "row",
                                    "<absent>" if k not in kb else "row"))
                    else:
                        diff(ka[k], kb[k], "%s[%s]" % (path, dict(k)), out, moved)
                return
        if len(a) != len(b):
            out.append((path + ".length", len(a), len(b)))
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, "%s[%d]" % (path, i), out, moved)
    elif a != b:
        out.append((path, a, b))


def order_ok(body) -> bool:
    rows = body if isinstance(body, list) else (body or {}).get("candidates", (body or {}).get("rows", []))
    keys = [(r["rank_in_disease"], str(r.get("gene_name"))) for r in rows if "rank_in_disease" in r]
    return keys == sorted(keys)


def compare(a_path: str, b_path: str) -> int:
    a, b = json.load(open(a_path)), json.load(open(b_path))
    differ = []
    moved_total, unordered = 0, []
    for key in sorted(set(a) | set(b)):
        if key not in a or key not in b:
            differ.append((key, ["only in %s" % ("second" if key in b else "first")]))
            continue
        out, moved = [], []
        if a[key]["status"] != b[key]["status"]:
            out.append(("status", a[key]["status"], b[key]["status"]))
        diff(a[key]["body"], b[key]["body"], "", out, moved)
        moved_total += len(moved)
        if key.startswith("/api/candidates?") and not order_ok(b[key]["body"]):
            unordered.append(key)
        if out:
            differ.append((key, out))
    print("calls: %d and %d; %d differ outside the predicted rank fields; %d predicted rank-field changes"
          % (len(a), len(b), len(differ), moved_total))
    print("candidate lists not ordered by (rank, gene name) in the second capture: %d" % len(unordered))
    for key, out in differ[:20]:
        print("\n  %s (%d)" % (key, len(out)))
        for item in out[:5]:
            print("    %s" % (item,))
    return 1 if differ or unordered else 0


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "capture":
        sys.exit(capture(sys.argv[2]))
    if len(sys.argv) == 4 and sys.argv[1] == "compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    sys.exit(__doc__)
