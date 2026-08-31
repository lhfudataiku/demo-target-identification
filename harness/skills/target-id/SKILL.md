---
name: target-id
description: Navigate the demo-target-identification repo without reading its large docs. Use when asked about this project's models (m1-m8), metrics, features, recipes, seed gates, past decisions, or when updating documented numbers after a model change. Answers most questions with a grep over .index/ instead of loading 135k tokens of markdown.
---

# Navigating this repo cheaply

The docs are well over 140k tokens and the recipes ~93k. **Do not read them to answer a factual question.** Four generated indexes answer most of it; `docs/prioritizer/TARGET_PRIORITIZER.md` is a last resort, and even then read one section, not the file. `docs/README.md` maps the whole doc set.

Regenerate after editing any doc or recipe: `./tools/check_indexes.sh` verifies, the two `tools/build_*.py` scripts rebuild. `build_recipe_index.py --refresh` also re-snapshots DSS (slow, ~3 min) — only needed when a recipe changed in the UI.

## Which index answers what

| question | query |
|---|---|
| "what was m5 / why was m8 rejected / what is the champion" | `cut -f1,3,4,15 .index/models.tsv \| column -t -s$'\t'` |
| "what is the current decision about X" | `grep -i 'X' .index/decisions.tsv` → stable ID and register line |
| "what happened historically around X" | `grep -i 'X' .index/decisions_history.tsv` → classified archived-log line |
| "which recipe makes feature F, is it gated" | `grep -P '^dwpc_GBGD\t' .index/features.tsv` |
| "which recipes carry a seed gate, and are they safe to widen" | `awk -F'\t' '$3!="-"' .index/recipes.tsv` |
| "is this documented number guarded by a notebook" | `grep -P '\t0\.8230\t' .index/claims.tsv \| grep -v DECISIONS` — `status` + `guarded_by` are fields 5-6 |
| "what is unguarded and could drift" | `.index/SUMMARY.md`, "Risk surface" section |
| "which entry points consume the champion" | `awk -F'\t' '$3=="yes"{print $16}' .index/models.tsv` |

`grep -i prox_kernel .index/decisions.tsv` costs ~100 tokens. The 22k-token retired chronology is
loaded only for an explicit historical investigation.

## Hard-won traps

**Numbers**
- **Never global-replace a metric.** Most occurrences are *historical and correct*: the ablation ladder, the m3 reconstruction record, per-model comparison tables. A `sed` across `TARGET_PRIORITIZER.md` corrupts six of ten `0.8197`s. Classify each hit before touching it.
- **Never put a pooled number beside a macro one**, or a route-only numerator beside a full-pool denominator. §8.4 had to be corrected for the first; I made the second on 2026-08-21 (claimed admitted rows were *denser* in positives; like-for-like they are 4.4× more dilute).
- **Report ties before means.** m3–m6 are the same ranker for ~90% of diseases; every aggregate difference in this project traces to 9–15 high-leverage diseases.
- Abstracts and preambles drift separately from the sections they summarise. `TARGET_PRIORITIZER.md` line ~43 kept a stale `r` for days after §7.4 was fixed.
- **DSS flow-zone descriptions are demo-facing prose that no index covers** — they live in DSS, not the repo. Three still quoted `m3-f12` numbers after the champion moved. Check them with `dku flow zones` when a champion changes; the field is `shortDesc`, not `description`, and there is no CLI verb — it needs a scenario using the python API.

**DSS**
- `dku ml settings <analysis> <mltask>` returns the **current mltask state, not a deployed model's config**. m8 was trained in m7's mltask, so it reports m8's features under a count that still matches `m7-f14`. Source features from `tools/model_registry.json`.
- `dku job list`: **line 3 is the first job** (line 2 is the header). Read job state from the JSON `state` field — a green assertion on a FAILED job is reading stale data.
- `--timeout` is not valid on `dku scenario run`.
- One job, repeated `--target`, `RECURSIVE_BUILD`. `flow propagate` **fully** before rebuilding, then build fused Spark stages separately, or schema validation fails against a schema `--auto-update-schema` never updated.
- Folder access error "Python process is running remotely" → switch the recipe to the DSS engine.

**Python / shell**
- Python 3.9: a backslash inside an f-string expression fails at parse time with **no output at all**. Hoist regexes to module constants.
- Millions of Python tuples get OOM-killed (exit 137). Use int64 keys (`disease*200000+gene`) with `np.searchsorted`.
- `grep -E '^(COST|EVAL)\|'` does **not** match `COST_GAP|` — the alternation needs the `|` right after. And an unescaped `.` in `grep 2.38` matches `0.2738`; use `-F`.
- A generated artifact that lands in the namespace it scans will feed on itself. `.index/SUMMARY.md` is a `.md` file; the claims index grew 1,630 → 1,744 per run until excluded.

## Standing rules

`compute_kg` is never touched or recomputed. Add a current decision only when the admission rule in
`docs/decisions/DECISION_REGISTER.md` is satisfied; never edit the retired log. New datasets use the
S3 connection. Joins go in visual Join recipes, not pandas `.merge()`.

## Longer procedures

Read these only when doing that task:

- **Retargeting documented numbers after a champion change** → `references/number-update.md`
- **Phase 3 / widening the seed gate** → `docs/prioritizer/PHASE3_PREREGISTRATION.md` (predictions and the committed adopt/reject rule) and `.index/recipes.tsv` for the Class 1 / Class 2 split
- **DSS platform behaviours in depth** → `docs/platform/DSS_CHEATSHEET.md`
