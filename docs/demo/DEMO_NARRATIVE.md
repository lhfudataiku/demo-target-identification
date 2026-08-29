# Demo narrative — reconstructing known biology from public knowledge

> **Lifecycle:** Canonical · **Audience:** research scientists, computational biologists and the
> data-platform team supporting them · **Authority:** business story, act order, audience voice and stable
> interpretation · **Update when:** the demo claim, audience or act order changes · **Generated
> dependencies:** notebook assertions; [`FLOW_MAP.md`](FLOW_MAP.md) for live flow lineage · **Excludes:**
> API design, DSS topology and build procedure.

**Who we are in this room.** An AI platform company. We are not a drug-discovery vendor, we are not
proposing to run anyone's target programme, and we are not going to tell a research team how to do
science. We build the machinery that lets their people test their own ideas quickly and show their
working.

**What this demo claims — and only this.** From public biomedical knowledge alone, a model can be
trained that, for a given disease, surfaces the targets the field has already validated. That is a
**reconstruction** claim, not a discovery claim.

**The bar, and it is deliberately low.** The test is the scientific team's own eyeball test: *open the
list for a disease you know, and tell us whether the top of it looks right.* We are not asking them to
accept a benchmark, and we are not claiming to have found anything they have not.

**Why a low bar is the right bar.** If a pipeline built only from public knowledge reconstructs what
your field already established, then the machinery is sound — the graph, the features, the split, the
scoring, the lineage. That is what earns the next conversation, which is the interesting one: point
the same pipeline at *your* data, where nobody knows the answer yet.

**Audience:** research scientists and computational biologists in early discovery, plus the
data-platform people who would own this internally. The second group is not an afterthought — they are
the ones who have to believe it is reproducible.

The technical companion — the implementation architecture, data contracts and guardrails that support
each act — is [WEBAPP_DESIGN.md](WEBAPP_DESIGN.md). Every number below is asserted in a
notebook and re-checked on every run.

---

## What we are explicitly not claiming

Say these out loud, early. They are what make the rest credible, and every one of them is a place a
competitor would overclaim.

| We are not claiming | What is true instead |
|---|---|
| That we discover novel targets | The model ranks not-yet-annotated genes above chance, and we will show you the number. It is **not** what we are asking you to believe today |
| That this beats your in-house method | We have not seen your method. This is a reconstruction test on public data |
| Any safety or toxicity assessment | We have none. The annotations we carry are public flags, and we will show you why they are not a filter |
| That the ranking is a research plan | It is a starting list that a scientist filters on their own thresholds |
| Domain expertise in your therapeutic area | You have that. We built the machine that makes your expertise testable |

---

## The four acts

Each act answers one question. The order matters: a scientist will not engage with a ranking until
they believe the substrate it came from.

| | Act | The question | What answers it |
|---|---|---|---|
| 1 | **The evidence base** | *What went in?* | six public sources, provenance on every node and edge |
| 2 | **Calibration** | *How faithfully does it reconstruct?* | the distribution across 670 diseases, not one number |
| 3 | **The therapeutic area** | *Does it hold across my area?* | every term in a family, with its uncertainty |
| 4 | **The list** | *Does this look right to you?* | the eyeball test — and they filter it themselves |

Acts 5 and 6 are a **spoken talk track**, not screens. They are about the platform, not the biology.

---

## Act 1 — The evidence base

> *What went in?*

A biomedical knowledge graph assembled from six public sources — **113,391 nodes, 2,851,510 edges, 18
relations** — and accepted against a frozen reference at **−0.03% on edges, with 14 of 18 relations
reproducing exactly**.

No model yet. This act is about what the machine can see, and about the fact that every node and every
edge can name where it came from.

**Why it goes first.** Nothing later is worth discussing if the substrate is not credible. A scientist
who does not believe the graph will not engage with the ranking — and rightly.

**What this act must not do:** claim quality. Faithful assembly is a lineage property, not an accuracy
one. Whether the ranking is any good is Act 2.

---

## Act 2 — Calibration

> *How faithfully does it reconstruct?*

The candidate pool is **6,754,128 disease–gene pairs at a 1.89% positive rate**. Ranking quality is
**macro per-disease AUC 0.8230 across 670 held-out diseases**.

**Read that as reconstruction fidelity, not predictive power.** It says: across 670 diseases, the model
puts the already-validated targets near the top of the list. That is the claim, and it is the claim
the eyeball test in Act 4 makes concrete.

**Show the distribution before the summary.** A single number answers a question nobody asked, and it
hides the thing that actually matters — that usefulness is not uniform. Some diseases reconstruct
almost perfectly; some do not reconstruct at all. **Which is which is more useful to them than the
average.**

**Report macro, never pooled.** Pooled reads 0.8932 and overstates by roughly seven points, because it
lets large diseases carry small ones. We show the macro figure.

### The one thing to raise before they do

Well-studied genes carry more edges in any public database, so any graph model drifts toward them. We
measured it against genes of the **same network degree** rather than against the pool average:

| | degree-matched enrichment |
|---|--:|
| Top 10 | **3.29×** |
| Top 200 | **2.42×** |

And the honest half: hold biology constant — known targets only — and the model still scores the
least-connected fifth at **0.59** against **0.79** for the most-connected. **The model under-scores
under-studied true targets.** We have not fixed that, and we are not going to imply we have.

> **How to put it:** *"This reconstructs biology adjacent to what is already well described. Where your
> field is under-studied, it will under-rank — here is the size of that effect, measured, today."*

---

## Act 3 — The therapeutic area

> *Does it hold across my area, or just on one term?*

Most groups own one therapeutic area, so a single cherry-picked disease proves nothing. Pick a family
and show the same model against **every term in it**.

**Across 505 disease families, reconstruction holds at 0.8009.**

**How the split was drawn, because it is the honest part.** Train and test are separated by disease
family from a curated medical ontology, not at random. Random splitting puts "diabetes" and "type 2
diabetes" on opposite sides — the same programme wearing two labels — and inflates the score. Using
the ontology *lowered* the number we report.

**This is also where a customer's own judgment already enters.** The rule that these two terms are one
programme is a biologist's call, compiled into the pipeline. It is the template for everything they
would plug in later.

**Per-term AUC is shown with its uncertainty.** A term with eight known targets and a term with six
hundred do not deserve the same visual weight.

**And the limit lives here.** HER2-positive and triple-negative breast share only **2** novel
candidates and **14** genes overall — genuinely different lists. Lung subtypes are the opposite: near
identical, because the public data barely distinguishes them. **We can tell you which of your subtypes
this resolves before you build anything on it.**

---

## Act 4 — The list, and the eyeball test

> *Does this look right to you?*

One disease, all the way down. **This is the act the demo exists for.**

Open **HER2-positive breast carcinoma**. The model reconstructs its known targets at **AUC 0.9365**.
Look at the top of the list: the genes a breast oncologist would name are there. That is the whole
test, and the scientist is the instrument.

**Then hand them the controls.** Nothing is pre-filtered. They set their own thresholds — must be a
membrane protein, must have a druggable pocket, exclude what is already known — and a five-figure list
narrows to something a team could work through in a quarter.

**Two explanations per candidate**, because one is never enough: the SHAP attribution (*which evidence
drove this*) and the path on the graph (*show me the mechanism*). A feature attribution without a
mechanism is a scoreboard; a mechanism without an attribution is a story.

### The secondary observation, offered as a footnote

If you remove every known target for a disease and re-rank the remainder, the top of that list is
enriched for genes that later turn out to be real drug targets — **16.88× at top-10 against approved
drugs, 21.32× against a curated target–disease source**.

> **Frame it exactly this way:** *"We report this because it is measured, not because we are asking you
> to act on it. Today's claim is the reconstruction you just looked at. What this number suggests is
> that the same machinery is worth pointing at data where the answer is not already known — which is
> your data, not ours."*

**Do not lead with this. Do not let it become the demo.** It is the one place where a reconstruction
pitch can slide into a discovery pitch, and the slide is not recoverable in the room.

---

## Acts 5 & 6 — the talk track

**Not screens.** These are about the platform, and they are the part a data-platform owner buys.

### What the machinery did with three hypotheses

Three times in this project, a plausible idea was tested and the measurement came back against it.
**The point is not that the ideas were wrong — it is that each took an afternoon to settle instead of
a quarter to argue about.**

| The idea | What the measurement said |
|---|---|
| *"Use druggability as a model input."* | Membrane receptors are **3.16×** more likely to be real drug targets but only **0.78×** as likely to be disease-linked in public data. A model trained on the association label would learn *score lower*. Ion channels, same shape, **11.89×** |
| *"Filter out genes the body cannot live without."* | Loss-of-function-intolerant genes are enriched on **both** labels — **2.07×** association, **1.37×** therapeutic. A drug is not a genetic deletion |
| *"Exclude targets with known safety liabilities."* | Liability-flagged genes are **4.62×** enriched among real drug targets. Liabilities are discovered *by* drugging something, so the flag marks the best-studied targets. **9 of the HER2+ top 15 carry one — including ERBB2** |

> **The platform claim, and it is the only claim we make in our own voice:** these were settled by one
> recipe each, and the record of why is in the flow where the next person can find it — not in
> someone's inbox. **That is the capability we are selling.** Which hypotheses are worth testing is
> their call, not ours.

### One honest limitation, stated because it will be found

Association ranking does **not** predict therapeutic relevance: across diseases the two are
uncorrelated, r = **+0.002**. And on a drug-target benchmark, a lookup table — *"how many diseases is
this gene already a target for"* — beats the trained model. **A benchmark a lookup table wins is
measuring the lookup**, so we do not report it as a score.

---

## Where their own knowledge enters

This is the bridge to the next conversation, and the reason a low bar today is worth setting.

| What they plug in | What it changes |
|---|---|
| **Failed internal programmes** | Trial-stage evidence — including failures — is far larger than approved-drug evidence and nobody publishes it. The highest-value private asset here |
| **Internal assay / screening data** | Replaces a public druggability proxy with a measured one |
| **Their own disease definitions** | Their indication strategy replaces the public ontology as the grouping rule |
| **Expert annotations and thresholds** | Tunes the shortlist without retraining — already built; it is the filter in Act 4 |

**The line to use:** public knowledge gets you the reconstruction you just saw. **Your own data is the
only place the rest of your institutional knowledge can enter the ranking at all** — and that is a
platform problem, which is ours, not a science problem, which is yours.

## Demo diseases

| Disease | Why it earns its slot |
|---|---|
| **HER2-positive breast carcinoma** | **the spine.** Reconstructs at AUC **0.9365**; a clinician recognises the top of the list immediately. Lead with this |
| **Non-small cell lung carcinoma** | strong reconstruction, and the subtype limitation is visible in the same family |
| **Diabetes mellitus** | broad, well-annotated, reconstructs cleanly |
| **Obesity disorder** | the filtering story — a coherent neuroendocrine cluster the scientist can sanity-check |

**Triple-negative breast is the deliberate hard case.** Only 8 known associations, so it cannot be
scored — use it in Act 3 to show where the method runs out, never as a success story. See
[BREAST_SURGEON_BRIEFING.md](BREAST_SURGEON_BRIEFING.md).

## What not to show

| Do not show | Because |
|---|---|
| Novel discovery as the headline | It is the claim we are explicitly not making today. Footnote only |
| The ablation ladder (7 → 10 → 12 → 14 features) | A modelling decision nobody asked about |
| Raw AUC as the opening number | It answers a question they did not ask. Lead with the evidence base |
| The drug-target benchmark as a score | A lookup table beats us on it |
| Any safety or toxicity claim | We do not have one |
| Drug badges as a filter | They are the ground truth the enrichment is measured against |
| Advice on how to run their discovery programme | Not our expertise, and claiming it costs us the room |

## The on-graph shot

The mechanism view is what makes a ranked row into something a scientist can argue with: top-ranked
genes, plus the interaction edges connecting them to genes already associated with the disease.

```cypher
// Why these genes? Top-10 predictions + interaction evidence to a KNOWN module gene.
MATCH (D:disease {node_index: $disease})
MATCH (g:protein) WHERE g.node_index IN $top10
MATCH (g)-[ppi:protein_protein]-(m:protein)-[assoc:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, ppi, m, assoc, D LIMIT 300
```

**Pick the anchor from the live ranking, not from memory.** The often-quoted version — *"the breast
top-10 contained RAD50, NBN and MRE11, the whole MRN repair complex"* — does not survive checking:
those rank **55, 99, 401** on HER2+ and **1, 5, 702** on TNBC. Re-derive the cluster on the disease you
are demoing, the morning of the demo, and name the ranks you actually see.

Three conventions that will bite you: traversal is **undirected**; relationship variables must be
**bound and returned** or the canvas shows floating nodes; the engine's label for genes is `protein`.
Node indices are snapshot-specific — re-derive before running.

⚠ **If you also show the drug path** (`gene ← drug → disease`), be precise: no model consumes it as a
feature, but it *is* one of three routes admitting pairs to the candidate pool. **Say "not a feature",
not "not used".**
