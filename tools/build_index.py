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
    .index/claims.tsv     every numeric claim in the docs, with its guard
    .index/decisions.tsv  a jump table for DECISIONS.md
    .index/SUMMARY.md     counts and the orphan list

Usage:  python3 tools/build_index.py [--check]
        --check exits non-zero if the committed indexes are stale (for CI / pre-commit).
"""

import ast
import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, ".index")

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
# RECORDS BY DESIGN. These files state what was true at a past date, so an unguarded number in them
# is correct behaviour, not risk. Excluding them is the difference between a 583-row list dominated
# by the append-only decision log and a list of live claims someone might quote.
RECORD_FILES = {
    "DECISIONS.md",                 # append-only log; corrections are new entries, never edits
    "docs/appendix/README.md",      # describes m3-era frozen snapshots
}
# Harness guidance is operational policy, not project evidence. Indexing it makes numerical examples
# and context-budget measurements look like live model claims. Keep source files and generated copies
# out of the claims scan; `tools/check_harness.py` owns their freshness and parity instead.
CLAIM_EXCLUDED_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "webapp/AGENTS.md",
    "webapp/CLAUDE.md",
}
CLAIM_EXCLUDED_PREFIXES = ("harness/", ".claude/", ".codex/")
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
        src = open(os.path.join(ROOT, path)).read()
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


def literal(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = literal(node.operand)
        return None if inner is None else -inner
    return None


# ---------------------------------------------------------------- claims
def build_claims(assertions):
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
    markdown_paths = [
        path for path in tracked("*.md")
        if path not in CLAIM_EXCLUDED_FILES and not path.startswith(CLAIM_EXCLUDED_PREFIXES)
    ]
    for path in sorted(markdown_paths):
        sec = ""
        for i, raw in enumerate(open(os.path.join(ROOT, path)), 1):
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


# ---------------------------------------------------------------- decisions jump table
def build_decisions():
    path = os.path.join(ROOT, "DECISIONS.md")
    if not os.path.exists(path):
        return []
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


# ---------------------------------------------------------------- output
def tsv(rows, cols):
    out = ["\t".join(cols)]
    for r in rows:
        out.append("\t".join(str(r[c]).replace("\t", " ") for c in cols))
    return "\n".join(out) + "\n"


def render(claims, decisions):
    files = {}
    for r in claims:
        d = files.setdefault(r["file"], defaultdict(int))
        d[r["status"]] += 1
    # risk surface = model-derived AND unguarded AND not obviously a historical record
    orphans = [r for r in claims
               if r["status"] == "ORPHAN" and not r["hint"] and r["model_dep"]
               and r["file"] not in RECORD_FILES]

    L = ["# Index summary", "",
         "Generated by `tools/build_index.py`. Do not edit by hand.", "",
         "`ORPHAN` = no notebook assertion covers this value. That is either a deliberate historical",
         "record or an unguarded claim that can drift silently. The `hint` column flags lines whose",
         "wording suggests a historical record; it is a hint, never a verdict.", "",
         "The risk surface is narrowed three ways: **model-derived** only (a frozen graph statistic",
         "cannot drift, since `compute_kg` is never recomputed), **records-by-design excluded**",
         "(`DECISIONS.md` and friends state what was true at a date), and lines whose wording already",
         "flags them as historical dropped.",
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
    L += ["", "## DECISIONS.md jump table", "",
          "%d entries, %d chars. Query `.index/decisions.tsv` rather than reading the file — it is"
          % (len(decisions), sum(d["chars"] for d in decisions)),
          "the densest file in the repo (~146 tokens per line).", ""]
    return "\n".join(L) + "\n"


def main():
    check = "--check" in sys.argv
    assertions = parse_assertions()
    claims = build_claims(assertions)
    decisions = build_decisions()

    files = {
        "assertions.tsv": tsv(
            [{"notebook": nb, "section": sec or "-", "check": nm, "expected": val}
             for sec, val, nb, nm in sorted(assertions, key=lambda a: (a[2], a[3]))],
            ["notebook", "section", "check", "expected"]),
        "claims.tsv": tsv(claims, ["file", "line", "section", "value", "status",
                                   "guarded_by", "model_dep", "hint", "context"]),
        "decisions.tsv": tsv(decisions, ["date", "line", "chars", "topic"]),
        "SUMMARY.md": render(claims, decisions),
    }

    if check:
        stale = [n for n, body in files.items()
                 if not os.path.exists(os.path.join(INDEX, n))
                 or open(os.path.join(INDEX, n)).read() != body]
        if stale:
            print("STALE index: %s — run `python3 tools/build_index.py`" % ", ".join(stale))
            return 1
        print("index up to date (%d claims, %d assertions, %d decisions)"
              % (len(claims), len(assertions), len(decisions)))
        return 0

    os.makedirs(INDEX, exist_ok=True)
    for n, body in files.items():
        open(os.path.join(INDEX, n), "w").write(body)
    orph = sum(1 for r in claims if r["status"] == "ORPHAN")
    print("wrote .index/  claims=%d (asserted=%d orphan=%d)  assertions=%d  decisions=%d"
          % (len(claims), sum(1 for r in claims if r["status"] == "ASSERTED"),
             orph, len(assertions), len(decisions)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
