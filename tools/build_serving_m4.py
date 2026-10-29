"""Build the rebuilt serving chains beside the old ones (FLOW_MIGRATION_WORKPLAN.md M4, map §4.2).

DRY RUN BY DEFAULT: it reads the main project and prints every object it would create. Nothing is
written to DSS without --apply, which needs the user's approval at the time. It builds nothing: the
datasets are created empty, and the user runs the staged build it prints.

    uv run --project notebooks python tools/build_serving_m4.py            # dry run
    uv run --project notebooks python tools/build_serving_m4.py --apply    # write DEMO_TARGET_IDENTIFICATION

--apply writes only to DEMO_TARGET_IDENTIFICATION, each step skipped when already done:
  1. stores validation_set_personas_2 and persona2_scored_shap5 (clears `virtualizable`): the new
     shortlist chain reads them, and a recursive build could otherwise drop their files (M4
     decision 2, 2026-10-29);
  2. creates 9 managed Parquet datasets, each with the `_m4` suffix (decision 3), so the old chain
     keeps serving the webapp until M5;
  3. creates the 9 visual recipes below in S1 and S3, and reads everything back.

The shortlist (S1) replaces zone 40's seven-recipe chain with four: a window over S1's existing
scoring run gives the rank with ties (DEC-MEAS-005); a group counts each disease's pool; one join
adds the pool size and what `decorate_target_candidates`, `join_disease_name` and
`join_dashboard_annotations` added in turn; a prepare fills the drug flags and computes
`rank_percentile`. Only the 32 columns the webapp reads
are kept (map §2.1). No scoring run is added: the chain reads `persona2_scored_shap5`.

The per-disease AUC (S3) folds `validation_auc_by_disease`, `validation_auc_ci` and
`persona_enrichment`'s served fields into one prepare after a disease-name join. `module_size` is
`n_pos + n_neg` and `rank_enrichment` is `(hits_at_50 / 50) / (n_pos / module_size)`, as in
`compute_persona_candidates`. The per-family AUC reads `scored_champion` directly instead of the
297 MB sync copy, with the window trimmed as in the evidence project.

Zone 40 is not touched (decision 1): the panel definition keeps reading `validation_auc_ci` until
M6 repoints `compute_family_panel` to `validation_auc_by_disease_m4`'s successor.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_evidence_flow import eq, left, no_filter, renamed, vi  # noqa: E402
from setup_evidence_project import MAIN, client  # noqa: E402

CONNECTION = "dataiku-managed-storage"
FORMAT = "PARQUET_HIVE"
SUFFIX = "_m4"
ZONES = {"S1": "rRjk3Zy", "S3": "dvo4Ry3"}
STORE_INPUTS = ("validation_set_personas_2", "persona2_scored_shap5")

# The 13 champion inputs the candidate card places as percentiles (map §2.1).
FEATURES = ["dwpc_GBGD", "dwpc_GFGD", "dwpc_GGD", "dwpc_GPGD", "gene_n_pathways", "gene_ppi_degree",
            "ppi_adamic_adar", "ppi_common_neighbors_z", "ppi_evidence_depth", "ppi_jaccard",
            "ppi_multi_source_frac", "prox_closest", "shared_pathway_frac"]
# The 32 columns of dashboard_candidates the webapp reads (map §2.1), in the served order.
SERVED = (["gene_index", "disease_index"] + FEATURES
          + ["is_target", "anchor_name", "gene_name", "druggability_class", "ot_class_l1",
             "ot_sm_tractable", "ot_ab_tractable", "has_safety_liability", "safety_events",
             "safety_flag", "score", "rank_in_disease", "disease_name", "disease_pool_size",
             "rank_percentile", "approved_for_disease", "investigational_for_disease"])
WINDOW_KEEP = ["disease_index", "gene_index", "proba_1", "is_target", "anchor_name"] + FEATURES
FAMILY_KEEP = ["disease_family_id", "disease_index", "gene_index", "is_target", "proba_1"]

# The per-disease prepare runs today's two prepares' steps verbatim (validation_auc_by_disease's,
# then validation_auc_ci's), then the two fields persona_enrichment served.
AUC_EXTRA = [("module_size", "n_pos + n_neg"),
             ("rank_enrichment", "(hits_at_50 / 50) / (n_pos / (n_pos + n_neg))")]


def m4(name: str) -> str:
    return name + SUFFIX


def grel(column: str, expression: str) -> dict:
    return {"metaType": "PROCESSOR", "type": "CreateColumnWithGREL", "preview": False,
            "disabled": False, "alwaysShowComment": False,
            "params": {"column": column, "expression": expression}}


def run_all(steps: list[dict]) -> list[dict]:
    """Copied Prepare steps, set to run. A step saved with `preview: true` (left by the step preview
    in the DSS editor) ends the recipe there: the copied `recall_at_20` step carried it, so the
    merged prepare silently dropped the six steps after it (first build, 2026-10-29)."""
    out = copy.deepcopy(steps)
    for step in out:
        step["preview"] = False
        step["disabled"] = False
    return out


def window_payload(template: dict, keep: list[str], types: dict, partition: str,
                   overrides: dict) -> dict:
    """A rank-with-ties window (1, 2, 2, 4) retrieving only `keep`, ordered by proba_1 descending.
    It carries no count: ordered, DSS counts from the partition start to the current row, with frame
    limits off and equally with limits on and neither side limited (two builds, 2026-10-29), so
    map §6.1's one-window pool size does not hold."""
    w = copy.deepcopy(template)
    w.update({"retrievedColumnsSelectionMode": "EXPLICIT", "rank": True, "denseRank": False,
              "rowNumber": False, "cumeDist": False, "ntile": False, "computedColumns": [],
              "preFilter": no_filter(), "postFilter": no_filter(),
              "outputColumnNameOverrides": overrides})
    w["values"] = [{"column": c, "type": types[c], "value": True} for c in keep]
    w["windows"] = [dict(copy.deepcopy(template["windows"][0]), enablePartitioning=True,
                         partitioningColumns=[partition], enableOrdering=True,
                         orders=[{"column": "proba_1", "desc": True}], enableLimits=False)]
    return w


def plan(p) -> list[dict]:
    """Every recipe to create, in build order, from the main project's live definitions."""
    types = {c["name"]: c["type"] for c in p.get_dataset("scored_champion").get_schema()["columns"]}
    raw = lambda r: p.get_recipe(r).get_settings()  # noqa: E731
    finalize = raw("finalize_dashboard_candidates")
    prepare_params = copy.deepcopy(finalize.recipe_settings["params"])
    auc_steps = (raw("compute_validation_auc_by_disease").get_json_payload()["steps"]
                 + raw("compute_validation_auc_ci").get_json_payload()["steps"])
    assert [s["params"]["column"] for s in auc_steps] == [
        "auc_disease", "recall_at_20", "auc_se", "auc_lo95", "auc_hi95", "auc_trustworthy"], auc_steps
    auc_steps = run_all(auc_steps) + [grel(*s) for s in AUC_EXTRA]

    shortlist_window = window_payload(
        raw("rank_per_disease").get_json_payload(), WINDOW_KEEP, types, "disease_index",
        {"rank": "rank_in_disease"})
    family_window = window_payload(
        raw("window_family_rank").get_json_payload(), FAMILY_KEEP, types, "disease_family_id", {})

    candidate_cols = [c for c in WINDOW_KEEP if c != "proba_1"] + ["rank_in_disease", "score"]
    annotated = [c for c in SERVED if c != "rank_percentile"]
    # Today's finalize steps without the rename, which the window's output name now does.
    steps = finalize.get_json_payload()["steps"]
    assert [x["type"] for x in steps] == ["ColumnRenamer", "FillEmptyWithValue", "CreateColumnWithGREL"], steps
    finalize_payload = dict(copy.deepcopy(finalize.get_json_payload()), steps=run_all(steps[1:]))
    auc_payload = dict(copy.deepcopy(raw("compute_validation_auc_ci").get_json_payload()), steps=auc_steps)

    return [
        {"name": m4("compute_top_candidates"), "type": "window", "zone": "S1",
         "inputs": ["persona2_scored_shap5"], "output": m4("top_candidates"), "payload": shortlist_window},
        # The pool size: an ordered window counts only up to the current row, whatever its frame
        # flags, so a count over the ranked window came out running (2026-10-29). Today's
        # count_candidates_per_disease, on the scoring output instead of target_candidates_2.
        {"name": m4("compute_disease_pool_sizes"), "type": "grouping", "zone": "S1",
         "inputs": ["persona2_scored_shap5"], "output": m4("disease_pool_sizes"),
         "payload": raw("count_candidates_per_disease").get_json_payload()},
        {"name": m4("compute_validation_set_scored_named"), "type": "join", "zone": "S3",
         "inputs": ["validation_set_scored_grouped", "graph_nodes"], "output": m4("validation_set_scored_named"),
         "payload": {"virtualInputs": [
             vi(0, ["disease_index", "target_rank_sum", "n_pos", "n_neg", "hits_at_10", "hits_at_20",
                    "hits_at_50", "count"]),
             vi(1, ["disease"], [renamed("disease", "node_name")])],
             "joins": [left(1, eq("disease_index", 0, "node_index", 1))]}},
        {"name": m4("window_family_rank"), "type": "window", "zone": "S3",
         "inputs": ["scored_champion"], "output": m4("family_validation_ranked"), "payload": family_window},
        {"name": m4("compute_candidates_annotated"), "type": "join", "zone": "S1",
         "inputs": [m4("top_candidates"), "graph_nodes", "enriched_gene_druggability_v2",
                    "enriched_gene_safety_v2", "drug_evidence_pairs", m4("disease_pool_sizes")],
         "output": m4("candidates_annotated"),
         "payload": {"virtualInputs": [
             vi(0, candidate_cols, [{"mode": "GREL", "name": "score", "expr": "proba_1", "type": "double"}]),
             vi(1, ["gene_name"], [renamed("gene_name", "node_name")]),
             vi(1, ["disease_name"], [renamed("disease_name", "node_name")]),
             vi(2, ["druggability_class", "ot_class_l1", "ot_sm_tractable", "ot_ab_tractable"]),
             vi(3, ["has_safety_liability", "safety_events", "safety_flag"]),
             vi(4, ["approved_for_disease", "investigational_for_disease"]),
             vi(5, ["disease_pool_size"],
                [{"mode": "GREL", "name": "disease_pool_size", "expr": "gene_index_count", "type": "bigint"}])],
             "joins": [
                 left(1, eq("gene_index", 0, "node_index", 1)),
                 left(2, eq("disease_index", 0, "node_index", 2)),
                 left(3, eq("gene_index", 0, "gene_index", 3)),
                 left(4, eq("gene_index", 0, "gene_index", 4)),
                 left(5, eq("disease_index", 0, "disease_index", 5), eq("gene_index", 0, "gene_index", 5)),
                 left(6, eq("disease_index", 0, "disease_index", 6))],
             "order": annotated}},
        {"name": m4("compute_validation_auc_by_disease"), "type": "shaker", "zone": "S3",
         "inputs": [m4("validation_set_scored_named")], "output": m4("validation_auc_by_disease"),
         "payload": auc_payload, "meta": {"params": prepare_params}},
        {"name": m4("group_family_auc"), "type": "grouping", "zone": "S3",
         "inputs": [m4("family_validation_ranked")], "output": m4("family_auc_grouped"),
         "payload": raw("group_family_auc").get_json_payload()},
        {"name": m4("finalize_dashboard_candidates"), "type": "shaker", "zone": "S1",
         "inputs": [m4("candidates_annotated")], "output": m4("dashboard_candidates"),
         "payload": finalize_payload, "meta": {"params": prepare_params}},
        {"name": m4("compute_family_auc"), "type": "shaker", "zone": "S3",
         "inputs": [m4("family_auc_grouped")], "output": m4("family_auc_by_family"),
         "payload": dict(raw("compute_family_auc").get_json_payload(),
                         steps=run_all(raw("compute_family_auc").get_json_payload()["steps"])),
         "meta": {"params": copy.deepcopy(raw("compute_family_auc").recipe_settings["params"])}},
    ]


# Build stages: a non-recursive job with several targets runs them side by side (2026-10-28).
STAGES = [[m4("top_candidates"), m4("disease_pool_sizes"), m4("validation_set_scored_named"),
           m4("family_validation_ranked")],
          [m4("candidates_annotated"), m4("validation_auc_by_disease"), m4("family_auc_grouped")],
          [m4("dashboard_candidates"), m4("family_auc_by_family")]]


def shaker_schema(p, item) -> list[dict]:
    """A prepare's output schema without reading its (unbuilt) input: the input's columns plus each
    created column, typed as the live dataset that column comes from."""
    cols = list(p.get_dataset(item["inputs"][0]).get_schema()["columns"])
    have = {c["name"] for c in cols}
    live = {}
    for d in ("validation_auc_ci", "persona_enrichment", "dashboard_candidates", "family_auc_by_family"):
        for c in p.get_dataset(d).get_schema()["columns"]:
            live.setdefault(c["name"], c["type"])
    for step in item["payload"]["steps"]:
        col = step["params"].get("column")
        if step["type"] == "CreateColumnWithGREL" and col not in have:
            cols.append({"name": col, "type": live.get(col, "double")})
            have.add(col)
    return cols


def configure(p, item) -> None:
    recipe = p.get_recipe(item["name"])
    settings = recipe.get_settings()
    if inputs_of(p, item["name"]) != item["inputs"]:
        # An existing recipe whose design gained an input (the pool sizes, 2026-10-29). A join's
        # virtual inputs refer to these by position, so the order is the plan's.
        settings.recipe_settings["inputs"] = {"main": {"items": [{"ref": x, "deps": []} for x in item["inputs"]]}}
    payload = copy.deepcopy(item["payload"])
    if item["type"] == "join":
        order = payload.pop("order", None)
        selected = [{"name": col, "table": t} for t, v in enumerate(payload["virtualInputs"])
                    for col in v["selectedColumns"]]
        if order:
            rank = {c: i for i, c in enumerate(order)}
            selected.sort(key=lambda s: rank.get(s["name"], len(rank)))
        payload["selectedColumns"] = selected
        payload.pop("resolvedSelectedColumns", None)
        base = settings.get_json_payload()
        base.update(payload)
        payload = base
    settings.set_json_payload(payload)
    settings.recipe_settings.update(item.get("meta", {}))
    settings.save()
    if item["type"] == "shaker":
        p.get_dataset(item["output"]).set_schema({"columns": shaker_schema(p, item), "userModified": False})
    else:
        # Only when DSS asks for it: applying a schema update drops the output's files, even an
        # unchanged one, so an unconditional apply on a rerun emptied five built datasets
        # (2026-10-29).
        has_schema = bool(p.get_dataset(item["output"]).get_schema()["columns"])
        try:
            updates = recipe.compute_schema_updates()
        except Exception as exc:  # noqa: BLE001
            # DSS will not compute a schema from an input without files; a rerun keeps the one set.
            if has_schema and "non-ready input" in str(exc):
                return
            raise
        if updates.any_action_required() or not has_schema:
            updates.apply()


def create(p, item, have_datasets) -> None:
    if item["output"] not in have_datasets:
        p.new_managed_dataset(item["output"]).with_store_into(CONNECTION, format_option_id=FORMAT).create()
    creator = p.new_recipe(item["type"], item["name"])
    for x in item["inputs"]:
        creator.with_input(x)
    if item["type"] == "grouping":
        creator.with_group_key(item["payload"]["keys"][0]["column"])
    creator.with_existing_output(item["output"])
    if item["type"] == "shaker":
        # A normal Prepare creation reads the input's files, which an `_m4` input lacks until it is
        # built. Raw creation skips that read. Only for Prepare: a join created raw lost its input
        # list (first --apply, 2026-10-29: "Recipes inputs are incorrect. Input index: 0").
        creator.set_raw_mode()
        creator.creation_settings["rawPayload"] = json.dumps(item["payload"])
    creator.create()


def inputs_of(p, name) -> list[str]:
    rs = p.get_recipe(name).get_settings().recipe_settings
    return [i["ref"] for role in rs["inputs"].values() for i in role["items"]]


def store(p, name) -> None:
    settings = p.get_dataset(name).get_settings()
    raw = settings.get_raw()
    if raw.setdefault("flowOptions", {}).get("virtualizable") is not False:
        raw["flowOptions"]["virtualizable"] = False
        settings.save()


def read_back(p, items) -> list[str]:
    problems = []
    flow = p.get_flow()
    for item in items:
        try:
            rs = p.get_recipe(item["name"]).get_settings().recipe_settings
        except Exception as exc:  # noqa: BLE001
            problems.append("%s: missing (%s)" % (item["name"], exc))
            continue
        got = [i["ref"] for role in rs["inputs"].values() for i in role["items"]]
        if got != item["inputs"]:
            problems.append("%s: inputs %s, expected %s" % (item["name"], got, item["inputs"]))
        ds = p.get_dataset(item["output"])
        raw = ds.get_settings().get_raw()
        if raw.get("params", {}).get("connection") != CONNECTION or raw.get("formatType") != "parquet":
            problems.append("%s: not managed Parquet" % item["output"])
        if raw.get("flowOptions", {}).get("virtualizable") is not False:
            problems.append("%s: virtualizable" % item["output"])
        if flow.get_zone_of_object(ds).id != ZONES[item["zone"]]:
            problems.append("%s: not in zone %s" % (item["output"], item["zone"]))
        if not ds.get_schema()["columns"]:
            problems.append("%s: empty schema" % item["output"])
    cols = [c["name"] for c in p.get_dataset(m4("dashboard_candidates")).get_schema()["columns"]]
    if sorted(cols) != sorted(SERVED):
        problems.append("%s columns differ from the 32 served: %s" % (
            m4("dashboard_candidates"), sorted(set(cols) ^ set(SERVED))))
    for name in STORE_INPUTS:
        if p.get_dataset(name).get_settings().get_raw().get("flowOptions", {}).get("virtualizable") is not False:
            problems.append("%s: still virtualizable" % name)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the main project (default: dry run)")
    args = ap.parse_args()
    act = "APPLY" if args.apply else "DRY-RUN"
    p = client().get_project(MAIN)
    items = plan(p)
    have_recipes = {r["name"] for r in p.list_recipes()}
    have_datasets = {d["name"] for d in p.list_datasets()}
    for name in STORE_INPUTS:
        flag = p.get_dataset(name).get_settings().get_raw().get("flowOptions", {}).get("virtualizable")
        print("%s store   %-34s virtualizable=%s -> False" % (act, name, flag))
    for item in items:
        state = "new"
        if item["name"] in have_recipes:
            state = "exists" if inputs_of(p, item["name"]) else "REPAIR"
        print("%s %-2s %-40s %-8s %-6s -> %-34s [%s]" % (act, item["zone"], item["name"], item["type"],
                                                        state, item["output"], ", ".join(item["inputs"])))
    print("\n%d recipes, %d datasets; %d already present" % (
        len(items), len(items), len(have_recipes & {i["name"] for i in items})))
    print("\nbuild, in order, after --apply (non-recursive):")
    for n, stage in enumerate(STAGES, 1):
        print("  %d. %s" % (n, ", ".join(stage)))
    if not args.apply:
        print("\nDry run: nothing written.")
        return 0

    for name in STORE_INPUTS:
        store(p, name)
    m4_outputs = {i["output"] for i in items}
    flow = p.get_flow()
    zones = {key: flow.get_zone(zid) for key, zid in ZONES.items()}
    for item in items:
        if item["name"] in have_recipes and not inputs_of(p, item["name"]):
            # A recipe the raw-mode bug left without inputs: recreate it on its (empty) output.
            print("recreate %s (it has no inputs)" % item["name"])
            p.get_recipe(item["name"]).delete()
            have_recipes.discard(item["name"])
        if item["name"] not in have_recipes:
            if item["output"] in have_datasets and item["output"] not in m4_outputs:
                raise SystemExit("%s exists without its recipe; remove it or finish by hand" % item["output"])
            create(p, item, have_datasets)
        configure(p, item)
        store(p, item["output"])
        zones[item["zone"]].add_item(p.get_dataset(item["output"]))
        zones[item["zone"]].add_item(p.get_recipe(item["name"]))
    problems = read_back(p, items)
    print("\nread back: %s" % ("OK" if not problems else "\n  " + "\n  ".join(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
