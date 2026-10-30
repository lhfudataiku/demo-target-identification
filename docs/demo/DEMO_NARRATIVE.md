# Demo narrative — reconstructing known biology from public knowledge

<!-- Governed claims consumed here: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-002 TI-VAL-003 TI-VAL-004 TI-VAL-007 TI-VAL-008 TI-VAL-009 -->

> **Lifecycle:** Canonical · **Audience:** presenters, research scientists, computational biologists
> and the data-platform team supporting them · **Authority:** the demo's story line, the message of
> each webapp page and section, and what is said around them · **Update when:** the demo claim, the
> audience, or a webapp page or section changes · **Generated dependencies:** notebook assertions;
> [`FLOW_MAP.md`](../operations/FLOW_MAP.md) for live flow lineage · **Excludes:** API design, data
> contracts and DSS topology, which are in [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md).

## The story

**One platform can bring machine learning and agentic AI to many kinds of data, and still support
rigorous science.** The demo makes that case on one concrete task: screening drug targets for a
disease.

A bench scientist screening targets today assembles the evidence by hand. Gene–disease links sit in
one database, tractability in another, drugs and their trials in a third, and the literature
everywhere. The demo shows that work done in one place. A knowledge graph built from public sources
feeds a model that ranks every candidate gene for a disease. Each ranked gene arrives with its
tractability, its drug history, the trials and papers that mention it, and an assistant that answers
questions from those sources. Every sentence the assistant writes shows where it came from.

The app has two pages, and they carry the two halves of the argument:

- **The shortlist is the deliverable.** It is what a scientist would use: one disease, every
  candidate ranked, and the evidence for any one of them on the same screen.
- **Why trust the list is the evidence.** It makes the shortlist traceable and reproducible: what went
  in, how well the model reconstructs known biology, and whether that holds across a disease family.

The scope is deliberately narrow. The data is public, a selected set of sources. The panel is twelve
diseases, and the claim is **reconstruction**: from public knowledge alone, the model puts the
targets the field already validated at the top of the list. That is a low bar on purpose. If the
machinery reconstructs what a field already knows, it is sound enough to point at the customer's own
data, where nobody knows the answer yet. That is the conversation the demo exists to open.

---

## Page 1 — The shortlist: screening a disease

> *Everything a scientist needs to judge a candidate, integrated on one screen, and every piece
> carries its source.*

The demo follows one scientist through one screening session, from the whole ranked list down to a
single gene they can argue about.

**Start with a disease they know.** Open **HER2-positive breast carcinoma** and ask the room: *does
the top of this list look right?* A breast oncologist reads the PI3K/AKT and RAS–MAPK axis in the
first rows. Those are targets the field has already validated, and the model has put them first. The
model reconstructs this disease's known targets at **AUC 0.9365**, but the page shows no AUC: the
scientist's own judgment is the test, and the list speaks first.

**Then let them narrow it on their own terms.** Nothing is pre-filtered. The controls are the
scientist's: novel only, tractable, small molecule or antibody, target class, exclude secreted
proteins, rank cut-off. The funnel above the list shows what each step removed. Turn on *novel only*,
*tractable* and *exclude secreted*: 12,272 candidates become 38 in the top 200. The third is
`SMARCA2`, an epigenetic regulator that the graph does not link to this disease as a target.

That row is what the list is for. Leave `ERBB2` aside, however recognisable: it is already a positive
label for this disease, so its rank shows only reconstruction. `SMARCA2` is a candidate a scientist
would want to examine, and selecting it makes every panel below describe it.

The next four tabs each add a different kind of evidence about the same gene.

**Overview — the brief.** *What a scientist checks first, assembled without an LLM.* A fixed summary
built from the data: the score's strongest driver, the gene's association in the graph, the drug
evidence for this exact disease, and what these sources cannot say. For `SMARCA2`: tractable by small
molecule, with no drug for HER2+ and no recorded liability. Each box links to the tab that holds its
detail.

**Why this ranking? — the machine-learning layer.** *Every rank names the evidence that drove it.*
The model (`m7-f14`, chosen on held-out diseases) attributes the score to its inputs. The five that
drove this score are shown, each placed against the rest of this disease's candidates. A scientist
can see whether the rank rests on pathway structure, on interaction partners or on how well-studied
the gene is.

**Trials and Literature — the agentic layer.** *Every statement points to the passage it came from.*
For the selected gene and disease, the app searches ClinicalTrials.gov and PubMed. An LLM then picks
the relevant records, gives each a role, and quotes the passage that supports it. The quote is checked
against the source text. Expect little that names `SMARCA2` together with HER2+: for a novel
candidate that gap is the point, and the evidence it finds sits at the breast-cancer and SWI/SNF
level.

**Drugs & graph — the mechanism.** *A rank becomes a path you can trace.* This tab lists the drugs
behind any badge and their source. It also gives five ready-made graph queries for the pair. With no
drug for HER2+, the graph carries the argument for `SMARCA2`: run a query in the Visual Graph Explorer
and show the path to genes already linked to the disease.

**Ask about the gene — the assistant.** *Ask anything, and every sentence shows its source or says it
has none.* The evidence assistant answers free questions about the pair. It draws on trials,
literature and the graph, and each graph answer shows the query that produced it. A sentence it
cannot ground is marked as such. *Explore in Agent Hub* opens the same agent inside Dataiku. Show the
marking, not the fluency: that marking is what makes an agent usable in science.

**Two things the page refuses to do.** Say both aloud.

- Drug and liability badges are shown but cannot be filtered on. Filtering out known liabilities
  sounds prudent, yet it would remove **9 of the HER2+ top 15, ERBB2 among them**: liabilities are
  found by drugging a target, so the flag marks the best-studied targets.
- The score orders candidates and does not measure them. Rank 9 means ninth, not 90% likely.

**Close the page with the footnote, not a headline.** Remove every known target and re-rank the rest:
the top is enriched for genes that later became drug targets, **16.88× at top 10** against approved
drugs. *"We report this because it is measured, not because we ask you to act on it. It suggests the
same machinery is worth pointing at data where the answer is not known yet: yours."*

Then ask the question the page has been building toward: *how do we know any of this is right?* The
list's *How do we know?* links answer it.

---

## Page 2 — Why trust the list: traceability and reproducibility

> *Every ranking can be traced to its sources and re-derived from them.*

This page holds the shortlist accountable. It answers three questions for the disease already open
on the shortlist, in the order a sceptical scientist asks them. Each section states its answer up
front and keeps the full analysis under *Show the detail*.

**1 · What the model can see.** *Traceable: every node and edge names its source.* The model learns
from a knowledge graph of **113,391 nodes and 2,851,510 edges** assembled from six public sources. The
graph was rebuilt in DSS and checked against a frozen reference, with edge counts within **0.03%**.
This section is about provenance, not quality: it shows exactly what went in, and nothing else.

**2 · How faithfully it reconstructs known biology.** *Measured on diseases the model never trained
on, and shown as a distribution, not one number.* Train and test are split by disease family, so
"diabetes" and "type 2 diabetes" never sit on opposite sides. Over **6,754,128 disease–gene pairs**
and **670 held-out diseases**, the macro per-disease AUC is **0.8230**. Show the distribution with
HER2+ marked, because usefulness is not uniform, and knowing which diseases reconstruct well is worth
more than the average. Pooling all pairs would read **0.8932**, about seven points higher, because
large diseases would carry small ones. The demo reports the per-disease figure.

Raise the known weakness here before the room does. Well-studied genes have more edges, so any graph
model leans toward them. Compared with genes of the same connectivity, the top 10 is still **3.29×**
enriched for real targets. Yet among known targets, the least-connected genes score lower than the
most-connected. *"Where your field is under-studied, it will under-rank. Here is the size of that
effect."*

**3 · Does it hold across the disease family.** *Robust: the same model on every term in the family,
each with its uncertainty.* Most teams own one therapeutic area, so one well-chosen disease proves
little. Across **505 disease families**, reconstruction holds at **0.8009**. Within breast cancer, each
subtype carries its interval, and thin subtypes are flagged rather than hidden. The subtypes really
do differ: HER2-positive and triple-negative breast share only **2** novel candidates in their top
50. *"We can tell you which of your subtypes this resolves before you build on it."*

All three sections rest on one discipline: an assertion notebook re-derives each headline model
number against the live flow, and fails loudly if a number drifts. The flow's lineage is browsable in DSS.
Reproducibility is a property of the platform, not a promise in a slide.

---

## The close — what the platform did

**Not on screen; this is the part a data-platform owner buys.** During the project, three plausible
ideas were tested and the measurements came back against each. *Use druggability as a model input.*
*Filter out essential genes.* *Exclude targets with known liabilities.* Each was settled in an
afternoon by one recipe, and the record of why stays in the flow for the next person. Which hypotheses
are worth testing is the scientist's call. Making them cheap to test is the platform's job.

State one limitation before it is found. Ranking by association does not predict therapeutic value:
across diseases the two are uncorrelated (r = **+0.002**). On a drug-target benchmark, a simple lookup
of how many diseases a gene already targets beats the model. That benchmark measures gene popularity,
so it is never presented as a score.

End on the customer's data. Public knowledge buys the reconstruction they just saw. Their failed
programmes, assay results, disease definitions and expert thresholds are what would take it further,
and the thresholds already enter, as the shortlist's filters. Bringing that data in is a platform
problem, which is ours, not a science problem, which is theirs.

---

## Presenter notes

**Before the demo.** Re-check the scripted path on the live app: the funnel from 12,272 to 38, and
`SMARCA2` at #3 (#51 unfiltered). Those counts come from the served list on 2026-10-29, and no
notebook asserts them. If you show a graph path, choose it from the live ranking: the often-quoted MRN
complex is not a HER2+ story (RAD50, NBN and MRE11 rank 55, 99 and 401).

**Diseases.** The shortlist serves twelve diseases across oncology, autoimmune and
cardio-renal-metabolic areas. Page 2's family section covers breast, stomach and uterine cancer; the
reasons are in [`panel_selection.html`](panel_selection.html). Lead with HER2+. Triple-negative breast
is the deliberate hard case: it has only 8 known associations, so it cannot be scored. Use it to show
where the method runs out, never as a success. See
[`BREAST_SURGEON_BRIEFING.md`](BREAST_SURGEON_BRIEFING.md).

**What we do not claim, or show.**

| Not | Because |
|---|---|
| Novel discovery as the headline | It is the claim we are not making; it stays a footnote |
| An AUC as the opening, or pooled AUC at all | The list opens the demo; pooled overstates |
| The drug-target benchmark as a score | A lookup table wins it |
| Any safety or toxicity assessment | We have none; the badges are public flags |
| Drug or liability badges as filters | They are the ground truth the enrichment is measured against |
| Advice on running their discovery programme | Not our expertise; claiming it loses the room |
| The drug path as "not used" | It is not a model feature, but it is one of three routes that admit pairs to the candidate pool |
