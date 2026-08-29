# Discovery Landscape — from target identification to candidate nomination

> **Lifecycle:** Canonical · **Audience:** platform-side teams scoping the wider discovery landscape ·
> **Authority:** the explanatory framework and its cited sources · **Update when:** the framework or a
> load-bearing source is revised · **Generated dependencies:** none · **Excludes:** project build plans,
> implementation contracts and unverified client-facing claims.

> **What this is.** A scoping companion for the *molecular screening* AI solution framework
> (the Story 1 / Story 2 personas), written to place our existing POC
> (`PROJECT_CONTEXT.md`, `TARGET_PRIORITIZER.md`) on the wider drug-discovery value chain.
>
> **Who it's for.** Us — platform-side, not bench scientists. It assumes no biology or
> chemistry background. Jargon is explained the first time it appears, and there is a
> decoder in §3.
>
> **What it is not.** A build plan, and not a proposal for an end-to-end drug-discovery
> product. We are not an R&D software vendor. The point is to find the places where a data
> platform is the right answer, and be honest about the places where it isn't.
>
> **Provenance.** Assembled 2026-07-30 from three parallel web-research passes. Sources are
> cited inline. Items marked ⚠️ are vendor-sourced, single-source, or otherwise unverified —
> §14 lists the verification debt. Same rule as `RESEARCH_NOTE.md`: **verify any specific
> figure before client-facing use.**

---

## 1. How to read this doc

Six stages, in order. Each stage section has the same four parts:

| Part | Answers |
|---|---|
| **In plain terms** | What actually happens at this stage, without jargon |
| **What's changed recently** | The 2024–2026 data/AI state of the art |
| **The honest limits** | What the evidence says doesn't work, or doesn't work yet |
| **Where Dataiku fits** | Strong / narrow / stay out — and why |

If you read nothing else, read §2 (the two numbers), §10 (the tool matrix), and §12
(concrete revisions to the drafted stories).

---

## 2. The two numbers that anchor everything

Everything in this document hangs off two published results. They point in opposite
directions, and holding both is what makes a credible pitch.

### Number 1 — computational chemistry improves *developability*, not efficacy

AI-derived molecules entering the clinic show:

- **Phase I success: 80–90%** (historical base rate 40–65%)
- **Phase II success: ~40%** — *i.e. at industry par*

([Drug Discov Today 2024](https://www.sciencedirect.com/science/article/pii/S135964462400134X))

**What Phase I and Phase II test.** Phase I asks *is this molecule safe and tolerable in
humans* — largely a property of the molecule itself (does it dissolve, absorb, clear at a
sensible rate, avoid poisoning the heart or liver). Phase II asks *does it actually treat the
disease* — a property of the **biological hypothesis**, not the molecule.

**So the result reads cleanly:** computational design is genuinely good at making
better-behaved molecules. It does nothing about whether you picked the right thing to aim at.
Anyone selling generative chemistry as a fix for efficacy failure is misreading their own best
evidence.

### Number 2 — genetic evidence improves *efficacy*

**Minikel et al., *Nature* 2024** ([paper](https://www.nature.com/articles/s41586-024-07316-0),
[open access](https://pmc.ncbi.nlm.nih.gov/articles/PMC11096124/)) — the current reference on
this question:

- Target–disease pairs with human genetic support have **2.6× relative success**
- **>2× in 11 of 17 therapy areas**; >3× in haematology, metabolic, respiratory, endocrine
- The effect is **concentrated in Phase II and III**, and is *weakest* in Phase I
- It **rises with confidence in the causal-gene assignment** — knowing *which* gene at a
  genetic signal matters more than the signal itself
- Only **~4.8%** of current Phase I–III target–disease pairs have this kind of support

The third and fourth bullets are the interesting ones. Genetics de-risks exactly the phase
that computational chemistry doesn't. And the value sits in the *gene assignment* step — which
is a data-integration and modelling problem, i.e. ours.

Lineage of the finding: Nelson 2015 ([Nat Genet](https://www.nature.com/articles/ng.3314)) →
King 2019 ([PLoS Genet](https://journals.plos.org/plosgenetics/article?id=10.1371/journal.pgen.1008489))
→ Minikel 2024.

### Why this pairing is the pitch

> Genetic and network evidence de-risks **efficacy** (Phase II/III).
> Computational chemistry de-risks **developability** (Phase I).
> Both are now demonstrated with real numbers — and they are *different halves of the same
> pipeline*, usually owned by different teams, on different systems, with no shared audit
> trail.
>
> The unsolved problem is the **connective tissue**: carrying a hypothesis from "this gene
> matters" to "this molecule is worth making" to "we nominate this candidate", with the
> evidence, the uncertainty and the human decisions preserved end to end.
>
> That is a data-platform problem. It is where Dataiku belongs — and we already have a working
> demo of the upstream half.

---

## 3. Jargon decoder

The 30 terms you need to read the rest of this document. Skim it now, refer back as needed.

### Biology side

| Term | Plain meaning |
|---|---|
| **Target** | The protein (usually) you want a drug to act on. "Target identification" = choosing it. |
| **Gene / protein** | A gene is the instruction; the protein is the machine built from it. In this field the two are used almost interchangeably when naming targets. |
| **Indication** | The disease a drug is being developed for. |
| **GWAS** | Genome-wide association study — scanning many people's genomes to find genetic variants statistically linked to a disease. Gives you a *region*, not usually a gene. |
| **Causal gene assignment / L2G** | Deciding *which* gene in that region is actually responsible. Open Targets' "Locus-to-Gene" model does this. |
| **pQTL / eQTL** | Genetic variants that change how much protein (p) or RNA (e) a gene makes. Used as natural experiments. |
| **Mendelian randomisation (MR)** | Using inherited genetic variation as a natural randomised trial, to test whether changing a protein changes disease risk. |
| **CRISPR screen** | Systematically switching off each gene in cells and seeing which ones the cells can't live without, or which change a measured behaviour. |
| **Essentiality** | Whether cells die without the gene. A pan-essential gene is a *bad* drug target — you'd poison healthy cells too. **DepMap** is the reference dataset. |
| **LOEUF** | A score from gnomAD measuring how intolerant a gene is to being broken in the healthy human population. Highly intolerant = disrupting it is likely harmful = safety flag. |
| **Tissue specificity** | Whether a gene is active in one tissue or everywhere. Specific = you can hit it without collateral damage. |
| **Tractability / druggability** | Whether the protein is physically the kind of thing a drug can grab hold of at all. |
| **Disease module** | The cluster of genes in a biological network that a given disease sits in. Our POC's core assumption. |
| **Knowledge graph (KG)** | Biology represented as nodes (genes, diseases, drugs, pathways) and typed edges between them. PrimeKG is the one we rebuilt. |

### Chemistry side

| Term | Plain meaning |
|---|---|
| **Hit** | A molecule that measurably interacts with the target. Cheap, weak, usually unusable as-is. |
| **Lead** | A hit that has been improved enough to be a serious starting point. |
| **Candidate** | The one molecule (plus backups) formally nominated to enter development. The big gate. |
| **Assay** | The laboratory measurement. Everything downstream is trained on assay numbers, so assay quality caps model quality. |
| **HTS** | High-throughput screening — physically testing 10⁵–10⁶ real molecules. |
| **DEL** | DNA-encoded library — billions of molecules each tagged with a DNA barcode, screened as one pooled mixture. |
| **Virtual screening / docking** | Computationally predicting how a molecule sits in the target's pocket and scoring it. Lets you "screen" billions without making anything. |
| **Pose** | The predicted 3D position and orientation of the molecule inside the pocket. |
| **holo / apo** | *holo* = protein structure solved **with** a molecule bound (pocket already the right shape). *apo* = solved **empty**. The distinction matters enormously — see §7. |
| **Fragment screening** | Screening very small molecules; weak binders but they reveal hidden ("cryptic") pockets. |
| **Bioactivity / QSAR model** | Predicting how strongly a molecule acts on a target from its structure. |
| **Morgan fingerprint / ECFP** | A molecule turned into a bit-vector describing its substructures. Old, simple, and still frequently beats deep learning. |
| **Tanimoto similarity** | How similar two fingerprints are, 0–1. Used to remove near-duplicates and pick a diverse shortlist. |
| **ADMET** | Absorption, Distribution, Metabolism, Excretion, Toxicity — does the molecule behave like a drug in a body. |
| **hERG / CYP / Ames / DILI** | Specific safety endpoints: heart-rhythm risk / drug-metabolism interference / mutagenicity / drug-induced liver injury. Prediction quality differs sharply between them. |
| **QED** | Quantitative Estimate of Drug-likeness, 0–1. A convenient single number that summarises "looks like a drug". Contested for anything unusual (see PROTACs, §8). |
| **MPO** | Multiparameter optimisation — trading off potency, safety, ADMET, physical properties simultaneously, because improving one usually damages another. |
| **FEP** | Free energy perturbation — expensive physics simulation that predicts binding strength. The most-trusted computational potency tool. Accuracy measured in kcal/mol (lower = better). |
| **DMTA** | Design–Make–Test–Analyse — the iterative loop of medicinal chemistry. |
| **Retrosynthesis** | Working backwards from a designed molecule to a route for actually making it. A molecule nobody can synthesise is worthless. |
| **Scaffold split** | Splitting train/test data by chemical skeleton rather than randomly. The only honest way to measure whether a model generalises. |
| **Applicability domain / conformal prediction** | Knowing when a model is being asked about something unlike its training data, and attaching a trustworthy uncertainty range to each prediction. |
| **PAINS** | A list of substructures that misbehave in certain assay technologies. Widely misused as a blanket exclusion filter — see §7. |

---

## 4. The chain in plain language

Six stages. Roughly 10–15 years and ~$2.2B per approved drug; ~90% of clinical candidates
fail, more than half for lack of efficacy or unmanageable toxicity.

**Stage 1 — Target identification.** *"What should we aim at?"* Sift genetics, omics,
literature and networks to nominate a protein whose modulation should change the disease.

**Stage 2 — Target prioritisation.** *"Of the plausible ones, which is worth money?"* Annotate
each candidate with how druggable, how safe, how precedented, how testable it is. Then choose.

**Stage 3 — Target validation & assay development.** *"Does interfering with it actually
help — and can we measure that reliably?"* Lab work: CRISPR, cell models, animal models, then
building the measurement that everything downstream is trained on.

**Stage 4 — Hit finding / lead discovery.** *"Which molecules bind it?"* Screen — physically,
or computationally against billion-molecule catalogues — then confirm the survivors.
**This is Story 1.**

**Stage 5 — Hit-to-lead & lead optimisation.** *"Can we turn this into a drug?"* Iteratively
redesign the molecule to balance potency, safety, ADMET and makeability. Repeated DMTA cycles.
**This is Story 2.**

**Stage 6 — Candidate nomination.** *"Which single molecule do we bet on?"* The formal gate.
Includes things no model produces: freedom-to-operate, manufacturability, portfolio fit,
chemist judgement.

### The map

| # | Stage | Question | Dominant data | Our POC | Dataiku fit |
|---|---|---|---|---|---|
| 1 | Target identification | What to aim at? | Genetics, omics, literature, KGs | ✅ **built** | **Strong** |
| 2 | Target prioritisation | Which one is worth it? | Tractability / safety / precedent annotations | 🟡 half-designed | **Strong** |
| 3 | Validation & assay dev | Does it work; can we measure it? | CRISPR screens, assay data | ❌ | Narrow (data plumbing) |
| 4 | Hit finding | Which molecules bind? | Structures, libraries, docking, bioactivity | ❌ = **Story 1** | Orchestration |
| 5 | Lead optimisation | Can it be a drug? | ADMET/tox, MPO, DMTA cycles | ❌ = **Story 2** | Orchestration + "Decide" |
| 6 | Candidate nomination | Which one do we bet on? | Everything, plus judgement | ❌ | **Strong** (governance) |

**The pattern to notice.** Stages 1–2 and stage 6 are **evidence-integration and
decision-governance** problems: many messy sources, identifier reconciliation, a ranking
model, an audit trail, a dashboard a human decides from. That is Dataiku's home turf.

Stages 4–5 are **computational chemistry and laboratory** problems. The modelling is
specialised, the incumbent software is deeply entrenched, and — per every source consulted —
the real bottleneck is *assay data plumbing*, not algorithms. Our role there is orchestration
and governance **around** those tools, not replacing them.

---

## 5. Stage 1 — Target identification

### In plain terms

Produce a defensible hypothesis: *modulating protein X should change disease Y*. This is the
first real go/no-go, and it happens before meaningful money is spent.

The evidence comes in classes, and they are not equal. Roughly in descending order of how well
they predict eventual clinical success:

1. **Human genetics** — people who naturally carry variants in this gene get more or less of
   this disease. The strongest evidence, because it is a natural experiment in humans.
2. **Functional genomics** — switch the gene off in cells and the disease-relevant behaviour
   changes. Strong, but cells aren't people.
3. **Expression** — the gene is unusually active in diseased tissue, or in the specific cell
   type that drives the disease. Suggestive; correlation, not causation.
4. **Network / pathway context** — the gene sits among genes already known to matter. This is
   what our POC computes.
5. **Animal models** — informative, and famously poor at transferring to humans.
6. **Literature** — cheap, huge, and heavily biased toward whatever was already fashionable.

### What's changed recently

**Causal-gene assignment became a supervised ML problem.** Open Targets' **Locus-to-Gene
(L2G)** takes a genetic signal and predicts which nearby gene is responsible. It is a
gradient-boosted classifier — not a neural network — over four feature families: distance to
the gene, colocalisation with protein/RNA-level genetic effects, predicted variant severity,
and enhancer-to-gene links. It outputs 0–1 and **explains each prediction with SHAP**
attributions. Release 26.06 added *trans*-pQTL features.
[docs](https://platform-docs.opentargets.org/gentropy/locus-to-gene-l2g)

> **Why this matters to us:** L2G is the industry-standard target-scoring model, and it is a
> tabular gradient-boosting model with SHAP explanations. That is a Dataiku Visual ML project,
> almost exactly. Our POC's prioritiser is deliberately built on the same pattern.

**Mendelian randomisation on protein-level genetics went mainstream.** Using cis-pQTL variants
as instruments (from UK Biobank's proteomics project, deCODE, FinnGen) to test causality, and
to anticipate side effects before any chemistry exists. Standing caveat: some apparent signals
are **assay artefacts** — a variant that changes the protein's shape can stop the measuring
reagent binding, which looks like a change in protein level. Replicate across platforms
(SomaScan vs Olink) before believing it.

**Knowledge graphs got a credible generative story.** **TxGNN** (*Nature Medicine* 2024) is
built on a PrimeKG-derived graph — the same graph family our POC rebuilds. A graph neural
network plus a disease-similarity decoder lets it rank treatments **zero-shot** for diseases
with no approved therapy at all, +49.2% over eight baselines, and it ships a **multi-hop path
explainer** that shows the mechanistic chain behind each prediction.
[paper](https://www.nature.com/articles/s41591-024-03233-x)

The path explainer is the part worth remembering. TxGNN's own usability study with 12 domain
experts found path explanations raised **expert accuracy by 46% and confidence by 49%**. That
is the single best argument for why our Visual Graph + SHAP pairing is a feature and not
decoration.

Also in this family: IBM **Otter-Knowledge** (>30M triples, per-modality pretrained embeddings
refined by a GNN), and **TxPert** (KG → predicted transcriptomic response to perturbation,
[Nat Biotech](https://www.nature.com/articles/s41587-026-03113-4)).

**CRISPR screens became first-class *evidence*, not just a safety annotation.** This is a real
2024–25 shift. Open Targets now ingests Sanger's **Project Score gen-2** (771 cancer cell
lines) and **CRISPRbrain** iPSC-neuron screens (33,579 associations, ~73.7% of them novel) as
target–disease *association* evidence. Separately, an integration of **930 genome-wide CRISPR
screens across 17,647 genes and 27 cancer types** produced 143 targetable dependencies
([Cancer Cell 2023](https://www.cell.com/cancer-cell/fulltext/S1535-6108(23)00444-0)).

**Single-cell and spatial data moved from "nice" to "expected"** for saying *which cell type*
drives the phenotype. Practical catch: most spatial technologies don't resolve individual
cells, so a **deconvolution** step (cell2location, RCTD, GraphCellNet) is doing load-bearing
statistical work before any biology is read off.

### The honest limits

- **The interactome is ~80% incomplete** (Menche 2015). Network features are computed on a
  partial map — which is exactly why our POC uses four complementary network views instead of
  trusting proximity alone (`RESEARCH_NOTE.md` §1).
- **Literature and association evidence are popularity-biased.** Open Targets says so
  explicitly about its own score (see §6). Under-studied diseases score low for sociological
  reasons, not biological ones.
- Only ~4.8% of clinical target–indication pairs have genetic support at all — so for most
  programmes, the strongest evidence class is simply absent, and you are ranking on weaker ones.

### Where Dataiku fits — **strong**

This is the POC, and it works. Multi-source ingestion with real identifier harmonisation
(the unglamorous majority of the effort), a governed flow, Visual ML + SHAP as an L2G analog,
graph-derived features, and a clickable evidence path.

What differentiates it from a bioinformatics script farm is **reproducibility, lineage and
explainability** — not the algorithm. Say that plainly; a scientist will respect it more than
a claim to novel method.

---

## 6. Stage 2 — Target prioritisation

### In plain terms

Stage 1 gives you a list of plausible targets — often hundreds. Stage 2 decides which one to
fund, by annotating each with the practical questions:

- **Has anyone drugged it before?** (precedent — reassuring, but also crowded IP)
- **Can it physically be drugged?** (is there a pocket; is it reachable in the body)
- **Will hitting it hurt the patient?** (is it essential; is it active everywhere)
- **Can we even test it?** (is there a mouse version; is there a chemical probe)

### The design fact that should shape our pitch

Open Targets' **Target Prioritisation** view is a target × attribute **matrix**, not a score.
Four buckets of attributes, each normalised to **−1…+1** (or binary 1/0, with NA for missing),
rendered as a red/green traffic light.

**The documentation describes no weighting and no composite score.** The scientist reads the
matrix, or exports it and builds their own ranking.
[docs](https://platform-docs.opentargets.org/web-interface/target-prioritisation)

That is deliberate — and it contrasts sharply with the *association* score on the same
platform, which **is** aggregated: a three-level weighted harmonic sum (Σ scoreᵢ/i², normalised
by π²/6 ≈ 1.644) with noisy sources deliberately down-weighted — Europe PMC, Expression Atlas
and IMPC all at 0.2. [docs](https://platform-docs.opentargets.org/associations)

Open Targets also warns, in its own documentation, that the association score "is a heuristic
based on the availability of data" — not a confidence measure.

> **The industry-standard architecture is therefore two layers:**
> an **aggregated efficacy-evidence score** (how much do we believe this target matters), kept
> strictly separate from an **unaggregated safety/tractability matrix** that a human reads.
>
> If a demo of ours collapses both into one number, we have deviated from the reference
> implementation. We should either not do that, or do it deliberately and say so. The better
> move: aggregate the evidence side, and render the prioritisation side as the traffic light —
> which is precisely what a Dataiku dashboard is good at.

### The four buckets, and where each attribute comes from

All free, all recreatable.

| Bucket | Attribute | Source | Scoring |
|---|---|---|---|
| **Precedence** | Target in clinic | ChEMBL clinical phase | 0.01 (preclinical) → 1.0 (approved) |
| **Tractability** | Membrane protein | HPA + UniProt | binary |
| | Secreted protein | HPA + UniProt | binary |
| | Ligand binder | ChEMBL tractability buckets | binary |
| | Small-molecule binder | PDB co-crystal exists | binary |
| | Predicted pockets | DrugEBIlity ≥ 0.7 | binary |
| **Doability** | Mouse ortholog identity | Ensembl Compara | linear 0–1 above 80% identity |
| | Chemical probe available | Probes & Drugs | binary |
| **Safety** | Genetic constraint | gnomAD **LOEUF** | −1 (least LoF-tolerant) → 1 |
| | Mouse phenotypes | MGI | harmonic sum, −1 → 0 |
| | **Gene essentiality** | **DepMap** pan-essential | −1 if pan-essential |
| | Known safety events | OT safety widget + ClinPGx | −1 if any |
| | Cancer driver gene | COSMIC Cancer Gene Census | −1 if oncogene/TSG |
| | Paralogues | Ensembl Compara | linear −1 → 0 above 60% identity |
| | **Tissue/cell-type specificity** | **GTEx + Tabula Sapiens** (CELLEX ESmu) | 1 (highly specific) → −1 |
| | Tissue/cell-type distribution | GTEx + Tabula Sapiens | 1 (expressed everywhere) → −1 |

Release **26.06** split baseline expression into four separate rows (tissue and cell-type ×
specificity and distribution), backed by Tabula Sapiens single-cell, GTEx and DICE bulk, and
PRIDE mass-spec proteomics
([release note](https://blog.opentargets.org/open-targets-platform-26-06-has-been-released/)).

⚠️ The *distribution* row's polarity reads counter-intuitively for a safety bucket —
broad expression scores **+1**. Confirm against the live UI colouring before replicating it.

> **Note for our roadmap:** the four bolded rows above — DepMap essentiality, gnomAD LOEUF,
> GTEx/Tabula Sapiens specificity, COSMIC driver status — are **exactly** the deferred
> value-prop (b) in `TARGET_PRIORITIZER.md` §11 (efficacy × safety traffic light). Resuming it
> puts us *on* the industry reference rather than near it. All four sources are free.

### The honest limits — and a trap worth naming

**The leakage trap.** Three of the attributes above — *target in clinic*, ChEMBL *ligand
binder*, and any known-drug edge — are **downstream of approval status**. A model that uses
them to "discover" good targets is just rediscovering which targets already have drugs. For a
discovery-first prioritiser they must be excluded from the feature set, or used only as
evaluation labels.

Our POC already solves the structurally identical problem with edge masking
(`TARGET_PRIORITIZER.md` §6: when scoring a known gene–disease pair, that edge is removed from
the graph and the gene dropped from the disease's seed set). **Make this a talking point** — it
is the thing that separates an honest demo from a circular one, and most demos in this space
are circular.

**Popularity bias, again.** Precedence and literature-derived evidence both reward
well-studied targets. If the client's stated goal is *novel* targets, features that encode
"has been studied a lot" are working against the brief.

### Where Dataiku fits — **strong, and under-appreciated**

This is a join-and-normalise problem over about eight public sources with an opinionated
scoring convention, plus a dashboard. No exotic modelling. It is arguably the most winnable
piece of the entire chain for us, and it is the natural next increment on the POC we already
have.

---

## 7. Stage 3 — Target validation & assay development

### In plain terms

Two jobs, both mostly wet lab.

**Validation:** prove that interfering with the target actually changes the disease-relevant
behaviour. Tools: CRISPR knockout/knockdown, base editing, Perturb-seq (perturb genes and read
the full transcriptional response), high-content imaging, animal models.

**Assay development:** build the laboratory measurement that hit finding will use — biochemical
or cell-based, choice of detection technology, plate normalisation, quality metrics like the
Z′-factor.

### Why a platform person should care anyway

**Assay development is the label generator for every model in stages 4–6.** Whether those
models can be trained at all depends on whether assay protocol, version, plate, and
*failed* runs were captured as structured data.

Every source consulted for this document — including the self-driving-lab reviews, which have
every incentive to talk about robots — names the same blockers: heterogeneous instrument output
formats, missing assay-protocol metadata, and unrecorded failures. **Not algorithms.**

That is an unglamorous data-engineering problem the client almost certainly has, and it is a
legitimate Dataiku answer that requires no chemistry expertise from us.

### What's changed recently

**Perturbation + imaging as a target-discovery modality in its own right.** Recursion's
approach: perturb cells (CRISPR or compound), image them at scale, embed the images with
computer vision, and read relationships between perturbations off the embedding space —
"maps of biology". Public benchmark data exists: **RxRx3**, cpg0016, GWPS
([benchmark framework](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1012463)).

### Where Dataiku fits — **narrow but real**

Screen QC and normalisation pipelines, hit-calling, and the assay-metadata capture problem
above. Not the biology, and not the instrumentation.

---

## 8. Stage 4 — Hit finding / lead discovery — **this is Story 1**

### In plain terms

You have a validated target. Now find molecules that stick to it. Five ways to do that, and
the choice drives everything downstream:

| Approach | How many molecules | Typical yield | What it costs you |
|---|---|---|---|
| **HTS** — physically test a real compound collection | 10⁵–10⁶ | ~0.1–1% hits | Real robots, real compounds, real money |
| **DEL** — screen a DNA-barcoded pooled library | 10⁸–10¹¹ | enrichment, not a % | Specialist chemistry; noisy readout |
| **Fragment screening** — screen tiny molecules | 10²–10⁴ | 1–10%, all very weak | Hits need heavy building-up; finds hidden pockets |
| **Virtual screening** — dock a catalogue computationally | 10⁹–10¹¹ | 5–15% at weak thresholds, published | Needs a good 3D structure; compute; false confidence |
| **Ligand-based screening** — predict from known actives | 10⁶–10¹⁰ | target-dependent | Needs ≥50–100 diverse known actives to start |

**The scale change is the headline.** You can now computationally screen catalogues that
nobody has ever made:

- **ZINC-22**: >37 billion enumerated molecules, >4.5 billion prepared in 3D and ready to dock
  ([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.2c01253))
- **Enamine REAL Space**: **83 billion** searchable as of Sept 2025
  ([BioSolveIT](https://www.biosolveit.de/2025/09/23/enamines-real-space-september-2025-update-now-83-billion/)).
  A vendor page claims ~94.5B ⚠️ (undated — the safe public claim is "≥83 billion")

These are *virtual* catalogues: molecules that a supplier commits to synthesising on demand
(typically 3–4 weeks, >80% success) from validated reaction protocols and in-stock building
blocks. You screen the catalogue, then order the handful you want.

**Then you confirm.** Computational and single-shot hits are guilty until proven innocent. The
standard confirmation cascade: dose–response → an orthogonal assay using a **different
detection mechanism** → counter-screens → biophysical confirmation (SPR/ITC/NMR/crystallography)
→ mechanism-of-inhibition. The **EFMC Best Practice Initiative: Hit to Lead** (ChemMedChem
2025) is the current consensus reference for how this should be run.

### What's changed recently

**1. Protein structure prediction is solved enough to be a commodity — with one crucial catch.**

AlphaFold2 is routine. **AlphaFold3** (2024) predicts protein–ligand complexes, but the weights
are **not open**: request-only, non-commercial. That gap created a genuine open ecosystem:

| Model | Licence | What it gives you |
|---|---|---|
| **Boltz-1 / Boltz-1x** | MIT (full training code, weights, data) | AF3-class co-folding. **1x adds physics-inspired inference that fixes stereochemistry and clashes** |
| **Chai-1** | Apache 2.0, commercial use OK | Inference code + weights only, no training code |
| **Boltz-2** | MIT | Predicts structure **and binding affinity** jointly |
| **RoseTTAFold All-Atom** | open | All-atom generalist; not independently benchmarked in this pass ⚠️ |

**Boltz-2** is the one being talked about: claimed Pearson r ≈ 0.62 on the FEP+/OpenFE
benchmark at **>1000× lower cost** than the physics it approximates
([preprint](https://www.biorxiv.org/content/10.1101/2025.06.14.659707v1)). See the limits
section before repeating that.

**The catch — apo vs holo.** A protein pocket changes shape when a molecule binds. AlphaFold2
predicts the *empty* (apo) shape, because it doesn't model the molecule. Retrospective
consensus on screening enrichment (EF1% — how much better than random the top 1% of your
ranked list is):

- **holo** crystal structure (solved with a ligand in it): **EF1% ≈ 24.2**
- **apo** crystal structure (solved empty): **≈ 11.4**
- **AlphaFold2** model: **≈ 13.0**

([JCIM](https://pubs.acs.org/doi/abs/10.1021/acs.jcim.3c01976)) — i.e. **AlphaFold behaves like
an apo structure, at roughly half the enrichment of a real holo one.** GPCRs (a major drug
target class) are a particular weak spot. Prospective counter-evidence exists for some targets,
and the 2025 direction of travel is to use **AF3/Boltz co-folded (holo-like) complexes** as the
screening receptor, or to sample AlphaFold's structural space via MSA subsampling to get an
ensemble.

**2. Docking: the deep-learning wave, then the correction, then the synthesis.**

Classical docking (AutoDock Vina/Smina, Schrödinger Glide, CCDC GOLD, OpenEye FRED) is physics-
and empirics-based and still the workhorse. **GNINA 1.3** adds CNN-based rescoring on top,
with knowledge-distilled student models fast enough for high-throughput use
([J Cheminform](https://jcheminf.biomedcentral.com/articles/10.1186/s13321-025-00973-x)).

Worth knowing: **CACHE Challenge #1 was effectively won with careful GNINA docking** — the
paper's title is roughly "Docking with GNINA Is All You Need"
([paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC11683865/)).

The generative/diffusion wave — **DiffDock**, DiffDock-L, DiffDock-Pocket, PocketVina,
DynamicBind — predicts poses directly instead of searching physically. What happened next is
the most important methodological story in this stage, and it's in the limits section.

**3. Active learning is how you actually screen 10 billion molecules.**

You don't dock 10 billion. You dock a seed sample, train a cheap 2D model on those scores,
predict the rest, dock the predicted top-K, and iterate. Reported efficiency: **~90% of the
top-1% docking hit list recovered after docking only 10% of the library** — sometimes with
plain linear regression as the surrogate
([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11005039/)). Tools: **HASTEN**, **Deep
Docking**.

**4. DEL + ML is the most credible "big data" story in hit finding.**

A 2025 benchmark (3 DNA-encoded libraries × 5 ML models, against CK1α/δ) found **10% of
predicted binders confirmed** biophysically — but **94% of predicted non-binders confirmed as
non-binders**, and it yielded two nanomolar binders. The authors' conclusion is the transferable
lesson: **training-set chemical diversity and generalisability matter more than headline
accuracy** ([npj Drug Discovery](https://www.nature.com/articles/s44386-025-00007-4)).

**5. Whole-library ADMET annotation is now cheap.**

**ADMET-AI** (a Chemprop-RDKit graph model over 41 datasets) ranked 1st on 18 of 22 benchmark
tasks and — the genuinely useful part — **contextualises each prediction against a reference
set of approved drugs**, so a number means something to a non-specialist. Fast enough to
annotate an entire library
([Bioinformatics 2024](https://academic.oup.com/bioinformatics/article/40/7/btae416/7698030)).
**Deep-PK** covers 73 endpoints via a free web server.

### The honest limits — four things to get right before demoing anything here

**Limit 1 — deep-learning docking needs a physics gate. This is not optional.**

**PoseBusters** (*Chem Sci* 2024) is the foundational correction. Its findings:

- DiffDock only beats classical docking if you score **pose accuracy alone (RMSD)**. Add
  physical-validity checks — bond lengths, aromatic rings being flat, correct stereochemistry,
  no atoms overlapping — and **Vina and GOLD beat all deep-learning methods**.
- On targets less than 30% sequence-similar to anything in the training set, DL methods produced
  **almost no physically valid poses at all**.
- Post-docking energy minimisation substantially rescues the DL methods, and does nothing for
  Vina/GOLD — because those were already producing physical poses.

([paper](https://pubs.rsc.org/sc/article/15/9/3130/827511/))

**PoseX** (2025, 23 methods, 718 self-docking + 1,312 cross-docking cases) then found the
opposite-looking result: AI methods *do* consistently beat physics on success rate — **provided
a physics relaxation step follows**, and provided the pocket is specified. It also found AI
co-folding mishandles molecular handedness (chirality) — *except* Boltz-1x, which has explicit
physics-inspired potentials ([arXiv](https://arxiv.org/pdf/2505.01700)).

> **The settled 2025 architecture is: AI generates the pose → physics minimises it → a validity
> gate rejects what's still broken.** Not "AI instead of physics". A demo that runs DiffDock and
> reports a confidence score, with no minimisation and no validity check, is running the 2023
> version of this pipeline.

A related, persistent problem: **pocket leakage** in benchmarks — test proteins whose pockets
resemble training pockets. DiffDock reportedly loses ~14% performance on properly unseen test
sets ⚠️ (secondary sources; verify before quoting).

**Practical rule:** never report DL docking results without (1) validity checks, (2) force-field
minimisation, (3) a train/test split controlled by *both* protein sequence identity and ligand
similarity, and (4) a classical Vina/GOLD/Glide baseline.

**Limit 2 — bioactivity models do not generalise the way leaderboards imply.**

**MoleculeACE** (24 methods × 30 targets) is the reference benchmark here. Findings:

- **Every** method degrades badly on "activity cliffs" — pairs of nearly identical molecules
  with wildly different potency. Which is precisely the situation medicinal chemistry lives in.
- **Morgan fingerprints + classical ML consistently beat deep learning.**
- Transformers and graph neural networks generally *underperform*.

([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.2c01073))

Molecular foundation models (MolFormer, ChemBERTa, Uni-Mol, MiniMol) frequently lose to
fingerprints on real tasks; multiple 2025–26 papers describe this underperformance as endemic
to the field.

And the safeguard is itself fragile: **applicability domain** methods (conformal prediction,
Venn-ABERS) give distribution-free guarantees *that break precisely under the distribution
shift that matters*. Worse, ensemble variance — the intuitive uncertainty proxy — perversely
**decreases** for molecules with no structural similarity to training data, so it fails to flag
exactly the errors you most need flagged.

**Practical rule:** report **scaffold-split** metrics, never random-split, and attach a
conformal interval plus an in/out-of-domain flag to every prediction.

**Limit 3 — the training data quality caps everything.**

- **PubChem does no curation of its own.** It aggregates (including from ChEMBL and BindingDB),
  and **assay metadata is lost during ingestion**.
- **ChEMBL** is expert-curated and much cleaner, but *"the ChEMBL EGFR dataset"* is not a
  well-defined object without a **version pin** — target-specific datasets vary substantially
  across ChEMBL releases. And whether you aggregate replicate potency values by **arithmetic or
  geometric mean changes the labels** ([chembl-downloader](https://arxiv.org/pdf/2507.17783)).
- **PDBbind**'s general/refined/core sets are cross-contaminated by protein and ligand
  similarity. Use **LP-PDBBind** leak-proof splits.
- **PAINS filters are widely misused.** The 480 substructure alerts were derived from frequent
  hitters in *one* assay technology (AlphaScreen). They are technology-dependent and do not
  reliably indicate general promiscuity. Correct use: a PAINS alert **triggers orthogonal
  follow-up**; it does not justify automatic deletion. Over-filtering throws away tractable
  chemistry ([Phantom PAINS](https://pubs.acs.org/doi/10.1021/acs.jcim.6b00465)).

**Limit 4 — the prospective, blinded evidence is sobering.**

**CACHE** is the only mechanism in the field that tests hit-finding methods on targets with
**no known ligands** and then **experimentally screens every prediction**. Results:

- **CACHE #1** (LRRK2 WD40): 23 participants; won with careful GNINA docking.
- **CACHE #4** (CBLB): of 23 teams, **one** produced a clearly novel, strongly validated hit.
  A second team's confirmed molecule turned out to resemble known patent-literature compounds.
- **CACHE #5** (MCHR1, a GPCR): ~1,455–1,553 compounds nominated across 23 participants.

([publications](https://cache-challenge.org/cache-publications))

Set against that, the most-cited "AI beats HTS" number is Atomwise's **26% average hit rate
across 318 targets** ([Sci Rep 2024](https://www.nature.com/articles/s41598-024-54655-z)).
⚠️ It is vendor-authored, hit-threshold-dependent (usually µM-level single-concentration
activity), and carries a published Author Correction. Treat 26% as vendor-reported.

> **The two framings to keep straight.** Retrospective and vendor benchmarks: hit rates of tens
> of percent. Blinded prospective challenge on a novel target: roughly **1 team in 23**. Both
> are true; they measure different things. If a client quotes the first at us, the second is the
> useful reply — and it is an argument *for* rigorous evaluation infrastructure, i.e. for us.

### Where Dataiku fits — **orchestration, not chemistry**

Honest value in Story 1:

- Call BioNeMo / AlphaFold / Boltz / DiffDock as **governed flow steps** with versioned inputs
  and outputs
- Own the ChEMBL/PubChem ingestion, the **version pinning** and the aggregation rules
- Train and **version** the bioactivity and tox models, with scaffold splits and conformal
  intervals as enforced defaults
- Hold the qualification thresholds as **project variables** the scientist can edit (this is
  already the draft's design — it's a good instinct)
- Run the deterministic Tanimoto similarity and diversity selection
- Serve the agent, the rationale panel, and the audit trail of what was decided and why

What we should **not** claim: better docking, better generative chemistry, or a substitute for
Schrödinger.

---

## 9. Stage 5 — Hit-to-lead & lead optimisation — **this is Story 2**

### In plain terms

You have a molecule that binds. It is almost certainly not a drug: too weak, or it gets
destroyed by the liver in minutes, or it doesn't get absorbed, or it interferes with the heart's
electrical rhythm. So you redesign it — repeatedly.

**The central difficulty is that the properties fight each other.** The classic example: making
a molecule stick harder to its target usually means making it greasier; greasier molecules get
cleared faster by the liver and are more likely to hit the hERG heart channel. Fix the greasiness
and you often lose the potency. There is no ordering of these fixes that works, which is why the
field does **multiparameter optimisation (MPO)** — score all the axes at once and manage the
trade-off explicitly, rather than filtering on them one at a time.

The axes: potency · selectivity (hits the target, not its relatives) · absorption · metabolic
stability · clearance · physical properties · safety endpoints · developability (can it be
formulated and manufactured) · patentability · **makeability**.

**How it's organised: DMTA.** Design a batch of molecules → Make them → Test them → Analyse,
then design again. Weeks to months per cycle. Everything computational in this stage exists to
make the cycles fewer or better-chosen.

### What's changed recently

**1. The loop gained a step: DMTA → D2MTL.**

AstraZeneca's framing is **Design–Decide–Make–Test–Learn** — inserting an explicit *Decide*
step, because human + machine design now generates far more candidate molecules than anyone can
synthesise. *Decide* is active-learning prioritisation: of these 10,000 designs, which 40 do we
make?
([Drug Discov Today](https://www.sciencedirect.com/science/article/pii/S1359644624000709))

> **That inserted step is the Dataiku-shaped hole in this stage.** It is a ranking-under-
> uncertainty problem over tabular data with a human in the loop. It is not owned by an
> incumbent — the chemistry vendors sell design tools and the ELN vendors sell data capture.

**2. Free energy calculation became cheap enough to sit inside the loop — and we now know its
real accuracy.**

FEP simulates the physics of binding. Schrödinger's **FEP+** is the commercial reference
(~1 kcal/mol error on closely related molecule series; deployed at Merck KGaA across 12 targets,
23 series, >400 blind-predicted molecules synthesised and tested).

The open alternative **OpenFE** ran a 15-pharma-company collaborative assessment, which is the
most useful realism anchor in this whole document:

| Benchmark set | Weighted error (RMSE) | Sub-1-kcal systems |
|---|---|---|
| **58 public systems** | **1.73 kcal/mol** [1.53–1.96] | 10 |
| **37 private industrial systems** | **2.44 kcal/mol** [1.94–3.06] | **2** |

([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.6c00089)) — ranking quality was comparable to
published FEP+ results, but an absolute-error gap remains, and the FEP+ numbers benefited from
manual expert optimisation.

> **2.44 kcal/mol is state-of-the-art physics on unseen industrial molecule series.** For
> intuition: ~1.4 kcal/mol is roughly a 10× difference in binding strength. So the best available
> physics has an error bar wider than an order of magnitude on real projects. Budget for that
> number; never quote 0.5.

**3. Machine learning is now claiming FEP-level affinity — with heavy caveats.**

**Boltz-2** claims near-FEP accuracy at >1000× lower cost. Independent evaluation is markedly
more cautious: generated poses show wrong bond lengths and angles, wrong stereochemistry at
chiral centres, non-planar aromatic rings; and performance is **weakest on closely related
molecule series** — which is *exactly* the lead-optimisation use case
([arXiv](https://arxiv.org/html/2603.05532v1),
[deepmirror](https://www.deepmirror.ai/post/boltz-2-real-drug-targets)). There is also evidence
its affinity predictions derive from features largely independent of the predicted pose, which
undercuts the structural story. ⚠️

**4. Generative design got good — and the architecture stopped mattering.**

The main tools:

| Tool | Who | Note |
|---|---|---|
| **REINVENT 4** | AstraZeneca, open source | The de-facto baseline. Explicitly LO-shaped: R-group replacement, linker design, scaffold hopping, molecule optimisation — not just de novo generation |
| **MolMIM** | NVIDIA | Latent-space optimisation (CMA-ES); search decoupled from the generator |
| **GenMol** | NVIDIA, ICML 2025 | Masked discrete diffusion over fragment sequences; one model covers de novo, linker design, scaffold decoration, LO |
| **Chemistry42** | Insilico | Closed commercial; source of the most-cited clinical AI-design datapoints |
| **Makya** | Iktos | Closed commercial; on AWS Marketplace |

**The finding that matters most to us:** a comparative study across generators (LLM-based,
REINVENT4, fragment-based CReM, MolMIM) found **most of them perform similarly well** — the
differentiator is the **scoring function and the constraints**, not the architecture
([J Cheminform 2025](https://link.springer.com/article/10.1186/s13321-025-01059-4)).

> Good news for us. If the generator is commoditised, the differentiated work is the scoring
> function, the constraint bookkeeping, the uncertainty handling and the audit trail. All
> platform work.

**5. Makeability moved from post-filter to in-loop objective.**

The old approach (SAScore, a heuristic) is legacy. Current tools plan actual synthetic routes:
**AiZynthFinder** (AstraZeneca, open source — described in practitioner sources as having
matured into routine industrial use), **ASKCOS** (adds forward-reaction prediction to prune
implausible routes), **RAscore** (a ~4500× faster surrogate for when you need to score millions),
and NVIDIA's **ReaSyn v2**. Best practice as of 2025 is to put retrosynthesis **inside** the
generative objective rather than filtering afterwards
([Chem Sci 2025](https://pubs.rsc.org/en/content/articlehtml/2025/sc/d5sc01476j)).

**6. Patent novelty is entering the scoring function.**

Reinforcement-learning rewards now include a *patent-novelty term* — distance in chemical space
to the nearest compound already enumerated in a patent corpus, pushing the generator away from
existing IP ("freedom-to-operate by design").

Legal overhang: as of mid-2025 the USPTO had issued **no guidance** on novelty, non-obviousness
or enablement for AI-generated compounds. Deals therefore carry human-oversight clauses and
require **contemporaneous documentation of the human inventive contribution**. ⚠️ That is a
governance requirement — and therefore a Dataiku argument.

**7. Uncertainty quantification became the thing that enables go/no-go decisions.**

A gate decision needs "the true value is in this range with this confidence", not a point
estimate. **Conformal prediction** gives distribution-free coverage guarantees. Current SOTA for
ADMET is conformalised fusion regression — a graph network with a joint mean-quantile loss plus
ensemble conformal calibration ([JCIM](https://pubs.acs.org/doi/10.1021/acs.jcim.4c01139)).

**8. Imputation is a genuinely different and better-fitted framing.**

Optibrium's **Cerella** treats the project's sparse compound × assay matrix as a *missing data*
problem: impute the expensive downstream measurements from the cheap upstream ones, and
simultaneously nominate **which experiment to run next**. For lead optimisation this arguably
fits better than training one QSAR model per endpoint. It is REST-accessible without their
desktop product — which matters for embedding it in a pipeline.

**9. Safety prediction maturity varies enormously by endpoint.** Worth internalising:

| Endpoint | Prediction maturity |
|---|---|
| **hERG** (heart rhythm) | Good — high reported AUC ⚠️ *under favourable data splits; random-split leakage is the standing criticism* |
| **CYP inhibition** (drug interactions) | Good |
| **Ames** (mutagenicity) | Good, and **regulatory-grade** — ICH M7 accepts (Q)SAR |
| **DILI** (liver injury) | **Hardest.** Mechanistically heterogeneous; models are weak |

**Regulatory driver:** the FDA's April 2025 move to phase out mandatory animal testing for
certain drug categories shifts in-silico ADMET from supporting to *primary* evidence in some
filings — which sharply raises the bar on validation, uncertainty quantification and **model
lineage**. ⚠️ Verify the current scope of that policy before citing it.

**10. Self-driving labs: real, but not here.** Genuinely working in narrow inorganic materials
domains (one system made 36 of 57 target compounds in 17 unattended days). **Not** working for
medicinal-chemistry MPO. The blockers named in the reviews are mundane: instrument interfacing,
data standardisation, failure handling. The honest current form is a "robotic co-pilot".

**Cycle-time reality anchor:** median lead-discovery → candidate-nomination interval for 15 new
chemical entities nominated since 2020 was **2.9 years**
([Drug Discov Today 2025](https://www.sciencedirect.com/science/article/pii/S1359644625000674)).

### One modality caveat worth a scoping question

**PROTACs / "beyond rule-of-5" molecules.** These are large two-headed molecules that tag a
protein for destruction rather than just blocking it. They break the standard physical-property
rules: high molecular weight and greasiness collapse solubility and absorption. The optimisation
levers are *conformational* — "molecular chameleonicity" (the molecule folds to hide its polar
groups when crossing a membrane), amide-to-ester substitution, linker methylation. Validation
for the modality: vepdegestrant (ARV-471) NDA submitted June 2025.

**Why it matters for the stories:** the QED / physicochemical scoring both stories rely on
**does not transfer to this modality** — the field uses AB-MPS and experimental EPSA instead. If
the client works on degraders, that's a scoping question to ask early, not a detail.

### The honest limits

Beyond the per-item caveats above, the summary from practitioner-facing sources:

| Industry trusts | Industry does not trust |
|---|---|
| FEP for ranking closely related molecules | Public leaderboard performance as evidence of project utility |
| Retrosynthesis planning (AiZynthFinder named specifically) | Predictions without an applicability-domain / uncertainty signal |
| Matched-molecular-pair transformation suggestions | Generative output a chemist cannot rationalise |
| In-house ADMET models trained on in-house assay data | |
| Imputation of expensive endpoints | |

**Matched molecular pairs** deserve a note: comparing pairs of molecules that differ by one
defined change ("what happens if I swap this chlorine for a fluorine, across all our data") is
the interpretability backbone chemists actually accept. Live directions: context-aware MMPA,
MMP+ML hybrids, and MMP-as-data-augmentation to expand small datasets combinatorially.

### Where Dataiku fits — **the Decide step, and the plumbing that closes the loop**

- The **MPO scoring layer** itself: desirability functions, Pareto fronts, per-project weights
  as governed parameters rather than a spreadsheet on someone's laptop
- The **Decide step**: active-learning / imputation-driven "what do we make next"
- **UQ-gated go/no-go** with conformal intervals attached to every prediction
- **Model lineage**: which model version, trained on which assay snapshot, justified which
  synthesis — increasingly an audit requirement, not a nice-to-have
- Orchestrating generators (REINVENT4 / MolMIM / GenMol) and retrosynthesis (AiZynthFinder /
  ReaSyn) as governed flow steps with the constraint set version-controlled

Not FEP. Not the generative model. Not structure preparation.

---

## 10. Stage 6 — Candidate nomination

### In plain terms

Pick **one** molecule (plus backups) to nominate as a development candidate. This is the
expensive, irreversible gate — everything after it costs orders of magnitude more.

The inputs include the entire MPO vector, plus things no model produces: freedom-to-operate,
manufacturability at scale, competitive landscape, portfolio fit, and medicinal-chemistry
judgement about what is likely to survive contact with reality.

### Two structural facts

**A human medicinal-chemistry gate before synthesis is non-negotiable** — scientifically, and
for inventorship and patent defensibility (see the USPTO overhang in §9).

**What chemists distrust is opacity, not error.** From a 2025 practitioner survey:
*"a recommendation a chemist cannot interpret is hard to trust or learn from"*
([Drug Discovery News](https://www.drugdiscoverynews.com/ai-driven-lead-optimization-how-machine-learning-is-accelerating-medicinal-chemistry-17354)).

> **The framing that survives contact with medicinal-chemistry teams: AI does prioritisation,
> not automation.** Which is, conveniently, the exact framing of the Dataiku pitch.

### Where Dataiku fits — **strong, and under-served**

A decision dashboard carrying the full MPO vector, per-prediction uncertainty, model lineage,
and a **recorded human decision with its rationale**. This is a governance product. No
chemistry vendor is really selling it, because it isn't chemistry.

---

## 11. Tool & dataset map

Stage codes: **S1** target ID · **S2** prioritisation · **S3** validation/assay · **S4** hit
finding · **S5** lead optimisation · **S6** candidate nomination.

"Us?" column: **✅ own it** = we'd build/run this · **🔌 integrate** = call it from a flow, don't
rebuild it · **📖 know it** = client-owned, be able to talk about it · **➖** = not our business.

### 11.1 At a glance — what dominates each stage

| Stage | The 4–6 things that actually matter |
|---|---|
| **S1** | Open Targets Platform · GWAS Catalog · UK Biobank / FinnGen · DepMap · PrimeKG / Hetionet · scanpy / CELLxGENE |
| **S2** | Open Targets prioritisation columns · gnomAD (LOEUF) · DepMap · GTEx + Tabula Sapiens · ChEMBL (precedent) · PDB / DrugEBIlity (pockets) |
| **S3** | DepMap / Project Score · MAGeCK / CRISPRcleanR · ELN-LIMS (Benchling, Dotmatics) · plate-QC pipelines |
| **S4** | RDKit · ChEMBL / PubChem / BindingDB · ZINC-22 / Enamine REAL · Vina / GNINA / Glide · AlphaFold / Boltz / Chai-1 · PoseBusters · ADMET-AI |
| **S5** | RDKit · REINVENT4 / MolMIM / GenMol · AiZynthFinder · FEP+ / OpenFE · Chemprop v2 · StarDrop / Cerella · LiveDesign |
| **S6** | LiveDesign / StarDrop · the ELN of record · conformal-prediction outputs · MLflow / W&B lineage |

### 11.2 Public datasets & databases

| Resource | Stages | What it is, in one line | Access | Us? |
|---|---|---|---|---|
| **Open Targets Platform** | S1 S2 | The central public evidence hub: ~63k genes, ~28k diseases, ~8M target–disease associations from >20 sources; also the prioritisation matrix | GraphQL API + Parquet (FTP/GCS/Azure), CC0 | ✅ |
| **GWAS Catalog** | S1 | Curated catalogue of genetic association studies | Free | ✅ |
| **Open Targets Genetics / Gentropy** | S1 | Credible sets, colocalisation, the L2G causal-gene model | Free, open code | ✅ |
| **UK Biobank** (incl. UKB-PPP proteomics) | S1 | 500k-participant cohort; proteomics enables cis-pQTL MR | Application + fee | 📖 |
| **FinnGen** | S1 | Finnish biobank; strong rare loss-of-function burden data | Controlled | 📖 |
| **gnomAD** | S1 S2 | Population variant frequencies; source of **LOEUF** constraint scores | Free | ✅ |
| **ClinVar / EVA** | S1 | Clinically interpreted variants | Free | ✅ |
| **DepMap** | S1 S2 S3 | CRISPR knockout dependency across ~1,000+ cancer cell lines; the essentiality reference | Free | ✅ |
| **Sanger Project Score** | S1 S3 | Independent large CRISPR screen resource (gen-2: 771 lines) | Free | ✅ |
| **CRISPRbrain** | S1 | CRISPR screens in iPSC-derived neurons | Free | 📖 |
| **cBioPortal / GDC-TCGA** | S1 | Cancer genomics: mutations, copy number, clinical outcomes | Free | ✅ |
| **COSMIC / Cancer Gene Census** | S2 | Curated cancer driver genes (oncogene / tumour suppressor) | Free (registration) | ✅ |
| **GTEx** | S2 | Bulk gene expression across ~50 human tissues | Free | ✅ |
| **Human Protein Atlas (HPA)** | S2 | Protein localisation and tissue expression; membrane/secreted calls | Free | ✅ |
| **Tabula Sapiens** | S2 | Human single-cell reference atlas; cell-type specificity | Free | ✅ |
| **DICE / PRIDE** | S2 | Immune-cell expression / mass-spec proteomics | Free | 📖 |
| **MGI / IMPC** | S2 | Mouse gene knockout phenotypes | Free | ✅ |
| **Ensembl Compara** | S2 | Orthologues (mouse model feasibility) and paralogues (off-target risk) | Free | ✅ |
| **Probes & Drugs** | S2 | Curated high-quality chemical probes | Free | ✅ |
| **DrugEBIlity** | S2 | Predicted pocket druggability scores | Free | 📖 |
| **PrimeKG** | S1 S2 | Precomputed biomedical KG: 4.05M edges, 29 edge types, 17,080 diseases — **what our POC rebuilds** | Free (Harvard Dataverse) | ✅ |
| **Hetionet** | S1 | Earlier heterogeneous biomedical network; source of the DWPC method | Free | ✅ |
| **Mondo / EFO / HPO / ChEBI / GO** | S1 S2 | Ontologies — the identifier backbone that makes joins possible | Free | ✅ |
| **DisGeNET** | S1 | Gene–disease associations; **now largely licence-gated** (we substituted Open Targets) | Paid/API | ➖ |
| **ChEMBL** | S2 S4 S5 | Expert-curated bioactivity: the primary QSAR training source. **Version-pin it** | Free | ✅ |
| **PubChem** | S4 | Huge aggregated bioactivity — **no independent curation, assay metadata lost on ingest** | Free | ✅ (with care) |
| **BindingDB** | S4 S5 | ~2.9M binding measurements; distinctive US-patent curation | Free | ✅ |
| **PDB** | S2 S4 | Experimental 3D protein structures — the holo/apo distinction lives here | Free | 🔌 |
| **PDBbind** (+ **LP-PDBBind**) | S4 | Structures with binding affinities; use the leak-proof splits | Free | 📖 |
| **AlphaFold DB** | S4 | Predicted structures for ~200M proteins | Free | 🔌 |
| **ZINC-22** | S4 | >37B enumerated / >4.5B ready-to-dock virtual compounds | Free | 🔌 |
| **Enamine REAL Space** | S4 | ~83B synthesisable-on-demand molecules; 3–4 week delivery | Free to search, paid to buy | 🔌 |
| **WuXi GalaXi / Mcule Ultimate** | S4 | Competing make-on-demand virtual libraries | Vendor | 📖 |
| **Tox21** | S4 S5 | Canonical public toxicity screening dataset | Free | ✅ |
| **TDC (Therapeutics Data Commons)** | S4 S5 | Benchmark suite: 22 ADMET datasets, 475–13,130 molecules each — **small, which caps what's learnable** | Free | ✅ |
| **RxRx3 / cpg0016 / GWPS** | S3 | Public perturbation-imaging and Perturb-seq benchmark data (Recursion-style) | Free | 📖 |

### 11.3 Structure prediction & docking

| Tool | Stages | One line | Licence | Us? |
|---|---|---|---|---|
| **AlphaFold2** | S4 | Commodity structure prediction; **apo-biased** | Open | 🔌 |
| **AlphaFold3** | S4 | Predicts protein–ligand complexes; **weights request-only, non-commercial** | Restricted | 📖 |
| **Boltz-1 / 1x** | S4 | Open AF3-class co-folding; **1x adds physics that fixes stereochemistry/clashes** | MIT | 🔌 |
| **Boltz-2** | S4 S5 | Structure **+ affinity** jointly; near-FEP claims, weakest on congeneric series ⚠️ | MIT | 🔌 |
| **Chai-1** | S4 | Co-folding, commercial use permitted; inference only | Apache 2.0 | 🔌 |
| **ESMFold** | S4 | Fast single-sequence structure prediction | Open | 🔌 |
| **AutoDock Vina / Smina** | S4 | The open docking workhorse; still a required baseline | Open | 🔌 |
| **GNINA 1.3** | S4 | Vina + CNN rescoring; **effectively won CACHE #1** | Open | 🔌 |
| **Schrödinger Glide** | S4 | The commercial docking standard | Commercial | 📖 |
| **CCDC GOLD** | S4 | Commercial docking; now integrated into Cadence Orion | Commercial | 📖 |
| **OpenEye/Cadence FRED, HYBRID, ROCS X** | S4 | Docking + 3D shape search at trillion scale ⚠️ vendor claim | Commercial | 📖 |
| **DiffDock / DiffDock-L** | S4 | Diffusion pose prediction; **requires physics minimisation + validity gate** | Open | 🔌 |
| **PoseBusters** | S4 | The physical-validity checker. **Non-negotiable after any DL docking** | Open (RDKit-based) | ✅ |
| **fpocket** | S2 S4 | Pocket detection | Open | 🔌 |
| **Schrödinger FEP+** | S5 | The trusted free-energy method (~1 kcal/mol on congeneric series) | Commercial | 📖 |
| **OpenFE** (+ alchemiscale) | S5 | Open free energy; **1.73 public / 2.44 private kcal/mol RMSE** | MIT | 🔌 |
| **MOE** | S3 S4 | Structure preparation, protein modelling, medchem workbench | Commercial | 📖 |

### 11.4 Molecular ML & cheminformatics

| Tool | Stages | One line | Us? |
|---|---|---|---|
| **RDKit** | S4 S5 | The substrate for everything: descriptors, Morgan fingerprints, QED, conformers, standardisation, MMP fragmentation. Also the engine inside PoseBusters | ✅ |
| **Chemprop v2** | S4 S5 | Message-passing GNN for property prediction; v2 adds UQ + calibration, ~2× faster | ✅ |
| **DeepChem** | S4 S5 | Model zoo; now hosts standardised ChemBERTa-3 | ✅ |
| **ADMET-AI** | S4 S5 | 41-dataset ADMET predictor; contextualises against approved drugs; library-scale throughput | ✅ |
| **Deep-PK** | S4 S5 | 73 PK/tox endpoints via free web server | 🔌 |
| **MolFormer / ChemBERTa / Uni-Mol / MiniMol** | S4 S5 | Molecular foundation models — **frequently lose to fingerprints** ⚠️ | 📖 |
| **MoleculeACE** | S4 S5 | The activity-cliff benchmark; the reason to distrust leaderboards | ✅ |
| **chembl-downloader** | S4 | Reproducible version-pinned ChEMBL extraction | ✅ |
| **HASTEN / Deep Docking** | S4 | Active-learning acceleration for ultra-large virtual screens | 🔌 |
| **BioSolveIT infinisee / SeeSAR / FTrees** | S4 | Chemical-space navigation over REAL Space | 📖 |
| **Conformal prediction / Venn-ABERS libraries** | S4 S5 S6 | Calibrated uncertainty and applicability domain | ✅ |

### 11.5 Generative design & synthesis planning

| Tool | Stages | One line | Licence | Us? |
|---|---|---|---|---|
| **REINVENT 4** | S4 S5 | The open baseline; scaffold hopping, R-group replacement, linker design, LO | Open (AZ) | 🔌 |
| **MolMIM** | S5 | Latent-space property-guided optimisation; shipped as a BioNeMo NIM | NVIDIA | 🔌 |
| **GenMol** | S4 S5 | Fragment-sequence discrete diffusion; one model for many LO tasks | NVIDIA | 🔌 |
| **Chemistry42** | S4 S5 | Insilico's closed platform; behind the rentosertib story | Commercial | 📖 |
| **Iktos Makya** | S5 | Closed generative platform; on AWS Marketplace | Commercial | 📖 |
| **AiZynthFinder** | S5 | Open retrosynthesis; **named as matured into routine industrial use** | Open (AZ) | 🔌 |
| **ASKCOS** | S5 | Retrosynthesis + forward-reaction prediction | Open (MIT) | 🔌 |
| **RAscore** | S5 | ~4500× faster synthesisability surrogate for scoring millions | Open | 🔌 |
| **NVIDIA ReaSyn v2** | S5 | Synthesisability of AI-designed molecules | NVIDIA | 🔌 |
| **SYNTHIA / IBM RXN / Molecule.one** | S5 | Commercial route planning | Commercial | 📖 |

### 11.6 MPO, design workbenches & decision tools

| Tool | Stages | One line | Us? |
|---|---|---|---|
| **Optibrium StarDrop** | S5 S6 | Probabilistic MPO scoring that propagates prediction *and* assay error; v8 (Nov 2025) added real-time collaboration | 📖 |
| **Optibrium Cerella** | S5 | Deep-learning imputation over the sparse compound × assay matrix + next-experiment recommendation; **REST API, no desktop needed** | 🔌 |
| **Schrödinger LiveDesign** | S5 S6 | The enterprise design hub, coupled to Glide/FEP+/QikProp | 📖 |
| **Cresset Flare** | S5 | Field-based 3D SAR, plus FEP | 📖 |
| **Chemaxon** | S4 S5 | Registration, JChem, Marvin — the plumbing layer | 📖 |
| **CNS MPO / AB-MPS / EPSA** | S5 S6 | Published desirability scores; AB-MPS/EPSA are the beyond-Ro5 replacements for QED | ✅ |

### 11.7 Data capture, ELN/LIMS & registration — *the incumbent layer*

| Tool | Stages | One line | Us? |
|---|---|---|---|
| **Dotmatics** | S3–S6 | ELN + LIMS + analytics + registration. **Acquired by Siemens, $5.1B EV, closed 1 July 2025** | 📖 integrate |
| **Revvity Signals** | S3–S6 | Signals Research Suite; now shipping **Models-as-a-Service off the ELN**; agreed to acquire ACD/Labs (Nov 2025) ⚠️ | 📖 integrate |
| **Benchling** | S3–S6 | Biology-first ELN/LIMS, strong API; launched Benchling AI agents (Oct 2025) ⚠️ | 📖 integrate |
| **CDD Vault** | S3–S6 | Hosted registry + assay data; pragmatic for biotechs/CROs; ships Boltz-2 co-folding built in | 📖 integrate |
| **IDBS Polar / LabWare / Sapio / L7** | S3 | Other LIMS/ELN incumbents; Sapio is embedding BioNeMo models directly ⚠️ | 📖 |

> **Read the trend, not the list.** Siemens buying Dotmatics, and Revvity serving models straight
> off the ELN, both point the same way: **incumbents are pulling model-serving toward the
> data-capture layer.** Our position must be the cross-domain analytical and decision layer
> *above* them — and we should say that early in any client conversation, or they will assume
> we are pitching against their ELN.

### 11.8 Orchestration, platform & serving

| Tool | Stages | One line | Us? |
|---|---|---|---|
| **Dataiku** | S1 S2 S5 S6 | Evidence integration, Visual ML + SHAP, the Decide step, governance, dashboards | ✅ |
| **KNIME** | S4 S5 | The dominant no-code workflow layer for chemists; strong RDKit/Schrödinger nodes. **Our closest analog in this space — expect the comparison** | 📖 |
| **BIOVIA Pipeline Pilot** | S4 S5 | Enterprise scientific workflow; entrenched, declining mindshare | 📖 |
| **Nextflow + nf-core / Snakemake** | S1 S3 | The bioinformatics pipeline standard | 📖 |
| **Neo4j / Kùzu / Memgraph** | S1 S2 | Graph storage and query. **Our POC uses Kùzu** via the Visual Graph plugin | ✅ |
| **PyKEEN / DGL-KE / PyTorch Geometric** | S1 | Knowledge-graph embedding and GNN libraries | ✅ |
| **scanpy / Seurat / squidpy / CELLxGENE Census** | S1 S3 | Single-cell and spatial analysis toolchain | ✅ |
| **MLflow / Weights & Biases** | S4 S5 S6 | Experiment tracking and model registry. **The lineage requirement**: which model version, on which assay snapshot, justified which synthesis | ✅ |
| **NVIDIA BioNeMo** (framework + NIM microservices) | S4 S5 | Containerised inference for AlphaFold2, ESMFold, OpenFold2, ESM-2, ProteinMPNN, RFdiffusion, MolMIM, GenMol, DiffDock; reference [generative virtual screening blueprint](https://github.com/NVIDIA-BioNeMo-blueprints/generative-virtual-screening) chains structure → generate → dock. ⚠️ **Catalogue changes frequently — verify live at build.nvidia.com before promising any specific NIM** | 🔌 |
| **Hugging Face** | S4 S5 | Good coverage of molecular language models; Boltz/Chai ship via GitHub + direct weights instead ⚠️ | 🔌 |

---

## 12. Dataiku's defensible position

### Where we genuinely win

| Play | Stages | Why it's ours |
|---|---|---|
| **Public-evidence integration + KG** | S1 S2 | Dozens of sources, identifier reconciliation, lineage, reproducibility. Already proven by this POC |
| **The prioritisation traffic light** | S2 | Join-and-normalise over ~8 free sources + a dashboard. Mirrors the Open Targets reference exactly. Most winnable increment we have |
| **Explainable ranking (Visual ML + SHAP)** | S1 S2 S4 S5 | L2G's own pattern. Explainability is the *adoption* driver: TxGNN's expert study showed path explanations raised accuracy +46%, confidence +49% |
| **The "Decide" step of D2MTL** | S5 | Active-learning prioritisation over more designs than can be synthesised. Named as a new step by AZ; **not owned by an incumbent** |
| **Orchestrating third-party AI as governed steps** | S4 S5 | AlphaFold/Boltz/DiffDock/MolMIM/GenMol as flow recipes with versioned inputs, outputs and parameters |
| **Assay-data plumbing & version pinning** | S3 S4 S5 | The bottleneck named by every source: instrument formats, protocol metadata, failure capture |
| **UQ-gated go/no-go + model lineage** | S5 S6 | Becomes an audit requirement as in-silico ADMET is admitted as primary evidence |
| **Agentic layer over deterministic tools** | S4 S5 | Exactly the Story 1 pattern: the LLM negotiates thresholds and explains; deterministic tools do the science |

### Where we should not pretend

Docking and pose prediction · free-energy calculation · the generative chemistry model itself ·
protein structure preparation · being the ELN/registry system of record.

### The narrative, in three sentences

> Genetic and network evidence de-risks **efficacy** (Phase II/III). Computational chemistry
> de-risks **developability** (Phase I). Both are now demonstrated with real numbers — but they
> live in different teams, on different systems, with no shared audit trail, and the handoff
> between them is where hypotheses lose their evidence.
>
> That connective tissue is a data-platform problem, not a chemistry problem.
>
> And we already have a working demo of the upstream half.

---

## 13. Concrete revisions to the drafted stories

The two stories are directionally sound — they are recognisable versions of real workflows, and
the "deterministic tools do the science, the LLM handles conversation and explanation" split is
the right instinct and should be kept prominently.

Below: eight specific changes. Each one gives the draft text, the replacement, the evidence, and
what it costs to build.

---

### 13.1 Structure sourcing — replace the AlphaFold fallback with an explicit tier

**Draft says:** *"When no suitable experimentally resolved structure is available, an
AlphaFold-predicted three-dimensional protein structure and an interactive viewer."*

**Problem:** this treats AlphaFold as a like-for-like substitute. It isn't. AlphaFold predicts
the *empty* pocket shape, and costs you roughly **half the screening enrichment** of a real
ligand-bound structure (EF1% ≈ 24.2 holo vs 13.0 AF2 — §8). Screening against an AlphaFold model
and reporting hit rates as if it were a crystal structure is the single most likely place for
this demo to be scientifically challenged in the room.

**Change to — a four-tier receptor selector, displayed in the UI:**

| Tier | Receptor source | Expected enrichment | UI label |
|---|---|---|---|
| 1 | PDB **holo** structure (co-crystallised with any ligand) | EF1% ≈ 24 | 🟢 *Experimental, ligand-bound* |
| 2 | **AF3 / Boltz-1x co-folded** complex (holo-*like*) | between tiers 1 and 3 | 🟡 *Predicted complex* |
| 3 | PDB **apo** structure | EF1% ≈ 11 | 🟠 *Experimental, empty pocket* |
| 4 | **AlphaFold2 / AFDB** model, ideally an MSA-subsampled ensemble | EF1% ≈ 13 | 🟠 *Predicted, apo-like* |

**Build:** a Python recipe querying the PDB REST API for structures of the target, splitting on
whether any non-solvent ligand is bound; a `receptor_tier` column carried through the whole flow;
the tier badge shown next to the structure viewer and stamped on every downstream score.

**Why this is a win, not a concession:** tiering *is* a governance feature. It turns "we used
AlphaFold" into "we know what our receptor is worth, and every score downstream is labelled with
it." That is a platform story no docking vendor tells.

**Bonus:** the tier also justifies a second Dataiku artifact — a per-target *screenability*
report. Tier 4 + GPCR target is a legitimate "don't bother with virtual screening, go DEL or
fragments" recommendation, and that recommendation is worth more to a client than another hit list.

---

### 13.2 Docking — add a physics gate, not just a disclaimer

**Draft says:** *"DiffDock-predicted binding poses… A persistent disclaimer explaining the
meaning and limitations of the DiffDock confidence score."*

**Assessment:** the disclaimer is good and correct — the confidence score is confidence in the
*pose*, not affinity, not evidence of activity. Keep every word of that. But a disclaimer
mitigates *reporting* risk, not *scientific* risk. The 2025 consensus architecture is **AI
generation → physics minimisation → validity gate** (PoseBusters, then PoseX — §8).

**Change to — a four-step pose pipeline, with a visible reject count:**

1. **Specify the pocket.** PoseX found pocket specification substantially improves success rates.
   Take the pocket from the tier-1/2 ligand position where available, else fpocket.
2. **Generate poses** — DiffDock (or Boltz-1x co-folding, which handles chirality correctly
   where other co-folding models don't).
3. **Minimise** — force-field relaxation of each pose in the pocket. This step is what rescues
   DL poses; without it the poses are frequently physically impossible.
4. **Gate with PoseBusters** — bond lengths, bond angles, aromatic-ring planarity,
   stereochemistry, internal clashes, protein–ligand clashes. Poses that fail are **rejected, and
   the reject count is shown.**

**Build:** PoseBusters is a pip-installable RDKit-based checker — a single Python recipe.
Minimisation via OpenMM or RDKit force fields. Both are cheap relative to the DiffDock call.

**Add a classical baseline.** Run Vina or GNINA alongside on the same shortlist. It costs almost
nothing, and it is the difference between "we used the new thing" and "we know the new thing was
better here." Note that **CACHE #1 was effectively won with careful GNINA docking** — the
baseline is not a straw man.

**UI change:** the pose viewer should show, per compound: poses generated → poses physically
valid → best valid pose. A visible "3 of 10 poses rejected as physically invalid" line is the
most credibility-building element you can put on that screen.

---

### 13.3 Predictions — make uncertainty and applicability domain first-class outputs

**Draft says:** *"Machine-learning predictions for bioactivity and toxicity"* and, in Story 2,
*"Rescoring of every generated compound using the existing workflow."*

**Problem:** this is the weakest scientific link in the whole chain, and it is structural, not
incidental. Story 2 generates molecules that are *by construction* pushed away from the training
data — that's the point of generative optimisation. That is precisely where QSAR models fail
(MoleculeACE: every method degrades on activity cliffs), and where the intuitive uncertainty
proxy actively misleads: **ensemble variance decreases for molecules with no structural
similarity to the training set** (§8, limit 2). So the rescoring step can hand back confident,
wrong numbers on exactly the compounds MolMIM was asked to invent.

**Change to — every prediction row carries four fields instead of one:**

| Field | Example | How |
|---|---|---|
| `pred_value` | pIC50 7.2 | the model |
| `pred_interval` | [6.1, 8.3] at 90% | conformal prediction on a held-out calibration set |
| `in_domain` | `false` | max Tanimoto similarity to training set < threshold (declare it) |
| `nearest_train_analog` | CHEMBL… , Tanimoto 0.28 | nearest-neighbour lookup |

**And enforce scaffold splits.** Report scaffold-split metrics for every model in the demo,
never random-split. Random splits on chemistry data are the single most common way to produce a
metric that is real on the slide and fake in the lab.

**UI change:** in the shortlist table, an out-of-domain compound should be visually marked, and
the agent's rationale panel should say so in words — *"predicted potency 7.2, but this compound
is outside the model's applicability domain (nearest training analog Tanimoto 0.28), so treat the
prediction as a hypothesis."*

**Why this is the highest-value change on this list:** it converts the demo's biggest scientific
weakness into its most differentiated feature. Practitioner sources are explicit that
*"predictions without a domain-of-applicability / uncertainty signal"* sit in the
**not-trusted** column (§10). Almost nobody ships this well. It is pure platform work — no
chemistry expertise required — and it is exactly what a governance-led vendor should be selling.

---

### 13.4 Assay data — pin the version and declare the aggregation rule

**Draft says:** *"Retrieval of previously studied molecules and available assay data from public
resources such as ChEMBL and PubChem."*

**Problem:** under-specified in three ways that each change the model's labels.

1. **PubChem does no curation of its own** and loses assay metadata on ingestion. Mixing it with
   ChEMBL without provenance flags silently degrades the training set.
2. *"The ChEMBL dataset for target X"* is not a well-defined object without a **version pin** —
   target-specific datasets vary substantially across releases.
3. When a molecule has several measurements, **arithmetic vs geometric mean of pIC50 changes the
   label** — and mixing assay types (IC50 vs Ki vs EC50) without normalising is worse.

**Change to — a documented, visible extraction contract:**

- Pin the ChEMBL release (e.g. `ChEMBL_35`) as a **project variable**, surfaced in the UI
- Extract via `chembl-downloader` for reproducibility
- Filter explicitly: assay type, confidence score ≥ 8 (direct single-protein), units normalised,
  activity comment exclusions
- **Geometric mean** for replicate aggregation (state it), with the replicate count and spread
  retained as columns
- `data_source` and `assay_id` provenance columns retained end to end
- PubChem, if used, kept as a **separate flagged tier**, never silently merged

**Build:** one Python extraction recipe plus a Prepare recipe. Trivial. And it makes a visible
platform point — "your model is reproducible because the dataset is addressable" is a sentence a
scientist will believe from us and not from a black box.

---

### 13.5 Toxicity — split the single score into per-endpoint predictions with per-endpoint trust

**Draft says:** *"Machine-learning predictions for bioactivity and toxicity"* and treats
toxicity as one qualification criterion.

**Problem:** prediction quality varies enormously by endpoint (§9). One score averages a credible
prediction together with a poor one and hides both.

**Change to — a per-endpoint panel with an explicit trust level:**

| Endpoint | What it risks | Model trust | Show as |
|---|---|---|---|
| **hERG** | Cardiac arrhythmia | Good ⚠️ split-dependent | value + interval |
| **CYP inhibition** (3A4, 2D6, 2C9) | Drug–drug interactions | Good | value + interval |
| **Ames** | Mutagenicity — **regulatory-grade**, ICH M7 accepts (Q)SAR | Good | value + interval + regulatory note |
| **DILI** | Liver injury | **Weak** — mechanistically heterogeneous | value + interval + explicit low-confidence flag |

**Source:** ADMET-AI covers these and — importantly for a non-specialist audience —
**contextualises each prediction against a reference set of approved drugs**, so "0.31" becomes
"in the 70th percentile of approved drugs." Use that framing in the UI; it is the single easiest
readability win available.

**Threshold consequence:** the scientist-editable qualification thresholds should therefore be
**per endpoint**, not one toxicity cutoff. That makes the "agent verifies criteria with the
scientist" interaction richer and more obviously useful, because there are genuinely several
decisions to negotiate.

---

### 13.6 Generative loop — put makeability inside the objective

**Draft says:** *"MolMIM-generated molecular variants guided towards improved QED"* → then
rescore, then Tanimoto-compare, then dock.

**Problem:** synthesisability appears nowhere. The most common medicinal-chemistry objection to
generative output is *"nobody can make that."* A diverse, high-QED, well-docked shortlist of
unmakeable molecules is a demo that dies in the first technical review. And 2025 best practice
has moved: retrosynthesis belongs **inside** the generative objective, not as a downstream filter
(§9).

**Change to:**

1. Add **synthesisability to the optimisation objective**, not the filter — MolMIM's CMA-ES
   latent search can optimise a composite objective, so include a retrosynthesis-derived term
   (**RAscore** as the fast surrogate inside the loop; **AiZynthFinder** for a full route on the
   final shortlist only).
2. Show the **proposed synthetic route** for each shortlisted variant. This is a genuinely
   compelling artifact for a bench audience and costs one AiZynthFinder call per compound.
3. Reframe the objective honestly. QED-only optimisation is a weak objective — and the comparative
   evidence says **the generator architecture barely matters; the scoring function is the whole
   game** (§9). So the demo's centre of gravity should be *the composite objective and its
   governance*, not MolMIM. Suggested composite: predicted potency (with interval) × per-endpoint
   safety × physicochemical desirability × synthesisability × Tanimoto-to-parent constraint.

**Bonus:** this reframing is strategically better for us. If the scoring function is the
differentiator, then the demo's hero is the Dataiku-managed objective and its audit trail — not
NVIDIA's model.

---

### 13.7 Add a patent-novelty term and inventorship documentation

**Not in the draft at all.** Two reasons to add it:

- **Scientific/commercial:** patent-novelty terms — distance to the nearest compound already
  enumerated in a patent corpus — are entering generative scoring functions ("freedom-to-operate
  by design"). A generated molecule that sits inside someone else's claim is worthless regardless
  of its QED.
- **Governance:** as of mid-2025 the USPTO had issued **no guidance** on novelty or
  non-obviousness for AI-generated compounds. ⚠️ Deals consequently require human-oversight
  clauses and **contemporaneous documentation of the human inventive contribution**.

**Change to:** (a) a `nearest_patent_analog` + `patent_distance` column in the shortlist, even if
computed against a modest corpus for the demo; (b) an immutable **decision record** — which
scientist approved which thresholds, at what time, on which model version, and which compounds
they selected and why.

**Why this matters more than it looks:** (b) is a pure Dataiku governance feature that maps onto a
live legal requirement the client's IP team already cares about. It is the kind of thing that
turns a science demo into a procurement conversation.

---

### 13.8 Story 1 → Story 2 handoff and QED's limits

Two smaller items.

**Reuse of the structure is right — say why explicitly.** The draft notes the target structure is
reused from Story 1, "avoiding an unnecessary second AlphaFold call." Good instinct, but the real
argument is stronger than cost: it means both stories score against the **same receptor at the
same tier**, so the parent and its variants are comparable. Make that the stated reason —
comparability, with cost as a side benefit.

**QED is a contested primary objective.** For anything beyond conventional small molecules —
PROTACs and other beyond-rule-of-5 modalities — molecular weight and greasiness rules break down,
and the field uses **AB-MPS** and experimental **EPSA** instead (§9). If the client works on
degraders, QED-guided optimisation is the wrong objective and should be swapped. **Ask this in
scoping**, early: *"are degraders or other beyond-Ro5 modalities in scope?"* It is a
five-second question that changes the entire scoring layer.

---

### 13.9 The framing correction that matters most

Both stories are **Phase-I-shaped**. They optimise developability and tolerability — potency,
QED, physical properties, predicted toxicity. That is genuinely where computational design has
proven value: **80–90% Phase I success** (§2).

But neither story addresses *whether this is the right target*. That question — the one that
drives the ~40% Phase II failure rate, unchanged by AI chemistry — is answered upstream, in
stages 1–3, by genetics and network evidence.

> **The recommendation:** pitch the two halves together. A solution that shows a target
> hypothesis being built from genetic and network evidence, *then* carried into structure-based
> screening and optimisation with the evidence and uncertainty preserved across the handoff, is a
> substantially stronger and more differentiated story than either half alone.
>
> We already have a working demo of the upstream half, on the same platform, with the same
> governance model. Nobody else in this conversation does.

**Concretely, the joining artifact is small:** a target-context panel on the Story 1 screen —
genetic-evidence score, network-evidence rank, DepMap essentiality, tissue specificity,
tractability flags — pulled from the existing POC's outputs. One join. It converts two demos into
one narrative.

---

## 14. Verification debt ⚠️

Same discipline as `RESEARCH_NOTE.md`: this document was assembled from a research pass, not from
independently validated facts. Before any client-facing use, verify:

| Claim | Why it's flagged |
|---|---|
| Open Targets prioritisation **distribution-row polarity** | Docs read counter-intuitively for a safety bucket; check the live UI colours |
| **Atomwise 26%** hit rate | Vendor-authored; threshold-dependent; carries a published Author Correction |
| **Boltz-2** near-FEP affinity claims | Authors' own claim; independent reviews are notably more cautious |
| **DiffDock-L** improvement percentages | Secondary sources only |
| **Pocket-leakage** ~14% figure | Secondary summaries of the primary arXiv work |
| **Enamine ~94.5B** | Undated vendor page; safe public claim is ≥83B |
| **OpenFE** exact company list and RMSE CIs | The ChemRxiv/JCIM papers are the fetchable primaries; the press release timed out during research |
| **MolGenBench** dataset scale | bioRxiv returned 403 during research |
| **NVIDIA BioNeMo NIM catalogue** | Changes frequently — check build.nvidia.com live before promising any specific microservice |
| **hERG AUC ~0.96** | Split-dependent; do not quote without stating the split |
| **FDA April 2025 animal-testing phase-out** scope | Verify which categories, and what it actually requires |
| Iktos / Sygnature / Schrödinger / OpenEye throughput claims | All vendor-sourced |
| Revvity–ACD/Labs, Benchling AI, Sapio–BioNeMo announcements | Press/secondary only |
| "Cell-type-specific expression → better Phase I odds" | Review-level claim; primary study not verified |
| **TxGNN +46% accuracy / +49% confidence** | Verified in the earlier POC research pass (`RESEARCH_NOTE.md`) — safe to cite |
| **Minikel 2024 2.6×** and the **Phase I 80–90% / Phase II ~40%** split | Primary, peer-reviewed, load-bearing — cite freely |
