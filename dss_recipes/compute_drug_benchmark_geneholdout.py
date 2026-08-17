# Can the drug-target benchmark measure NOVEL target prediction at all?
#
# BACKGROUND: a gene-popularity lookup (no graph, no disease information -- just "how many
# training diseases is this gene drugged for") scores 0.9354 per-disease AUC on this benchmark,
# beating both m7 (0.9324, trained on the drug label) and m3-f12 (0.6836). So the benchmark is
# dominated by gene identity, and a model that refuses that shortcut is penalised for it.
#
# THE HONEST VERSION: hold out GENES as well as diseases. Evaluate only on strict (approved
# indication) pairs whose gene is NOT a drug target in any training disease -- no popularity
# shortcut is available, so this measures genuine novel-target prediction.
#
# THE RISK THIS MEASURES: the strict ground truth spans only 778 genes. If nearly all of them
# are already train-popular, the novel subset is empty and this ground truth CANNOT measure
# novel-target prediction -- in which case drug AUC should be retired as a headline metric
# rather than repaired.
import dataiku
import numpy as np
import pandas as pd

SCORE = "proba_1"

train = dataiku.Dataset("psplit_train_drug").get_dataframe(
    columns=["gene_index", "is_drug_target_weak"])
seen_genes = set(train.loc[train.is_drug_target_weak == 1, "gene_index"].unique())
print(f"genes drugged in >=1 TRAIN disease (the shortcut set): {len(seen_genes):,}")

val = dataiku.Dataset("scored_m7").get_dataframe(
    columns=["disease_index", "gene_index", "is_target", "is_drug_target_strict", SCORE])
strict = val[val.is_drug_target_strict == 1]
val_genes = set(strict.gene_index.unique())
novel_genes = val_genes - seen_genes
print(f"genes appearing in validation STRICT pairs                : {len(val_genes):,}")
print(f"  of which never drugged in a training disease (NOVEL)    : {len(novel_genes):,}"
      f"  ({len(novel_genes)/max(len(val_genes),1):.1%})")
print(f"strict validation pairs total                             : {len(strict):,}")
n_novel_pairs = int(strict.gene_index.isin(novel_genes).sum())
print(f"  of which involve a NOVEL gene                           : {n_novel_pairs:,}"
      f"  ({n_novel_pairs/max(len(strict),1):.1%})")

# per-disease AUC restricted to novel-gene positives; negatives = all non-target genes
rows = []
for d, g in val.groupby("disease_index"):
    m = (g.is_drug_target_strict == 1) & (g.gene_index.isin(novel_genes))
    neg = g.is_drug_target_strict == 0
    n1, n0 = int(m.sum()), int(neg.sum())
    if n1 == 0 or n0 == 0:
        continue
    sub = g[m | neg]
    r = sub[SCORE].rank()
    mm = sub.is_drug_target_strict == 1
    rows.append({"disease_index": d, "n_novel_drug": n1,
                 "auc_m7_novel": (r[mm].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)})
out = pd.DataFrame(rows)
print(f"\n=== novel-gene evaluation ===")
print(f"  diseases with >=1 novel-gene drug target: {len(out)}  (vs 112 in the standard version)")
if len(out):
    print(f"  m7 mean per-disease AUC on novel genes  : {out.auc_m7_novel.mean():.4f}")
    print(f"  total novel-gene positives evaluated    : {int(out.n_novel_drug.sum()):,}")
else:
    print("  NONE — the ground truth cannot measure novel-target prediction.")
print(f"\n  interpretation: with {len(novel_genes)} novel genes across {n_novel_pairs} pairs, this "
      f"benchmark is {'usable but thin' if n_novel_pairs > 200 else 'TOO THIN to support a headline metric'}.")
dataiku.Dataset("drug_benchmark_geneholdout").write_with_schema(
    out if len(out) else pd.DataFrame([{"disease_index": -1, "n_novel_drug": 0, "auc_m7_novel": np.nan}]))
