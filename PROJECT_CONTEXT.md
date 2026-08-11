# Target Identification — POC Project Context

> Internal context for a Dataiku DSS proof-of-concept. This file orients any
> contributor (human or AI) on *why* the project exists, *who* it serves, and
> *what* has been built.
>
> **The POC document set** (this file is the *project* view — why / who / scope / status):
> - [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md) — *engineering* view: per-source extraction,
>   grounding, schema conformance, ETL/zone design (Part 1).
> - [TARGET_PRIORITIZER.md](TARGET_PRIORITIZER.md) — Part 2: the Explainable Target
>   Prioritizer (features → model → validation → persona results).
> - [RESEARCH_NOTE.md](RESEARCH_NOTE.md) — evidence base (literature/industry) behind the
>   Part 2 feature & model choices.
>
> Decisions are logged in the **appendix** of each document, not inline.

## 1. Purpose

Demonstrate that the Dataiku platform can **recreate a biomedical knowledge-graph
data pipeline for drug-discovery target identification**, end to end, in a single
governed flow.

Two highlights:

1. **Recreate the PrimeKG pipeline** ([mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg)) —
   ingest public biomedical sources and harmonize them into graph nodes/edges as a Dataiku Flow.
2. **Materialize and explore the graph with the Dataiku Visual Graph plugin** — an
   interactive, queryable knowledge graph for target exploration.

## 2. Business context

The pharmaceutical industry faces a productivity crisis: ~$2.23B and 10–15 years
per successful therapeutic, with ~90% of clinical candidates failing — more than
half due to lack of efficacy or unmanageable toxicity. The field has shifted from
phenotypic screening to a **data-driven, targeted approach**, where **target
identification** is the critical "go/no-go" checkpoint: generating a therapeutic
hypothesis backed by foundational evidence *before* significant capital is deployed.

Knowledge graphs are the central tool for the **data-silo problem** — integrating
fragmented biomedical data so ML can reason over it at scale.

**Value narrative:** integrating siloed data into one graph enables (a) discovery of
novel targets, (b) early prediction of off-target toxicity and clinical biomarkers,
therefore (c) reduced early-stage attrition and higher probability of success.

**Accounts of interest:** Ipsen, Boehringer, Pfizer, Astellas (Japan), Jazz.

## 3. Personas & user stories

| # | Persona | Goal |
|---|---------|------|
| 1 | Computational biologist, early R&D (metabolic diseases) | Understand obesity-related biological networks to identify key inflammatory & metabolic targets (e.g. IL6, TNF, IL1B; LEP/LEPR & insulin signaling → GLP-1 agonist) as intervention points. |
| 2 | Oncology data scientist, cancer center | Investigate signaling hubs/pathways in breast-cancer progression to validate & extend targets across tumor biology and immune response (e.g. PI3K/AKT/mTOR — PIK3CA, AKT1, MTOR, PTEN; hormone signaling — ESR1). |

Persona diseases drive both graph exploration and Part 2 validation
(TARGET_PRIORITIZER §9).

## 4. Scope & status

| Part | Scope | Status |
|---|---|---|
| **Part 1 — knowledge graph** | Ingest biomedical sources, harmonize to PrimeKG-exact schema, render in Visual Graph | **BUILT** — 113,544 nodes / 2,852,298 edges, 18 relations |
| **Part 2 — Explainable Target Prioritizer** | Visual ML + SHAP ranking of candidate targets per disease, with on-graph evidence paths | **BUILT & VALIDATED** — see TARGET_PRIORITIZER.md |
| Part 2b — toxicity / safety | DepMap essentiality + tissue expression → efficacy×safety | **Deferred** |
| Literature / trial cross-reference | PubMed, ClinicalTrials.gov | **Optional, not built** |

## 5. Data sources — in the build

Every source below is freely downloadable over HTTP(S) (no credentials) and is fetched
inside a DSS Python recipe. Extraction/grounding detail per source: PRIMEKG_MAPPING §5.

| Source | Provides | Node types contributed | Edge relations contributed |
|---|---|---|---|
| **HGNC** | gene identity vocab (symbol ↔ Entrez ↔ UniProt) | — *(vocab; every gene-touching edge joins on it)* | — |
| **MONDO** (`MONDO.obo`) | disease backbone + cross-reference hub | `disease` (25,906 MONDO + 1,247 MONDO_grouped) | `disease_disease` |
| **Open Targets** (26.06) | gene–disease associations + the whole drug layer | `drug` (5,282, DrugBank-keyed) | `disease_protein`, `drug_protein`, `indication`, `drug_investigated_for` |
| **PPI: Menche + HuRI + STRING** | protein interactome (merged, provenance kept in `edge_metadata.ppi_sources`) | `gene/protein` (20,861, NCBI) | `protein_protein` |
| **Reactome** | curated pathways | `pathway` (2,883) | `pathway_protein`, `pathway_pathway` |
| **GO + NCBI gene2go** | functional annotation, 3 namespaces | `biological_process` (24,129), `molecular_function` (10,041), `cellular_component` (4,075) | `bioprocess_protein`, `molfunc_protein`, `cellcomp_protein`, `bioprocess_bioprocess`, `molfunc_molfunc`, `cellcomp_cellcomp` |
| **HPO** (`hp.obo`, `phenotype.hpoa`, `genes_to_phenotype`) | phenotype layer | `effect/phenotype` (19,120) | `disease_phenotype_positive`, `disease_phenotype_negative`, `phenotype_protein`, `phenotype_phenotype` |
| **Hetionet DO Slim** | 137 curated Disease Ontology terms | **none — adds no nodes or edges** | **none** |

**Hetionet is not a graph source.** It is a curated *anchor set* used only to build
`disease_family_id` for leakage-controlled train/test splitting (TARGET_PRIORITIZER §6).

## 6. Data sources — deferred or not freely accessible

| Source | Gate / reason | Decision |
|---|---|---|
| **DisGeNET** | Portal moved to a paid API model (2023); legacy URL returns an HTML login page | **Replaced by Open Targets** for gene–disease |
| **DrugBank** | Account + commercial license, manual download | **Replaced by Open Targets** drug layer (DrugBank IDs still used as `node_id` via OT xref) |
| **UMLS Metathesaurus** | UMLS/UTS license (2024AB is on hand) | **Parked** — both UMLS-speaking sources were replaced by OT, which is EFO/MONDO-native, so nothing is left to translate (PRIMEKG_MAPPING §2) |
| **OMIM** | Free API key required | **Deferred** — loses Mendelian-disease enrichment |
| **DrugCentral** | Full dump ~4.5 GB; REST API viable | **Fallback only** — the sole route to contraindication / off-label edges, which OT lacks |
| **UBERON + Bgee** | Free, but heavy (anatomy + expression) | **Optional / stretch** — would add ~3M anatomy–protein edges |
| **CTD** | Free | **Optional / stretch** — exposure edges |
| **SIDER** | Free | **Optional / stretch** — drug side-effect edges |
| **disgenet.cn RNA-KG** | Free | **Optional** — an RNA-centric KG, *not* a DisGeNET substitute (gene–disease only 5,959) |

## 7. Build status

**Instance:** `design.solutions.dataiku-dss.io` (DSS 14.7), project `KNOWLEDGE_GRAPH_PRIMEKG`.
**Code env:** `primekg_kg` (py3.11: pandas, pyarrow, requests, obonet, networkx, scipy).
**Storage:** S3 `dataiku-managed-storage`, parquet (Spark-capable).

**Flow pattern:** one zone per source — Python `extract_*` (fetch → parse to native ids) →
visual `harmonize_*` (Prepare/Join → 8-col name-free `*_edges`) → Python `compute_kg`
assembly (stack → clean → reverse-all → attach names → disease grouping → giant component
→ emergent `node_index`). Zone/recipe detail: PRIMEKG_MAPPING §4.

**Outputs (PrimeKG-exact schema):** `graph_nodes` · `kg` (12-col) · `graph_edges` (4-col)
· `edge_metadata` (provenance side table: `datatypes`, `ppi_sources`).

### Nodes — 113,544

| Node type | Count | Source of record |
|---|--:|---|
| disease | 27,153 | MONDO (25,906 + 1,247 grouped) |
| biological_process | 24,129 | GO |
| gene/protein | 20,861 | NCBI (via HGNC) |
| effect/phenotype | 19,120 | HPO |
| molecular_function | 10,041 | GO |
| drug | 5,282 | DrugBank ID via OT xref |
| cellular_component | 4,075 | GO |
| pathway | 2,883 | Reactome |

### Edges — 2,852,298 (undirected; reverse edges included)

| Relation | Count | Provenance |
|---|--:|---|
| protein_protein | 520,380 | Menche + HuRI + STRING (merged; `ppi_sources`) |
| phenotype_protein | 487,054 | HPO `genes_to_phenotype` |
| disease_phenotype_positive | 380,280 | HPO `phenotype.hpoa` |
| disease_protein | 378,888 | OT `genetic_association` + `somatic_mutation` @≥0.3 (`datatypes`) |
| bioprocess_protein | 251,858 | GO + gene2go |
| cellcomp_protein | 186,806 | GO + gene2go |
| molfunc_protein | 156,248 | GO + gene2go |
| disease_disease | 129,606 | MONDO `is_a` |
| pathway_protein | 97,618 | Reactome NCBI2Reactome |
| bioprocess_bioprocess | 81,726 | GO hierarchy |
| drug_investigated_for | 69,682 | OT `clinical_indication`, in-trial stages |
| phenotype_phenotype | 45,912 | HPO hierarchy |
| molfunc_molfunc | 24,536 | GO hierarchy |
| drug_protein | 15,918 | OT mechanism of action |
| indication | 9,418 | OT `clinical_indication`, APPROVAL/PREAPPROVAL |
| cellcomp_cellcomp | 9,386 | GO hierarchy |
| pathway_pathway | 5,798 | Reactome hierarchy |
| disease_phenotype_negative | 1,184 | HPO (`NOT` qualifier) |

**Validated:** 0 duplicate rows, 0 self-loops, 0 dangling endpoints, reverse-all symmetry
holds on every sampled relation.

**Kuzu snapshot:** folder `enriched_clean-gFdnaU` (`tblWzpfx`), built by `build-graph-gFdnaU`.
All `compute_enriched_*` graph-feature recipes read from it.

**Visual Graph Editor** webapp `lVWgU2m` → `graph_nodes`/`graph_edges`; runs as a local
process (`containerMode=NONE`). Schema mapping: node id=`node_index`, name=`node_name`,
group by `node_type`/`node_source`; edge source=`x_index`, target=`y_index`.

## 8. Reference comparison vs published PrimeKG

Reference: Chandak et al., *Sci Data* 2023, Tables
[2](https://www.nature.com/articles/s41597-023-01960-3/tables/2) /
[3](https://www.nature.com/articles/s41597-023-01960-3/tables/3). Both are undirected.

| Node type | PrimeKG | Ours | Note |
|---|--:|--:|---|
| Biological process | 28,642 | 24,129 | close |
| Protein | 27,671 | 20,861 | no anatomy/exposure proteins |
| Disease | 17,080 | 27,153 | higher — full MONDO, less grouping |
| Phenotype | 15,311 | 19,120 | higher — full HPO |
| Anatomy | 14,035 | 0 | UBERON/Bgee not built |
| Molecular function | 11,169 | 10,041 | close |
| Drug | 7,957 | 5,282 | OT drugs with a DrugBank xref only |
| Cellular component | 4,176 | 4,075 | close |
| Pathway | 2,516 | 2,883 | close |
| Exposure | 818 | 0 | CTD not built |
| **Total** | **129,375** | **113,544** | |

| Relation | PrimeKG | Ours | Note |
|---|--:|--:|---|
| anatomy–protein (present/absent) | 3,076,180 | 0 | not built |
| drug–drug | 2,672,628 | 0 | DrugBank-only DDI, out of scope |
| protein–protein | 642,150 | 520,380 | **closed the gap** — was 276k with Menche alone |
| disease–phenotype (pos) | 300,634 | 380,280 | higher — full HPO |
| biological process–protein | 289,610 | 251,858 | close |
| cellular component–protein | 166,804 | 186,806 | close |
| disease–protein | 160,822 | 378,888 | higher — OT genetic + somatic |
| molecular function–protein | 139,060 | 156,248 | close |
| drug–phenotype | 129,568 | 0 | SIDER not built |
| bioprocess–bioprocess | 105,772 | 81,726 | close |
| pathway–protein | 85,292 | 97,618 | close |
| disease–disease | 64,388 | 129,606 | higher — MONDO version |
| drug–disease (contraindication) | 61,350 | 0 | DrugCentral-only |
| drug–protein | 51,306 | 15,918 | OT mechanism vs DrugBank all-roles |
| phenotype–phenotype | 37,472 | 45,912 | close |
| molfunc–molfunc | 27,148 | 24,536 | close |
| drug–disease (indication) | 18,776 | 9,418 | OT APPROVAL/PREAPPROVAL only |
| drug–disease (investigational) | — | 69,682 | **no PrimeKG equivalent** |
| cellcomp–cellcomp | 9,690 | 9,386 | close |
| phenotype–protein | 6,660 | 487,054 | **far higher** — HPO `genes_to_phenotype` is much denser than PrimeKG's DisGeNET-derived edge |
| drug–disease (off-label) | 5,136 | 0 | DrugCentral-only |
| pathway–pathway | 5,070 | 5,798 | close |
| exposure–* | 14,532 | 0 | CTD not built |
| disease–phenotype (neg) | 2,386 | 1,184 | lower |
| **Total** | **8,100,498** | **2,852,298** | |

**Reading this:** every built layer is now in the right ballpark or intentionally different.
The remaining gap is almost entirely **unbuilt layers** (anatomy ~3.1M, drug–drug 2.7M,
side-effect, exposure) rather than under-coverage of what we do build.

## 9. Platform building blocks (Dataiku)

- **Flow + flow zones** — one zone per source group, feeding an assembly zone.
- **Code recipes** — Python for extraction, graph math, and anything visual recipes can't express.
- **Visual recipes** — Prepare/Join/Group/Split for harmonization and resampling.
- **Visual Graph plugin** — Build Graph (Kuzu), Execute Cypher, Graph Features, Explorer webapp.
- **Visual ML** — XGBoost + native Shapley for Part 2.
- **Code env** `primekg_kg`; storage on S3 `dataiku-managed-storage` (parquet).

## 10. Open questions

- Which optional layers (anatomy/CTD/SIDER) are worth the ingest cost for the demo story?
- Include DrugCentral contraindication/off-label edges (~70k, needs UMLS crosswalk revived)?
- Part 2b (toxicity/safety) — in scope for this POC or a follow-on?

---

## Appendix — decision log

| Date | Decision |
|---|---|
| 2026-06 | **Build from scratch** in DSS rather than loading the pre-built Dataverse `kg.csv` — the pipeline recreation *is* highlight #1. Pre-built graph kept as a fallback. |
| 2026-06 | **DisGeNET → Open Targets** for gene–disease (portal went paid). |
| 2026-06 | **DrugBank dropped → Open Targets drug layer** (license gate). DrugBank IDs retained as `node_id` via OT cross-reference. |
| 2026-06 | **UMLS parked** — replacing both UMLS-speaking sources with OT (EFO/MONDO-native) left nothing to translate. Recipes kept in repo. |
| 2026-06 | **PPI = Menche only** initially; storage `filesystem_managed`. |
| 2026-07 | **Part 2 prioritized ahead of further source ingestion** — a more valuable graph beats a bigger graph for the demo. |
| 2026-08-05 | **Task 10 scope set:** add GO+gene2go and HPO (with HP↔MONDO reclassification and a `phenotype_protein` replacement); add `somatic_mutation` to the OT gene–disease filter (cancer persona); add `drug_investigated_for` to the Kuzu graph. **Rejected:** OT `known_drug` datatype (redundant with the `dwpc_GCD` metapath). |
| 2026-08-06 | **PPI augmented to Menche + HuRI + STRING** as a single `protein_protein` relation with `ppi_sources` provenance in `edge_metadata`, rather than separate relations — HuRI adds unbiased Y2H coverage, STRING adds filtered experimental/database evidence. |
| 2026-08-08 | **Hetionet DO Slim adopted as split-control vocabulary only** — no graph contribution. |
| 2026-08-09 | **Storage migrated to S3 `dataiku-managed-storage` (parquet)** to enable the Spark engine. All new datasets go there. |
| 2026-08-10 | Reference comparison refreshed: PPI gap closed (276k → 520k); `phenotype_protein` far exceeds PrimeKG because HPO's own gene file is denser than PrimeKG's DisGeNET-derived edge. |

## References

- PrimeKG repo & build guide: https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg
- PrimeKG paper: Chandak et al., *Sci Data* 2023
- Hetionet: https://github.com/hetio/hetionet
- Open Targets: https://platform-docs.opentargets.org/getting-started
