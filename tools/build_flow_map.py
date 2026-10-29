#!/usr/bin/env python3
"""Generate docs/operations/FLOW_MAP.md from live DSS plus the repository's readers.

FLOW_MAP.md was marked "Generated / never edit by hand" for months without a
generator existing -- it was produced by hand from live DSS and then drifted
(it claimed 100 datasets against 92 live, and its whole `serving (webapp TBD)`
flag vocabulary predated the webapp that now reads those zones). This script is
the missing generator.

Sources, in order of authority:
  live DSS zones               -- `dku flow zones`      (zone membership)
  .index/dss_snapshot.json     -- recipe inputs/outputs (the producer graph)
  webapp/backend/**/*.py       -- which routes read which dataset
  notebooks/*.py               -- which notebook reads which dataset

Usage:
  python3 tools/build_recipe_index.py --refresh     # first, if DSS changed
  python3 tools/build_flow_map.py                   # then this
  python3 tools/build_flow_map.py --check           # verify without writing
  python3 tools/build_flow_map.py --project DEMO_TI_EVIDENCE [--check]

`--project DEMO_TI_EVIDENCE` maps the evidence project (ADR-003) into FLOW_MAP_EVIDENCE.md, from
.index/dss_snapshot_evidence.json. There the notebooks' bare names are reads, because the notebook
runner makes that project their default; the webapp reads nothing there.
"""
import json
import os
import re
import subprocess
import sys

MAIN = "DEMO_TARGET_IDENTIFICATION"
EVIDENCE = "DEMO_TI_EVIDENCE"
PROJECT = MAIN
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# project -> (map file, snapshot, the other project's map)
TARGETS = {
    MAIN: ("FLOW_MAP.md", "dss_snapshot.json", "FLOW_MAP_EVIDENCE.md"),
    EVIDENCE: ("FLOW_MAP_EVIDENCE.md", "dss_snapshot_evidence.json", "FLOW_MAP.md"),
}
OUT = os.path.join(ROOT, "docs", "operations", "FLOW_MAP.md")
SNAPSHOT = os.path.join(ROOT, ".index", "dss_snapshot.json")
# A quoted dataset name is a real read; a bare occurrence is usually prose. The webapp backend's
# default project is this one, so a bare name reads here. The notebooks run with DEMO_TI_EVIDENCE
# as their default (workplan M2), so only their qualified reads
# (`"DEMO_TARGET_IDENTIFICATION.scored_champion"`) are reads of this project; a bare one reads the
# evidence copy of the same name.
QUOTED = r'''["'](?:%s\.)?{}["']''' % re.escape(PROJECT)
QUALIFIED = r'''["']%s\.{}["']''' % re.escape(PROJECT)


def configure(project):
    """Point the module at one project."""
    global PROJECT, OUT, SNAPSHOT, QUOTED, QUALIFIED
    if project not in TARGETS:
        raise SystemExit("unknown project %s; one of %s" % (project, ", ".join(TARGETS)))
    PROJECT = project
    OUT = os.path.join(ROOT, "docs", "operations", TARGETS[project][0])
    SNAPSHOT = os.path.join(ROOT, ".index", TARGETS[project][1])
    QUOTED = r'''["'](?:%s\.)?{}["']''' % re.escape(project)
    QUALIFIED = r'''["']%s\.{}["']''' % re.escape(project)


def counts_as_read(label):
    """Which pattern makes a reader's quoted name a read of PROJECT, or None for no read.
    Main: the webapp's bare names, the notebooks' qualified ones. Evidence: the notebooks' bare
    names only (the runner's default project); the webapp never reads there."""
    if PROJECT == EVIDENCE:
        return None if label.startswith("webapp:") else QUOTED
    return QUOTED if label.startswith("webapp:") else QUALIFIED


def dku_json(args):
    out = subprocess.run(["dku", "--format", "json"] + args,
                         capture_output=True, text=True).stdout
    return json.loads(out)


def readers():
    """dataset -> sorted list of reader labels (webapp routes, notebooks)."""
    sources = []
    backend = os.path.join(ROOT, "webapp", "backend")
    for base, _, files in os.walk(backend):
        if "__pycache__" in base:
            continue
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(base, f), backend)
                sources.append((os.path.join(base, f), "webapp:" + rel[:-3].replace(os.sep, "/")))
    nbdir = os.path.join(ROOT, "notebooks")
    for f in sorted(os.listdir(nbdir)):
        if f.endswith(".py"):
            sources.append((os.path.join(nbdir, f), f.split("_")[0]))
    texts = []
    for path, label in sources:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            texts.append((fh.read(), label))
    return texts


def build():
    zones = dku_json(["flow", "zones", "-P", PROJECT])
    with open(SNAPSHOT, encoding="utf-8") as fh:
        snap = json.load(fh)
    if PROJECT == EVIDENCE:
        snap = snap["recipes"]
    recipes = {k: v for k, v in snap.items() if not k.startswith("_")}

    produced, consumed = {}, {}
    for name, r in recipes.items():
        for o in (r.get("outputs") or []):
            produced[o] = name
        for i in (r.get("inputs") or []):
            consumed.setdefault(i, []).append(name)

    # Zone membership is keyed by (projectKey, objectId): a zone holds both the
    # foreign reference and its local synced copy under the SAME objectId, so
    # deduplicating on the name alone silently doubles every row in zone 00.
    # The local dataset list -- not zone membership -- is the dataset universe,
    # so a dataset assigned to no zone still appears.
    listed = set(subprocess.run(
        ["dku", "--format", "ids", "dataset", "list", "-P", PROJECT],
        capture_output=True, text=True).stdout.split())
    # The listing also names the other project's datasets this one reads (the evidence project's
    # 18 main-project inputs). A name the recipes reach only by `<project>.<name>` is foreign
    # unless a local recipe builds it, as the main project's synced copies of DEMO_KG_LS are.
    foreign_names = {i.split(".", 1)[1] for ins in consumed for i in [ins] if "." in i}
    local = sorted(d for d in listed if d not in foreign_names or d in produced)
    zone_of, foreign_of = {}, {}
    localset = set(local)

    def classify(item):
        """(kind, key) for a zone item. The DERIVED `Default` zone reports items
        with objectType None and the project prefix folded into objectId, so the
        explicit objectType cannot be relied on for it."""
        oid, otype = item["objectId"], item.get("objectType")
        if otype == "RECIPE":
            return "recipe", oid
        if otype == "DATASET":
            if item.get("projectKey") == PROJECT:
                return "dataset", oid
            return "foreign", "{}.{}".format(item.get("projectKey"), oid)
        if otype is None:
            if "." in oid:
                return "foreign", oid
            if oid in localset:
                return "dataset", oid
        return "other", oid

    # Explicit assignments win; a derived zone (Default) only claims what no
    # explicit zone already holds, otherwise the foreign refs count twice.
    for derived in (False, True):
        for z in zones:
            if bool(z.get("itemsDerived")) != derived:
                continue
            for item in z["items"]:
                kind, key = classify(item)
                if kind == "dataset" and key not in zone_of:
                    zone_of[key] = z["name"]
                elif kind == "foreign":
                    if not any(key in v for v in foreign_of.values()):
                        foreign_of.setdefault(z["name"], []).append(key)
    datasets = local
    texts = readers()
    reads = {}
    for d in datasets:
        hits = sorted({label for text, label in texts
                       if counts_as_read(label)
                       and re.search(counts_as_read(label).format(re.escape(d)), text)})
        if hits:
            reads[d] = hits

    def flag(d):
        if d in reads:
            return "webapp" if any(h.startswith("webapp:") for h in reads[d]) else "notebook"
        if consumed.get(d):
            return "intermediate"
        return "**ORPHAN**"

    orphans = [d for d in datasets if flag(d) == "**ORPHAN**"]
    endpoints = sorted(reads)

    L = []
    L.append("# Flow map" if PROJECT == MAIN else "# Flow map: evidence project (`%s`)" % PROJECT)
    L.append("")
    L.append("> **Lifecycle:** Generated · **Audience:** flow maintainers and reviewers considering pruning")
    L.append("> or changing a data contract · **Authority:** live DSS zones, datasets, producers and")
    L.append("> consumers · **Update when:** the DSS flow or its generation inputs change · **Generated")
    L.append("> dependencies:** live DSS (`dku flow zones`), `.index/%s`, `notebooks/*.py`," % TARGETS[PROJECT][1])
    L.append("> `webapp/backend/**/*.py` · **Excludes:** hand-authored rationale, design policy and build")
    L.append("> chronology.")
    L.append(">")
    L.append("> **Never edit by hand. Regenerate:**")
    L.append("> ```sh")
    L.append("> python3 tools/build_recipe_index.py --refresh   # only if DSS changed in the UI")
    L.append("> python3 tools/build_flow_map.py%s" % ("" if PROJECT == MAIN else " --project " + PROJECT))
    L.append("> ```")
    L.append("")
    other = TARGETS[PROJECT][2]
    L.append("Project `{}`. The other Part 2 project is mapped in [`{}`]({}): {}".format(
        PROJECT, other, other,
        "the evidence project, which the notebooks read and nothing here reads."
        if PROJECT == MAIN else
        "the main project, whose zones 00-31 this project reads by qualified name. Those reads "
        "appear below as foreign references."))
    L.append("")
    L.append("Live DSS: **{} datasets across {} zones**, cross-referenced against the recipe graph "
             "({} recipes), `notebooks/*.py` and `webapp/backend/**/*.py`.".format(
                 len(datasets), len(zones), len(recipes)))
    L.append("")
    L.append("A dataset counts as **read** only when its name appears *quoted* in reader code. A bare")
    L.append("mention is prose: `calibration.py` names the three DWPC feature datasets in a display")
    L.append("table, which is not a read.")
    L.append("")
    L.append("| flag | meaning |")
    L.append("|---|---|")
    L.append("| webapp | a webapp route reads it — serving the live demo |")
    L.append("| notebook | a notebook reads it — it guards a documented number |")
    L.append("| intermediate | no reader, but a recipe consumes it — load-bearing inside the flow |")
    L.append("| **ORPHAN** | nothing reads it and no recipe consumes it — a pruning candidate |")
    L.append("")
    if PROJECT == MAIN:
        L.append("The retired `serving (webapp TBD)` flag is gone: the consumer it deferred to now exists,")
        L.append("so zones A1-A4 are read by named routes rather than by an unbuilt UI.")
        L.append("")
    L.append("## Summary")
    L.append("")
    L.append("- datasets: **{}**".format(len(datasets)))
    L.append("- endpoints (read by a webapp route or a notebook): **{}**".format(len(endpoints)))
    L.append("- flow intermediates (consumed by a recipe, no direct reader): **{}**".format(
        sum(1 for d in datasets if flag(d) == "intermediate")))
    L.append("- genuine orphans: **{}**{}".format(
        len(orphans), " — " + ", ".join("`%s`" % o for o in orphans) if orphans else ""))
    L.append("")
    if orphans and PROJECT == MAIN:
        L.append("> Every orphan here is a deliberate decision, not a finding. See")
        L.append("> `.index/_dead.json` `keep_do_not_prune` for why each one survives.")
        L.append("")
    # Computed, not asserted. This section used to name `pool_unreachable_targets` /
    # `compute_pool_reachability` as the live example; that dataset has since been deleted and the
    # recipe now has one output, so the warning outlived the hazard. Derive it instead.
    shared = []
    for name, r in sorted(recipes.items()):
        outs = r.get("outputs") or []
        if len(outs) < 2:
            continue
        keep = [o for o in outs if o in reads or consumed.get(o)]
        drop = [o for o in outs if o not in reads and not consumed.get(o)]
        if keep and drop:
            shared.append((name, keep, drop))
    L.append("### Shared-recipe caution")
    L.append("")
    L.append("A dataset may go while its producing recipe must not, when the recipe has a second output")
    L.append("that something reads. Deleting the recipe to remove the unread output would take the read")
    L.append("one with it.")
    L.append("")
    if shared:
        L.append("| recipe | unread output (may go) | output that is read (recipe must stay) |")
        L.append("|---|---|---|")
        for name, keep, drop in shared:
            L.append("| `{}` | {} | {} |".format(
                name, ", ".join("`%s`" % d for d in drop), ", ".join("`%s`" % k for k in keep)))
    else:
        L.append("**No recipe currently has this shape.** Every multi-output recipe in the flow has all")
        L.append("of its outputs either read or consumed, so no recipe is load-bearing for a dataset that")
        L.append("looks disposable.")
    L.append("")

    for z in sorted(zones, key=lambda x: x["name"]):
        ds = sorted(d for d in datasets if zone_of.get(d) == z["name"])
        rc = sorted({i["objectId"] for i in z["items"] if i.get("objectType") == "RECIPE"})
        fr = sorted(set(foreign_of.get(z["name"], [])))
        L.append("## {}  ({} datasets, {} recipes)".format(z["name"], len(ds), len(rc)))
        L.append("")
        if fr:
            L.append("Foreign references in this zone ({}), {}: {}".format(
                len(fr),
                "each feeding exactly one Sync or Merge recipe" if PROJECT == MAIN
                else "read by name by this project's recipes, with no local copy",
                ", ".join("`%s`" % f for f in fr)))
            L.append("")
        if not ds:
            L.append("_No datasets in this zone._")
            L.append("")
            continue
        L.append("| dataset | read by | producing recipe | recipe consumers | flag |")
        L.append("|---|---|---|--:|---|")
        for d in ds:
            L.append("| `{}` | {} | {} | {} | {} |".format(
                d,
                ", ".join("**%s**" % h if h.startswith("webapp:") else h for h in reads.get(d, [])) or "—",
                "`%s`" % produced[d] if d in produced else "— *(source)*",
                len(consumed.get(d, [])),
                flag(d)))
        L.append("")

    unzoned = sorted(d for d in datasets if d not in zone_of)
    if unzoned:
        L.append("## Assigned to no zone  ({} datasets)".format(len(unzoned)))
        L.append("")
        L.append("A dataset outside every zone is invisible to zone-based reasoning and to the")
        L.append("`Refresh_serving_layer` steps, which build by zone. Assign it or delete it.")
        L.append("")
        L.append("| dataset | read by | producing recipe | recipe consumers | flag |")
        L.append("|---|---|---|--:|---|")
        for d in unzoned:
            L.append("| `{}` | {} | {} | {} | {} |".format(
                d,
                ", ".join(reads.get(d, [])) or "—",
                "`%s`" % produced[d] if d in produced else "— *(source)*",
                len(consumed.get(d, [])),
                flag(d)))
        L.append("")

    return "\n".join(L) + "\n"


def main():
    if "--project" in sys.argv:
        configure(sys.argv[sys.argv.index("--project") + 1])
    text = build()
    check = "--check" in sys.argv
    if check:
        with open(OUT, encoding="utf-8") as fh:
            current = fh.read()
        if current == text:
            print("%s up to date" % os.path.basename(OUT))
            return 0
        print("%s STALE -- run: python3 tools/build_flow_map.py%s" % (
            os.path.basename(OUT), "" if PROJECT == MAIN else " --project " + PROJECT))
        return 1
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote {} ({} lines)".format(os.path.relpath(OUT, ROOT), text.count("\n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
