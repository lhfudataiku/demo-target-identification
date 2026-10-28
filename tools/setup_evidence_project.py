"""Create the supporting evidence project and its inputs (ADR-003, workplan M2 step 2).

DRY RUN BY DEFAULT: it reads both projects and prints every change it would make. Nothing is
written to DSS without --apply, and --apply needs the user's approval at the time (workplan §1).

    uv run --project notebooks python tools/setup_evidence_project.py            # dry run
    uv run --project notebooks python tools/setup_evidence_project.py --apply    # writes

What --apply does, in order, each step idempotent so a re-run resumes:
  1. creates DEMO_TI_EVIDENCE ("Target Identification — Supporting Evidence"), owned by the API
     key's user, unless it already exists;
  2. sets its default Python code env to the main project's (`demo_kg-drug-discovery`);
  3. copies the main project's standard variables verbatim (DEC-OPS-006: demo_panel and the
     threshold scalars), replacing the new project's;
  4. writes /python/demo_identity.py from dss_lib/demo_identity.py, after checking it equals the
     main project's library copy;
  5. adds 18 exposure rules to DEMO_TARGET_IDENTIFICATION's settings, sharing the zone 00-31
     objects of EVIDENCE_PROJECT_DESIGN.md §3.1 with the evidence project. This is the one change
     to the main project, and it is additive: nothing there is rebuilt, moved or removed.
It then reads everything back and reports any mismatch.

It creates no recipe and no dataset, and builds nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import dataikuapi

ROOT = Path(__file__).resolve().parent.parent
MAIN = "DEMO_TARGET_IDENTIFICATION"
EVIDENCE = "DEMO_TI_EVIDENCE"
EVIDENCE_NAME = "Target Identification — Supporting Evidence"
LIBRARY_FILE = "/python/demo_identity.py"
LIBRARY_SOURCE = ROOT / "dss_lib" / "demo_identity.py"

# EVIDENCE_PROJECT_DESIGN.md §3.1: every recipe input the evidence project reads from the main
# project. Not the saved model -- the evidence shortlist ranks scored_champion instead.
EXPOSED = [
    "scored_champion",
    "psplit_train_set", "psplit_validation_set", "psplit_test_set",
    "enriched_graph_features_candidate_psplit",
    "disease_family_id", "gene_crosswalk", "enriched_gene_druggability_v2",
    "enriched_gene_safety_v2", "drug_evidence_pairs",
    "enriched_dwpc_GCD", "enriched_dwpc_GGD",
    "graph_nodes", "graph_edges",
    "drug_disease_edges", "drug_protein_edges", "raw_ot_known_drug",
    "gene_names",
]


def client() -> dataikuapi.DSSClient:
    url = os.environ.get("DKU_URL") or os.environ.get("DSS_URL")
    key = os.environ.get("DKU_API_KEY") or os.environ.get("DSS_API_KEY")
    if not (url and key):
        raise SystemExit("no DSS credentials: run `eval \"$(dku auth export-env)\"` first")
    return dataikuapi.DSSClient(url.rstrip("/"), key)


def dku_library_read(project: str) -> str | None:
    r = subprocess.run(["dku", "library", "read", LIBRARY_FILE, "-P", project],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def exposed_to(settings, target: str) -> set[str]:
    objs = settings.settings.get("exposedObjects", {}).get("objects", [])
    return {o["localName"] for o in objs if o.get("type") == "DATASET"
            and any(r.get("targetProject") == target for r in o.get("rules", []))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write to DSS (default: dry run)")
    args = ap.parse_args()
    act = "APPLY" if args.apply else "DRY-RUN"
    c = client()
    main_p = c.get_project(MAIN)

    # -- read the main project: everything below is copied from here --------------------------
    main_settings = main_p.get_settings()
    code_env = main_settings.settings["settings"]["codeEnvs"]["python"]
    variables = main_p.get_variables()
    main_lib = dku_library_read(MAIN)
    source_lib = LIBRARY_SOURCE.read_text()
    if main_lib is None or main_lib.rstrip("\n") != source_lib.rstrip("\n"):
        raise SystemExit("%s differs from %s in %s -- reconcile first" % (LIBRARY_SOURCE, LIBRARY_FILE, MAIN))
    datasets = {d["name"] for d in main_p.list_datasets()}
    missing = [d for d in EXPOSED if d not in datasets]
    if missing:
        raise SystemExit("not in %s: %s" % (MAIN, missing))

    exists = EVIDENCE in c.list_project_keys()
    owner = c.get_auth_info()["authIdentifier"]
    print("%s 1 project      %s %s (owner %s)" % (act, EVIDENCE, "exists, kept" if exists else "create", owner))
    print("%s 2 code env     python -> %s" % (act, json.dumps(code_env)))
    print("%s 3 variables    %d standard: %s" % (act, len(variables["standard"]), sorted(variables["standard"])))
    print("%s 4 library      %s (%d bytes, equals %s's)" % (act, LIBRARY_FILE, len(source_lib), MAIN))
    already = exposed_to(main_settings, EVIDENCE)
    todo = [d for d in EXPOSED if d not in already]
    print("%s 5 exposures    %d to add, %d already present, on %s" % (act, len(todo), len(already & set(EXPOSED)), MAIN))
    for d in todo:
        print("                   + DATASET %s -> %s" % (d, EVIDENCE))
    if not args.apply:
        print("\nDry run: nothing written. Re-run with --apply once approved.")
        return 0

    # -- apply ---------------------------------------------------------------------------------
    if not exists:
        c.create_project(EVIDENCE, EVIDENCE_NAME, owner,
                         description="Supporting evidence for model development (ADR-003). Reads "
                                     "DEMO_TARGET_IDENTIFICATION zones 00-31 only; nothing reads it.")
    ev = c.get_project(EVIDENCE)
    ev_settings = ev.get_settings()
    ev_settings.settings["settings"]["codeEnvs"]["python"] = code_env
    ev_settings.save()
    ev.set_variables({"standard": variables["standard"], "local": {}})
    subprocess.run(["dku", "library", "write", LIBRARY_FILE, "-c", "@" + str(LIBRARY_SOURCE), "-P", EVIDENCE],
                   check=True, capture_output=True)
    if todo:
        for d in todo:
            main_settings.add_exposed_object("DATASET", d, EVIDENCE)
        main_settings.save()

    # -- read back -----------------------------------------------------------------------------
    problems = []
    if c.get_project(EVIDENCE).get_settings().settings["settings"]["codeEnvs"]["python"] != code_env:
        problems.append("code env differs")
    if c.get_project(EVIDENCE).get_variables()["standard"] != variables["standard"]:
        problems.append("variables differ")
    if (dku_library_read(EVIDENCE) or "").rstrip("\n") != source_lib.rstrip("\n"):
        problems.append("library file differs")
    got = exposed_to(c.get_project(MAIN).get_settings(), EVIDENCE)
    if set(EXPOSED) - got:
        problems.append("not exposed: %s" % sorted(set(EXPOSED) - got))
    print("\nread back: %s" % ("OK" if not problems else "; ".join(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
