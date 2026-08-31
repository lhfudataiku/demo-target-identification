# Target Prioritizer — validation evidence map

> **Lifecycle:** Evidence · **Audience:** model reviewers, demo owners and claim consumers ·
> **Authority:** interpretation and provenance map for current Part 2 claims · **Update when:** a
> governed measurement, its assertion, its consumer or a material limitation changes · **Generated
> dependencies:** notebook assertions, [`CLAIM_REGISTRY.json`](CLAIM_REGISTRY.json) and
> `.index/governed_claims.tsv` · **Excludes:** modelling implementation, DSS topology, build chronology
> and copied notebook output.

This is the compact review surface for the target-prioritizer evidence. Notebooks are the
computational authority: this document interprets their assertions but never replaces them. The
modelling choices are in [TARGET_PRIORITIZER.md](TARGET_PRIORITIZER.md); the complete pre-split record
is preserved in
[`archive/prioritizer/TARGET_PRIORITIZER_PRE_PHASE3.md`](../../archive/prioritizer/TARGET_PRIORITIZER_PRE_PHASE3.md).

## 1. Reading contract

Every governed current claim has a stable `TI-*` ID. Its exact values, display precision,
authority-match tolerance, assertion source, documentation consumers, webapp/API consumers and
review trigger are machine-readable in `CLAIM_REGISTRY.json`. That tight registry tolerance checks
the notebook's expected literal; the notebook's own `check()` tolerance separately governs live-data
acceptance. A number without a claim ID may still be important historical evidence, but it is not a
current headline and must not be silently promoted into one.

Three distinctions are non-negotiable:

1. **Macro per-disease is not pooled.** Macro asks how well genes are ordered within the average
   disease. Pooled also rewards separating rows across diseases and lets large diseases carry small
   ones. The governed headline is macro.
2. **Association is not therapeutic relevance.** Association AUROC reconstructs the curated graph
   label. Drug agreement, discovery enrichment and degree-matched tractability are separate axes.
3. **The pool defines the estimand.** Claims apply to pairs admitted by an evidence-bearing graph
   route. They are not claims about all disease–gene pairs or prospective clinical success.

## 2. Governed current claims

| claim | governed reading | computational authority |
|---|---|---|
| `TI-DATA-001` | Candidate pool: **6,754,128** deduplicated pairs at **1.89%** positives, admitted through GGD, GPGD or GCD. | `nb2` §5.2 |
| `TI-MOD-001` | Champion: **`m7-f14`**, saved model **`hJLGoYn4`**, 14 features. | `tools/model_registry.json` |
| `TI-VAL-001` | Reconstruction fidelity: macro per-disease AUROC **0.8230** across **670** held-out diseases. | `nb3` §10.1 |
| `TI-VAL-002` | Pooled AUROC **0.8932** versus macro **0.8230**; pooled is a warning, never the headline. | `nb3` header + §10.1 |
| `TI-VAL-003` | Family view: **505** families, macro AUROC **0.8009**. | `nb3` §7.3 |
| `TI-VAL-004` | Therapeutic agreement: drug-target macro AUROC **0.6886**; association/drug Pearson **+0.002**, R² **0.0000**. | `nb3` §7.4 |
| `TI-VAL-005` | Hub-bias weakness: known-target Q1/Q5 mean probability **0.5938 / 0.7873**, spread **0.1935**, ρ **0.3273**. | `nb3b` §7.2 |
| `TI-VAL-006` | Drug-target AUROC: **0.6886** on all positives and **0.7471** on route-supported positives. | `nb2` §5.2.1 |
| `TI-VAL-007` | Novel approved-target lift: **16.88×** at K=10 and **5.04×** at K=200. | `nb4` §8.3 |
| `TI-VAL-008` | Degree-matched tractability lift: pooled **3.29×** and macro **3.11×** at K=10; pooled **2.42×** at K=200. | `nb4` §8.4; duplicated in `nb6` §5.1 |
| `TI-VAL-009` | HER2-positive AUROC **0.9365**; HER2-positive/TNBC novel top-50 overlap **2**; TNBC has only **8** known targets. | `nb4` §8.10; overlap also asserted in `nb6`/`nb7` |
| `TI-LIM-001` | Curated drug-target reachability **98.5%**; pool-size/coverage ρ **+0.081**; only **2** diseases below 50%. | `nb2` §10.4 |

The registry governs these claims as bundles because their interpretation depends on the denominator
or comparator. For example, `TI-VAL-002` is not two interchangeable AUCs, and `TI-VAL-006` is not
permission to report only the larger route-supported value.

## 3. Metric meaning and uncertainty

### 3.1 Macro per-disease is the headline

Per-disease AUROC is the probability that a randomly chosen known target ranks above a randomly
chosen non-target for the same disease. It is macro-averaged over held-out diseases. The pooled value
is about seven points larger because it includes easy across-disease comparisons (`TI-VAL-001`,
`TI-VAL-002`). Report the distribution with the macro summary; never put pooled beside macro without
the warning.

AUROC is used for cross-disease reporting because its chance baseline stays 0.5 as prevalence varies.
AUPRC is retained for model selection and head-of-list questions, but raw per-disease AUPRC is strongly
tied to each disease's positive rate. Neither metric measures probability calibration.

Thin diseases need uncertainty, not a confident point estimate. A term below the 50-positive
usability floor can carry a ranked list and enrichment-at-K, but not a quotable AUROC. TNBC is the
load-bearing example: only eight positives make its normal-approximation interval exceed the possible
AUROC ceiling (`TI-VAL-009`).

### 3.2 Four axes, two ground truths

| axis | question | governed evidence | required caveat |
|---|---|---|---|
| association | Does the ranker reconstruct known disease–gene associations? | `TI-VAL-001`–`003` | study-biased retrospective label |
| therapeutic agreement | Do higher ranks agree with curated drug targets? | `TI-VAL-004`, `TI-VAL-006` | outcome-selected route and uneven feature support |
| discovery | Are novel high ranks enriched for approved/in-trial targets? | `TI-VAL-007` | a drug lookup can reward gene popularity |
| tractability | Does enrichment survive a degree-matched null? | `TI-VAL-008` | pooled and macro are different estimands; K is part of the claim |

Association AUROC and drug-target AUROC are statistically orthogonal (`TI-VAL-004`). Therefore a
model change is not adopted on association improvement alone. It must be corroborated on a
degree-matched axis and assessed for hub bias.

### 3.3 Hub bias is a measured weakness

Among rows already known to be positives, the champion assigns materially higher probability to
high-degree genes (`TI-VAL-005`). This holds biology constant and exposes network-position bias. The
earlier claim that the current generation improved under-studied targets was refuted: compared with a
retired generation, Q1 fell, Q5 rose and the spread nearly doubled. Restoring `prox_closest` recovered
only about 3% of that historical gap, so the proposed feature-level cause was also refuted. Population
differences remain a plausible explanation, not an established one.

## 4. Historical model evidence preserved for review

Historical rows are evidence for the selection rationale, not current governed claims. They remain
here so a future reviewer can see why `m7-f14` was chosen and why a larger single metric was rejected.

### 4.1 Original ablation ladder

| model | features | macro per-disease AUROC | drug-target AUROC | reading |
|---|--:|--:|--:|---|
| `m1-f7` | 7 | 0.7593 | 0.6787 | pruned core |
| `m2-f10` | 10 | 0.7882 | 0.6880 | provenance/degree controls recover useful signal |
| `m3-f12` | 12 | 0.8197 | 0.6911 | functional metapaths lift association most strongly |

The reference-generation values were 0.7617/0.6716, 0.7846/0.6845 and 0.8228/0.6836 respectively;
the rebuild preserved the ladder ordering. Pruning alone had failed: pooled AUROC stayed essentially
flat while macro per-disease AUROC fell. That negative result is why pooled AUROC cannot select the
model.

### 4.2 `m3` through `m8`

| model | macro AUROC | macro AUPRC | hub spread | drug all | drug supported | dm lift@200 | discovery lift@50 / @200 | verdict |
|---|--:|--:|--:|--:|--:|--:|--:|---|
| `m3-f12` | 0.8197 | 0.1737 | 0.1954 | 0.6911 | 0.7337 | 2.376 | 7.46 / 4.53 | former champion |
| `m4-f13` | 0.8200 | 0.1762 | 0.1932 | 0.6949 | 0.7371 | 2.381 | 7.09 / 4.83 | rejected |
| `m5-f13` | 0.8175 | 0.1711 | 0.1915 | 0.6931 | 0.7384 | 2.380 | 9.08 / 5.52 | never adopted; apparent discovery lead did not survive paired review |
| `m6-f13-new-pc` | 0.8197 | 0.1749 | **0.1900** | 0.6949 | 0.7418 | 2.391 | 7.43 / 4.78 | intermediate; pre-registered mechanism refuted |
| **`m7-f14`** | **0.8230** | 0.1778 | 0.1935 | 0.6886 | **0.7471** | **2.418** | **9.43 / 5.04** | adopted (`TI-MOD-001`) |
| `m8-f14-pm` | 0.8225 | **0.1816** | 0.1968 | — | — | flat-to-declining | mostly ties | rejected despite higher AUPRC |

Ties come before means. `m3`–`m6` were the same ranker for roughly 90% of diseases; discovery
differences rested on 9–15 high-leverage diseases. `m7` was the break: against `m6`, association and
degree-matched tractability both improved in paired tests with zero exact ties. `m8` then improved
AUPRC significantly, but AUROC was flat, tractability did not improve and hub spread worsened. It was
rejected under the rule that an association gain must be corroborated on the degree-matched axis.

The proposed `m7` mechanism was refuted. Spearman(module size, per-disease delta) was approximately
−0.003: the model works, but the saturation explanation does not. The adoption rests on multi-axis
paired evidence, not a causal story.

## 5. Negative results that constrain interpretation

- **Nearest-distance imputation did not reopen the missingness leak.** Re-scoring only rows where
  `prox_closest` was present left model gaps unchanged to four decimals.
- **Lowering the nearest-distance seed floor did not preferentially rescue sparse diseases.** The
  pre-registered treated-versus-control prediction failed; the aggregate movement came from a changed
  training population.
- **Training on the drug label was a dead end.** The probe achieved high row-split performance but
  collapsed under gene holdout and strict disease-plus-gene holdout; it mostly learned gene
  popularity. The deleted experimental chain's documentation-only figures (0.9324 versus 0.6444,
  439-of-1,507 hits@50, popularity baseline 0.9354) are historical and deliberately not governed.
- **Druggability as a model input was rejected.** Under the association label, membrane receptors
  are depleted even though they are enriched among drug targets, so the tree would learn the wrong
  direction. Druggability remains a presentation/annotation axis.
- **Safety proxies cannot be filters.** Loss-of-function constraint and observed liabilities both
  track target relevance or study history. Absence of a liability is not evidence of safety.
- **Morphological subtype resolution did not generalise.** Lung adenocarcinoma and squamous-cell
  lists were nearly identical because their source annotations were nearly identical. Molecular
  breast subtypes can separate (`TI-VAL-009`); neither result licenses a generic subtype promise.

## 6. Limits and honest use

### 6.1 Candidate-pool boundary

`TI-DATA-001` is a leakage control and a coverage boundary. `TI-LIM-001` shows that aggregate curated
drug-target coverage is high, not that every disease is well covered. A pathless pair remains
unscoreable by topology features; embeddings or richer upstream interactions are possible remedies,
not evidence already possessed. `TACSTD2` in triple-negative disease is the concrete failure case.

The GCD route also selects on the therapeutic outcome. Route-supported drug AUROC is higher than the
all-positive value (`TI-VAL-006`), but that difference measures scoreability under outcome-dependent
support. Both estimands must stay visible.

### 6.2 Discovery and therapeutic benchmarks

The discovery lift in `TI-VAL-007` is a useful retrospective check inside the admitted pool. It is
not a prospective trial-success rate and must not become an optimisation target: a drug-target lookup
can reward genes that are popular across indications. Report both approved and investigational
ground truths when making disease-level claims because their conclusions can differ.

### 6.3 Panel claims

The breast panel is designed to be falsified by a clinician, not to manufacture another aggregate.
HER2-positive disease provides a recognisable calibration spine, while TNBC exposes thin-label and
pool defects (`TI-VAL-009`). “Novel” means unannotated for that disease term, not unknown to science.
If a clinician rejects the known-target block, the novel block should not be presented as validated.

### 6.4 Evidence availability

Notebook assertions are authoritative for governed values. Some negative experiments survive only in
the archived record because their flow chains were intentionally deleted; those values are evidence
history, not live claims. The hub-bias notebook is the computational artifact for `TI-VAL-005`, so a
champion or population change must rerun it before the claim is refreshed.

## 7. Review path

1. Query `.index/governed_claims.tsv` for the affected `TI-*` IDs and consumers.
2. Run the named authoritative notebook checks; do not edit a value to make documentation agree.
3. Review the claim's precision/tolerance and interpretation in `CLAIM_REGISTRY.json`.
4. Update only the mapped consumers, preserving macro/pooled and axis semantics.
5. Run `tools/check_claim_registry.py --check` and `tools/check_indexes.sh`.

## References

Per-reference summaries, the feature-to-reference map and provenance caveats are in
[RESEARCH_NOTE.md](../reference/RESEARCH_NOTE.md). That corpus is unvalidated and must be checked
before client-facing use.

- Mountjoy et al., *Nature Genetics* (2021), Locus-to-Gene.
- Guney et al., *Nature Communications* (2016), network proximity.
- Menche et al., *Science* (2015), disease modules and incomplete interactomes.
- Himmelstein et al., *eLife* (2017), degree-weighted path counts.
- Huang et al., *Nature Medicine* (2024), path-explanation interpretability.
- Minikel et al., *Nature* (2024), genetic support and clinical success.
