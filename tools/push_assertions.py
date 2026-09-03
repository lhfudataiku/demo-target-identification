#!/usr/bin/env python3
"""Push the repository assertion scripts into the DSS project library, or report drift.

Replaces `tools/pull_notebooks.py` (deleted 2026-09-03), which mirrored the other way
(DSS Jupyter -> repo). Having two editable copies cost real correctness: on 2026-08-25 all five had
diverged in BOTH directions, while `.index/assertions.tsv` counted expectations from the repository
copy -- so the index described scripts that were not the ones being run. The DSS notebooks are now
retired; see `archive/notebooks-dss-2026-09-03/README.md`.

The direction is now one-way. `notebooks/*.py` is the single source of truth; the project library
holds a generated copy that the `validate_notebooks` scenario executes through
`nb_assertions/runner.py`. Nothing is edited in DSS.

    python3 tools/push_assertions.py            # report drift, exit 1 if any  (default, safe)
    python3 tools/push_assertions.py --push     # overwrite the library from the repository

`--check` is an alias for the default so this can sit in tools/check_indexes.sh.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "DEMO_TARGET_IDENTIFICATION"
REMOTE = "/python/nb_assertions"
# nb5 is exploration and defines no check(); the runner refuses a script that asserts nothing.
SKIP = {"nb5_data_exploration.py"}

# Repository data files a script reads relative to its own location. nb7 compares live DSS data
# against frozen expectations held in the repo:
#     HERE = os.path.dirname(os.path.abspath(__file__))
#     ET   = os.path.join(HERE, "..", "docs", "demo", "panel_selection", "analysis", "eyeball_test.csv")
# In the library HERE is /python/nb_assertions, so that resolves to /python/docs/... . Uploading the
# file there keeps the path working WITHOUT editing the script, which matters because
# tools/build_index.py parses these scripts for the assertion text and values it indexes.
DATA_FILES = {
    "../docs/demo/panel_selection/analysis/eyeball_test.csv":
        os.path.join("docs", "demo", "panel_selection", "analysis", "eyeball_test.csv"),
}


def scripts():
    d = os.path.join(ROOT, "notebooks")
    return sorted(f for f in os.listdir(d)
                  if f.startswith("nb") and f.endswith(".py") and f not in SKIP)


def payload():
    """remote basename -> local absolute path."""
    out = {"runner.py": os.path.join(ROOT, "tools", "nb_assertions", "runner.py"),
           "derive.py": os.path.join(ROOT, "tools", "nb_assertions", "derive.py"),
           "__init__.py": os.path.join(ROOT, "tools", "nb_assertions", "__init__.py")}
    for f in scripts():
        out[f] = os.path.join(ROOT, "notebooks", f)
    for remote_rel, local_rel in DATA_FILES.items():
        out[remote_rel] = os.path.join(ROOT, local_rel)
    return out


def remote_read(name):
    r = subprocess.run(["dku", "library", "read", REMOTE + "/" + name, "-P", PROJECT],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def main():
    push = "--push" in sys.argv
    drift = []
    for name, path in sorted(payload().items()):
        with open(path, encoding="utf-8") as fh:
            local = fh.read()
        if push:
            subprocess.run(["dku", "library", "write", REMOTE + "/" + name,
                            "-c", "@" + path, "-P", PROJECT],
                           check=True, capture_output=True, text=True)
            print("pushed %s/%s (%d bytes)" % (REMOTE, name, len(local.encode())))
            continue
        remote = remote_read(name)
        if remote is None:
            drift.append((name, "MISSING in library"))
        elif remote.rstrip("\n") != local.rstrip("\n"):
            drift.append((name, "DIFFERS from repository"))
    if push:
        print("pushed %d file(s) to %s" % (len(payload()), REMOTE))
        return 0
    for name, why in drift:
        print("DRIFT  %s/%s -- %s" % (REMOTE, name, why))
    if drift:
        print("run: python3 tools/push_assertions.py --push")
        return 1
    print("assertion library up to date (%d files)" % len(payload()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
