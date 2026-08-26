#!/usr/bin/env python3
"""Verify no dataset is older than the inputs it was built from.

WHY THIS EXISTS: on 2026-08-25 `candidates_annotated` was found to be SIX DAYS older than
`target_candidates_2`, the dataset it is built from. Nothing detected it. The flow served the right
numbers only because the dataset downstream of the stale link happened to hold a newer build — so a
single routine rebuild silently changed every rank in the demo (ERBB2 moved 14 -> 13, four genes left
the top 15). Row count, schema and build status were all unchanged and all green.

A stale middle link is invisible until something rebuilds through it. This makes it visible first.

    ./tools/check_freshness.py                 # whole project
    ./tools/check_freshness.py --zone A4       # one zone, by name prefix
    ./tools/check_freshness.py --quiet         # exit code only, for a pre-build gate

Exit 1 if any dataset is stale relative to a parent. Run it BEFORE a migration rebuild, not after.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, ".index", "dss_snapshot.json")
PROJECT = os.environ.get("DKU_PROJECT", "DEMO_TARGET_IDENTIFICATION")
# `dku dataset info` prints a tab table; these are the two lines we need.
BUILD_RE = re.compile(r"^last_build\t(.+)$", re.M)
OK_RE = re.compile(r"^build_ok\t(.+)$", re.M)


def sh(args: list[str]) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def dataset_build(name: str) -> tuple[str, str | None, str | None]:
    """(name, last_build, build_ok). last_build None means never built."""
    out = sh(["dku", "dataset", "info", name, "-P", PROJECT])
    b = BUILD_RE.search(out)
    o = OK_RE.search(out)
    val = b.group(1).strip() if b else None
    if val in ("", "(never)", "(unknown)", "None"):
        val = None
    return name, val, (o.group(1).strip() if o else None)


def parents_of(snap: dict) -> dict[str, list[str]]:
    """dataset -> the input datasets of the recipe that produces it (same-project only)."""
    out: dict[str, list[str]] = {}
    for rname, r in snap.items():
        if rname.startswith("_"):
            continue
        ins = [i.split(".")[-1] for i in r.get("inputs", []) if "." not in i or i.startswith(PROJECT + ".")]
        for ds in r.get("outputs", []):
            out.setdefault(ds, []).extend(ins)
    return out


def zone_of(name: str) -> str:
    out = sh(["dku", "dataset", "zone", name, "-P", PROJECT])
    m = re.search(r"is in zone '(.*)' \(ID:", out)
    return m.group(1) if m else "?"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", help="only datasets whose zone name starts with this")
    ap.add_argument("--quiet", action="store_true", help="exit code only")
    args = ap.parse_args()

    snap = json.load(open(SNAP))
    parents = parents_of(snap)
    # Recipe inputs/outputs also carry SAVED MODEL ids (a scoring recipe takes a model as an input),
    # and a model has no last_build, so it reads as "never built" and pollutes the report. Keep only
    # names DSS lists as datasets.
    listing = sh(["dku", "--format", "json", "dataset", "list", "-P", PROJECT])
    real = {r["name"] for r in json.loads(listing)} if listing else set()
    # A scoring recipe takes a SAVED MODEL as an input; a model has no last_build, so it must be
    # dropped from both sides or it reads as a permanently "never built" parent.
    parents = {ds: [p for p in ps if p in real] for ds, ps in parents.items() if ds in real}
    names = sorted(({d for ds in parents.values() for d in ds} | set(parents)) & real)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        builds = {n: (b, ok) for n, b, ok in ex.map(dataset_build, names)}

    if args.zone:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            zones = dict(zip(names, ex.map(zone_of, names)))
        keep = {n for n in names if zones.get(n, "").startswith(args.zone)}
    else:
        keep = set(names)

    stale, never, unbuilt_parent = [], [], []
    for ds in sorted(keep):
        child_b, child_ok = builds.get(ds, (None, None))
        if child_b is None:
            if ds in parents:            # only flag things that SHOULD have been built
                never.append(ds)
            continue
        for p in sorted(set(parents.get(ds, []))):
            par_b, _ = builds.get(p, (None, None))
            if par_b is None:
                unbuilt_parent.append((ds, p))
            elif par_b > child_b:        # ISO-8601-ish strings compare correctly
                stale.append((ds, child_b, p, par_b))

    if not args.quiet:
        print(f"checked {len(keep)} datasets in {PROJECT}" + (f" (zone {args.zone}*)" if args.zone else ""))
        if stale:
            print(f"\nSTALE — built BEFORE an input it depends on ({len(stale)}):")
            for ds, cb, p, pb in stale:
                print(f"  {ds}\n      built {cb}\n      but  {p} built {pb}")
        if never:
            print(f"\nNEVER BUILT ({len(never)}): {', '.join(never)}")
        if unbuilt_parent:
            print(f"\nPARENT NEVER BUILT ({len(unbuilt_parent)}):")
            for ds, p in unbuilt_parent:
                print(f"  {ds}  <- {p}")
        if not (stale or never or unbuilt_parent):
            print("all datasets are at least as new as their inputs")

    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
