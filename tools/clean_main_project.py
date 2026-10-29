"""Remove from the main project what M2 retires or moves (FLOW_MIGRATION_WORKPLAN.md §2, M2).

DRY RUN BY DEFAULT: it reads both projects, re-runs the safety checks, and prints every change.
Nothing is written to DSS without --apply, and each run needs the user's approval at the time.
Nothing is built.

    uv run --project notebooks python tools/clean_main_project.py                       # dry run
    uv run --project notebooks python tools/clean_main_project.py --apply               # stage 1
    uv run --project notebooks python tools/clean_main_project.py --originals           # dry run, 1+2
    uv run --project notebooks python tools/clean_main_project.py --originals --apply   # stage 2

Stage 1, retirements, writes only to DEMO_TARGET_IDENTIFICATION:
  1. drops shap_drivers_long and shap_driver_frequency from Refresh_serving_layer's zone-40 step,
     before anything is deleted, so no scenario names a deleted dataset;
  2. deletes those two recipes and datasets (read by no notebook, no recipe and no webapp);
  3. deletes the validate_notebooks scenario, which has had no steps since 2026-10-05;
  4. deletes the /python/nb_assertions/ library folder, whose copies predate the notebook revision.

Stage 2, only with --originals, once the user has accepted M2: stage 1 (each step skipped when
already done), then the four recipes and datasets the evidence project now owns. Its checks require
each evidence copy to exist with stored rows.

Each delete is refused if anything outside this set still reads the dataset, if it is exposed, or if
a scenario names it. Deleting a dataset drops its data: the main copies of the moved four can be
rebuilt only by recreating their recipes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_evidence_project import EVIDENCE, MAIN, client  # noqa: E402

SCENARIO, SCENARIO_STEP = "Refresh_serving_layer", "build_serving_40"
RETIRED_SCENARIO = "validate_notebooks"
LIBRARY_FOLDER = "/python/nb_assertions"

# (recipe, dataset), downstream first, so no delete cascades to a recipe.
RETIRED = [("compute_shap_driver_frequency", "shap_driver_frequency"),
           ("compute_shap_drivers_long", "shap_drivers_long")]
ORIGINALS = [("compute_filter_three_axes", "filter_three_axes"),
             ("compute_pool_reachability", "pool_reachability"),
             ("compute_known_drug_truth", "known_drug_truth"),
             ("compute_breast_panel", "breast_panel_metrics")]


def readers(recipes: list[dict], dataset: str) -> list[str]:
    return [r["name"] for r in recipes
            if any(i["ref"] == dataset for role in r.get("inputs", {}).values() for i in role.get("items", []))]


def check(main_p, ev, pairs: list[tuple[str, str]], originals: bool) -> list[str]:
    problems = []
    recipes = main_p.list_recipes()
    have = {r["name"] for r in recipes}
    deleting = {r for r, _ in pairs}
    exposed = {o["localName"] for o in main_p.get_settings().get_raw()
               .get("exposedObjects", {}).get("objects", [])}
    scenarios = {s["id"]: json.dumps(main_p.get_scenario(s["id"]).get_settings().get_raw())
                 for s in main_p.list_scenarios()}
    for recipe, dataset in pairs:
        if recipe not in have:
            continue  # already deleted
        outs = [i["ref"] for role in main_p.get_recipe(recipe).get_settings().recipe_settings["outputs"].values()
                for i in role["items"]]
        if outs != [dataset]:
            problems.append("%s writes %s, expected [%s]" % (recipe, outs, dataset))
        others = set(readers(recipes, dataset)) - deleting
        if others:
            problems.append("%s is read by %s" % (dataset, sorted(others)))
        if dataset in exposed:
            problems.append("%s is exposed" % dataset)
        named = [sid for sid, blob in scenarios.items() if '"%s"' % dataset in blob
                 and not (sid == SCENARIO and (recipe, dataset) in RETIRED)]
        if named:
            problems.append("%s is named by scenario %s" % (dataset, named))
        if originals and (recipe, dataset) in ORIGINALS:
            names = {d["name"] for d in ev.list_datasets()}
            if dataset not in names or recipe not in {r["name"] for r in ev.list_recipes()}:
                problems.append("%s: no evidence copy" % dataset)
            elif next(ev.get_dataset(dataset).iter_rows(), None) is None:
                problems.append("%s: evidence copy has no stored rows" % dataset)
    return problems


def scenario_step(main_p):
    settings = main_p.get_scenario(SCENARIO).get_settings()
    raw = settings.get_raw()
    step = next(s for s in raw["params"]["steps"] if s["id"] == SCENARIO_STEP)
    return settings, step


def library_has(project: str, path: str) -> bool:
    r = subprocess.run(["dku", "library", "list", "--path", path.rsplit("/", 1)[0], "-P", project],
                       capture_output=True, text=True)
    return path in r.stdout.split()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the main project (default: dry run)")
    ap.add_argument("--originals", action="store_true", help="stage 2: delete the four moved originals")
    args = ap.parse_args()
    act = "APPLY" if args.apply else "DRY-RUN"
    c = client()
    main_p, ev = c.get_project(MAIN), c.get_project(EVIDENCE)
    pairs = RETIRED + (ORIGINALS if args.originals else [])

    problems = check(main_p, ev, pairs, args.originals)
    if problems:
        raise SystemExit("refused:\n  " + "\n  ".join(problems))

    have_recipes = {r["name"] for r in main_p.list_recipes()}
    have_datasets = {d["name"] for d in main_p.list_datasets()}
    have_scenarios = {s["id"] for s in main_p.list_scenarios()}
    retired_names = {d for _, d in RETIRED}
    settings, step = scenario_step(main_p)
    builds = step["params"]["builds"]
    keep = [b for b in builds if b.get("itemId") not in retired_names]
    print("%s %s step %s: %d -> %d builds (drop %s)" % (
        act, SCENARIO, SCENARIO_STEP, len(builds), len(keep),
        ", ".join(sorted(retired_names & {b.get("itemId") for b in builds})) or "nothing, done"))
    for recipe, dataset in pairs:
        print("%s delete recipe %-32s %s" % (act, recipe, "" if recipe in have_recipes else "(gone)"))
        print("%s delete dataset %-31s %s" % (act, dataset, "" if dataset in have_datasets else "(gone)"))
    print("%s delete scenario %s %s" % (act, RETIRED_SCENARIO, "" if RETIRED_SCENARIO in have_scenarios else "(gone)"))
    print("%s delete library folder %s %s" % (act, LIBRARY_FOLDER, "" if library_has(MAIN, LIBRARY_FOLDER) else "(gone)"))
    if not args.apply:
        print("\nDry run: nothing written. Checks passed.")
        return 0

    if len(keep) != len(builds):
        step["params"]["builds"] = keep
        settings.save()
    for recipe, dataset in pairs:
        if recipe in have_recipes:
            main_p.get_recipe(recipe).delete()
        if dataset in have_datasets:
            main_p.get_dataset(dataset).delete(drop_data=True)
    if RETIRED_SCENARIO in have_scenarios:
        main_p.get_scenario(RETIRED_SCENARIO).delete()
    if library_has(MAIN, LIBRARY_FOLDER):
        subprocess.run(["dku", "library", "delete-folder", LIBRARY_FOLDER, "-P", MAIN, "--yes",
                        "--confirm-name", LIBRARY_FOLDER], check=True, capture_output=True)

    # Read back.
    problems = []
    names = {d["name"] for d in main_p.list_datasets()}
    recs = {r["name"] for r in main_p.list_recipes()}
    problems += ["%s still exists" % x for r, d in pairs for x in (r, d) if x in names | recs]
    _, step = scenario_step(main_p)
    left = retired_names & {b.get("itemId") for b in step["params"]["builds"]}
    if left:
        problems.append("%s still builds %s" % (SCENARIO, sorted(left)))
    if RETIRED_SCENARIO in {s["id"] for s in main_p.list_scenarios()}:
        problems.append("%s still exists" % RETIRED_SCENARIO)
    if library_has(MAIN, LIBRARY_FOLDER):
        problems.append("%s still exists" % LIBRARY_FOLDER)
    print("\nread back: %s; %d recipes, %d datasets" % ("OK" if not problems else "; ".join(problems),
                                                        len(recs), len(names)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
