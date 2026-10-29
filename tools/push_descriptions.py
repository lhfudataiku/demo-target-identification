#!/usr/bin/env python3
"""Push dataset and column descriptions into DSS, or report drift.

WHY A REPO SOURCE. Descriptions set only in the DSS UI are invisible to the repository, so nothing
can tell you when they go stale against a champion change or a renamed column. `tools/dataset_
descriptions.json` holds them as reviewable text; this pushes them and `--check` reports drift.

FEATURE WORDING IS NOT DUPLICATED HERE. `webapp/backend/feature_glossary.py` is the single copy --
its own docstring records that two hand-maintained copies is how the two acts started describing the
same model differently. This tool imports it at push time, so a DSS column description and the act 2
glossary card cannot disagree.

    python3 tools/push_descriptions.py            # report drift, exit 1 if any (default, safe)
    python3 tools/push_descriptions.py --push     # write to DSS
    python3 tools/push_descriptions.py --check    # alias for the default

A dataset entry with a "project" key lives in that project, not in PROJECT: the four the evidence
project took over in M2 (2026-10-29).
"""
import importlib.util
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "DEMO_TARGET_IDENTIFICATION"
SOURCE = os.path.join(ROOT, "tools", "dataset_descriptions.json")
GLOSSARY_PY = os.path.join(ROOT, "webapp", "backend", "feature_glossary.py")


def feature_columns():
    """champion feature -> description, taken from the ONE glossary copy."""
    spec = importlib.util.spec_from_file_location("feature_glossary", GLOSSARY_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = {}
    for name, _kind, _label, what in mod.GLOSSARY:
        out[name] = "Champion m7-f14 feature: %s." % what
    return out


def load():
    with open(SOURCE, encoding="utf-8") as fh:
        src = json.load(fh)
    cols = dict(src["columns"])
    for name, text in feature_columns().items():
        cols[name] = text          # glossary wins over the static file, by design
    return src["datasets"], cols


def project_of(meta):
    return meta.get("project", PROJECT)


def live_schema(dataset, project):
    """[(column, existing comment)] for one dataset.

    Reads `dataset get-definition`, NOT `dataset schema`: the latter strips the `comment` field, so
    checking against it reports every described column as drifted forever.
    """
    r = subprocess.run(["dku", "--format", "json", "dataset", "get-definition", dataset,
                        "-P", project], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        definition = json.loads(r.stdout)
    except ValueError:
        return None
    columns = (definition.get("schema") or {}).get("columns") or []
    return [(c.get("name"), c.get("comment") or "") for c in columns if isinstance(c, dict)]


def main():
    push = "--push" in sys.argv
    datasets, cols = load()
    live = {p: set(subprocess.run(["dku", "--format", "ids", "dataset", "list", "-P", p],
                                  capture_output=True, text=True).stdout.split())
            for p in {project_of(m) for m in datasets.values()}}
    missing = sorted(d for d, m in datasets.items() if d not in live[project_of(m)])
    drift, applied_ds, applied_cols = [], 0, 0

    for name in sorted(datasets):
        meta = datasets[name]
        project = project_of(meta)
        if name not in live[project]:
            continue
        schema = live_schema(name, project)
        described = [(c, t) for c, t in (schema or []) if c in cols]

        if not push:
            for c, current in (schema or []):
                if c in cols and current.strip() != cols[c].strip():
                    drift.append("%s.%s" % (name, c))
            continue

        args = ["dku", "dataset", "set-metadata", name, "-P", project,
                "--short-desc", meta["short"]]
        if meta.get("long"):
            args += ["--description", meta["long"]]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL metadata %s: %s" % (name, r.stderr.strip()[:120]))
            continue
        applied_ds += 1
        if described:
            pairs = []
            for c, _ in described:
                pairs += [c, cols[c]]
            r = subprocess.run(["dku", "dataset", "set-column-description", name, *pairs,
                                "-P", project], capture_output=True, text=True)
            if r.returncode != 0:
                print("FAIL columns %s: %s" % (name, r.stderr.strip()[:120]))
            else:
                applied_cols += len(described)
        print("  %-44s short=%3dch long=%4dch cols=%d" % (
            name, len(meta["short"]), len(meta.get("long") or ""), len(described)))

    if missing:
        print("NOT IN DSS (described but absent): %s" % ", ".join(missing))
    if push:
        print("pushed %d dataset descriptions, %d column descriptions" % (applied_ds, applied_cols))
        return 1 if missing else 0
    if drift:
        print("DRIFT in %d column description(s), first 10: %s" % (len(drift), ", ".join(drift[:10])))
        print("run: python3 tools/push_descriptions.py --push")
        return 1
    print("descriptions up to date (%d datasets, %d column concepts)" % (len(datasets), len(cols)))
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
