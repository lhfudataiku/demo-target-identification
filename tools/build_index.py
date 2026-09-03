#!/usr/bin/env python3
"""Generate .index/ — the navigation layer for this repo.

WHY THIS EXISTS. The docs carry ~135k tokens of prose and the recipes another ~93k. Answering
"is this number current or stale?" used to mean grepping a value, getting ten hits, and reading
four context regions to classify each one by hand. That is the operation that dominated the
2026-08-21 doc sweep, and it is the one that let the section 8.3 adopted row drift unnoticed.

THE DESIGN CHOICE. This does NOT try to classify claims as current vs historical -- that is a
judgement call and automating it badly would create a new stale-claim surface, which is the exact
failure mode the indexes exist to prevent. It classifies **asserted vs unasserted**, which is
objective and mechanically derivable:

    a documented number that no notebook assertion covers is either historical or an ORPHAN

ORPHAN rows are the risk surface. Everything else is either guarded by a notebook or is a
deliberate historical record.

Outputs (committed, so `ASSERTED -> ORPHAN` shows up in review):
    .index/claims.tsv     numeric claims from the explicit current-doc manifest
    .index/historical_claims.tsv  separately named historical comparison surface
    .index/decisions.tsv  current durable decisions, with stable IDs
    .index/decisions_history.tsv  classified jump table for the retired log
    .index/SUMMARY.md     counts and the orphan list

Usage:  python3 tools/build_index.py [--check]
        --check exits non-zero if the committed indexes are stale (for CI / pre-commit).
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, ".index")
MANIFEST = os.path.join(ROOT, "tools", "index_manifest.json")

# ---------------------------------------------------------------- number extraction
# Claim-shaped numbers only. A bare small integer is almost never a claim, and section numbers,
# dates and ISO-ish tokens are noise that would swamp the signal.
NUM = re.compile(
    r"""(?<![\w.])(
          \d{1,3}(?:,\d{3})+          # 3,958,921
        | \d+\.\d{2,}                 # 0.8230, 16.88
        | \d+\.\d(?=\s*[×x%])         # 16.9x, 8.9%
    )(?![\w])""",
    re.X,
)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SECREF = re.compile(r"§\s*\d+(?:\.\d+)*")
HEADING = re.compile(r"^(#{1,6})\s+(?:\*\*)?(\d+(?:\.\d+)*)\.?\s")
# MODEL-DEPENDENT vocabulary. This is the filter that makes the orphan list usable. The numbers
# that actually drift when the champion changes are model-derived metrics; the rest are frozen graph
# statistics (113,391 nodes, 2,851,510 edges) or literature citations, which cannot drift because
# `compute_kg` is never recomputed. Without this filter the risk surface was 1,292 rows and useless.
MODELDEP = re.compile(
    r"\bAUC\b|AUROC|AUPRC|\blift\b|spread|\brho\b|ρ|proba|probability|precision|recall"
    r"|macro|pooled|tractab|discovery|therapeutic|association AUC|Spearman|Pearson|R²"
    r"|\bties\b|quintile|champion|\bm[1-8]\b|scored_m|hits@|hits at|rank(?:ed|s|ing)?\b"
    r"|\bt = |\bdm\b|degree-matched|per-disease|per-family|split-key|null gap|single-feature",
    re.I,
)
# a hint only -- never used to decide ORPHAN status
HIST = re.compile(
    r"SUPERSEDED|CORRECTED|REFUTED|retired|reference|previously|deleted|"
    r"at the time|no longer|historical|frozen",
    re.I,
)


def tracked(pattern):
    """Tracked files matching pattern, EXCLUDING .index/ itself.

    .index/SUMMARY.md is a .md file. Once committed it becomes tracked, so without this filter the
    generator re-indexes the numbers it printed in its own summary and the claim count grows on
    every run (observed: 1,630 -> 1,744). Self-referential and compounding.
    """
    out = subprocess.run(["git", "ls-files", pattern], cwd=ROOT,
                         capture_output=True, text=True).stdout.split("\n")
    return [f for f in out if f.strip() and not f.startswith(".index/")]


def load_manifest():
    """Load and strictly validate the bounded current/history claim surfaces.

    The manifest is intentionally a reviewed source file rather than an inferred directory walk:
    new Markdown, harness material and setup guides cannot silently become current claim risk.
    """
    with open(MANIFEST) as handle:
        manifest = json.load(handle)
    required = {"schema_version", "current_claim_documents", "historical_claim_documents",
                "current_scan_exclusions", "index_metadata"}
    if set(manifest) != required or manifest["schema_version"] != 1:
        raise ValueError("invalid tools/index_manifest.json schema")
    exclusions = manifest["current_scan_exclusions"]
    if set(exclusions) != {"prefixes", "files"}:
        raise ValueError("manifest exclusions must declare prefixes and files")
    prefixes, files = exclusions["prefixes"], exclusions["files"]
    if not all(isinstance(x, str) for x in prefixes + files):
        raise ValueError("manifest exclusions must be strings")
    tracked_md = set(tracked("*.md"))
    current, seen = [], set()
    for item in manifest["current_claim_documents"]:
        if set(item) != {"path", "index"} or item["index"] not in {"heuristic", "governed_registry"}:
            raise ValueError("each current manifest entry needs path and supported index")
        path = item["path"]
        if (not isinstance(path, str) or path not in tracked_md or path in seen
                or any(path.startswith(p) for p in prefixes) or path in files):
            raise ValueError("invalid or excluded current claim document: %r" % path)
        seen.add(path)
        current.append(item)
    historical, hseen = [], set()
    for path in manifest["historical_claim_documents"]:
        if (not isinstance(path, str) or path not in tracked_md or path in hseen
                or not (path.startswith("archive/") or path in {
                    "docs/appendix/README.md", "docs/operations/PHASE_0_BASELINE_2026-08-28.md"})):
            raise ValueError("invalid historical claim document: %r" % path)
        hseen.add(path)
        historical.append(path)
    if seen & hseen:
        raise ValueError("a claim document cannot be both current and historical")
    classified = seen | hseen | set(files)
    unclassified = sorted(path for path in tracked_md
                          if path not in classified
                          and not any(path.startswith(prefix) for prefix in prefixes))
    if unclassified:
        # A bare list here stops the whole index build and says nothing about how
        # to clear it, which is how one harness-generated document (a licence
        # review, 2026-09-03) left `.index/` unbuildable for a day. The hard
        # failure is deliberate -- nothing becomes claim surface silently -- so
        # the fix is to make the failure actionable, not to soften it.
        raise ValueError(
            "tracked Markdown lacks a manifest role:\n"
            + "".join("  %s\n" % path for path in unclassified)
            + "\nEvery tracked .md must be classified in tools/index_manifest.json.\n"
              "The deciding question is whether the document makes MEASURABLE claims\n"
              "that could drift against a notebook assertion:\n\n"
              "  yes -> add to current_claim_documents as\n"
              "         {\"path\": \"...\", \"index\": \"heuristic\"}\n"
              "  no  -> add the path to current_scan_exclusions.files\n"
              "         (governance, operations records, reference, scope and\n"
              "          setup documents all live here)\n\n"
              "For a whole generated tree, add a trailing-slash prefix to\n"
              "current_scan_exclusions.prefixes instead of listing each file.\n\n"
              "Unsure? Classify it as a claim document, run this script, and read\n"
              "what it contributed to .index/claims.tsv:\n"
              "  awk -F'\\t' '$1==\"<path>\"' .index/claims.tsv\n"
              "All-ORPHAN rows, or version strings and dates scraped as values,\n"
              "mean it belongs in the exclusions.")
    required_indexes = {
        ".index/claims.tsv", ".index/historical_claims.tsv", ".index/decisions.tsv",
        ".index/decisions_history.tsv", ".index/models.tsv", ".index/features.tsv",
        ".index/recipes.tsv", ".index/code.tsv",
    }
    metadata = manifest["index_metadata"]
    paths = set()
    for item in metadata:
        if set(item) != {"path", "owner", "freshness", "scope"} or not all(item.values()):
            raise ValueError("each index metadata entry needs path, owner, freshness and scope")
        paths.add(item["path"])
    if not required_indexes <= paths or len(paths) != len(metadata):
        raise ValueError("manifest metadata is missing a required index or repeats a path")
    return manifest, current, historical


def scrub(line):
    """Remove tokens that look numeric but are never claims."""
    line = DATE.sub(" ", line)
    line = SECREF.sub(" ", line)
    return line


def norm(tok):
    return float(tok.replace(",", ""))


def decimals(tok):
    return len(tok.split(".")[1]) if "." in tok else 0


# ---------------------------------------------------------------- assertions
def parse_assertions():
    """(section, value, notebook, check_name) for every literal-valued check() call.

    Assertion names in this repo start with the section they guard ("8.3 approved lift@10"),
    which is what makes precise claim<->assertion matching possible: matching on value alone
    would mark coincidental collisions as guarded.
    """
    rows = []
    for path in tracked("notebooks/*.py"):
        with open(os.path.join(ROOT, path)) as handle:
            src = handle.read()
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            print("WARN  %s does not parse (%s) -- assertions not indexed" % (path, e),
                  file=sys.stderr)
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "check" and len(node.args) >= 2):
                continue
            name = static_prefix(node.args[0])
            val = literal(node.args[1])
            if name is None or val is None:
                continue
            m = re.match(r"^(\d+(?:\.\d+)*)", name)
            rows.append((m.group(1) if m else "", val, os.path.basename(path), name))

        # Loop-table assertions: the expected value is a loop variable, not a literal argument.
        #     for lab, docA, docS in [("approved join", 0.6886, 0.7471), ...]:
        #         check(f"5.2.1 {lab} auc_supported", docS, ...)
        # Without this the numbers in that table are invisible and the doc lines they guard get
        # reported as ORPHAN. Found by the champion-metric cross-check failing on 0.7471.
        for node in ast.walk(tree):
            if not (isinstance(node, ast.For) and isinstance(node.iter, (ast.List, ast.Tuple))):
                continue
            checks = [c for c in ast.walk(node)
                      if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                      and c.func.id == "check"]
            if not checks:
                continue
            # Preserve exact loop-table provenance when the loop target and tuple rows are literal.
            # This lets governed claims distinguish, for example, approved/all from
            # approved/supported instead of accepting any coincident numeric value in the table.
            target_names = []
            if isinstance(node.target, (ast.Tuple, ast.List)):
                target_names = [item.id if isinstance(item, ast.Name) else None
                                for item in node.target.elts]
            for item in node.iter.elts:
                if not (target_names and isinstance(item, (ast.Tuple, ast.List))
                        and len(item.elts) == len(target_names)):
                    continue
                bindings = {}
                for target_name, value_node in zip(target_names, item.elts):
                    if target_name is None or not isinstance(value_node, ast.Constant):
                        continue
                    bindings[target_name] = value_node.value
                for c in checks:
                    if len(c.args) < 2 or not isinstance(c.args[1], ast.Name):
                        continue
                    value = bindings.get(c.args[1].id)
                    name = resolved_fstring(c.args[0], bindings)
                    if name is None or not isinstance(value, (int, float)) \
                            or isinstance(value, bool):
                        continue
                    m = re.match(r"^(\d+(?:\.\d+)*)", name)
                    rows.append((m.group(1) if m else "", float(value),
                                 os.path.basename(path), name))

            vals = [literal(n) for n in ast.walk(node.iter)
                    if isinstance(n, (ast.Constant, ast.UnaryOp))]
            vals = [v for v in vals if v is not None]
            for c in checks:
                nm = static_prefix(c.args[0]) or ""
                m = re.match(r"^(\d+(?:\.\d+)*)", nm)
                sec = m.group(1) if m else ""
                for v in vals:
                    rows.append((sec, v, os.path.basename(path), nm + " [loop-table]"))
    return rows


def static_prefix(node):
    """Leading static text of a str or f-string, so f"5.2.1 {lab} auc" still yields its section."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                return v.value
            break
    return None


def resolved_fstring(node, bindings):
    """Resolve a simple f-string whose substitutions are literal loop bindings."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if not isinstance(node, ast.JoinedStr):
        return None
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) \
                and value.value.id in bindings:
            parts.append(str(bindings[value.value.id]))
        else:
            return None
    return "".join(parts)


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = literal(node.operand)
        return None if inner is None else -inner
    return None


# ---------------------------------------------------------------- claims
def build_claims(assertions, markdown_paths):
    by_sec = defaultdict(list)
    all_vals = []
    for sec, val, nb, name in assertions:
        by_sec[sec].append((val, nb, name))
        all_vals.append((val, nb, name))

    def guard(sec, tok):
        """Match at the claim's own precision: the doc rounds (16.9x) where the check holds 16.88."""
        want, d = norm(tok), decimals(tok)
        for val, nb, name in by_sec.get(sec, []):
            if round(val, d) == want:
                return "ASSERTED", "%s:%s" % (nb, name)
        for val, nb, name in all_vals:
            if round(val, d) == want:
                return "VALUE_ONLY", "%s:%s" % (nb, name)
        return "ORPHAN", ""

    rows = []
    for path in sorted(markdown_paths):
        sec = ""
        with open(os.path.join(ROOT, path)) as handle:
            for i, raw in enumerate(handle, 1):
                h = HEADING.match(raw)
                if h:
                    sec = h.group(2)
                    continue
                line = scrub(raw)
                seen = set()
                for m in NUM.finditer(line):
                    tok = m.group(1)
                    if tok in seen:
                        continue
                    seen.add(tok)
                    status, by = guard(sec, tok)
                    rows.append({
                        "file": path, "line": i, "section": sec or "-", "value": tok,
                        "status": status, "guarded_by": by,
                        "hint": "hist" if HIST.search(raw) else "",
                        "model_dep": "y" if MODELDEP.search(raw) else "",
                        "context": re.sub(r"\s+", " ", raw.strip())[:110].rstrip(),
                    })
    return rows


# ---------------------------------------------------------------- decision indexes
DECISION_HEADING = re.compile(r"^##\s+(DEC-[A-Z0-9]+-\d{3})\s+—\s+(.+?)\s*$")
DECISION_FIELD = re.compile(r"^-\s+\*\*(.+?):\*\*\s*(.*?)\s*$")
REQUIRED_DECISION_FIELDS = {
    "Date", "Domain", "Status", "Decision", "Rationale", "Evidence", "Consequences",
    "Supersedes", "Superseded by", "Historical sources",
}


def build_current_decisions():
    path = os.path.join(ROOT, "docs/decisions/DECISION_REGISTER.md")
    if not os.path.exists(path):
        raise ValueError("missing current decision register: docs/decisions/DECISION_REGISTER.md")
    records = []
    current = None
    for i, raw in enumerate(open(path), 1):
        heading = DECISION_HEADING.match(raw.rstrip("\n"))
        if heading:
            if current:
                records.append(current)
            current = {"id": heading.group(1), "topic": heading.group(2), "line": i, "fields": {}}
            continue
        field = DECISION_FIELD.match(raw.rstrip("\n"))
        if current and field:
            current["fields"][field.group(1)] = field.group(2)
    if current:
        records.append(current)
    if not records:
        raise ValueError("current decision register contains no records")

    errors, seen = [], set()
    rows = []
    for rec in records:
        rid, fields = rec["id"], rec["fields"]
        if rid in seen:
            errors.append("duplicate current decision ID %s" % rid)
        seen.add(rid)
        missing = sorted(REQUIRED_DECISION_FIELDS - set(fields))
        extra = sorted(set(fields) - REQUIRED_DECISION_FIELDS)
        if missing:
            errors.append("%s missing fields: %s" % (rid, ", ".join(missing)))
        if extra:
            errors.append("%s unexpected fields: %s" % (rid, ", ".join(extra)))
        blank = sorted(name for name in REQUIRED_DECISION_FIELDS - {"Historical sources"}
                       if not fields.get(name, "").strip())
        if blank:
            errors.append("%s has blank fields: %s" % (rid, ", ".join(blank)))
        if fields.get("Historical sources", "").strip() in {"", "lines"}:
            errors.append("%s must declare historical line numbers or an em dash" % rid)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields.get("Date", "")):
            errors.append("%s has invalid date %r" % (rid, fields.get("Date")))
        if fields.get("Status") not in {"accepted", "approved-not-executed", "rejected", "superseded"}:
            errors.append("%s has invalid status %r" % (rid, fields.get("Status")))
        sources = []
        for token in re.findall(r"\d+", fields.get("Historical sources", "")):
            sources.append(int(token))
        rows.append({
            "id": rid, "date": fields.get("Date", ""), "domain": fields.get("Domain", ""),
            "status": fields.get("Status", ""), "line": rec["line"], "topic": rec["topic"],
            "decision": fields.get("Decision", ""), "evidence": fields.get("Evidence", ""),
            "historical_sources": sources,
        })
    if errors:
        raise ValueError("current decision register invalid:\n- " + "\n- ".join(errors))
    return rows


def build_historical_decisions():
    path = os.path.join(ROOT, "archive/decisions/DECISIONS_2026-08-31.md")
    if not os.path.exists(path):
        raise ValueError("missing archived decision log")
    rows = []
    for i, raw in enumerate(open(path), 1):
        m = re.match(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.*?)\s*\|\s*$", raw)
        if not m:
            continue
        date, body = m.group(1), m.group(2)
        b = re.search(r"\*\*(.+?)\*\*", body)          # entries lead with a bolded verdict
        topic = (b.group(1) if b else body)
        rows.append({"date": date, "line": i,
                     "chars": len(body),
                     "topic": re.sub(r"\s+", " ", topic).strip(" .")[:150]})
    return rows


def apply_decision_triage(history, current):
    path = os.path.join(ROOT, "archive/decisions/TRIAGE.json")
    triage = json.load(open(path))
    source = triage.get("source", "")
    source_path = os.path.join(ROOT, source)
    if not os.path.isfile(source_path):
        raise ValueError("triage source does not exist: %s" % source)
    actual_hash = hashlib.sha256(open(source_path, "rb").read()).hexdigest()
    if actual_hash != triage.get("source_sha256"):
        raise ValueError("archived decision log hash changed: %s" % actual_hash)

    allowed = {"durable_decision", "reusable_trap", "experiment_evidence", "incident_history", "operation"}
    categories = triage.get("categories", {})
    if set(categories) != allowed:
        raise ValueError("triage categories must be exactly: %s" % ", ".join(sorted(allowed)))
    routes = triage.get("routes", {})
    if set(routes) != allowed or any(not routes[key].strip() for key in allowed):
        raise ValueError("triage must declare one non-empty route per category")
    assigned = {}
    for category, lines in categories.items():
        for line in lines:
            if line in assigned:
                raise ValueError("historical line %d classified twice" % line)
            assigned[line] = category
    history_lines = {row["line"] for row in history}
    if set(assigned) != history_lines:
        missing = sorted(history_lines - set(assigned))
        extra = sorted(set(assigned) - history_lines)
        raise ValueError("triage coverage mismatch; missing=%s extra=%s" % (missing, extra))

    current_ids = {row["id"] for row in current}
    promotions = {int(line): ids for line, ids in triage.get("promotions", {}).items()}
    durable = set(categories["durable_decision"])
    if set(promotions) != durable:
        raise ValueError("every durable historical entry must have exactly one promotion mapping")
    for line, ids in promotions.items():
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("historical line %d has an empty or duplicate promotion" % line)
        unknown = sorted(set(ids) - current_ids)
        if unknown:
            raise ValueError("historical line %d promotes unknown IDs: %s" % (line, unknown))

    reverse = defaultdict(set)
    for line, ids in promotions.items():
        for rid in ids:
            reverse[rid].add(line)
    for row in current:
        declared = set(row.pop("historical_sources"))
        if declared != reverse.get(row["id"], set()):
            raise ValueError("%s historical sources disagree with TRIAGE.json" % row["id"])

    for row in history:
        row["category"] = assigned[row["line"]]
        row["promoted_to"] = ",".join(promotions.get(row["line"], [])) or "-"
        row["route"] = routes[row["category"]]
    return history


# ---------------------------------------------------------------- output
def tsv(rows, cols):
    out = ["\t".join(cols)]
    for r in rows:
        out.append("\t".join(str(r[c]).replace("\t", " ") for c in cols))
    return "\n".join(out) + "\n"


def render(claims, decisions, decision_history):
    files = {}
    for r in claims:
        d = files.setdefault(r["file"], defaultdict(int))
        d[r["status"]] += 1
    # risk surface = model-derived AND unguarded AND not obviously a historical record
    orphans = [r for r in claims
               if r["status"] == "ORPHAN" and not r["hint"] and r["model_dep"]
               ]

    L = ["# Index summary", "",
         "Generated by `tools/build_index.py`. Do not edit by hand.", "",
         "Governed current Part 2 claims and their consumers are indexed separately in",
         "`.index/governed_claims.tsv` from `docs/prioritizer/CLAIM_REGISTRY.json`; the evidence map",
         "is intentionally excluded from this heuristic numeric scan.", "",
         "`ORPHAN` = no notebook assertion covers this value. That is either a deliberate historical",
         "record or an unguarded claim that can drift silently. The `hint` column flags lines whose",
         "wording suggests a historical record; it is a hint, never a verdict.", "",
         "The current-doc manifest excludes archived material, harness instructions and setup guides",
         "before scanning. The risk surface is further narrowed to **model-derived** claims only",
         "(a frozen graph statistic cannot drift, since `compute_kg` is never recomputed), and lines",
         "whose wording already flags them as historical are dropped.",
         "", "## Claims by file", "",
         "| file | asserted | value-only | orphan | total |", "|---|--:|--:|--:|--:|"]
    for f in sorted(files):
        d = files[f]
        L.append("| `%s` | %d | %d | %d | %d |" % (
            f, d["ASSERTED"], d["VALUE_ONLY"], d["ORPHAN"],
            d["ASSERTED"] + d["VALUE_ONLY"] + d["ORPHAN"]))
    tot = defaultdict(int)
    for r in claims:
        tot[r["status"]] += 1
    L += ["| **total** | **%d** | **%d** | **%d** | **%d** |" % (
        tot["ASSERTED"], tot["VALUE_ONLY"], tot["ORPHAN"], len(claims)), "",
        "## Risk surface — model-derived, unguarded, no historical wording", "",
        "**%d rows.** Of %d total orphans, these are the model-dependent ones: the numbers that move"
        % (len(orphans), tot["ORPHAN"]),
        "when the champion changes and that no notebook would catch.", "",
        "| file:line | §  | value | context |", "|---|---|--:|---|"]
    for r in orphans[:60]:
        L.append("| `%s:%d` | %s | %s | %s |" % (
            r["file"], r["line"], r["section"], r["value"],
            r["context"].replace("|", "\\|")[:90]))
    if len(orphans) > 60:
        L.append("")
        L.append("*%d more in `claims.tsv` — filter `status=ORPHAN` and empty `hint`.*"
                 % (len(orphans) - 60))
    triage_counts = defaultdict(int)
    for row in decision_history:
        triage_counts[row["category"]] += 1
    L += ["", "## Decision indexes", "",
          "**%d current durable decisions.** Query `.index/decisions.tsv` by stable ID, domain or"
          % len(decisions),
          "topic; open `docs/decisions/DECISION_REGISTER.md` only for the rationale and consequences.",
          "", "The retired log remains recoverable as **%d classified historical entries** in"
          % len(decision_history),
          "`.index/decisions_history.tsv`: %s."
          % ", ".join("%s=%d" % (key, triage_counts[key]) for key in sorted(triage_counts)), ""]
    return "\n".join(L) + "\n"


def main():
    check = "--check" in sys.argv
    manifest, current_documents, historical_documents = load_manifest()
    assertions = parse_assertions()
    claims = build_claims(assertions, [item["path"] for item in current_documents
                                       if item["index"] == "heuristic"])
    historical_claims = build_claims(assertions, historical_documents)
    decisions = build_current_decisions()
    decision_history = apply_decision_triage(build_historical_decisions(), decisions)

    files = {
        "assertions.tsv": tsv(
            [{"notebook": nb, "section": sec or "-", "check": nm, "expected": val}
             for sec, val, nb, nm in sorted(assertions, key=lambda a: (a[2], a[3]))],
            ["notebook", "section", "check", "expected"]),
        "claims.tsv": tsv(claims, ["file", "line", "section", "value", "status",
                                   "guarded_by", "model_dep", "hint", "context"]),
        "historical_claims.tsv": tsv(historical_claims, ["file", "line", "section", "value", "status",
                                                           "guarded_by", "model_dep", "hint", "context"]),
        "decisions.tsv": tsv(decisions, ["id", "date", "domain", "status", "line", "topic", "decision", "evidence"]),
        "decisions_history.tsv": tsv(
            decision_history,
            ["date", "line", "chars", "category", "promoted_to", "route", "topic"]),
        "SUMMARY.md": render(claims, decisions, decision_history),
        "index_metadata.tsv": tsv(manifest["index_metadata"], ["path", "owner", "freshness", "scope"]),
    }

    if check:
        stale = [n for n, body in files.items()
                 if not os.path.exists(os.path.join(INDEX, n))
                 or open(os.path.join(INDEX, n)).read() != body]
        if stale:
            print("STALE index: %s — run `python3 tools/build_index.py`" % ", ".join(stale))
            return 1
        print("index up to date (%d current claims, %d historical claims, %d assertions, %d current decisions, %d historical)"
              % (len(claims), len(historical_claims), len(assertions), len(decisions), len(decision_history)))
        return 0

    os.makedirs(INDEX, exist_ok=True)
    for n, body in files.items():
        open(os.path.join(INDEX, n), "w").write(body)
    orph = sum(1 for r in claims if r["status"] == "ORPHAN")
    print("wrote .index/  current_claims=%d (asserted=%d orphan=%d) historical_claims=%d assertions=%d decisions=%d history=%d"
          % (len(claims), sum(1 for r in claims if r["status"] == "ASSERTED"), orph,
             len(historical_claims), len(assertions), len(decisions), len(decision_history)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
