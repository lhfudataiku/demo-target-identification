# Split integrity audit for the set_2 pipeline (elevated `disease_split_key`).
#
# WHY: set_2 is the first split keyed on `disease_split_key` (the anchor's most-specific
# parent under the fanout cap) rather than `disease_family_id` (the anchor itself). The
# whole point of the change is to stop MONDO parent/child pairs -- `diabetes mellitus` vs
# `type 2 diabetes mellitus` -- from straddling train/test. That guarantee has to be
# verified on the built data, not assumed from the GREL.
#
# Checks: (1) no split key appears in two splits, (2) no disease_index appears in two
# splits, (3) positive rate is comparable across splits, (4) the persona diseases and the
# diabetes pair all land in validation.
import dataiku
import pandas as pd

COLS = ["disease_index", "disease_split_key", "disease_family_id", "split_key_name", "is_target"]
SETS = {"train": "enriched_train_full_2",
        "validation": "enriched_validation_set_2",
        "test": "enriched_test_set_2"}
# personas + the pair that motivated the elevated key
# Indices remapped 2026-08-17 for the DEMO_KG_LS graph, resolved through
# (node_id, node_type, node_source) -- see index_remap.json. node_index is DETERMINISTIC in that
# graph, so these are stable from here on; they were not stable in the old single-project build.
# They are still project-specific: the same diseases carry different integers per graph build.
WATCH = {47530: "morbid obesity", 37143: "obesity disorder",
         49721: "breast cancer", 47415: "breast carcinoma",
         47437: "diabetes mellitus", 47537: "type 2 diabetes mellitus",
         54058: "type 1 diabetes mellitus"}

frames = {k: dataiku.Dataset(v).get_dataframe(columns=COLS) for k, v in SETS.items()}

rows = []
for name, df in frames.items():
    rows.append({"split": name, "rows": len(df),
                 "positives": int(df.is_target.sum()),
                 "pos_rate_pct": round(100 * df.is_target.mean(), 4),
                 "n_diseases": df.disease_index.nunique(),
                 "n_split_keys": df.disease_split_key.nunique(),
                 "n_anchor_families": df.disease_family_id.nunique()})
summary = pd.DataFrame(rows)
print("\n=== set_2 split summary ===")
print(summary.to_string(index=False))

keys = {k: set(df.disease_split_key.unique()) for k, df in frames.items()}
dis = {k: set(df.disease_index.unique()) for k, df in frames.items()}
print("\n=== integrity (must all be 0) ===")
for a, b in [("train", "test"), ("train", "validation"), ("test", "validation")]:
    print(f"  split_key overlap {a:10s} n {b:10s}: {len(keys[a] & keys[b]):5d}"
          f"   |  disease overlap: {len(dis[a] & dis[b]):5d}")

print("\n=== watched diseases ===")
allf = pd.concat([df.assign(split=k) for k, df in frames.items()], ignore_index=True)
lookup = (allf.drop_duplicates("disease_index")
              .set_index("disease_index")[["split", "disease_split_key", "split_key_name",
                                           "disease_family_id"]])
for idx, label in WATCH.items():
    if idx in lookup.index:
        r = lookup.loc[idx]
        print(f"  {label:20s} idx {idx:6d} -> {r.split:10s} key {r.disease_split_key} "
              f"({r.split_key_name})")
    else:
        print(f"  {label:20s} idx {idx:6d} -> NOT PRESENT (filtered out)")

# the diabetes pair: locate by split_key_name, since the indices shift between rebuilds
dm = allf[allf.split_key_name.astype(str).str.contains("diabetes", case=False, na=False)]
print("\n=== diseases under a 'diabetes' split key ===")
if len(dm):
    g = (dm.drop_duplicates("disease_index")
           .groupby(["split_key_name", "split"]).disease_index.nunique())
    print(g.to_string())
else:
    print("  none")

# per-split-key straddle report (should be empty) + the largest keys
straddle = (allf.drop_duplicates(["disease_split_key", "split"])
                .groupby("disease_split_key").split.nunique())
print("\nsplit keys appearing in >1 split:", int((straddle > 1).sum()))

out = summary.copy()
out["overlap_train_test_keys"] = len(keys["train"] & keys["test"])
out["overlap_train_val_keys"] = len(keys["train"] & keys["validation"])
out["overlap_test_val_keys"] = len(keys["test"] & keys["validation"])
out["straddling_split_keys"] = int((straddle > 1).sum())
dataiku.Dataset("split_audit_2").write_with_schema(out)



