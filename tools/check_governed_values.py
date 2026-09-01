#!/usr/bin/env python3
"""Fail when a governed value reappears as a literal in a recipe.

Governance decays quietly. The 30-vs-50 usability floor is the proof: `n_pos >= 30`
sat in a shaker step of `compute_validation_auc_ci` for weeks while every document,
notebook and Python recipe said 50, and nothing could see it because visual recipe
payloads were not mirrored into the repo. This script is the guard that would have
caught it on the first run after the drift.

It reads only the repo -- the Python mirrors in `dss_recipes/*.py`, the Cypher in
`dss_recipes/cypher/`, the visual formulas in `dss_recipes/visual/` and the generated
`.index/recipes.tsv`. No DSS connection, so it is cheap enough for a pre-commit hook.
That also means it is only as fresh as the last `build_recipe_index.py --refresh`:
it catches drift that has been mirrored, not drift still sitting in the DSS UI.

Three rules:

  1. IDENTITY   the recipes converted under DEC-OPS-006 must hold no bare disease
                node_index. Indices renumber on a graph rebuild; these recipes resolve
                names through python/demo_identity.py instead.
  2. THRESHOLDS a value that has a project variable must not appear as a comparison
                literal. Comments are exempt -- the converted recipes deliberately
                quote the old literals to explain what changed.
  3. GATES      the ten seed-gated recipes must still carry exactly the gate
                DEC-OPS-006 pins them to. This is the inverse guard: those literals
                are supposed to stay, and a silent change to one is as bad as drift.

Run: python3 tools/check_governed_values.py
"""

from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECIPES = os.path.join(ROOT, "dss_recipes")
INDEX = os.path.join(ROOT, ".index", "recipes.tsv")
SNAP = os.path.join(ROOT, ".index", "dss_snapshot.json")

# DEC-MEAS-004 pins these two and, crucially, pins them APART. They answer different
# questions -- "can this AUROC be quoted at all" (trust) versus "does this term go on
# stage" (panel) -- and the interval evidence shows the break is at 30, not 50, so 50 is
# a conservative presentation choice. Setting them equal is a real decision with a
# measured cost (unifying down takes the overlap grid from 148 pairs to 179 and
# invalidates the nb7 assertions), so it must not happen as a tidy-up.
EXPECTED_VARIABLES = {"trust_n_pos": 30, "panel_n_pos": 50, "near_dup": 0.6}
DISTINCT_PAIRS = (("trust_n_pos", "panel_n_pos"),)

# Recipes whose disease identity is resolved by name (DEC-OPS-006). Adding a recipe
# here after converting it is what keeps the guarantee from rotting.
IDENTITY_RECIPES = (
    "compute_demo_panel_config",
    "compute_breast_panel",
    "compute_split_audit_2",
)

# The observed disease node_index range, widened a little. Bare integers in this band
# inside an identity recipe are almost certainly a pinned index.
INDEX_RANGE = (30000, 60000)

# A governed value only matters when it is compared against the quantity the variable
# governs. Keying on the value alone is too broad: `hits_at_50`, `coverage_pct < 50` and
# a pool size of >= 50 are all unrelated 50s. Each rule is (variable, subject, values) --
# subject is matched on the same line, left of the comparison.
GOVERNED = (
    ("trust_n_pos", "a positive count", re.compile(r"\bn_?pos\b", re.I), {"30"}),
    ("panel_n_pos", "a positive count", re.compile(r"\bn_?pos\b", re.I), {"50"}),
    ("near_dup", "a top-50 overlap", re.compile(r"jaccard|near_?dup|inter\s*/\s*union", re.I), {"0.6"}),
)

# The one recipe whose seed literal is pinned on purpose (DEC-OPS-006).
THRESHOLD_EXEMPT_FILES = {"compute_dwpc_go_metapaths.py"}

# DEC-OPS-006: these stay literal, and this is the list a future seed change must touch.
EXPECTED_GATES = {
    "compute_dwpc_go_metapaths": "MIN_MODULE 20",
    "compute_enriched_disease_context_1": "module_size >= 20",
    "compute_enriched_dwpc_GCD": "module_size >= 20",
    "compute_enriched_dwpc_GGD": "module_size >= 20",
    "compute_enriched_dwpc_GPGD": "module_size >= 20",
    "compute_enriched_guilt_by_association_1": "module_size >= 20",
    "compute_enriched_module_size_1": "module_size >= 20",
    "compute_enriched_prox_closest": "MIN_SEEDS 5; POOL_MIN 20",
    "compute_enriched_rwr_score_1": "MIN_SEEDS 20",
    "compute_enriched_shared_pathway_count_1": "module_size >= 20",
}

COMPARISON = re.compile(r"(>=|<=|==|>|<)\s*(\d+(?:\.\d+)?)")
INT_LITERAL = re.compile(r"(?<![\w.])(\d{5})(?![\w.])")


def strip_comment(line: str, visual: bool) -> str:
    """Drop the comment tail. Both mirrors use `#`; formulas do not carry comments."""
    if visual:
        return "" if line.lstrip().startswith("#") else line
    return line.split("#", 1)[0]


def read_lines(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def check_identity(fail):
    for name in IDENTITY_RECIPES:
        path = os.path.join(RECIPES, name + ".py")
        if not os.path.exists(path):
            fail.append(f"{name}: mirror missing from dss_recipes/ -- cannot verify identity")
            continue
        for n, raw in enumerate(read_lines(path), 1):
            line = strip_comment(raw, visual=False)
            for m in INT_LITERAL.finditer(line):
                if INDEX_RANGE[0] <= int(m.group(1)) <= INDEX_RANGE[1]:
                    fail.append(
                        f"{name}.py:{n}: bare node_index {m.group(1)} in an identity recipe. "
                        f"Resolve it by name via demo_identity.name_to_index (DEC-OPS-006)."
                    )


def check_thresholds(fail):
    targets = []
    for fn in sorted(os.listdir(RECIPES)):
        if fn.endswith(".py"):
            targets.append((fn, os.path.join(RECIPES, fn), False))
    vdir = os.path.join(RECIPES, "visual")
    if os.path.isdir(vdir):
        for fn in sorted(os.listdir(vdir)):
            if fn.endswith(".txt"):
                targets.append((fn, os.path.join(vdir, fn), True))

    for fn, path, visual in targets:
        if fn in THRESHOLD_EXEMPT_FILES:
            continue
        for n, raw in enumerate(read_lines(path), 1):
            line = strip_comment(raw, visual)
            if not line.strip():
                continue
            if "variables[" in line:
                continue
            for op, val in COMPARISON.findall(line):
                for var, label, subject, values in GOVERNED:
                    if val in values and subject.search(line):
                        fail.append(
                            f"{fn}:{n}: `{op} {val}` against {label} is governed by the "
                            f"`{var}` project variable. Read it instead of pinning the value."
                        )


def check_gates(fail):
    if not os.path.exists(INDEX):
        fail.append(".index/recipes.tsv missing -- run tools/build_recipe_index.py")
        return
    live = {}
    for row in read_lines(INDEX)[1:]:
        parts = row.split("\t")
        if len(parts) > 2 and parts[2] and parts[2] != "-":
            live[parts[0]] = parts[2]
    for name, gate in sorted(EXPECTED_GATES.items()):
        if name not in live:
            fail.append(f"{name}: expected to carry gate `{gate}` but it is no longer gated. "
                        f"DEC-OPS-006 pins these ten; changing one is a Phase 3 decision.")
        elif live[name] != gate:
            fail.append(f"{name}: gate is `{live[name]}`, DEC-OPS-006 pins `{gate}`.")
    for name, gate in sorted(live.items()):
        if name not in EXPECTED_GATES:
            fail.append(f"{name}: newly gated (`{gate}`) and not recorded in DEC-OPS-006. "
                        f"Add it to the decision and to EXPECTED_GATES, or remove the gate.")


def check_variables(fail):
    """The project variables, as snapshotted by build_recipe_index.py --refresh."""
    if not os.path.exists(SNAP):
        fail.append(".index/dss_snapshot.json missing -- run build_recipe_index.py --refresh")
        return
    import json
    with open(SNAP, encoding="utf-8") as fh:
        live = (json.load(fh) or {}).get("_variables") or {}
    if not live:
        fail.append("no project variables in the snapshot -- re-run "
                    "build_recipe_index.py --refresh against a project that has them")
        return
    for key, want in sorted(EXPECTED_VARIABLES.items()):
        if key not in live:
            fail.append(f"project variable `{key}` is gone. DEC-MEAS-004 / DEC-OPS-006 "
                        f"expect it; recipes read it and will fail loudly without it.")
        elif live[key] != want:
            fail.append(f"project variable `{key}` is {live[key]!r}, pinned at {want!r}. "
                        f"Changing it moves shipped numbers -- update the decision first.")
    for a, b in DISTINCT_PAIRS:
        if a in live and b in live and live[a] == live[b]:
            fail.append(f"`{a}` and `{b}` are both {live[a]!r}. DEC-MEAS-004 keeps them "
                        f"DISTINCT on purpose: they answer different questions and the "
                        f"interval evidence supports no single cliff.")


def main() -> int:
    fail: list[str] = []
    check_variables(fail)
    check_identity(fail)
    check_thresholds(fail)
    check_gates(fail)
    if fail:
        print("GOVERNED VALUE DRIFT:")
        for f in fail:
            print("  " + f)
        return 1
    print(f"governed values ok ({len(IDENTITY_RECIPES)} identity recipes, "
          f"{len(GOVERNED)} variables, {len(EXPECTED_GATES)} pinned gates)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
