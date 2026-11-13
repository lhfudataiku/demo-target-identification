# Future directions — what the shortlist cannot yet tell apart, and what would fix it

> **Lifecycle:** Evidence and proposal · **Audience:** whoever picks the project up after release,
> and presenters who need to answer "what would make it better?" · **Authority:** the 2026-11-10
> review of the served shortlist, the limitations it traces to the graph and model, and candidate
> extensions to Part 1; not a plan of record · **Update when:** an extension is scoped into a
> workplan, or the champion or served panel changes enough to move the findings · **Generated
> dependencies:** none (measured once on the served data; no notebook asserts these numbers) ·
> **Excludes:** the demo story, in [`DEMO_NARRATIVE.md`](DEMO_NARRATIVE.md); the graph method, in
> [`GRAPH_BUILDING.md`](../graph/GRAPH_BUILDING.md).

**Status:** written at release, 2026-11-10. Nothing here is scheduled. Every number below was measured
once, on `dashboard_candidates` after the R6 rebuild (champion `m7-f14-cal`, saved-model version
`1794305004361`, graph snapshot `ZKGaRg` of 2026-11-10), and the label measurements in §3.4 on
`scored_champion` (graph-revision step R7). No notebook asserts them, so re-measure before quoting any
of them.

## 1. In one paragraph

The model does what the demo claims: from public knowledge alone it puts the genes each field already
knows at the top of the list. The review shows *which* knowledge that is. In the large cancers, "known"
means the general set of cancer-driver genes, so HER2-positive breast, lung and gastric cancer get
almost the same list. Outside cancer, a single protein complex can fill the top, and approved drug
targets that carry no genetic evidence rank low. Each pattern traces to a specific choice in the labels,
the graph or the features (§3). The labels matter most, and we measured by how much (§3.4): scored on
germline evidence alone, HER2+ falls from AUC 0.94 to 0.81. So the first fix is to the labels, from data
already in hand, before any new source is added (§4).

## 2. What the review found

The top 100 genes of each of the twelve served diseases.

| Finding | Evidence |
|---|---|
| **The three large cancer lists are one list.** | HER2+, lung adenocarcinoma and gastric adenocarcinoma share 93–95 of their top 100 genes, 91–94% of them known associations. The same gene scores alike across them (rank correlation 0.95, HER2+ against lung). |
| **The gene that defines HER2+ is not at the top.** | ERBB2 ranks #29 for HER2+. GRB7, amplified with it, ranks #1,778. |
| **The same "novel" genes appear in every large cancer.** | STAT1, SMARCA2, SMARCD3 and IRS1 sit in all three top 100s. SMARCA2 ranks #46 (HER2+), #51 (gastric), #52 (lung). |
| **"Novel" mostly means unlabelled, not discovered.** | Endometrial cancer's "novel" genes include the Lynch-syndrome genes PMS2 and MSH6. Triple-negative breast's top is the DNA-repair set (RAD50, ATM, BRCA2 at #3, BRIP1, BARD1, RAD51C): biologically coherent, but it has only 8 known genes, so it is a label gap, not a result. |
| **One protein complex can fill a list.** | In diabetes, the top is mitochondrial complex I. 37 of the top 100 carry an approved-drug badge; 35 are complex I subunits, almost certainly because metformin is recorded against the whole complex (the other two are PPARG and COXFA4). ATP synthase does the same in dilated cardiomyopathy. |
| **Approved drug targets without genetic evidence rank low.** | Diabetes: GLP1R #1,087, DPP4 #2,489, SLC5A2 #10,482. Rheumatoid arthritis: TNF #431, IL6R #200. Familial hypercholesterolemia: PCSK9 #217, HMGCR #198, and no approved badge anywhere in its top 100. |
| **Some lists are excellent.** | Dilated cardiomyopathy: TTN #1, TNNT2 #2, MYH6, MYBPC3, with plausible new sarcoglycan and desmosome genes. Psoriatic arthritis: IL23A #3, IL12B and IL23R, the targets of its approved antibodies. |
| **Scores are nearly flat at the top.** | The top score is about 0.40 for most diseases; HER2+'s top 100 spans 0.407 to 0.374. The order inside that band is fragile: ERBB2 moved #16 → #29 between two retrains on nearly the same data. |

**For the demo.** The reconstruction claim holds. But the HER2+ opening is an easy pass, and it would
look the same on lung: most of HER2+'s AUC comes from pan-cancer labels (§3.4). A disease-specific list
makes the stronger opening: dilated cardiomyopathy, whose labels are germline and phenotype rather than
somatic and which scores *higher* (0.885) once its phenotype-only labels are removed, or psoriatic
arthritis. HER2+ then works as the comparison.

## 3. Why: limitations inherited from the graph and the model

### 3.1 The labels

- **Cancer labels are pan-cancer somatic-mutation genes.** Of HER2+'s 644 gene links in the graph,
  639 are "somatic mutation association"; gastric's are all somatic. These sources list recurrent
  drivers, so the same genes attach to almost every cancer: **592 of HER2+'s 599 known genes are also
  known for lung adenocarcinoma.** Diseases with the same labels get the same list.
- **Phenotype-derived links add genes by shared symptom, not mechanism.** They are 128 of dilated
  cardiomyopathy's 242 links and 198 of diabetes's 1,289. This route probably explains psoriatic
  arthritis's skeletal and glycan-enzyme genes and the mitochondrial genes in diabetes and
  cardiomyopathy. §3.4 measures how much it matters: less than expected.
- **Labels sit on the exact disease node,** so a gene recorded for a parent or sibling disease counts
  as novel.
- **The label means genetic association, not drug target.** Many successful targets have no genetic
  evidence for their disease, and the model was never shown drug mechanisms.

### 3.2 The graph

- **No disease-specific molecular data:** no expression, tissue, copy number or receptor status.
  HER2+, luminal B and triple-negative breast differ mainly in exactly those things. HER2+'s defining
  event is ERBB2 amplification, which mutation-based association sources capture poorly.
- **Protein complexes act as one dense block.** Subunits share GO terms and pathways and all interact,
  so when several are labelled, every other subunit inherits nearly the same features. One fact is
  counted dozens of times.
- **Drug links are recorded on the exact disease node,** which is why familial hypercholesterolemia
  shows no approved drug.
- **Interaction data reflects how much a gene has been studied.**

### 3.3 The features and the model

- **10 of the 14 features measure closeness to the disease's known genes.** They cannot be more
  specific than those labels: with pan-cancer labels, closeness means "close to cancer drivers".
- **4 of the 14 do not depend on the disease at all** (`gene_ppi_degree`, `gene_n_pathways`,
  `ppi_evidence_depth`, `ppi_multi_source_frac`; each has one value per gene in every disease). They
  carry **31%** of the model's Shapley importance: a built-in "well-studied gene" prior.
- **The hub preference is strongest where the known genes are hubs:** score against network degree
  correlates 0.32 in HER2+ but 0.03 in cardiomyopathy and psoriatic arthritis.
- **Features need at least 20 known genes.** Below that, the path and topology features are left
  blank, so triple-negative breast (8 known) is ranked on proximity and the disease-independent
  features alone.
- **Per-disease AUC rewards this.** A held-out cancer's known genes are the same drivers seen in
  training, so recognising a cancer driver scores well on any cancer. The grouped split stops a
  disease leaking across folds, not the same labels recurring across diseases. §3.4 shows the size of
  the reward.

### 3.4 Measured: how much the labels carry (graph-revision step R7)

Every validation positive is exactly one disease–gene link in the graph, and the graph says what kind:
of 65,546 validation positives, 35,981 are somatic-mutation links, 20,840 germline, 394 both, and
8,331 (12.7%) phenotype-derived only. Re-scoring the champion's per-disease AUC without each kind:

| scored on | diseases scored | unchanged | higher / lower | macro AUC (same diseases) | paired test |
|---|--:|--:|--:|---|---|
| all positives (the headline) | 603 | — | — | 0.8180 | — |
| without phenotype-only positives | 564 (39 lose all positives) | 466 | 40 / 58 | 0.8177 → 0.8132 | Wilcoxon p = 0.035 |
| germline positives only | 424 (179 lose all positives) | 260 | 51 / 113 | 0.7821 → 0.7591 | p = 3×10⁻⁸ |

| disease | all positives | without phenotype-only | germline only |
|---|--:|--:|--:|
| HER2+ breast carcinoma | 0.938 | 0.938 | **0.809** (5 positives) |
| lung adenocarcinoma | 0.934 | 0.934 | **0.775** |
| gastric adenocarcinoma, both endometrial | 0.94–0.97 | unchanged | no germline positive |
| dilated cardiomyopathy | 0.837 | **0.885** | 0.885 |
| diabetes mellitus | 0.683 | **0.659** | 0.659 |

What it settles:

- **The somatic labels are the large effect.** On the 164 diseases the germline-only view changes,
  macro AUC falls from 0.849 to 0.790. The cancers' high AUC is mostly the model recognising
  pan-cancer drivers, the same mechanism that makes their lists identical.
- **The phenotype-derived links are a small, two-sided effect.** 466 of 564 diseases have none; on the
  98 that do, macro falls from 0.827 to 0.801. They help the model in diabetes and hurt it in
  cardiomyopathy, so dropping them is a per-disease choice, not a general correction.
- **The headline is robust to the phenotype question** (0.8180 → 0.8132) **but not to the somatic one.**
  A reconstruction claim made on cancers should say which evidence it reconstructs.

## 4. Proposal: what Part 1 could add

Ordered by fit to the findings and by cost. Licences are as understood at writing and must be checked
before use, by the same triage as the current sources in
[`DATA_SOURCE_LICENSE_REVIEW.md`](../graph/DATA_SOURCE_LICENSE_REVIEW.md).

### 4.1 First: better labels from data already in hand

§3.4 says this is where the leverage is, and none of it needs a new download.

- **Split Open Targets evidence by source,** not just by type. Pan-cancer catalogues (Cancer Gene
  Census) then stay apart from cohort-specific driver calls (IntOGen), and Mendelian evidence apart
  from GWAS gene assignment, so the training label is chosen rather than inherited. This is the direct
  fix for the largest measured effect: cancers trained and evaluated on labels that differ between
  them.
- **Report the germline-only evaluation as a standard second reading** beside the headline, as §3.4
  does, so a reader can see how much of a cancer's AUC is pan-cancer recognition. It should get a
  notebook assertion before it is quoted anywhere outside this document.
- **Keep phenotype-derived links as their own relation** (R2 already labels them), so they can leave
  the label without leaving the graph. Decide per disease: §3.4 shows they help some and hurt others.
- **Inherit drug links through the MONDO hierarchy** for the drug badges and the benchmark (not the
  label). This gives familial hypercholesterolemia its LDL-lowering drugs.

### 4.2 Then: disease-specific signal

| Addition | Nodes and edges | Addresses |
|---|---|---|
| **Open Targets `animal_model` evidence** | new relation `disease_protein_animal_model` | Evidence independent of human genetics and not pan-cancer. Same pinned release (26.06) and the same table `extract_ot_assoc` already reads |
| **Mouse phenotypes** (IMPC / MGI, Mammalian Phenotype ontology, uPheno mapping) | `mouse_phenotype` node; gene → mouse phenotype; mouse ↔ human phenotype | The structured form of the above, enabling new path features |
| **Tissue expression** (Bgee; or GTEx / Human Protein Atlas) | `anatomy` node (Uberon); gene expressed / absent in tissue; disease affects tissue | Separates heart from tumour genes. The original PrimeKG carried this; this graph dropped it |
| **Cell types** (Cell Ontology, single-cell markers) | `cell_type` node; gene marks cell type; disease involves cell type | Finer than tissue: cardiomyocytes, T cells |
| **Cancer dependency** (DepMap CRISPR, by lineage) | gene dependent in a lineage, linked to diseases through MONDO | Separates breast, lung and gastric by what their cells need |
| **Copy number** (TCGA via cBioPortal) | gene amplified / deleted in a cancer type | Captures ERBB2 amplification. Avoid COSMIC copy-number data (commercial licence) |

### 4.3 Structure

| Addition | Nodes and edges | Addresses |
|---|---|---|
| **Protein complexes** (Complex Portal) | `complex` node; gene part of complex | Count a complex once, or cap its members in the top N |
| **Directed, signed signalling** (SIGNOR, OmniPath) | gene activates / inhibits gene | Cause-and-effect edges, less driven by study volume |
| **Tissue-specific networks** | interaction edges tagged by tissue | A neighbourhood per disease context instead of one shared network |
| **Genetic constraint** (gnomAD LOEUF) | gene property | A disease-independent signal not driven by study volume |

### 4.4 Deliberately left out

- **Open Targets literature evidence:** it encodes how often a gene is mentioned and would amplify
  the popularity bias.
- **Open Targets `known_drug` as a feature:** already rejected as redundant, and it overlaps the drug
  badges the enrichment is measured against.
- **DisGeNET, OMIM, COSMIC:** licences restrict commercial use.

### 4.5 Suggested order

1. **The per-source label split and the germline-only second reading** (§4.1): no new download, and
   aimed at the largest effect §3.4 measured.
2. Open Targets `animal_model`: the same pinned release, a new relation.
3. Bgee anatomy: restores PrimeKG parity on the existing pipeline pattern.
4. Complex Portal: small, and fixes the complex inflation directly.
5. DepMap and copy number, only if cancer subtypes become the story.

Alongside, one change that needs no new data: report a model **without** the four disease-independent
features beside the champion.

## 5. Rules any extension must keep

- **New evidence stays out of the label.** An animal-model edge may be a feature, never a positive
  label, and passes the same review as features already rejected for leaking label information.
- **The model learns from new edges only through new features,** and `DEC-OPS-004` allows one such
  intervention per model, with predictions and the adopt/reject rule declared first.
- **A graph-definition change gets a new snapshot** saved from the editor, with sources pinned in
  `DEMO_KG_PREP`. `KNOWLEDGE_GRAPH_PRIMEKG` stays frozen.
- **Count every Kuzu build against its tables.** The Visual Graph comma bug is fixed in v1.6; the
  check stays.
- **Part 2 must rebuild after any renumbering, together with its copies.** A graph rebuild renumbers
  `node_index`; anything keyed on it (the evidence cache, the webapp's graph queries) must move with
  it or check the names it was written for.
