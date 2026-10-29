"""Create the evidence project's recipes and datasets (EVIDENCE_PROJECT_DESIGN.md §3, workplan M2).

DRY RUN BY DEFAULT: it reads both projects and prints every object it would create. Nothing is
written to DSS without --apply or --main-identity, and each needs the user's approval at the time.
Neither builds anything: the datasets are created empty, and the user runs the build.

    uv run --project notebooks python tools/build_evidence_flow.py                    # dry run
    uv run --project notebooks python tools/build_evidence_flow.py --code-out DIR     # + write the
                                                                                      #   rewritten code
    uv run --project notebooks python tools/build_evidence_flow.py --apply            # evidence only
    uv run --project notebooks python tools/build_evidence_flow.py --main-identity    # main only

--apply writes only to DEMO_TI_EVIDENCE, each step skipped when already done:
  1. writes /python/demo_identity.py from dss_lib/ (graph_nodes read by its qualified name);
  2. creates four zones, E1-E4;
  3. creates each output as a managed Parquet dataset on dataiku-managed-storage, with the main
     project's schema for a copy, and never virtualizable (store_output());
  4. recreates the 21 copied or moved recipes from the main project's live definitions, with the
     input changes the design names, and adds the 4 recipes of the slim shortlist (§3.4);
  5. reads everything back and reports any mismatch.

Copies are recreated because DSS cannot copy a recipe into another project from the API.

A Python recipe reads an input from another project only by its qualified name: the dataiku client
matches `dataiku.Dataset(name)` against the recipe's declared inputs, and a foreign input is declared
as `DEMO_TARGET_IDENTIFICATION.<name>`. So each copy's code is rewritten from the main project's
live code (`rewrite()`): upstream names are qualified, and the two input changes are applied. A
qualified name with the main project's key also resolves in the main project itself, so the shared
identity recipes and the library can stay identical across the two projects.

--main-identity brings the main project into line, without building:
  - writes the same /python/demo_identity.py to the main project's library;
  - sets the code of compute_split_audit_2 and compute_demo_panel_config to the rewritten code;
  - removes persona_enrichment from compute_demo_panel_config's inputs (M0: the names come from
    graph_nodes, which equals persona_enrichment on all 670 family_panel diseases).
Run `python3 tools/build_recipe_index.py --refresh` afterwards, so dss_recipes/ mirrors it.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_evidence_project import (EVIDENCE, EXPOSED, LIBRARY_FILE, LIBRARY_SOURCE, MAIN,  # noqa: E402
                                    client, dku_library_read)

import subprocess  # noqa: E402

CONNECTION = "dataiku-managed-storage"
FORMAT = "PARQUET_HIVE"
UPSTREAM = set(EXPOSED)

ZONES = {
    "E1": "E1 Reconstruction",
    "E2": "E2 Panels",
    "E3": "E3 Shortlist evidence",
    "E4": "E4 Drug truth and breast panel",
}

# (recipe, zone, input changes {old: new or None to drop}), in build order. Design §3.2, §3.3, §3.5.
COPIES = [
    ("compute_validation_set_scored_windows", "E1", {}),
    ("compute_validation_set_scored_grouped", "E1", {}),
    ("compute_validation_auc_by_disease", "E1", {}),
    ("compute_validation_auc_ci", "E1", {}),
    ("window_family_rank", "E1", {"family_validation_scored": "scored_champion"}),
    ("group_family_auc", "E1", {}),
    ("compute_family_auc", "E1", {}),
    ("compute_split_audit_2", "E1", {}),
    ("compute_drug_target_benchmark", "E1", {}),
    ("compute_novel_discovery_eval", "E1", {}),
    ("compute_persona_candidates", "E1", {}),
    ("compute_persona_enrichment", "E1", {}),
    ("compute_family_panel", "E2", {}),
    ("compute_demo_panel_config", "E2", {"persona_enrichment": None}),
    ("compute_family_panel_top50", "E2", {}),
    ("compute_family_panel_overlap", "E2", {}),
    ("compute_family_panel_programme", "E2", {}),
    ("compute_known_drug_truth", "E4", {}),
    ("compute_pool_reachability", "E4", {}),
    ("compute_filter_three_axes", "E4", {"target_candidates_2": "dashboard_candidates"}),
    ("compute_breast_panel", "E4", {}),
]
# Built before compute_filter_three_axes, which reads dashboard_candidates.
FIRST_AFTER_SHORTLIST = "compute_known_drug_truth"

# The identity recipes that exist in both projects (DEC-OPS-006 note); --main-identity aligns them.
SHARED_IDENTITY = ("compute_split_audit_2", "compute_demo_panel_config")

# The window column trims (M0, design §3.2): each window keeps its partition key and the columns
# its group aggregates (gene_index, is_target, rank) plus proba_1 to order by; the main copies keep
# all 45 columns of scored_champion. group_family_auc reads disease_index too.
WINDOW_TRIMS = {
    "compute_validation_set_scored_windows": ["disease_index", "gene_index", "is_target", "proba_1"],
    "window_family_rank": ["disease_family_id", "disease_index", "gene_index", "is_target", "proba_1"],
}
# The per-disease group lists every input column as an inactive value; those must exist after the trim.
TRIMMED_GROUPS = {"compute_validation_set_scored_grouped": "compute_validation_set_scored_windows"}

# The columns nb6 and nb7 read, plus those compute_filter_three_axes reads (design §2.1, §3.4).
SHORTLIST_COLUMNS = {"disease_index", "gene_index", "disease_name", "gene_name", "rank_in_disease",
                     "is_target", "has_safety_liability", "approved_for_disease", "ot_sm_tractable",
                     "ot_ab_tractable", "druggability_class", "safety_flag"}

OLD_NAMES = 'names = dataiku.Dataset("persona_enrichment").get_dataframe()[["disease_index", "disease"]]\n'
NEW_NAMES = '''\
# Disease names come from graph_nodes, the panel's own name source (M0, 2026-10-28). They equal
# persona_enrichment's on all 670 family_panel diseases, and reading them here drops the panel's
# dependency on the persona chain.
names = (dataiku.Dataset("graph_nodes")
         .get_dataframe(columns=["node_index", "node_name", "node_type"])
         .query("node_type == 'disease'")
         .rename(columns={"node_index": "disease_index", "node_name": "disease"})
         [["disease_index", "disease"]])
'''


def rewrite(name: str, code: str, changes: dict, inputs: list[str]) -> str:
    """The evidence copy of a Python recipe's code. Idempotent, so it also applies to rewritten code.

    Only the recipe's own upstream inputs are qualified: `disease_family_id` is a dataset and also a
    column, and qualifying every upstream name rewrote it as a column in three recipes.
    """
    for old, new in changes.items():
        if new is not None:
            code = code.replace('"%s"' % old, '"%s"' % new)
    if name == "compute_demo_panel_config" and OLD_NAMES in code:
        code = code.replace(OLD_NAMES, NEW_NAMES)
    for x in sorted(UPSTREAM & set(inputs)):
        code = code.replace('"%s"' % x, '"%s.%s"' % (MAIN, x))
    return code


def evidence_inputs(main_inputs: list[str], changes: dict) -> list[str]:
    """The copy's inputs, in the main recipe's order: a join's virtual inputs refer to them by index."""
    out = []
    for x in main_inputs:
        x = changes.get(x, x)
        if x is not None:
            out.append(x)
    return out


def ref(x: str) -> tuple[str, str | None]:
    return (x, MAIN) if x in UPSTREAM else (x, None)


def check_code(name: str, code: str, inputs: list[str], problems: list) -> None:
    """Every declared input is read by the name the evidence project resolves; no bare upstream read."""
    for x in inputs:
        want = '"%s.%s"' % (MAIN, x) if x in UPSTREAM else '"%s"' % x
        via_library = x == "graph_nodes" and "import demo_identity" in code
        if want not in code and not via_library:
            problems.append("%s: input %s is never read as %s" % (name, x, want))
    for x in UPSTREAM & set(inputs):
        if '"%s"' % x in code:
            problems.append("%s: bare read of upstream %s" % (name, x))


def eq(c1: str, t1: int, c2: str, t2: int) -> dict:
    return {"column1": {"name": c1, "table": t1}, "column2": {"name": c2, "table": t2}, "type": "EQ"}


def no_filter() -> dict:
    return {"enabled": False, "distinct": False}


def grel_filter(expression: str) -> dict:
    """The CUSTOM-mode filter the DSS UI saves; DSS ignores `expression` in any other mode."""
    return {"enabled": True, "distinct": False, "expression": expression,
            "uiData": {"mode": "CUSTOM", "$latestOperator": "&&", "$filterOptions": "CUSTOM",
                       "conditions": []}}


def vi(index: int, columns: list[str], computed: list[dict] | None = None, pre=None) -> dict:
    return {"index": index, "outputColumnsSelectionMode": "MANUAL", "selectedColumns": columns,
            "computedColumns": computed or [], "preFilter": pre or no_filter()}


def renamed(column: str, expr: str) -> dict:
    return {"mode": "GREL", "name": column, "expr": expr, "type": "string"}


def left(t2: int, *on: dict) -> dict:
    return {"table1": 0, "table2": t2, "type": "LEFT", "conditionsMode": "AND", "on": list(on)}


def shortlist_recipes(window_template: dict, prepare_template: dict, prepare_params: dict) -> list[dict]:
    """Design §3.4: the 12 shortlist diseases ranked with ties (DEC-MEAS-005), then decorated."""
    window = copy.deepcopy(window_template)
    window.update({"values": [], "retrievedColumnsSelectionMode": "ALL", "rank": True,
                   "denseRank": False, "rowNumber": False, "cumeDist": False, "ntile": False,
                   "computedColumns": [], "preFilter": no_filter(), "postFilter": no_filter(),
                   "outputColumnNameOverrides": {"rank": "rank_in_disease"}})
    window["windows"][0].update({"enablePartitioning": True, "partitioningColumns": ["disease_index"],
                                 "enableOrdering": True,
                                 "orders": [{"column": "proba_1", "desc": True}],
                                 "enableLimits": False})
    return [
        {"name": "compute_shortlist_scored", "type": "join", "output": "shortlist_scored",
         "inputs": ["scored_champion", "demo_panel_config"],
         "payload": {
             "virtualInputs": [
                 vi(0, ["disease_index", "gene_index", "proba_1", "is_target"]),
                 vi(1, [], pre=grel_filter('toString(in_act4) == "true"'))],
             "joins": [{"table1": 0, "table2": 1, "type": "INNER", "conditionsMode": "AND",
                        "on": [eq("disease_index", 0, "disease_index", 1)]}]}},
        {"name": "compute_shortlist_ranked", "type": "window", "output": "shortlist_ranked",
         "inputs": ["shortlist_scored"], "payload": window},
        {"name": "compute_shortlist_joined", "type": "join", "output": "shortlist_joined",
         "inputs": ["shortlist_ranked", "graph_nodes", "enriched_gene_druggability_v2",
                    "enriched_gene_safety_v2", "drug_evidence_pairs"],
         "payload": {
             "virtualInputs": [
                 vi(0, ["disease_index", "gene_index", "proba_1", "is_target", "rank_in_disease"]),
                 vi(1, ["gene_name"], [renamed("gene_name", "node_name")]),
                 vi(1, ["disease_name"], [renamed("disease_name", "node_name")]),
                 vi(2, ["druggability_class", "ot_sm_tractable", "ot_ab_tractable"]),
                 vi(3, ["has_safety_liability", "safety_flag"]),
                 vi(4, ["approved_for_disease"])],
             "joins": [
                 left(1, eq("gene_index", 0, "node_index", 1)),
                 left(2, eq("disease_index", 0, "node_index", 2)),
                 left(3, eq("gene_index", 0, "gene_index", 3)),
                 left(4, eq("gene_index", 0, "gene_index", 4)),
                 left(5, eq("disease_index", 0, "disease_index", 5),
                      eq("gene_index", 0, "gene_index", 5))]}},
        # A pair with no drug evidence is 0 in the served table, not empty. has_safety_liability
        # stays empty for the 193 pairs whose gene has no safety row, as it does there.
        {"name": "compute_dashboard_candidates", "type": "shaker", "output": "dashboard_candidates",
         "inputs": ["shortlist_joined"],
         # Raw creation leaves the recipe's params null, and the job then fails reading their
         # engineType. Take the copied Prepare recipes' params, minus their per-input repartition.
         "meta": {"params": prepare_params},
         "payload": dict(copy.deepcopy(prepare_template), steps=[
             {"metaType": "PROCESSOR", "type": "FillEmptyWithValue",
              "params": {"appliesTo": "SINGLE_COLUMN", "columns": ["approved_for_disease"],
                         "value": "0"}}])},
    ]


def trim_window(payload: dict, keep: list[str], types: dict) -> dict:
    """Retrieve only `keep`: in EXPLICIT mode a window outputs the values marked `value`."""
    payload = copy.deepcopy(payload)
    payload["retrievedColumnsSelectionMode"] = "EXPLICIT"
    payload["values"] = [{"column": col, "type": types[col], "value": True} for col in keep]
    payload["postFilter"] = no_filter()
    return payload


def trim_group(payload: dict, keep: list[str]) -> dict:
    """Drop the inactive value entries of columns the trimmed window no longer outputs."""
    payload = copy.deepcopy(payload)
    payload["values"] = [v for v in payload["values"] if "customExpr" in v or v["column"] in keep]
    payload["postFilter"] = no_filter()
    return payload


def plan(main_p) -> list[dict]:
    """Every recipe to create, in build order, read from the main project's live definitions."""
    items = []
    window_template = prepare_template = prepare_params = None
    types = {c["name"]: c["type"] for c in main_p.get_dataset("scored_champion").get_schema()["columns"]}
    for name, zone, changes in COPIES:
        if name == FIRST_AFTER_SHORTLIST:
            for s in shortlist_recipes(window_template, prepare_template, prepare_params):
                items.append(dict(s, zone="E3", copy=False))
        src = main_p.get_recipe(name).get_settings()
        raw = src.recipe_settings
        main_inputs = [i["ref"] for role in raw["inputs"].values() for i in role["items"]]
        outputs = [i["ref"] for role in raw["outputs"].values() for i in role["items"]]
        assert len(outputs) == 1, (name, outputs)
        item = {"name": name, "type": raw["type"], "zone": zone, "copy": True, "output": outputs[0],
                "inputs": evidence_inputs(main_inputs, changes), "meta": {k: copy.deepcopy(raw[k]) for k in ("params", "shortDesc", "description", "tags")
                         if k in raw}}
        if raw["type"] == "python":
            item["code"] = rewrite(name, src.get_code(), changes, item["inputs"])
        else:
            item["payload"] = src.get_json_payload()
            if name == "compute_validation_set_scored_windows":
                window_template = copy.deepcopy(item["payload"])
            if name == "compute_validation_auc_by_disease":
                prepare_template = copy.deepcopy(item["payload"])
                prepare_params = copy.deepcopy(raw["params"])
                prepare_params["engineParams"]["spark"]["readParams"]["map"] = {}
            if name in WINDOW_TRIMS:
                item["payload"] = trim_window(item["payload"], WINDOW_TRIMS[name], types)
            if name in TRIMMED_GROUPS:
                item["payload"] = trim_group(item["payload"], WINDOW_TRIMS[TRIMMED_GROUPS[name]] + ["rank"])
        missing = [x for x in changes if changes[x] is not None and x not in main_inputs]
        assert not missing, (name, missing)
        items.append(item)
    return items


def create_output(ev, main_p, item) -> None:
    out = item["output"]
    ev.new_managed_dataset(out).with_store_into(CONNECTION, format_option_id=FORMAT).create()
    if item["copy"]:
        ev.get_dataset(out).set_schema(main_p.get_dataset(out).get_schema())


def store_output(ev, out) -> None:
    """Clear the virtualizable flag. This instance sets it on every new dataset, so a recursive
    build passed the shortlist chain in memory and wrote no files; the next build then found
    shortlist_scored built but unreadable ("Root path of the dataset does not exist", 2026-10-28).
    An evidence output is read by notebooks and comparisons, so it must be on disk."""
    settings = ev.get_dataset(out).get_settings()
    raw = settings.get_raw()
    if raw.setdefault("flowOptions", {}).get("virtualizable") is not False:
        raw["flowOptions"]["virtualizable"] = False
        settings.save()


def create_recipe(ev, item):
    creator = ev.new_recipe(item["type"], item["name"])
    for x in item["inputs"]:
        name, project = ref(x)
        creator.with_input(name, project_key=project)
    if item["type"] == "python":
        creator.with_output(item["output"])
        creator.with_script(item["code"])
    else:
        if item["type"] == "grouping":
            creator.with_group_key(item["payload"]["keys"][0]["column"])
        creator.with_existing_output(item["output"])
    if item["type"] == "shaker":
        # A normal Prepare creation reads the input's files, and an evidence input has none until
        # the first build ("Root path of the dataset does not exist"). Raw creation skips that
        # read and takes the payload as given.
        creator.set_raw_mode()
        creator.creation_settings["rawPayload"] = json.dumps(item["payload"])
    return configure(ev, creator.create(), item)


def configure(ev, recipe, item):
    """Set a recipe's code or payload and its output schema. Re-run on every --apply for the new
    recipes, so a corrected payload reaches a recipe that already exists."""
    settings = recipe.get_settings()
    if item["type"] == "python":
        settings.set_code(item["code"])
    else:
        payload = settings.get_json_payload() if not item["copy"] else {}
        payload.update(copy.deepcopy(item["payload"]))
        if item["type"] == "join" and not item["copy"]:
            # DSS writes the join's output from the top-level list, not from each virtual input's
            # selection: left as generated at creation, it kept every column of input 0 and none
            # of the computed names (first --apply, 2026-10-28).
            payload["selectedColumns"] = [{"name": col, "table": t}
                                          for t, v in enumerate(payload["virtualInputs"])
                                          for col in v["selectedColumns"]]
            payload.pop("resolvedSelectedColumns", None)
        settings.set_json_payload(payload)
    settings.recipe_settings.update(item.get("meta", {}))
    settings.save()
    if item["type"] == "shaker" and not item["copy"]:
        # Filling empty cells keeps the columns, so the output schema is the input's.
        ev.get_dataset(item["output"]).set_schema(ev.get_dataset(item["inputs"][0]).get_schema())
    elif not item["copy"] or item["name"] in WINDOW_TRIMS:
        # Applied unconditionally: narrowing an existing output is not an "action required".
        recipe.compute_schema_updates().apply()
    return recipe


def trimmed(item) -> bool:
    return item["name"] in WINDOW_TRIMS or item["name"] in TRIMMED_GROUPS


def zone_by_name(ev):
    flow = ev.get_flow()
    have = {z.name: z for z in flow.list_zones()}
    return {key: have.get(label) or flow.create_zone(label) for key, label in ZONES.items()}


def read_back(ev, items) -> list[str]:
    problems = []
    flow = ev.get_flow()
    for item in items:
        name, out = item["name"], item["output"]
        try:
            raw = ev.get_recipe(name).get_settings().recipe_settings
        except Exception as exc:  # noqa: BLE001
            problems.append("%s: missing (%s)" % (name, exc))
            continue
        got = [i["ref"] for role in raw["inputs"].values() for i in role["items"]]
        want = ["%s.%s" % (MAIN, x) if x in UPSTREAM else x for x in item["inputs"]]
        if got != want:
            problems.append("%s: inputs %s, expected %s" % (name, got, want))
        if item["type"] == "python":
            check_code(name, ev.get_recipe(name).get_settings().get_code(), item["inputs"], problems)
        ds = ev.get_dataset(out).get_settings().get_raw()
        if ds.get("params", {}).get("connection") != CONNECTION or ds.get("formatType") != "parquet":
            problems.append("%s: stored as %s/%s" % (out, ds.get("params", {}).get("connection"),
                                                     ds.get("formatType")))
        zone = flow.get_zone_of_object(ev.get_dataset(out))
        if zone.name != ZONES[item["zone"]]:
            problems.append("%s: in zone %r, expected %r" % (out, zone.name, ZONES[item["zone"]]))
        if ds.get("flowOptions", {}).get("virtualizable") is not False:
            problems.append("%s: virtualizable" % out)
        columns = [c["name"] for c in ev.get_dataset(out).get_schema()["columns"]]
        if not columns:
            problems.append("%s: empty schema" % out)
        if name in WINDOW_TRIMS and sorted(columns) != sorted(WINDOW_TRIMS[name] + ["rank"]):
            problems.append("%s: columns %s, expected the trim" % (out, columns))
    cols = {c["name"] for c in ev.get_dataset("dashboard_candidates").get_schema()["columns"]}
    if SHORTLIST_COLUMNS - cols:
        problems.append("dashboard_candidates lacks %s" % sorted(SHORTLIST_COLUMNS - cols))
    if (dku_library_read(EVIDENCE) or "").rstrip("\n") != LIBRARY_SOURCE.read_text().rstrip("\n"):
        problems.append("evidence library differs from %s" % LIBRARY_SOURCE)
    return problems


def write_library(project: str) -> None:
    subprocess.run(["dku", "library", "write", LIBRARY_FILE, "-c", "@" + str(LIBRARY_SOURCE),
                    "-P", project], check=True, capture_output=True)


def main_identity(main_p, items, apply: bool) -> int:
    act = "APPLY" if apply else "DRY-RUN"
    print("%s main  library %s from %s" % (act, LIBRARY_FILE, LIBRARY_SOURCE.relative_to(LIBRARY_SOURCE.parents[1])))
    by_name = {i["name"]: i for i in items}
    for name in SHARED_IDENTITY:
        print("%s main  %s: code := the evidence copy's" % (act, name))
    print("%s main  compute_demo_panel_config: drop input persona_enrichment" % act)
    if not apply:
        return 0
    write_library(MAIN)
    for name in SHARED_IDENTITY:
        settings = main_p.get_recipe(name).get_settings()
        settings.set_code(by_name[name]["code"])
        if name == "compute_demo_panel_config":
            for role in settings.recipe_settings["inputs"].values():
                role["items"] = [i for i in role["items"] if i["ref"] != "persona_enrichment"]
        settings.save()
    problems = []
    if (dku_library_read(MAIN) or "").rstrip("\n") != LIBRARY_SOURCE.read_text().rstrip("\n"):
        problems.append("main library differs")
    for name in SHARED_IDENTITY:
        raw = main_p.get_recipe(name).get_settings()
        if raw.get_code() != by_name[name]["code"]:
            problems.append("%s: main code differs" % name)
        refs = [i["ref"] for role in raw.recipe_settings["inputs"].values() for i in role["items"]]
        if "persona_enrichment" in refs:
            problems.append("%s: still reads persona_enrichment" % name)
    print("\nread back (main): %s" % ("OK" if not problems else "; ".join(problems)))
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="write the evidence project (default: dry run)")
    ap.add_argument("--main-identity", action="store_true",
                    help="align the main project's library and shared identity recipes")
    ap.add_argument("--code-out", help="write each rewritten Python recipe to this directory")
    args = ap.parse_args()
    act = "APPLY" if args.apply else "DRY-RUN"
    c = client()
    main_p, ev = c.get_project(MAIN), c.get_project(EVIDENCE)
    items = plan(main_p)

    problems = []
    for item in items:
        if item["type"] == "python":
            check_code(item["name"], item["code"], item["inputs"], problems)
    if problems:
        raise SystemExit("the rewritten code does not resolve:\n  " + "\n  ".join(problems))
    if args.code_out:
        out = Path(args.code_out)
        out.mkdir(parents=True, exist_ok=True)
        for item in items:
            if item["type"] == "python":
                (out / (item["name"] + ".py")).write_text(item["code"])

    if args.main_identity:
        return main_identity(main_p, items, apply=True)

    have_recipes = {r["name"] for r in ev.list_recipes()}
    have_datasets = {d["name"] for d in ev.list_datasets()}
    print("%s library  %s on %s (graph_nodes qualified)" % (act, LIBRARY_FILE, EVIDENCE))
    print("%s zones    %s" % (act, ", ".join(ZONES.values())))
    for item in items:
        state = "exists, kept" if item["name"] in have_recipes else ("copy" if item["copy"] else "new")
        if item["name"] in have_recipes and trimmed(item):
            state = "exists, trim"
        inputs = ", ".join(("%s.%s" % (MAIN, x)) if x in UPSTREAM else x for x in item["inputs"])
        print("%s %-2s %-38s %-8s %-12s -> %s   [%s]" % (act, item["zone"], item["name"], item["type"],
                                                         state, item["output"], inputs))
    print("\n%d recipes, %d datasets (%d copied or moved, %d new); %d already present"
          % (len(items), len(items), sum(i["copy"] for i in items), sum(not i["copy"] for i in items),
             len(have_recipes & {i["name"] for i in items})))
    main_identity(main_p, items, apply=False)
    if not args.apply:
        print("\nDry run: nothing written. Re-run with --apply (evidence) or --main-identity (main) "
              "once approved.")
        return 0

    write_library(EVIDENCE)
    zones = zone_by_name(ev)
    for item in items:
        if item["output"] not in have_datasets:
            create_output(ev, main_p, item)
        store_output(ev, item["output"])
        if item["name"] not in have_recipes:
            create_recipe(ev, item)
        elif not item["copy"] or trimmed(item):
            configure(ev, ev.get_recipe(item["name"]), item)
        zones[item["zone"]].add_item(ev.get_dataset(item["output"]))

    problems = read_back(ev, items)
    print("\nread back: %s" % ("OK" if not problems else "\n  " + "\n  ".join(problems)))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
