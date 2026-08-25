#!/usr/bin/env python3
"""Mirror the DSS Jupyter notebooks into notebooks/*.py, or report how far they have drifted.

WHY: `notebooks/*.py` are described as mirrors of the DSS notebooks, but nothing enforced it. On
2026-08-25 all five had diverged **in both directions** — DSS had gained markdown-cell structure and
figures in nb1, while the repo mirror held two figures and three assertions that DSS did not. Neither
side was a superset, and `.index/assertions.tsv` counts assertions from the MIRROR, so the assertion
index was describing notebooks that were not the ones being run.

    ./tools/pull_notebooks.py            # report drift, exit 1 if any  (default, safe)
    ./tools/pull_notebooks.py --pull     # overwrite the mirrors from DSS
    ./tools/pull_notebooks.py --pull nb1_features_and_config

`--pull` is deliberately not the default: the mirror is sometimes ahead, and clobbering it loses work
that was never pushed to DSS. Read the drift report first.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NBDIR = os.path.join(ROOT, "notebooks")
PROJECT = os.environ.get("DKU_PROJECT", "DEMO_TARGET_IDENTIFICATION")
CHECK_RE = re.compile(r"\bcheck\s*\(")
PLOT_RE = re.compile(r"\bplt\.")
DATASET_RE = re.compile(r'Dataset\("([^"]+)"\)')


def sh(args: list[str]) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def dss_notebooks() -> list[str]:
    out = sh(["dku", "notebook", "list", "-P", PROJECT])
    names = []
    for ln in out.split("\n")[1:]:
        parts = ln.split("\t")
        if len(parts) >= 2 and parts[1].strip() == "jupyter" and parts[0].startswith("nb"):
            names.append(parts[0].strip())
    return sorted(names)


def to_py(nb: dict) -> str:
    """Flatten an .ipynb to a diffable .py. Markdown cells become `# ==== heading ====` so the
    mirror keeps the section structure the DSS notebook now carries in markdown cells."""
    out = []
    for c in nb.get("cells", []):
        src = "".join(c.get("source", []))
        if c.get("cell_type") == "markdown":
            for line in src.strip().split("\n"):
                h = line.strip()
                if h.startswith("#"):
                    out.append(f"# ==== {h.lstrip('#').strip()} ====")
                elif h:
                    out.append(f"# {h}")
            out.append("")
        elif c.get("cell_type") == "code":
            out.append(src.rstrip() + "\n")
    return "\n".join(out).rstrip() + "\n"


def stats(text: str) -> dict:
    return {
        "lines": len(text.splitlines()),
        "checks": len(CHECK_RE.findall(text)),
        "plots": len(PLOT_RE.findall(text)),
        "datasets": sorted(set(DATASET_RE.findall(text))),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true", help="overwrite the mirrors from DSS")
    ap.add_argument("only", nargs="*", help="limit to these notebook names")
    args = ap.parse_args()

    names = args.only or dss_notebooks()
    if not names:
        print("no DSS notebooks found — is DKU_PROJECT set and dku authenticated?")
        return 1

    drift = 0
    for n in names:
        raw = sh(["dku", "notebook", "get", n, "-P", PROJECT])
        if not raw:
            print(f"  {n:32s} COULD NOT READ from DSS")
            drift += 1
            continue
        dss_py = to_py(json.loads(raw))
        path = os.path.join(NBDIR, n + ".py")
        repo_py = open(path).read() if os.path.exists(path) else ""

        d, r = stats(dss_py), stats(repo_py)
        # Byte equality is the wrong bar: the mirror is a FLATTENED .ipynb, so markdown cells become
        # comments and the two can never match exactly while the mirror is also hand-edited. What
        # matters is whether they assert the same things against the same data.
        substantive = (d["checks"] == r["checks"] and d["datasets"] == r["datasets"])
        if dss_py == repo_py:
            print(f"  {n:32s} identical ({d['lines']} lines, {d['checks']} assertions)")
            continue
        if substantive:
            print(f"  {n:32s} in sync — {d['checks']} assertions, same reads "
                  f"(formatting differs: {d['lines']} vs {r['lines']} lines)")
            continue

        drift += 1
        print(f"  {n:32s} DRIFT")
        print(f"      {'':10s} {'lines':>7} {'assertions':>11} {'figures':>8}")
        print(f"      {'DSS':10s} {d['lines']:>7} {d['checks']:>11} {d['plots']:>8}")
        print(f"      {'mirror':10s} {r['lines']:>7} {r['checks']:>11} {r['plots']:>8}")
        only_dss = sorted(set(d["datasets"]) - set(r["datasets"]))
        only_repo = sorted(set(r["datasets"]) - set(d["datasets"]))
        if only_dss:
            print(f"      reads only in DSS   : {', '.join(only_dss)}")
        if only_repo:
            print(f"      reads only in mirror: {', '.join(only_repo)}")
        if d["checks"] < r["checks"] or d["plots"] < r["plots"]:
            print("      ⚠ the MIRROR is ahead — pulling would DISCARD assertions or figures")
        if args.pull:
            open(path, "w").write(dss_py)
            print(f"      pulled -> {os.path.relpath(path, ROOT)}")

    if not args.pull and drift:
        print(f"\n{drift} notebook(s) drifted. Review above, then: ./tools/pull_notebooks.py --pull")
        print("Rebuild the assertion index afterwards: python3 tools/build_index.py")
    return 1 if drift and not args.pull else 0


if __name__ == "__main__":
    sys.exit(main())
