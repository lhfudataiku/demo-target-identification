"""Retire the old serving chains in the main project (FLOW_MIGRATION_WORKPLAN.md M6).

DRY RUN BY DEFAULT: each stage reads DEMO_TARGET_IDENTIFICATION and prints what it would change.
Nothing is written without --apply, and each stage needs the user's approval at the time. No stage
builds anything; the user runs the builds it prints.

    uv run --project notebooks python tools/retire_serving_m6.py repoint [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py scenario [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py delete [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py rename [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py zones [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py refresh [--apply]
    uv run --project notebooks python tools/retire_serving_m6.py split-s3 [--apply]

Stages, in order:
  repoint  The two kept recipes that still read an old dataset read validation_auc_by_disease_m4
           instead, with today's columns selected by name so their outputs' schemas do not change:
           join_orthogonality (was validation_auc_by_disease) and compute_family_panel (was
           validation_auc_ci). A dataset delete in DSS also deletes the recipes reading it, so this
           runs before any delete. Then rebuild orthogonality_scatter and family_panel
           non-recursively and compare them with the saved copies.
  scenario Refresh_serving_layer stops naming the datasets `delete` removes, so no scenario names
           a deleted dataset. It stays inactive; stage E rewrites it around the final zones.
  delete   The 17 old recipes and their datasets (map §4.2), each reader before what it reads, so
           no delete cascades to a recipe outside the set. Refused when a dataset has a reader
           outside the set, is exposed, or is named by a scenario. Deleting drops the data.
  rename   The 9 `_m4` datasets and their recipes take their final names (mostly the old ones), so
           the backend's original names serve them. A rename keeps the data and every recipe link
           but not the build history, and the storage path stays at the `_m4` name (M4 rename
           test): never create a dataset under a vacated `_m4` name. The webapp reads the `_m4`
           names until `make deploy` restores the original names in webapp/backend/config.py, so
           deploy straight after. Then rebuild each renamed dataset non-recursively, so its build
           history, which keys the backend's cache, is truthful again.
  zones    Zone 20 splits in three along map §6.2, which has no cycle: gene annotation stays in 20
           (renamed), druggability and drug evidence move to a new 21, disease family and split key
           to a new 22. Each dataset moves with its producing recipe; nothing is built. Then every
           zone's short description is rewritten to say what it holds and, for S1-S4, which page
           it serves (map §6.3).
  refresh  Refresh_serving_layer rebuilds the serving zones (S2, S3, 40, S4, S1) one dependency
           level per step, worked out from the live recipe graph. Its old steps put dependent
           datasets in one non-recursive job, which runs them side by side. It stays inactive and
           is not run.
  split-s3 S3 holds five independent chains. The three audits (split audit, hub bias, disease
           eligibility) move with their recipes to a new zone, S5 Evidence · audits, so S3 keeps
           the per-disease and per-family reconstruction, whose per-disease AUC feeds zone 40.
           Moves only; the refresh levels do not change.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_evidence_project import MAIN, client  # noqa: E402

NEW_AUC = "validation_auc_by_disease_m4"
# recipe -> (old input, input position)
REPOINT = {"join_orthogonality": ("validation_auc_by_disease", 0),
           "compute_family_panel": ("validation_auc_ci", 0)}


# (recipe, dataset), every reader before what it reads.
RETIRED = [
    # zone 40: the old shortlist chain, from scoring to the served dataset
    ("finalize_dashboard_candidates", "dashboard_candidates"),
    ("join_dashboard_annotations", "candidates_annotated"),
    ("count_candidates_per_disease", "disease_pool_sizes"),
    ("join_disease_name", "target_candidates_2"),
    ("decorate_target_candidates", "top_annotated"),
    ("rank_per_disease", "top_candidates"),
    ("compute_top_shap_drivers_1", "persona2_scored_shap"),
    ("score_persona_candidates", "persona2_scored"),
    # S3: the persona chain, the old per-disease prepares and the old per-family chain
    ("compute_persona_enrichment", "persona_enrichment"),
    ("compute_persona_candidates", "persona_candidates"),
    ("compute_novel_discovery_eval", "novel_discovery_eval"),
    ("compute_validation_auc_ci", "validation_auc_ci"),
    ("compute_validation_auc_by_disease", "validation_auc_by_disease"),
    ("compute_family_auc", "family_auc_by_family"),
    ("group_family_auc", "family_auc_grouped"),
    ("window_family_rank", "family_validation_ranked"),
    ("compute_family_validation_scored", "family_validation_scored"),
]
SCENARIO = "Refresh_serving_layer"
# (`_m4` dataset, final name, its recipe, the recipe's final name)
RENAMES = [
    ("top_candidates_m4", "top_candidates", "compute_top_candidates_m4", "compute_top_candidates"),
    ("disease_pool_sizes_m4", "disease_pool_sizes", "compute_disease_pool_sizes_m4", "compute_disease_pool_sizes"),
    ("candidates_annotated_m4", "candidates_annotated", "compute_candidates_annotated_m4", "compute_candidates_annotated"),
    ("dashboard_candidates_m4", "dashboard_candidates", "finalize_dashboard_candidates_m4", "finalize_dashboard_candidates"),
    ("validation_set_scored_named_m4", "validation_set_scored_named",
     "compute_validation_set_scored_named_m4", "compute_validation_set_scored_named"),
    ("validation_auc_by_disease_m4", "validation_auc_by_disease",
     "compute_validation_auc_by_disease_m4", "compute_validation_auc_by_disease"),
    ("family_validation_ranked_m4", "family_validation_ranked", "window_family_rank_m4", "window_family_rank"),
    ("family_auc_grouped_m4", "family_auc_grouped", "group_family_auc_m4", "group_family_auc"),
    ("family_auc_by_family_m4", "family_auc_by_family", "compute_family_auc_m4", "compute_family_auc"),
]
ZONE_20 = "oL387nh"
SPLIT_20 = {  # new zone name -> datasets (map §6.2)
    "20 Gene annotation": ["gene_crosswalk", "enriched_gene_localization", "gene_safety_joined",
                           "enriched_gene_safety_v2"],
    "21 Druggability · drug evidence": ["ot_drug_mapped", "drug_joined", "drug_classified",
                                        "enriched_gene_druggability_v2", "drug_evidence_pairs"],
    "22 Disease family · split key": ["hetionet_disease_slim", "disease_family_id"],
}
# Zone short descriptions, keyed by zone name after the split (map §6.3). The 00-04 imports keep
# theirs, which still hold.
DESCRIPTIONS = {
    "10 Features - graph traversal (Cypher)":
        "Graph features computed as Cypher queries on the local Kuzu graph: path counts (DWPC), "
        "module size, centrality and proximity. Model inputs; the webapp does not show them.",
    "11 Features - matrix (Python)":
        "Graph features too heavy for a query, computed in Python: two DWPC metapaths, PPI evidence "
        "depth and z-scores, proximity and random-walk scores. Model inputs; not shown in the webapp.",
    "12 Features - assembly":
        "Joins every feature onto one row per gene-disease pair: the 21.6 million-row feature table "
        "that the split and the model read.",
    "20 Gene annotation":
        "Per-gene facts that are never model inputs: the gene crosswalk, subcellular localisation "
        "and safety liabilities.",
    "21 Druggability · drug evidence":
        "Which genes are druggable, and which gene-disease pairs already have an approved or "
        "investigational drug. Feeds the shortlist's badges and filters; never a model input.",
    "22 Disease family · split key":
        "Assigns each disease a family from its ontology anchor. The split keys on the family, so "
        "related diseases never straddle training and testing.",
    "30 Split & modelling table":
        "The split by disease family into training, validation and test sets, and the candidate "
        "pool the model scores.",
    "31 Train & score":
        "The champion model m7-f14 (saved model hJLGoYn4) and its scores for every candidate pair.",
    "40 Candidate ranking (shared by acts)":
        "The panel definition both pages share: which diseases and families the demo shows "
        "(family_panel, demo_panel_config), and the validation pairs of the shortlist diseases.",
    "S1 Shortlist":
        "Serves the shortlist page: each shortlist disease's whole candidate pool, ranked with ties, "
        "with each gene's drivers, drug records and identity. Read only by the webapp backend.",
    "S2 Evidence · graph":
        "Serves 'Why trust the list', section 1: what the model can see. Counts of the graph's "
        "nodes, relations, sources and evidence.",
    "S3 Evidence · reconstruction":
        "Serves 'Why trust the list', section 2: how well held-out targets are recovered, disease "
        "by disease and family by family. Its per-disease AUC also feeds the panel definition in 40.",
    "S5 Evidence · audits":
        "Serves 'Why trust the list', section 2: the checks on the result. Leakage across the "
        "split, bias toward well-connected genes, and which diseases are eligible at all.",
    "S4 Evidence · family panels":
        "Serves 'Why trust the list', section 3: per-subtype accuracy, overlap and shared "
        "programmes for the three demo families.",
}
SERVING_ZONES = ["S2 Evidence · graph", "S3 Evidence · reconstruction", "S5 Evidence · audits",
                 "40 Candidate ranking (shared by acts)", "S4 Evidence · family panels", "S1 Shortlist"]
S3_AUDITS = ("S5 Evidence · audits", ["split_audit_2", "hub_bias_meter", "disease_eligibility"])

REBUILD = [["top_candidates", "disease_pool_sizes", "validation_set_scored_named", "family_validation_ranked"],
           ["candidates_annotated", "validation_auc_by_disease", "family_auc_grouped"],
           ["dashboard_candidates", "family_auc_by_family"]]


def inputs_of(settings) -> list[str]:
    return [i["ref"] for role in settings.recipe_settings["inputs"].values() for i in role["items"]]


def repoint(p, apply: bool) -> list[str]:
    act = "APPLY" if apply else "DRY-RUN"
    new_cols = {c["name"] for c in p.get_dataset(NEW_AUC).get_schema()["columns"]}
    problems = []
    for name, (old, pos) in REPOINT.items():
        settings = p.get_recipe(name).get_settings()
        payload = settings.get_json_payload()
        ins = inputs_of(settings)
        if ins[pos] == NEW_AUC:
            print("%s %-22s already reads %s" % (act, name, NEW_AUC))
            continue
        if ins[pos] != old:
            problems.append("%s: input %d is %s, expected %s" % (name, pos, ins[pos], old))
            continue
        keep = [c["name"] for c in payload["selectedColumns"] if c["table"] == pos]
        missing = sorted(set(keep) - new_cols)
        if missing:
            problems.append("%s: %s lacks %s" % (name, NEW_AUC, missing))
            continue
        print("%s %-22s input %s -> %s, selecting its %d columns: %s" % (
            act, name, old, NEW_AUC, len(keep), ", ".join(keep)))
        if not apply:
            continue
        for role in settings.recipe_settings["inputs"].values():
            for item in role["items"]:
                if item["ref"] == old:
                    item["ref"] = NEW_AUC
        vi = next(v for v in payload["virtualInputs"] if v["index"] == pos)
        vi["outputColumnsSelectionMode"] = "MANUAL"
        vi["selectedColumns"] = keep
        payload.pop("resolvedSelectedColumns", None)
        settings.set_json_payload(payload)
        settings.save()
    if apply and not problems:
        for name, (old, pos) in REPOINT.items():
            settings = p.get_recipe(name).get_settings()
            if inputs_of(settings)[pos] != NEW_AUC:
                problems.append("%s: still reads %s" % (name, inputs_of(settings)[pos]))
            if p.get_recipe(name).compute_schema_updates().any_action_required():
                problems.append("%s: its output schema would change" % name)
    print("\nthen build, non-recursive: orthogonality_scatter, family_panel")
    return problems


def scenario(p, apply: bool) -> list[str]:
    act = "APPLY" if apply else "DRY-RUN"
    gone = {d for _, d in RETIRED}
    settings = p.get_scenario(SCENARIO).get_settings()
    raw = settings.get_raw()
    for step in raw["params"]["steps"]:
        builds = step.get("params", {}).get("builds")
        if builds is None:
            continue
        drop = [b["itemId"] for b in builds if b.get("itemId") in gone]
        print("%s %s step %-36s %2d -> %2d builds%s" % (act, SCENARIO, step["name"], len(builds),
              len(builds) - len(drop), (" (drop %s)" % ", ".join(drop)) if drop else ""))
        step["params"]["builds"] = [b for b in builds if b.get("itemId") not in gone]
    # A dataset-change trigger can watch a retired dataset too (two did, on an inactive scenario).
    triggers = raw.get("triggers", [])
    keep = [t for t in triggers
            if not (t.get("params", {}).get("watches")
                    and all(w.get("itemId") in gone for w in t["params"]["watches"]))]
    for t in triggers:
        if t not in keep:
            print("%s %s drop trigger %s on %s" % (act, SCENARIO, t.get("type"),
                  ", ".join(w["itemId"] for w in t["params"]["watches"])))
    raw["triggers"] = keep
    if apply:
        settings.save()
        left = [b["itemId"] for st in p.get_scenario(SCENARIO).get_settings().get_raw()["params"]["steps"]
                for b in st.get("params", {}).get("builds", []) if b.get("itemId") in gone]
        return ["%s still builds %s" % (SCENARIO, left)] if left else []
    return []


def delete(p, apply: bool) -> list[str]:
    import json
    act = "APPLY" if apply else "DRY-RUN"
    recipes = p.list_recipes()
    have_r = {r["name"] for r in recipes}
    have_d = {d["name"] for d in p.list_datasets()}
    deleting = {r for r, _ in RETIRED}
    exposed = {o["localName"] for o in p.get_settings().get_raw().get("exposedObjects", {}).get("objects", [])}
    scen = {sc["id"]: json.dumps(p.get_scenario(sc["id"]).get_settings().get_raw()) for sc in p.list_scenarios()}
    problems = []
    for recipe, dataset in RETIRED:
        if recipe in have_r:
            outs = [i["ref"] for role in p.get_recipe(recipe).get_settings().recipe_settings["outputs"].values()
                    for i in role["items"]]
            if outs != [dataset]:
                problems.append("%s writes %s, expected [%s]" % (recipe, outs, dataset))
        readers = {r["name"] for r in recipes
                   if any(i["ref"] == dataset for role in r.get("inputs", {}).values() for i in role.get("items", []))}
        if readers - deleting:
            problems.append("%s is read by %s" % (dataset, sorted(readers - deleting)))
        if dataset in exposed:
            problems.append("%s is exposed" % dataset)
        named = [sid for sid, blob in scen.items() if '"%s"' % dataset in blob]
        if named:
            problems.append("%s is named by scenario %s (run the scenario stage first)" % (dataset, named))
        print("%s delete %-36s %-6s and %-28s %s" % (act, recipe, "" if recipe in have_r else "(gone)",
              dataset, "" if dataset in have_d else "(gone)"))
    if problems or not apply:
        return problems
    for recipe, dataset in RETIRED:
        if recipe in have_r:
            p.get_recipe(recipe).delete()
        if dataset in have_d:
            p.get_dataset(dataset).delete(drop_data=True)
    names = {d["name"] for d in p.list_datasets()} | {r["name"] for r in p.list_recipes()}
    left = [x for pair in RETIRED for x in pair if x in names]
    print("\n%d recipes, %d datasets remain" % (len(p.list_recipes()), len(p.list_datasets())))
    return ["still present: %s" % left] if left else []


def rename(p, apply: bool) -> list[str]:
    import subprocess
    act = "APPLY" if apply else "DRY-RUN"
    have_d = {d["name"] for d in p.list_datasets()}
    have_r = {r["name"] for r in p.list_recipes()}
    problems = []
    for ds, final, rec, final_rec in RENAMES:
        for old, new, have, kind in ((ds, final, have_d, "dataset"), (rec, final_rec, have_r, "recipe")):
            if old in have and new in have:
                problems.append("%s %s: both %s and %s exist" % (kind, old, old, new))
            elif old not in have and new not in have:
                problems.append("%s %s: neither %s nor %s exists" % (kind, old, old, new))
            print("%s rename %-7s %-40s -> %s%s" % (act, kind, old, new, "" if old in have else "  (done)"))
    if problems or not apply:
        return problems
    for ds, final, rec, final_rec in RENAMES:
        if ds in have_d:
            subprocess.run(["dku", "dataset", "rename", ds, "--name", final, "-P", MAIN], check=True,
                           capture_output=True)
        if rec in have_r:
            subprocess.run(["dku", "recipe", "rename", rec, "--name", final_rec, "-P", MAIN], check=True,
                           capture_output=True)
    have_d = {d["name"] for d in p.list_datasets()}
    have_r = {r["name"] for r in p.list_recipes()}
    for ds, final, rec, final_rec in RENAMES:
        if final not in have_d or ds in have_d:
            problems.append("dataset %s not renamed to %s" % (ds, final))
        if final_rec not in have_r or rec in have_r:
            problems.append("recipe %s not renamed to %s" % (rec, final_rec))
        elif not problems:
            outs = [i["ref"] for role in p.get_recipe(final_rec).get_settings().recipe_settings["outputs"].values()
                    for i in role["items"]]
            if outs != [final]:
                problems.append("%s writes %s, expected [%s]" % (final_rec, outs, final))
    print("\nnow: make -C webapp deploy (config.py names the final datasets), then rebuild, non-recursive:")
    for n, stage in enumerate(REBUILD, 1):
        print("  %d. %s" % (n, ", ".join(stage)))
    return problems


def zones(p, apply: bool) -> list[str]:
    act = "APPLY" if apply else "DRY-RUN"
    flow = p.get_flow()
    by_name = {z.name: z for z in flow.list_zones()}
    producer = {}
    for r in p.list_recipes():
        for role in r.get("outputs", {}).values():
            for i in role.get("items", []):
                producer[i["ref"]] = r["name"]
    problems = []
    z20 = flow.get_zone(ZONE_20)
    in_20 = {i["objectId"] for i in z20.get_settings().get_raw().get("items", []) if i["objectType"] == "DATASET"}
    planned = {d for ds in SPLIT_20.values() for d in ds}
    first = next(iter(SPLIT_20))
    if z20.name != first:
        if in_20 != planned:
            problems.append("zone 20 holds %s, not the 11 of map §6.2" % sorted(in_20 ^ planned))
        print("%s rename zone %s %r -> %r" % (act, ZONE_20, z20.name, first))
    for name, datasets in SPLIT_20.items():
        here = by_name.get(name) or (z20 if name == first else None)
        state = "exists" if here is not None else "new"
        for d in datasets:
            zone_now = flow.get_zone_of_object(p.get_dataset(d)).name
            if zone_now != name:
                print("%s move %-30s + %-38s %s -> %s (%s)" % (act, d, producer.get(d), zone_now, name, state))
    for name, text in DESCRIPTIONS.items():
        print("%s describe %-38s %s" % (act, name, text[:70] + "..."))
    if problems or not apply:
        return problems
    if z20.name != first:
        settings = z20.get_settings()
        settings.name = first
        settings.save()
    by_name = {z.name: z for z in flow.list_zones()}
    for name, datasets in SPLIT_20.items():
        zone = by_name.get(name) or flow.create_zone(name)
        for d in datasets:
            zone.add_item(p.get_dataset(d))
            zone.add_item(p.get_recipe(producer[d]))
    by_name = {z.name: z for z in flow.list_zones()}
    for name, text in DESCRIPTIONS.items():
        if name not in by_name:
            problems.append("no zone named %r" % name)
            continue
        settings = by_name[name].get_settings()
        settings.get_raw()["shortDesc"] = text
        settings.save()
    for name, datasets in SPLIT_20.items():
        for d in datasets:
            for obj in (p.get_dataset(d), p.get_recipe(producer[d])):
                if flow.get_zone_of_object(obj).name != name:
                    problems.append("%s is not in %s" % (d, name))
    for name, text in DESCRIPTIONS.items():
        if name in by_name and by_name[name].get_settings().get_raw().get("shortDesc") != text:
            problems.append("%s: description not saved" % name)
    return problems


def refresh_levels(p) -> list[list[str]]:
    """The serving zones' datasets in dependency levels: a dataset sits one level after the
    deepest serving dataset its recipe reads."""
    flow = p.get_flow()
    by_name = {z.name: z for z in flow.list_zones()}
    serving = []
    for name in SERVING_ZONES:
        if name in by_name:
            serving += [i["objectId"] for i in by_name[name].get_settings().get_raw().get("items", [])
                        if i["objectType"] == "DATASET"]
    inputs = {}
    for r in p.list_recipes():
        outs = [i["ref"] for role in r.get("outputs", {}).values() for i in role.get("items", [])]
        ins = [i["ref"] for role in r.get("inputs", {}).values() for i in role.get("items", [])]
        for o in outs:
            inputs[o] = ins
    level = {}

    def depth(d, seen=()):
        if d in level:
            return level[d]
        if d in seen:
            raise SystemExit("cycle at %s" % d)
        up = [depth(x, seen + (d,)) for x in inputs.get(d, []) if x in serving]
        level[d] = 1 + max(up, default=-1)
        return level[d]

    built = [d for d in serving if d in inputs]
    for d in built:
        depth(d)
    return [sorted(d for d in built if level[d] == n) for n in range(max(level.values()) + 1)]


def refresh(p, apply: bool) -> list[str]:
    import copy
    act = "APPLY" if apply else "DRY-RUN"
    levels = refresh_levels(p)
    settings = p.get_scenario(SCENARIO).get_settings()
    raw = settings.get_raw()
    template = copy.deepcopy(raw["params"]["steps"][0])
    steps = []
    for n, datasets in enumerate(levels, 1):
        step = copy.deepcopy(template)
        step["id"] = "build_serving_level_%d" % n
        step["name"] = "Level %d" % n
        step["params"].update(jobType="NON_RECURSIVE_FORCED_BUILD",
                              builds=[{"type": "DATASET", "itemId": d} for d in datasets])
        steps.append(step)
        print("%s %s step %-8s %s" % (act, SCENARIO, step["name"], ", ".join(datasets)))
    print("%s %s keeps its %d triggers and stays inactive (active=%s)" % (
        act, SCENARIO, len(raw.get("triggers", [])), raw.get("active")))
    if not apply:
        return []
    raw["params"]["steps"] = steps
    settings.save()
    got = [[b["itemId"] for b in st["params"]["builds"]]
           for st in p.get_scenario(SCENARIO).get_settings().get_raw()["params"]["steps"]]
    return [] if got == levels else ["%s steps did not save as planned" % SCENARIO]


def split_s3(p, apply: bool) -> list[str]:
    act = "APPLY" if apply else "DRY-RUN"
    flow = p.get_flow()
    name, datasets = S3_AUDITS
    producer = {}
    for r in p.list_recipes():
        for role in r.get("outputs", {}).values():
            for i in role.get("items", []):
                producer[i["ref"]] = r["name"]
    by_name = {z.name: z for z in flow.list_zones()}
    problems = []
    for d in datasets:
        now = flow.get_zone_of_object(p.get_dataset(d)).name
        if now not in (name, "S3 Evidence · reconstruction"):
            problems.append("%s is in %s, not S3" % (d, now))
        print("%s move %-22s + %-30s %s -> %s%s" % (act, d, producer[d], now, name,
              "" if name in by_name else " (new)"))
    for zname in ("S3 Evidence · reconstruction", name):
        print("%s describe %-30s %s" % (act, zname, DESCRIPTIONS[zname]))
    if problems or not apply:
        return problems
    zone = by_name.get(name) or flow.create_zone(name)
    for d in datasets:
        zone.add_item(p.get_dataset(d))
        zone.add_item(p.get_recipe(producer[d]))
    by_name = {z.name: z for z in flow.list_zones()}
    for zname in ("S3 Evidence · reconstruction", name):
        settings = by_name[zname].get_settings()
        settings.get_raw()["shortDesc"] = DESCRIPTIONS[zname]
        settings.save()
    for d in datasets:
        for obj in (p.get_dataset(d), p.get_recipe(producer[d])):
            if flow.get_zone_of_object(obj).name != name:
                problems.append("%s is not in %s" % (d, name))
    if [x for lv in refresh_levels(p) for x in lv].__len__() != 33:
        problems.append("the serving zones no longer hold 33 built datasets")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("stage", choices=["repoint", "scenario", "delete", "rename", "zones", "refresh", "split-s3"])
    ap.add_argument("--apply", action="store_true", help="write the main project (default: dry run)")
    args = ap.parse_args()
    p = client().get_project(MAIN)
    problems = {"repoint": repoint, "scenario": scenario, "delete": delete, "rename": rename,
                "zones": zones, "refresh": refresh, "split-s3": split_s3}[args.stage](p, args.apply)
    if problems:
        print("\nPROBLEMS:\n  " + "\n  ".join(problems))
        return 1
    print("\n%s" % ("read back: OK" if args.apply else "Dry run: nothing written."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
