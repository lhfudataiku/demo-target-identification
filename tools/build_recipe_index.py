#!/usr/bin/env python3
"""Index the recipe layer, and put the Cypher under version control.

TWO PROBLEMS THIS SOLVES.

1. The gate inventory was not derivable without a two-minute sweep of `dku recipe get-settings`
   across every recipe. I ran that sweep twice on 2026-08-21 to answer the same question.

2. **The Cypher recipes are not in the repo.** Only the 48 Python recipes are mirrored in
   `dss_recipes/`. The six Cypher recipes that carry `module_size >= 20` -- including the three pool
   routes that decide which diseases exist at all -- live only in the DSS UI. They can be edited
   with no diff, no review and no history. Phase 3 consists entirely of editing those gates, so
   this script mirrors them to `dss_recipes/cypher/*.cypher` and makes a gate change a reviewable
   diff for the first time.

CLASS 1 vs CLASS 2 IS NOT AUTO-DERIVED, DELIBERATELY.

    Class 1  widening the gate only ADDS rows; existing values are untouched
    Class 2  the recipe recomputes an aggregate over the ELIGIBLE set, so widening the gate
             CHANGES existing rows -- a different intervention, not a NULL fill

That distinction decided the whole Phase 3 design and it rests on reading what each aggregate's
scope is. Guessing it from a regex would be exactly the kind of plausible-but-wrong automation this
repo keeps getting burned by. So it is recorded by hand in `tools/recipe_classes.json`, and **this
script exits non-zero if a gated recipe has no class recorded** -- a new gate cannot slip through
unclassified. Auto-detected evidence is emitted alongside as a hint to whoever classifies it.

Usage:
    python3 tools/build_recipe_index.py --refresh     # hits DSS, rewrites snapshot + cypher mirror
    python3 tools/build_recipe_index.py               # offline, rebuilds indexes from the snapshot
    python3 tools/build_recipe_index.py --check       # non-zero if indexes or classes are stale
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, ".index")
SNAP = os.path.join(INDEX, "dss_snapshot.json")
CYPHER_DIR = os.path.join(ROOT, "dss_recipes", "cypher")
CLASSES = os.path.join(ROOT, "tools", "recipe_classes.json")
REGISTRY = os.path.join(ROOT, "tools", "model_registry.json")
PROJECT = os.environ.get("DKU_PROJECT", "DEMO_TARGET_IDENTIFICATION")
# dss_recipes/ mirrors recipes from the graph-building projects too. Names only (one cheap list call
# each) so a mirror is called stale only when NO project owns it.
SIBLING_PROJECTS = ["DEMO_KG_LS", "KNOWLEDGE_GRAPH_PRIMEKG", "PRIMEKG"]

GATES = [
    (re.compile(r"module_size\s*>=\s*(\d+)"), "module_size >="),
    (re.compile(r"MIN_SEEDS\s*=\s*(\d+)"), "MIN_SEEDS"),
    (re.compile(r"POOL_MIN\s*=\s*(\d+)"), "POOL_MIN"),
    (re.compile(r"MIN_MODULE\s*=\s*(\d+)"), "MIN_MODULE"),
]

# Heuristic evidence only -- an aggregate taken after filtering to the eligible set is the shape that
# makes a recipe Class 2. Reported as a hint, never used as the answer.
C2_HINT = re.compile(
    r"eligible\s*=|isin\(set\(eligible|\.groupby\([^)]*\)\s*\.\s*size\(\)|"
    r"gd\s*=\s*gd\[",
)


def sh(args):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout


def refresh():
    """Snapshot every recipe's settings and mirror any Cypher into the repo."""
    listing = sh(["dku", "recipe", "list", "-P", PROJECT]).split("\n")
    names = []
    for ln in listing:
        parts = ln.split("\t") if "\t" in ln else ln.split()
        if parts and parts[0] and parts[0] not in ("name", "Recipe"):
            names.append(parts[0])
    snap = {}
    for i, n in enumerate(names, 1):
        raw = sh(["dku", "recipe", "get-settings", n, "-P", PROJECT])
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            print("  WARN no settings for %s" % n, file=sys.stderr)
            continue
        try:
            d = json.loads(m.group(0))
        except json.JSONDecodeError:
            print("  WARN unparseable settings for %s" % n, file=sys.stderr)
            continue
        payload = d.get("params", {}) or {}
        cy = None
        # the visual-graph plugin stores the query under params, key name varies by version
        for k, v in payload.items():
            if isinstance(v, str) and "cypher" in k.lower():
                cy = v
        if cy is None:
            blob = json.dumps(payload)
            mm = re.search(r'"cypher_query"\s*:\s*"((?:[^"\\]|\\.)*)"', blob)
            if mm:
                cy = mm.group(1).encode().decode("unicode_escape")
        code = None
        if d.get("type") in ("python", "shell", "r", "sql_query", "sql_script"):
            raw_code = sh(["dku", "recipe", "get-code", n, "-P", PROJECT])
            if raw_code and "has no code payload" not in raw_code:
                code = raw_code
        snap[n] = {
            "code": code,
            "type": d.get("type", ""),
            "inputs": sorted({x.get("ref") for v in (d.get("inputs") or {}).values()
                              for x in (v.get("items") or []) if x.get("ref")}),
            "outputs": sorted({x.get("ref") for v in (d.get("outputs") or {}).values()
                               for x in (v.get("items") or []) if x.get("ref")}),
            "cypher": cy,
        }
        if i % 15 == 0:
            print("  ... %d/%d" % (i, len(names)))
    # Dataset schemas, so emitted columns can be derived as (output cols - input cols) instead of
    # by regexing each recipe's source. The regex missed dwpc_GBGD/dwpc_GFGD and two ppi_* features
    # because not every python recipe builds its output from a dict literal.
    schemas = {}
    for ln in sh(["dku", "dataset", "list", "-P", PROJECT]).split("\n"):
        nm = (ln.split("\t") or [""])[0].strip()
        if not nm or nm in ("name", "Datasets", "dataset"):
            continue
        out = sh(["dku", "dataset", "schema", nm, "-P", PROJECT])
        cols = []
        for row in out.split("\n"):
            parts = row.split("\t")
            if len(parts) == 2 and parts[0] not in ("name",) and not row.startswith("Schema:"):
                cols.append(parts[0].strip())
        if cols:
            schemas[nm] = cols
    print("schemas: %d datasets" % len(schemas))
    models = {}
    for ln in sh(["dku", "model", "list", "-P", PROJECT]).split("\n"):
        parts = ln.split("\t")
        if len(parts) >= 3 and parts[0] not in ("id",) and not ln.startswith("Saved Models"):
            models[parts[0].strip()] = {"name": parts[1].strip(), "type": parts[2].strip()}
    print("models: %d saved" % len(models))
    sibling = set()
    for proj in SIBLING_PROJECTS:
        for ln in sh(["dku", "recipe", "list", "-P", proj]).split("\n"):
            nm = (ln.split("\t") or [""])[0].strip()
            if nm and nm not in ("name", "Recipe"):
                sibling.add(nm)
    print("sibling-project recipes: %d (for the mirror check)" % len(sibling))
    snap["_sibling_recipes"] = sorted(sibling)
    snap["_models"] = models
    snap["_schemas"] = schemas
    os.makedirs(INDEX, exist_ok=True)
    json.dump(snap, open(SNAP, "w"), indent=1, sort_keys=True)

    # A python recipe that is not mirrored in dss_recipes/ is invisible to review AND was invisible
    # to this scan until the snapshot started carrying `code`. compute_enriched_rwr_score_1 carries a
    # gate and was missed for exactly that reason.
    # `_sibling_recipes` is a LIST and `_models` / `_schemas` are dicts, so the meta keys must be
    # skipped before calling .get() -- otherwise --refresh dies with AttributeError AFTER the
    # snapshot has already been written, leaving the index half-refreshed and the exit code 0.
    # `not os.path.exists` alone meant --refresh could only CREATE a missing mirror, never update a
    # drifted one. On 2026-08-25 twelve mirrors still read `scored_m3` months after the live recipes
    # moved to `scored_champion`, and --refresh reported success without touching any of them.
    # A refresh that cannot refresh is worse than no refresh: it launders staleness as freshness.
    unmirrored, drifted = [], []
    for n, r in sorted(snap.items()):
        if n.startswith("_") or not r.get("code"):
            continue
        mp = os.path.join(ROOT, "dss_recipes", n + ".py")
        if not os.path.exists(mp):
            unmirrored.append(n)
        elif open(mp).read() != r["code"]:
            drifted.append(n)
    for n in unmirrored + drifted:
        open(os.path.join(ROOT, "dss_recipes", n + ".py"), "w").write(snap[n]["code"])
    if unmirrored:
        print("mirrored %d previously-unversioned python recipes: %s"
              % (len(unmirrored), ", ".join(unmirrored)))
    if drifted:
        print("REFRESHED %d drifted mirror(s) from live DSS: %s"
              % (len(drifted), ", ".join(drifted)))

    # mirror the Cypher so a gate change becomes a reviewable diff
    os.makedirs(CYPHER_DIR, exist_ok=True)
    n_cy = 0
    for name, r in sorted(snap.items()):
        if name.startswith("_") or not r.get("cypher"):
            continue
        body = r["cypher"].replace("\\n", "\n")
        hdr = ("// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:\n"
               "// this file is a copy for review and grep. The live query is in the DSS recipe.\n"
               "// recipe: %s\n// inputs: %s\n// outputs: %s\n\n"
               % (name, ", ".join(r["inputs"]) or "-", ", ".join(r["outputs"]) or "-"))
        open(os.path.join(CYPHER_DIR, name + ".cypher"), "w").write(hdr + body + "\n")
        n_cy += 1
    print("snapshot: %d recipes, %d cypher mirrored to dss_recipes/cypher/" % (len(snap), n_cy))
    return snap


def source_for(name, rec):
    """Whatever text we can search for a gate: mirrored python, or the snapshot's cypher."""
    p = os.path.join(ROOT, "dss_recipes", name + ".py")
    if os.path.exists(p):
        return open(p).read(), "dss_recipes/%s.py" % name
    if rec.get("cypher"):
        return rec["cypher"], "dss_recipes/cypher/%s.cypher" % name
    if rec.get("code"):
        return rec["code"], "DSS-only (python, not mirrored)"
    return "", ""


def mirror_status(stem, own, sibling, snap=None, path=None):
    """Status of one mirrored file.

    This used to test only whether a live recipe of that NAME existed anywhere, so "0 stale mirror"
    was reported while twelve mirrors held m3-era code. Name-existence and content-freshness are
    different questions; DRIFTED MIRROR answers the second."""
    if stem in own:
        if snap and path and os.path.exists(path):
            live = (snap.get(stem) or {}).get("code")
            if live is not None and open(path).read() != live:
                return "DRIFTED MIRROR (content differs from live DSS)"
        return "MIRROR"
    if stem in sibling:
        return "MIRROR (graph-build project)"
    return "STALE MIRROR (no DSS recipe in any known project)"


def find_gates(text):
    out = []
    for rx, label in GATES:
        for m in rx.finditer(text):
            out.append((label, int(m.group(1))))
    # dedupe, keep order
    seen, res = set(), []
    for g in out:
        if g not in seen:
            seen.add(g)
            res.append(g)
    return res


def emitted_columns(name, rec, schemas=None):
    """Columns the recipe introduces = output schema minus every input schema.

    Derived from dataset schemas rather than from source text, because no single source pattern
    covers cypher RETURN clauses, dict-literal frames and write_with_schema alike.
    """
    if schemas:
        outs, ins = set(), set()
        for d in rec.get("outputs") or []:
            outs |= set(schemas.get(d, []))
        for d in rec.get("inputs") or []:
            ins |= set(schemas.get(d.split(".")[-1], []) or schemas.get(d, []))
        new = sorted(outs - ins)
        if new:
            return new
    if rec.get("cypher"):
        cy = rec["cypher"].replace("\\n", "\n")
        m = re.search(r"\bRETURN\b(.*)$", cy, re.S | re.I)
        if m:
            tail = m.group(1)
            cols = []
            for part in tail.split(","):
                part = part.strip().rstrip('"').strip()
                a = re.search(r"\bAS\s+([A-Za-z_]\w*)", part, re.I)
                if a:
                    cols.append(a.group(1))
                else:
                    b = re.match(r"^([A-Za-z_]\w*)\s*$", part)
                    if b:
                        cols.append(b.group(1))
            return cols
    p = os.path.join(ROOT, "dss_recipes", name + ".py")
    if os.path.exists(p):
        src = open(p).read()
        cols = re.findall(r'^\s*"([a-z][a-z0-9_]{2,})":', src, re.M)
        return sorted(set(cols))
    return []


def main():
    if "--refresh" in sys.argv:
        snap = refresh()
    else:
        if not os.path.exists(SNAP):
            print("no snapshot — run: python3 tools/build_recipe_index.py --refresh")
            return 1
        snap = json.load(open(SNAP))

    schemas = snap.pop("_schemas", None) if isinstance(snap, dict) else None
    sibling_recipes = set(snap.pop("_sibling_recipes", None) or [])
    classes = json.load(open(CLASSES)) if os.path.exists(CLASSES) else {}
    champion = set(classes.get("_champion_features", []))
    recmeta = classes.get("recipes", {})

    rows, feats, unclassified = [], [], []
    for name in sorted(snap):
        rec = snap[name]
        text, where = source_for(name, rec)
        gates = find_gates(text) if text else []
        gate_s = "; ".join("%s %d" % g for g in gates) or "-"
        cls = recmeta.get(name, {}).get("class", "")
        if gates and not cls:
            unclassified.append(name)
            cls = "UNCLASSIFIED"
        evidence = "c2?" if (gates and C2_HINT.search(text)) else ""
        cols = emitted_columns(name, rec, schemas)
        rows.append({
            "recipe": name, "type": rec.get("type", ""), "gate": gate_s,
            "class": cls or "-", "auto_hint": evidence,
            "source": where or "DSS-only",
            "inputs": ",".join(rec.get("inputs") or []) or "-",
            "outputs": ",".join(rec.get("outputs") or []) or "-",
        })
        for c in cols:
            feats.append({
                "feature": c, "produced_by": name, "gate": gate_s, "class": cls or "-",
                "in_champion": "y" if c in champion else "",
                "note": recmeta.get(name, {}).get("note", ""),
            })

    # ---- model index: identity + consumers + decision refs generated; metrics hand-recorded ----
    reg = json.load(open(REGISTRY)) if os.path.exists(REGISTRY) else {}
    models = snap.pop("_models", None) or {}
    champion = reg.get("champion", "")
    ladder = set(reg.get("ablation_ladder") or [])
    ok_consumers = set(reg.get("ablation_consumers") or [])
    mreg = reg.get("models", {})

    blob = {n: json.dumps(r) for n, r in snap.items() if not n.startswith("_")}
    decision_sources = []
    for rel in ("docs/decisions/DECISION_REGISTER.md",
                "archive/decisions/DECISIONS_2026-08-31.md"):
        path = os.path.join(ROOT, rel)
        if os.path.exists(path):
            decision_sources.append((rel, open(path).read().split("\n")))

    # Cross-check the champion's hand-recorded metrics against .index/assertions.tsv. Without this
    # the registry becomes another unguarded number surface -- the very thing the indexes exist to
    # prevent. Only the champion is checked: retired models have no live assertions.
    asserted = []
    apath = os.path.join(INDEX, "assertions.tsv")
    if os.path.exists(apath):
        for ln in open(apath).read().split("\n")[1:]:
            f = ln.split("\t")
            if len(f) == 4:
                try:
                    asserted.append(float(f[3]))
                except ValueError:
                    pass
    drift = []
    if champion and asserted:
        for key in ("assoc_auroc", "drug_all", "drug_supported", "tract_dm200"):
            v = (mreg.get(champion) or {}).get(key)
            if v is None:
                continue
            # match at the recorded precision: the registry may hold 2.418 where nb4 asserts 2.42
            if not any(round(a, len(str(v).split(".")[1])) == v or round(v, 2) == round(a, 2)
                       for a in asserted):
                drift.append("%s=%s" % (key, v))

    mrows, strays, unrecorded = [], [], []
    # Iterate live saved models UNION registry entries. Seven retired models were deleted from the
    # flow on 2026-08-26; iterating only live objects would have silently dropped the whole ablation
    # ladder from the index, which is the one place those numbers are meant to stay greppable.
    combined = {mid: meta["name"] for mid, meta in models.items()}
    for mid, rec_ in mreg.items():
        combined.setdefault(mid, rec_.get("name", mid))
    for mid, name in sorted(combined.items(), key=lambda kv: kv[1]):
        meta = models.get(mid) or {"name": name}
        consumers = sorted(n for n, b in blob.items() if mid in b)
        # a consumer is "expected" if it is this model's own train/score recipe or a declared
        # ablation consumer; anything else is a live entry point on a retired model
        own = re.compile(r"^(train|score)_.*" + re.escape(name.split("-")[0]) + r"\b|^train_"
                         + re.escape(name) + r"$")
        stray = [c for c in consumers
                 if mid != champion and c not in ok_consumers and not own.search(c)]
        if stray:
            strays.append((name, stray))
        rec = mreg.get(mid)
        if rec is None:
            unrecorded.append("%s (%s)" % (name, mid))
            rec = {}
        refs = ["%s:%d" % (rel, i + 1)
                for rel, lines in decision_sources for i, ln in enumerate(lines) if name in ln]

        def g(k):
            v = rec.get(k)
            return "?" if v is None else v
        mrows.append({
            "model": name, "id": mid,
            "in_flow": "yes" if mid in models else "no (lab %s)" % rec.get("lab_session", "?"),
            "role": (("CHAMPION" if mid == champion else
                      "ablation" if mid in ladder else "-")),
            "n_feat": g("n_features"),
            "assoc_auroc": g("assoc_auroc"), "assoc_auprc": g("assoc_auprc"),
            "hub_spread": g("hub_spread"),
            "drug_all": g("drug_all"), "drug_supported": g("drug_supported"),
            "tract_dm200": g("tract_dm200"),
            "disc_lift50": g("disc_lift50"), "disc_lift200": g("disc_lift200"),
            "delta": rec.get("delta", "?"),
            "verdict": rec.get("verdict", "NOT RECORDED"),
            "consumers": ",".join(consumers) or "-",
            "decision_refs": ",".join(refs) or "-",
        })

    # ---- code index: every tracked .py/.json, and whether anything references it ----
    # Answers "is this file orphaned or stale?" mechanically. Root-level scripts, scripts/ and
    # webapp/ were invisible to every index until 2026-08-21; four dead prototypes had been sitting
    # in the repo root since 11 August, one of them carrying a MIN_SEEDS constant in dead code.
    code_files = [f for f in (sh(["git", "ls-files"]).split("\n")) if f.strip()
                  and (f.endswith(".py") or f.endswith(".json") or f.endswith(".cypher")
                       or f.endswith(".sh"))
                  # Harness configuration is not project code. `.claude/`/`.codex/` are already
                  # excluded from the claim manifest for the same reason; without this a tracked
                  # .claude/settings.json would enter the code index and stale it on every edit.
                  and not f.startswith(".claude/") and not f.startswith(".codex/")
                  and not f.startswith(".index/") and not f.startswith("__pycache__")]
    recipe_names = {n for n in snap if not n.startswith("_")}
    entry_points = set(classes.get("entry_points") or [])
    haystack = {}
    for f in (sh(["git", "ls-files"]).split("\n")):
        f = f.strip()
        # `.claude/`/`.codex/` are excluded as reference sources for the same reason they are
        # excluded as entries: a permission allowlist that names a tool is not a consumer of it, and
        # the skill copies there would count one document as four independent references.
        if not f or f.startswith(".index/") or "__pycache__" in f:
            continue
        if f.startswith(".claude/") or f.startswith(".codex/"):
            continue
        fp = os.path.join(ROOT, f)
        if os.path.isfile(fp) and os.path.getsize(fp) < 4_000_000:
            try:
                haystack[f] = open(fp, errors="ignore").read()
            except OSError:
                pass

    crows = []
    for f in sorted(code_files):
        base = os.path.basename(f)
        stem = base.rsplit(".", 1)[0]
        refs = sorted(o for o, txt in haystack.items()
                      if o != f and (base in txt or ("/" in f and f in txt)))
        if f.startswith("dss_recipes/cypher/"):
            kind = "cypher-mirror"
            status = mirror_status(stem, recipe_names, sibling_recipes)
        elif f.startswith("dss_recipes/"):
            kind = "recipe-mirror"
            status = mirror_status(stem, recipe_names, sibling_recipes,
                                   snap, os.path.join(ROOT, f))
        elif f.startswith("notebooks/"):
            kind, status = "notebook", "LIVE (tripwire)"
        elif f.startswith("tools/"):
            kind, status = "tool", "LIVE"
        elif f.startswith("archive/"):
            kind, status = "archive", "ARCHIVED"
        else:
            kind = "root-script" if "/" not in f else f.split("/")[0]
            if refs:
                status = "LIVE (referenced)"
            elif f in entry_points:
                status = "LIVE (external entry point)"
            else:
                status = "ORPHAN (referenced by nothing)"
        crows.append({"path": f, "kind": kind, "status": status,
                      "n_refs": len(refs), "referenced_by": ",".join(refs[:4]) or "-"})

    def tsv(rr, cols):
        return "\n".join(["\t".join(cols)] +
                         ["\t".join(str(r[c]).replace("\t", " ") for c in cols) for r in rr]) + "\n"

    files = {
        "code.tsv": tsv(sorted(crows, key=lambda r: (not r["status"].startswith("ORPHAN"),
                                                     not r["status"].startswith("STALE"),
                                                     r["path"])),
                        ["path", "kind", "status", "n_refs", "referenced_by"]),
        "models.tsv": tsv(mrows, ["model", "id", "in_flow", "role", "n_feat", "assoc_auroc", "assoc_auprc",
                                  "hub_spread", "drug_all", "drug_supported", "tract_dm200",
                                  "disc_lift50", "disc_lift200", "delta", "verdict",
                                  "consumers", "decision_refs"]),
        "recipes.tsv": tsv(sorted(rows, key=lambda r: (r["gate"] == "-", r["recipe"])),
                           ["recipe", "type", "gate", "class", "auto_hint", "source",
                            "inputs", "outputs"]),
        "features.tsv": tsv(sorted(feats, key=lambda r: (r["in_champion"] == "", r["feature"])),
                            ["feature", "produced_by", "gate", "class", "in_champion", "note"]),
    }

    if "--check" in sys.argv:
        bad = [n for n, b in files.items()
               if not os.path.exists(os.path.join(INDEX, n))
               or open(os.path.join(INDEX, n)).read() != b]
        if drift:
            print("CHAMPION METRIC NOT ASSERTED ANYWHERE: %s — either the registry drifted or the "
                  "notebooks stopped guarding it" % ", ".join(drift))
        if strays:
            for nm, ss in strays:
                print("STRAY CONSUMER: %s (non-champion) is referenced by %s" % (nm, ", ".join(ss)))
        if unrecorded:
            print("MODELS NOT IN tools/model_registry.json: %s" % ", ".join(unrecorded))
        if bad or unclassified or strays or unrecorded or drift:
            if bad:
                print("STALE: %s" % ", ".join(bad))
            if unclassified:
                print("UNCLASSIFIED gated recipes (add to tools/recipe_classes.json): %s"
                      % ", ".join(unclassified))
            return 1
        print("recipe index up to date (%d recipes, %d gated)"
              % (len(rows), sum(1 for r in rows if r["gate"] != "-")))
        return 0

    os.makedirs(INDEX, exist_ok=True)
    for n, b in files.items():
        open(os.path.join(INDEX, n), "w").write(b)
    gated = [r for r in rows if r["gate"] != "-"]
    orph = [r for r in crows if r["status"].startswith("ORPHAN")]
    stale = [r for r in crows if r["status"].startswith("STALE")]
    print("wrote .index/recipes.tsv (%d recipes, %d gated), features.tsv (%d columns), "
          "models.tsv (%d models), code.tsv (%d files: %d orphan, %d stale mirror)"
          % (len(rows), len(gated), len(feats), len(mrows), len(crows), len(orph), len(stale)))
    if drift:
        print("\n!! CHAMPION METRICS WITH NO MATCHING NOTEBOOK ASSERTION: %s\n"
              "   The registry is hand-transcribed; an unguarded metric there can drift exactly the\n"
              "   way the docs did." % ", ".join(drift))
    for nm, ss in strays:
        print("\n!! STRAY CONSUMER: %s is not the champion yet is referenced by %s\n"
              "   A retired model with a live scoring entry point is how score_persona_candidates\n"
              "   stayed on m3-f12 after the champion moved." % (nm, ", ".join(ss)))
    if unrecorded:
        print("\n!! %d saved models missing from tools/model_registry.json: %s"
              % (len(unrecorded), ", ".join(unrecorded)))
    if unclassified:
        print("\n!! %d GATED RECIPES HAVE NO CLASS RECORDED — Phase 3 must not proceed without\n"
              "   classifying these, because Class 2 changes existing rows:\n     %s"
              % (len(unclassified), "\n     ".join(unclassified)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
