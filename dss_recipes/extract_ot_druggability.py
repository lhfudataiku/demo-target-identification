# Open Targets — EXTRACT druggability annotations (target class, tractability, localization).
#
# Source B for the ligand-vs-receptor problem (TARGET_PRIORITIZER §10.3). Complements the
# GO-derived Source A (`compute_gene_localization`), which has better coverage but is a
# proxy; OT's `targetClass` is the authoritative ChEMBL protein-family classification.
#
# NODE_INDEX SAFETY: emits a per-gene ATTRIBUTE table only. No nodes, no edges, so
# `compute_kg`'s positional node_index assignment is untouched.
#
# Fields pulled from the OT `target` parquet (26.06):
#   targetClass          list<struct<id, label, level>>  -- ChEMBL family, levels l1/l2/l3
#   tractability         list<struct<modality, id, value>> -- SM/AB/PR/OC buckets
#   subcellularLocations list<struct<location, source, termSL, labelSL, targetModifier>>
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
COLS = ["id", "approvedSymbol", "targetClass", "tractability", "subcellularLocations"]

MEMBRANE_KW = ["cell membrane", "plasma membrane", "cell surface"]
SECRETED_KW = ["secreted", "extracellular"]


def read_ot(subdir, columns):
    html = requests.get(BASE + subdir + "/", timeout=120, headers=HEADERS).text
    files = sorted(f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f)
    frames = []
    for f in files:
        rr = requests.get(BASE + subdir + "/" + f, timeout=600, headers=HEADERS)
        rr.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(rr.content)
            tmp = tf.name
        try:
            frames.append(pd.read_parquet(tmp, columns=columns))
        finally:
            os.remove(tmp)
    return pd.concat(frames, ignore_index=True)


t = read_ot("target", COLS)
print(f"OT target rows: {len(t):,}")


def is_list(v):
    return v is not None and hasattr(v, "__len__") and len(v) > 0


def class_at(v, level):
    if not is_list(v):
        return None
    labs = [e.get("label") for e in v if e.get("level") == level and e.get("label")]
    return labs[0] if labs else None


def tract_buckets(v, modality):
    if not is_list(v):
        return None
    hits = [e.get("id") for e in v if e.get("modality") == modality and e.get("value")]
    return "|".join(sorted(set(hits))) if hits else None


def loc_flag(v, keywords):
    if not is_list(v):
        return None                      # None = unannotated, distinct from 0 = annotated-but-not
    locs = " ; ".join(str(e.get("location") or "").lower() for e in v)
    return int(any(k in locs for k in keywords))


out = pd.DataFrame({
    "ensg": t["id"],
    "symbol": t["approvedSymbol"],
    "ot_class_l1": t.targetClass.apply(lambda v: class_at(v, "l1")),
    "ot_class_l2": t.targetClass.apply(lambda v: class_at(v, "l2")),
    "ot_sm_buckets": t.tractability.apply(lambda v: tract_buckets(v, "SM")),
    "ot_ab_buckets": t.tractability.apply(lambda v: tract_buckets(v, "AB")),
    "ot_subcell_membrane": t.subcellularLocations.apply(lambda v: loc_flag(v, MEMBRANE_KW)),
    "ot_subcell_secreted": t.subcellularLocations.apply(lambda v: loc_flag(v, SECRETED_KW)),
})
out["ot_sm_tractable"] = out.ot_sm_buckets.notna().astype(int)
out["ot_ab_tractable"] = out.ot_ab_buckets.notna().astype(int)

print("\n=== COVERAGE (of %d OT targets) ===" % len(out))
for c in ["ot_class_l1", "ot_class_l2", "ot_sm_buckets", "ot_ab_buckets",
          "ot_subcell_membrane", "ot_subcell_secreted"]:
    print(f"  {c:24s} non-null {out[c].notna().sum():6,d}  ({out[c].notna().mean():.1%})")

print("\n=== ot_class_l1 distribution ===")
print(out.ot_class_l1.value_counts().head(15).to_string())
print("\n=== sample SM tractability buckets ===")
print(out.loc[out.ot_sm_buckets.notna(), "ot_sm_buckets"].value_counts().head(8).to_string())

dataiku.Dataset("raw_ot_druggability").write_with_schema(out)
