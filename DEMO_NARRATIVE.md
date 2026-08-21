# Demo narrative — what we show R&D scientists, and in what order

**Audience:** research scientists and computational biologists in early drug discovery, plus the
data-platform people who would own this internally.

**Read this before designing the dashboard or pruning the flow.** Both should be derived from the
story, not the other way round. We tried it the other way round and it produced a plan to delete our
best material.

---

## What you are demoing — the one-page version

**The deliverable.** For a given disease, a ranked shortlist of candidate targets, each with **two
independent explanations**: a SHAP attribution (*which evidence drove this*) and a **graph path** to the
disease module on the webapp (*show me the mechanism*).

**The artifact.** `target_candidates_2` — **129,253 scored candidates across 13 diseases**, each row
carrying score, SHAP drivers, rank, known-target status, druggability class, tractability and safety
annotation. Nothing is pre-cut: the scientist filters.

| | |
|---|---|
| **Model** | gradient-boosted trees + SHAP, 12 network-topology features |
| **Why not a GNN** | it is the Open Targets Locus-to-Gene pattern (*Nat Genet* 2021). The differentiator is reproducibility and lineage, not the algorithm |
| **Ranking quality** | macro per-disease AUC **0.82** over 670 held-out diseases; **0.80** across 505 families |
| **Discovery** | novel candidates enriched **16.9×** for approved drug targets at top-10 |
| **Actionability** | **2.4–2.9×** enrichment for druggable targets vs equally-connected genes |
| **What it does not do** | no safety axis, no *morphological* subtype resolution, and association ranking does **not** predict therapeutic relevance (r = +0.024) |

**Progressive filtering is the demo moment** — obesity disorder, on the scientist's own thresholds:
13,126 candidates → novel only 12,364 → tractable 8,615 → not secreted 7,877 → rank ≤ 200 **≈ 70**.
Landing on GHSR (#8), ADRB2 (#17), MCHR1 (#23) — a coherent neuroendocrine cluster, two of them
clinically pursued for obesity.

**Method, and every number's source: [TARGET_PRIORITIZER.md](TARGET_PRIORITIZER.md)** — all 38 of its
subsections name the dataset they come from and the notebook that re-derives them. 44 of 44 assertions
passed on 2026-08-19, so anything quoted here is verified, not remembered.

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

**Then there is the harder version of the same question, and it is the natural follow-up — so get
there first.** Hold the biology constant: take only genes we *already know* are targets, and ask whether
the model scores the poorly-connected ones as highly as the hubs.

| known targets, by connectivity | mean model score | predicted positive |
|---|--:|--:|
| lowest fifth *(median 6 connections)* | **0.59** | **17.3%** |
| highest fifth *(median 155)* | **0.79** | **57.0%** |

**A 3.3× detection swing on network position alone, with biology held constant.** Both things are true
and they answer different questions: the *ranking* is not explained by popularity (the table above), and
the model still **under-scores under-studied true targets**.

> **What to say:** *"We will find you targets adjacent to biology you already know. We will not fix your
> neglected-gene problem — and we can hand you the number today instead of you discovering it in year
> two."* Then the part that lands: **we went looking for the cause, tested the obvious candidate, and it
> was not the cause** — so we are still carrying this as an open weakness rather than a fixed one
> (TARGET_PRIORITIZER §7.2). Say that. A vendor who names an unsolved problem is worth more than one who
> names only solved ones.

> **The point to make out loud:** we can tell you exactly where the popularity effect explains our
> ranking and where it does not, and what it costs. Nobody else in the room can do that for their own
> tool.

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
| Against approved drugs | **16.9×** | **5.0×** |
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
on it. **The discovery result got stronger** — 21.3× instead of 16.9×.

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

Everything above is about the model. This is about the platform, and it is what closes.

> **Three times in this project, an idea every biologist in the room would have approved was killed by
> a measurement that took one afternoon. Each would have made the product worse.**

- **"Use druggability as a model input."** Measured: it points the *wrong way*. Membrane receptors are
  3.2× more likely to be real drug targets but 1.3× *less* likely to be disease-linked in our data, so
  the model would learn "membrane receptor → score lower". Rejected; grouped the *display* by class
  instead, which recovered most of the benefit at no risk.
- **"Filter out genes the body cannot live without."** We predicted drug targets would avoid them.
  **The measurement went cleanly the other way.** Genes that matter enough to be lethal are genes worth
  drugging — and a drug is not a genetic deletion. Rejected.
- **"Exclude targets with known safety liabilities."** The most obviously-right of the three. Measured:
  it destroys 15–70% of confirmed hits and makes obesity **worse than no filter**. The thirty-second
  check: **ADRB2 sits at rank 17, is a confirmed obesity target, and carries a liability flag.**
  Liabilities are discovered *by* drugging something, so the flag marks the best-studied targets.

**And the slide no vendor shows you:** on one benchmark a dumb lookup table — *"how many diseases is
this gene already a drug target for"* — scores **0.935** and **beats our trained model**. So we refused
to headline that benchmark. A benchmark a lookup table wins is measuring the lookup.

> **The platform claim:** you do not need a better algorithm. You need somewhere your biologists'
> hypotheses get tested in an afternoon instead of argued about for a quarter. Three plausible ideas
> died here at one recipe each — and the record of why is in the flow, not someone's inbox.

## 4. Where the customer's own knowledge enters

**We already demonstrate this once.** The train/test divide comes from a curated medical ontology, not
an algorithm. A biologist's judgment — *"type 2 diabetes and diabetes mellitus are the same programme,
do not let them straddle"* — became a rule in the pipeline and changed the honest score. **That is
domain expertise compiled into a control**, and it is the template for everything below.

| What they plug in | Why it matters |
|---|---|
| **Failed internal programmes** | Trial-stage evidence — which includes failures — is the *fairer* test for target discovery and is 13× larger than approved-drug evidence. Nobody publishes their failures; this is the highest-value private asset in the pipeline |
| **Internal assay / screening data** | Replaces our public druggability proxy with a measured one |
| **Their own disease definitions** | Their indication strategy replaces the public ontology as the grouping rule |
| **Expert annotations and thresholds** | The biologist tunes the shortlist without touching the model — already built, it is the filter in Q1 |

**The line to use:** the public data buys you the genetic-evidence effect — genetically supported
targets are 2.6× more likely to survive the clinic *(Minikel et al., Nature 2024)*. **Your own graph is
the only place the rest of your institutional knowledge can enter the ranking at all.**

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

Chosen by measurement, not familiarity — TARGET_PRIORITIZER §8.7 and §8.10.

| Disease | Why it earns its slot |
|---|---|
| **Non-small cell lung carcinoma** | the MAPK3 story; best ranking precision in the panel (19× enrichment) |
| **HER2-positive breast carcinoma** | passes clinical sanity outright — ERBB2 at rank 13, PI3K/AKT in the top 10, AUC 0.93 on 599 known targets. **Lead with this one in front of a clinician** |
| **Diabetes mellitus** | best discoverer of *approved* targets across all 670 validation diseases |
| **Obesity disorder** | the filtering story and the ADRB2 counterexample |

**Triple-negative breast is the deliberate hard case, not a fifth showcase.** Its list is the only
genuinely subtype-specific one in the breast panel and the only one we cannot score (8 known
associations). Use it for Q6 — *"here are four things we already think are wrong with this list"* —
never as a success story. See [BREAST_SURGEON_BRIEFING.md](docs/annotation/BREAST_SURGEON_BRIEFING.md).

**Retire:** type 2 diabetes (weakest on every axis, and its parent term is the strongest), chronic
kidney disease (below chance on discovery), and two of the three lung terms (~63% shared lists).

## 7. What each disease's list actually looks like

The qualitative half of validation — and useful in the room, because a scientist checks coherence
before they check any metric.

| Disease | Signature of the top candidates |
|---|---|
| **NSCLC / lung adenocarcinoma** | JAK-STAT and chromatin (STAT1, STAT5A/B, SMARCA2, HDAC3), the PI3K axis (IRS1/2, PIK3R2, PDPK1), DNA repair (MRE11, TOPBP1), and CRKL — an amplified 22q11 driver |
| **HER2-positive breast** | ERBB2 itself at #13, TP53 #2, PIK3CA #7, AKT1 #10 — the PI3K/AKT axis that actually drives trastuzumab resistance |
| **triple-negative breast** | the homologous-recombination panel: RAD50, NBN, ATM, BRCA2, BRIP1, BARD1, RAD51C. **Read the briefing before showing this one** |
| **obesity disorder** | GHSR (#8, ghrelin receptor), ADRB2 (#17, approved-validated), MCHR1 (#23) — a coherent neuroendocrine receptor cluster |

**Ranking quality falls monotonically with rank**, pooled over personas: known-target density 60.0%
(ranks 1–10) → 43.3% (41–50). **That is calibration evidence, not a novelty ceiling.**

## 8. The on-graph shot

**Anchor demo:** the breast-cancer top-10 contained **RAD50, NBN and MRE11** — all three members of the
MRN double-strand-break repair complex, two of them novel. *The prediction explains itself on the
canvas.*

```cypher
// Why these genes? Top-10 predictions + interaction evidence to a KNOWN module gene.
MATCH (D:disease {node_index: $disease})
MATCH (g:protein) WHERE g.node_index IN $top10
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D LIMIT 300
```

Three conventions that will bite you: traversal is **undirected**; relationship variables must be
**bound and returned** or the canvas shows floating nodes; the engine's label for genes is `protein`.
Node indices are snapshot-specific — **re-derive before running**. Use the interactive explorer, not the
query recipe.

⚠ **If you also show the drug path** (`gene ← drug → disease`), be precise: no model consumes it as a
feature, but it *is* one of three routes admitting pairs to the candidate pool, so it shapes the scored
population (TARGET_PRIORITIZER §5.2.1). **Say "not a feature", not "not used".**
