# Demo narrative — what we show R&D scientists, and in what order

**Audience:** research scientists and computational biologists in early drug discovery, plus the
data-platform people who would own this internally.

**Read this before designing the dashboard or pruning the flow.** Both should be derived from the
story, not the other way round. We tried it the other way round and it produced a plan to delete our
best material.

---

## 1. The one thing to understand about this audience

They have seen a ranked gene list before. Several vendors have shown them one.

So they do not evaluate our accuracy. They run an **interrogation**, and they already know the
questions. Surviving that interrogation *is* the demo. The score is not the point — the score is
what we have left after the interrogation.

This is not a guess about buyer psychology. It is in the literature we already cite: the TxGNN study
(*Nature Medicine*, 2024) found that showing experts *why* a prediction was made raised their
accuracy by 46% and their confidence by 49%. **Explainability drove adoption. Accuracy did not.**

---

## 2. The demo, in the order they will ask

Six questions. Each one has an artifact behind it. Run them in this order, because each answer only
lands once the previous objection is dead.

### Q1 — "Show me the list."

Open the ranked candidates for one disease. Every candidate carries a score, the features that drove
it, and the actual paths through the graph that connect it to the disease.

Then show the filtering. A scientist sets their own thresholds — "must be a membrane protein",
"must not already be a known target", "must have a druggable pocket" — and the list narrows to
something a team could actually work through. For obesity that lands at **65 candidates**.

> **The point to make out loud:** the scientist is not asking the model to be right. They are asking
> to be able to argue with it.

### Q2 — "These are just the famous genes."

This is the first real objection and it is usually correct about other people's tools. Well-studied
genes have more connections in any biology database, so any graph model drifts towards them.

So we measured it. We compared each of our top candidates not against the average gene, but
**against other genes with the same number of connections** — a fair fight instead of a rigged one.

| Where in the list | Enrichment for druggable targets, vs equally-connected genes |
|---|--:|
| Top 10 | **2.9×** |
| Top 50 | **2.7×** |
| Top 200 | **2.4×** |

And the honest detail that makes it credible: **from rank 20 downwards, controlling for connectivity
makes our result look better, not worse.** Deep in the list the model is finding something that
popularity does not explain. But in the **top 10** it goes the other way — so the very head of the
list does carry a popularity effect, and we say so.

> **The point to make out loud:** we can tell you exactly where the popularity effect explains our
> ranking and where it does not. Nobody else in the room can do that for their own tool.

### Q3 — "You already knew all of these."

The strongest question, and the one the whole deliverable stands on.

So we delete the answer key. We remove every target already known for the disease, re-rank what is
left, and ask whether the top of *that* list contains real targets — ones we never told the model
about.

Take non-small cell lung cancer. The model scores **12,310** candidate genes. **621** are already
known targets. We throw all 621 away and look at the remaining **11,689**.

**The third-highest is MAPK3.** Nothing in the training data pointed at it. It is a **live clinical
programme** for that disease — MAPK3 is ERK1, the last step in the KRAS → MEK → ERK cascade that
drives much of lung cancer. Three more of the top 15 are also in trials.

Across all diseases, the novel candidates are enriched for real drug targets:

| | Top 10 | Top 200 |
|---|--:|--:|
| Against approved drugs | **11.4×** | **4.5×** |
| Against drugs in trials | **7.4×** | **4.0×** |

> **The point to make out loud:** this is the deliverable. Not "the model reproduces what you know" —
> it surfaces things you have not annotated, and a meaningful share of them turn out to be real.

### Q4 — "Your ground truth is garbage."

Also usually correct, and we agree. Here is the flaw, in one sentence: the public data says *this
drug treats this disease* and *this drug hits these targets*, but never *this target treats this
disease*. Joining the two invents pairs. A drug that hits 40 proteins and is approved for 13
diseases manufactures 520 "validated" pairs.

We measured how bad it is: **82% of our validated pairs come from drugs that hit more than one
target.** Only **8%** survive if we demand single-target drugs.

Then we found a curated source that asserts the target–disease link directly, and re-ran everything
on it. **The discovery result got stronger** — 17.7× instead of 11.4×.

> **The point to make out loud:** we found the flaw in our own evidence, quantified it, and re-tested
> against a better source. The finding survived. That is what due diligence looks like.

### Q5 — "Would this work on a disease you had not tuned?"

We never let related diseases sit on both sides of the train/test divide. If "diabetes" trains the
model and "type 2 diabetes" tests it, the score is meaningless — same programme, different label.

Measured across **505 disease families**, average ranking quality holds at **0.80**. Headline number
across 670 individual diseases: **0.82**.

### Q6 — "What can't it do?"

Show the limits. This is not modesty, it is what makes Q1–Q5 believable.

- **It cannot tell lung cancer subtypes apart.** Lung adenocarcinoma and squamous carcinoma get
  near-identical lists, because the underlying data barely distinguishes them. We show why.
- **It leans towards secreted proteins in some diseases** — molecules floating between cells rather
  than sitting on them. Harder to drug. We measured where this happens and where it does not.
- **We have no real safety axis and we are not pretending otherwise.** See below — this is the
  strongest part of the pitch.

---

## 3. The punch line

Everything above is about the model. This is about the platform, and it is the part that closes.

> **Three times in this project, an idea that every biologist in the room would have approved was
> killed by a measurement that took one afternoon. Each one would have made the product worse.**

**"Use druggability as a model input."** Obviously sensible — prefer genes we know how to drug.
Measured: it points the *wrong way*. Membrane receptors are 3.2× more likely to be real drug targets
but 1.3× *less* likely to be linked to the disease in our data. A model given this feature learns
"membrane receptor → score it lower". We rejected it, and instead grouped the *display* by
druggability class. That recovered most of the benefit at no risk to the model.

**"Filter out genes the human body cannot live without."** Sensible: if losing a gene is lethal,
blocking it is dangerous. We predicted real drug targets would avoid these genes. **The measurement
showed the exact opposite**, cleanly and in one direction. Genes that matter enough to be lethal are
genes that matter enough to be worth drugging — and a drug is not a genetic deletion. Rejected.

**"Exclude targets with known safety liabilities."** The most obviously-right of the three. Measured:
it destroys 15–70% of the confirmed hits, and for obesity it makes the shortlist **worse than no
filter at all**. The reason a biologist can check in thirty seconds: **ADRB2 sits at rank 17, is a
confirmed obesity target, and carries a liability flag.** The filter would have deleted it.

Why it happens: safety liabilities get discovered *by* drugging a target. The flag marks the
best-studied targets, not the most dangerous ones.

**And the slide no vendor shows you:** on one of our benchmarks we found that a dumb lookup table —
"how many diseases is this gene already a drug target for" — scores **0.935** and **beats our trained
model**. So we refused to use that benchmark as a headline. A benchmark a lookup table wins is
measuring the lookup, not the model.

> **The platform claim:** you do not need a better algorithm. You need somewhere your biologists'
> hypotheses get tested in an afternoon instead of argued about for a quarter. Three plausible ideas
> died here at a cost of one recipe each — and the record of why is sitting in the flow, not in
> someone's inbox.

---

## 4. Where the customer's own knowledge enters

This is what the question "can it integrate *our* expertise" actually means, and we have a concrete
answer rather than a promise.

**We already demonstrate it once.** Our train/test divide comes from a curated medical ontology, not
from an algorithm. A biologist's judgment — *"type 2 diabetes and diabetes mellitus are the same
programme, do not let them straddle"* — became a rule in the pipeline and changed the honest score.
**That is domain expertise compiled into a control.** It is the template for everything below.

| What they plug in | Why it matters | Why we cannot fake it |
|---|---|---|
| **Failed internal programmes** | Our own analysis found that trial-stage evidence — which includes failures — is the *fairer* test for target discovery, and it is 13× larger than approved-drug evidence | Nobody publishes their failures. This is the highest-value private asset in the whole pipeline |
| **Internal assay and screening data** | Replaces our public druggability proxy with a real, measured one | We flagged the public version as a proxy; this is the fix |
| **Their own disease definitions** | Their indication strategy replaces the public ontology as the grouping rule | Their commercial thinking, not ours |
| **Expert annotations and thresholds** | The biologist tunes the shortlist without touching the model | Already built — the filter in Q1 |

**The line to use:** the public data buys you the genetic-evidence effect — targets with human
genetic support are 2.6× more likely to survive the clinic *(Minikel et al., Nature 2024)*. Your own
graph is the only place the rest of your institutional knowledge can enter the ranking at all.

---

## 5. What not to show

| Do not show | Because |
|---|---|
| The ablation ladder (7 → 10 → 12 features) | A modelling decision. No scientist asks it, and it invites a conversation about hyperparameters |
| Raw AUC as the opening number | It is the answer to a question they did not ask. Lead with Q3, land the AUC at Q5 |
| The drug-target benchmark as a headline | We know a lookup table beats us on it. Use it as the honesty slide (§3), never as a score |
| Feature engineering internals | 12 features, and the interesting ones are graph paths. Show the paths, not the column list |
| A safety or toxicity claim of any kind | We do not have one. Saying so is worth more than faking one |

---

## 6. Demo diseases

Chosen by measurement, not by familiarity — see TARGET_PRIORITIZER §8.8.

| Disease | Why it earns its slot |
|---|---|
| **Non-small cell lung carcinoma** | The MAPK3 story. Best ranking precision in the panel (19× enrichment) |
| **HER2-positive breast carcinoma** | **Passes clinical sanity outright** — ERBB2 at rank 13, PI3K/AKT in the top 10. AUC 0.93 on 599 known targets. The arm to lead with in front of a clinician |
| **Diabetes mellitus** | Best discoverer of *approved* targets across all 670 diseases |
| **Obesity disorder** | The filtering story, the ADRB2 counterexample, and a strong tractability result |

**Triple-negative breast carcinoma is the deliberate hard case, not a fourth showcase.** Its list is
the only genuinely subtype-specific one in the breast panel and the only one we cannot score (8 known
associations). Use it for Q6 — *"here are four things we already think are wrong with this list"* —
never as a success story. See [BREAST_SURGEON_BRIEFING.md](docs/annotation/BREAST_SURGEON_BRIEFING.md).

**Retire:** type 2 diabetes (weakest case on every axis, and its parent term is the strongest),
chronic kidney disease (below chance on discovery), and two of the three lung terms (they share ~63%
of their lists — one is enough).

**Breast is now measured, not assumed.** PROJECT_CONTEXT §3 recommended "breast cancer" on no
evidence; the generic `breast cancer` term turns out to be the **worst** in the breast panel (AUC 0.69,
beaten by its own subtypes). Use **HER2-positive** instead — see TARGET_PRIORITIZER §8.13.

---

## 7. Numbers sheet

Re-verified against live project data on 2026-08-19 where marked ✓.

| Claim | Value | |
|---|--:|:--|
| Ranked candidates delivered | 129,253 over 13 diseases | ✓ |
| NSCLC candidate pool / known / novel | 12,310 / 621 / 11,689 | ✓ |
| MAPK3 for NSCLC | novel #3, list #61 | ✓ |
| Discovery lift, approved drugs, top 10 / 200 | 11.4× / 4.5× | ✓ |
| Discovery lift, trial-stage drugs, top 10 / 200 | 7.4× / 4.0× | ✓ |
| Degree-matched tractability, novel, top 10 / 50 / 200 | 2.9× / 2.7× / 2.4× | ✓ |
| Disease families measured | 505 | ✓ |
| Macro ranking quality, 670 diseases | 0.82 | |
| Per-family ranking quality | 0.80 | |
| Inflated pairs from multi-target drugs | 82% | |
| Discovery lift on the curated label | 17.7× | |
| Lookup-table baseline that beats the model | 0.935 | |
| Obesity shortlist after filtering | 65 candidates | |

---

## Appendix — decision log

| Date | Decision |
|---|---|
| 2026-08-19 | **The demo is an objection ladder, not a scorecard.** Six questions in a fixed order, each with an artifact. Derived from the audience's actual scepticism rather than from our metric list. Consequence: the confound controls, leakage audits and refuted gates are **front-of-house material, not appendix material** — they are the answers to Q2, Q4 and Q6. |
| 2026-08-19 | **Rejected deriving the flow from the dashboard.** A pruning plan built on "does this feed the dashboard" cut 46 of 62 validation items — including the degree-matched tractability control, the entire leakage audit and the per-family generalisation evidence. The dashboard does not exist yet, so the criterion was circular. **Replaced with: does a scientist ask this out loud in the room?** |
| 2026-08-19 | **The platform pitch is the gate, not the model.** Three expert-plausible ideas were killed by measurement at ~one recipe each (druggability as a feature, loss-of-function filtering, liability exclusion). This is the reusable capability claim and it needs no dashboard to demonstrate. |
| 2026-08-19 | **CORRECTION to TARGET_PRIORITIZER §8.4, found while fact-checking this document.** The claim "controlling for connectivity strengthens the result" was stated unconditionally. Its evidence was a table row putting a **pooled** degree-matched lift (3.06×) beside a **macro** naive lift (2.97×) — two different estimators, which manufactured the crossover. Recomputed consistently, degree-matching helps from rank 20 down but **hurts at rank 10** under both estimators (pooled 3.06 vs 3.31; macro 2.86 vs 2.97). The quotable range is unaffected. **The corrected version is the better demo line** — being able to say where popularity does and does not explain the ranking beats claiming it never does. |
| 2026-08-19 | **Every headline number in §7 was re-verified against live project data before this document was written**, not carried from prose. MAPK3 confirmed at novel #3 / list #61 for NSCLC off `scored_m3`; pool 12,310 / 621 known / 11,689 novel; discovery and tractability lifts recomputed from `novel_discovery_eval` and `tractability_axis`. **One of the six checks found an error** (above), which is the argument for doing it. |
