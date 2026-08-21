# Retargeting documented numbers after a champion change

The procedure that produced the 2026-08-21 sweep, including the four mistakes it made. Follow the
order — it is what makes the failures show up early instead of in a customer-facing doc.

## 1. Repoint, then rebuild

Both champion entry points move, not one:

```bash
awk -F'\t' '$3=="CHAMPION"{print $15}' .index/models.tsv
```

`sync_scored_champion` is the obvious one. `score_persona_candidates` is the one that was missed and
sat on `m3-f12` after the champion moved. `compute_model_comparison` **stays** on `scored_m1/m2/m3` —
it is the ablation ladder, not a champion consumer.

Then one job, all endpoints, recursive:

```bash
dku job run --target A --target B --type RECURSIVE_BUILD --auto-update-schema --wait
```

## 2. Run the notebooks first, and treat failures as the worklist

```bash
for NB in nb1_features_and_config nb2_splitting_and_pool nb3_validation_and_plots \
          nb3b_hub_bias_meter nb4_results_three_axes; do ...  # see any prior session's scenario wrapper
```

**The failing assertions are the doc-update worklist.** Do not start editing docs before this — it is
how §6.2's split sizes were caught as provably wrong and how §7.2's central claim was refuted.

**But first check whether the assertion or the doc is wrong.** In the 2026-08-21 sweep, 3 of 20
failures were assertion bugs against a doc that was already correct: §6.1 had been fixed two days
earlier and the expected values were never updated. A tripwire firing on correct values trains you to
ignore it.

## 3. Classify every hit before editing

For each stale value, `grep -nF` it and classify each occurrence:

- **current-state claim** → update
- **per-model comparison table row** → leave, it is correct for that model
- **reconstruction / cross-validation record** → leave, it is a dated record
- **`DECISIONS.md`** → never edit, append-only

Of ten `0.8197`s in `TARGET_PRIORITIZER.md`, only four were current-state. A global replace corrupts
the other six.

**Verify section references by target title, not by number.** Removing a subsection shifts `8.7`→`8.6`
and the old refs still *resolve* — they just point at different content.

## 4. Check the whole table, not just the asserted cells

The three §8.4 magnitude assertions all passed after updating, while the claim they sat under became
false: the macro estimator's crossover had moved from K=20 to K=50. **Assert directions, not only
magnitudes**, when a claim is about a direction. `nb4` now asserts the sign of `dm − naive` at all
five K.

## 5. Hunt the numbers no notebook guards

```bash
awk -F'\t' '$5=="ORPHAN" && $7=="y" && $8=="" && $1!="DECISIONS.md"' .index/claims.tsv
```

Start with the small client-facing files — `DEMO_NARRATIVE.md`,
`docs/demo/BREAST_SURGEON_BRIEFING.md`. Both carried stale numbers into external-audience
documents in the last sweep.

Orphans found this way that mattered: the §8.3 **adopted** discovery row (headline claim, computed ad
hoc, drifted, and its `expected@10` implied a disease count that no longer reproduced); the header's
`pooled` and `per-split-key`, which is how m7's macro came to sit beside m3's pooled.

**When you find an orphan that matters, add an assertion rather than just fixing the value.** Otherwise
it drifts again next time.

## 6. Consistency sweeps that are easy to forget

- **Abstracts and preambles** — they summarise sections and drift separately.
- **Coincidental digit collisions** — §7.2's hub delta `+0.024` survived a grep for the orthogonality
  `r = +0.024`. Different quantity, same digits.
- **Derived quantities in the same table** — updating a delta without its baseline leaves
  `0.7471 − 0.6911 ≠ +0.0585`.
- **Model-specific prose**, not just metrics: gene ranks (`MAPK3 novel #3 → #4`), score gaps, "worst
  of twelve" counts.
- **Monotonicity and shape claims** — "falls monotonically with rank" became false on m7 while every
  endpoint stayed plausible.

## 7. Close out

```bash
./tools/check_indexes.sh
```

Then append `DECISIONS.md` entries for anything refuted, corrected, or newly unguarded — including
your own mistakes, with the mechanism. That log is the reason the same errors get caught faster each
time.

Ask before committing.
