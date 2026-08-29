# Appendix snapshots

> **Lifecycle:** Historical · **Audience:** reviewers reproducing retired analyses · **Authority:**
> frozen, versioned evidence captured when the corresponding flow artifacts were removed · **Update
> when:** never, except to repair provenance or successor pointers · **Generated dependencies:** the
> listed live inputs · **Excludes:** current champion claims and current demo guidance.

Frozen results for analyses **removed from the DSS flow** on 2026-08-19. They back specific claims in
[TARGET_PRIORITIZER.md](../prioritizer/TARGET_PRIORITIZER.md) but no scientist asks about them in a demo, so
they were pruned from the flow and preserved here instead.

**Why these exist at all.** On 2026-08-18 the `drug-label-probe` experiment was deleted from the flow
without a snapshot, and its most reusable finding — a gene-popularity lookup table scoring 0.9354 and
beating the trained model — now survives only as prose. These files are the fix for that mistake:
version-controlled, diffable, citable, and independent of whether anyone re-runs a notebook.

| File | Rows | Backs | Reproduce from |
|---|--:|---|---|
| `model_comparison.csv` | 2,010 | §6.4 ablation ladder, m1-f7 → m2-f10 → m3-f12 | saved models `Lx5Mz2hY`, `6hEivCx0`, `cGPhBOGC` + `psplit_validation_set` |
| `validation_auc_by_disease_2.csv` | 1,113 | §7.1 per-split-key AUC (the second metric run) | `scored_m3` |
| `drug_target_benchmark_staged.csv` | 780 | §7.4 staged drug-target benchmark variant | `scored_m3`, drug edges, `graph_nodes` |
| `disease_hierarchy_annotation.csv` | 27,153 | §3.2 ontology redundancy, §3.3 granularity trade-off | `disease_family_id`, `hetionet_disease_slim`, `mondo_references`, `raw_disease_disease`, `enriched_module_size_1`, `graph_nodes` |
| `maturity_confound.csv` | 60 | §8.2 the metabolic/oncology correction (Spearman +0.110) | `novel_discovery_eval`, drug edges, `graph_nodes` |
| `target_reachability.csv` | 44 | §5.2 candidate-pool reachability scoping | `scored_m3`, drug edges, `graph_nodes` |

**Every "reproduce from" input is still live in the flow** — verified before deletion, so each of
these is re-derivable. The recipe source for each is mirrored in [`dss_recipes/`](../../dss_recipes/)
and in git history.

**Staleness warning.** These are a point-in-time export from the 2026-08-17 graph generation. They are
outside the build graph, so nothing will tell you when they no longer match a rebuilt flow. If the
graph is rebuilt, re-export or stop citing them. The stamp is in `manifest.json`.

> ⚠ **These snapshots predate the `m7-f14` champion (adopted 2026-08-21).** They were
> exported from `m3-f12` and are kept as the frozen evidence for the sections that cite the
> ablation ladder. For current champion numbers use the notebooks, which re-measure live.
