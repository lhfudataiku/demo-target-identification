# Target Identification — POC Project Context

> Internal context for a Dataiku DSS proof-of-concept. This file orients any
> contributor (human or AI) on *why* the project exists, *who* it serves, and
> *what* we are building.
>
> **Companion doc:** [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md) — the *engineering* view
> (per-source extraction, grounding, schema conformance, ETL/zone design). This file is
> the *project* view.

## 1. Purpose

Demonstrate that the Dataiku platform can **recreate a biomedical knowledge-graph
data pipeline for drug-discovery target identification**, end to end, in a single
governed flow.

The POC has two highlights:

1. **Recreate the PrimeKG pipeline by reusing the scripts published by PrimeKG**
   ([mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg)) —
   ingest multiple public biomedical sources and harmonize them into graph
   nodes and edges, orchestrated as a Dataiku Flow.
2. **Materialize and explore the graph using the Dataiku Visual Graph plugin** —
   turn the harmonized node/edge tables into an interactive, queryable knowledge
   graph for target exploration.

## 2. Business context

The pharmaceutical industry faces a productivity crisis: ~$2.23B and 10–15 years
per successful therapeutic, with ~90% of clinical candidates failing — more than
half due to lack of efficacy or unmanageable toxicity. The field has shifted from
phenotypic screening to a **data-driven, targeted approach**, where **target
identification** is the critical "go/no-go" checkpoint: generating a therapeutic
hypothesis backed by foundational evidence *before* significant capital is deployed.

This requires cross-referencing multi-omics evidence (genomic, transcriptomic,
clinical) to find novel pathophysiological pathways and "druggable" targets
(enzymes, receptors, transcription factors, DNA sequences). Knowledge graphs are
the central tool for solving the **data-silo problem** — integrating fragmented
biomedical data so that ML and analytics can reason over it at scale.

**Value narrative for the POC:** integrating siloed biomedical data into one graph
enables (a) discovery of novel targets, (b) early prediction of off-target toxicity
and clinical biomarkers, and therefore (c) reduced early-stage attrition and higher
probability of success (PoS) downstream.

**Accounts of interest:** Ipsen, Boehringer, Pfizer, Astellas (Japan), Jazz.

## 3. Personas & user stories

| # | Persona | Goal |
|---|---------|------|
| 1 | Computational biologist, early R&D (metabolic diseases) | Understand obesity-related biological networks to identify key inflammatory & metabolic targets (e.g., IL6, TNF, IL1B; LEP/LEPR & insulin signaling → GLP-1 agonist) as intervention points. |
| 2 | Oncology data scientist, cancer center | Investigate signaling hubs/pathways in breast-cancer progression to validate & extend targets across tumor biology and immune response (e.g., PI3K/AKT/mTOR — PIK3CA, AKT1, MTOR, PTEN; hormone signaling — ESR1). |

These two disease areas (metabolic/obesity and breast cancer) are the concrete
demo scenarios to drive graph exploration and, later, target prioritization.

## 4. Scope

**Part 1 (this POC's core):** ingest multiple biomedical datasets and build a
knowledge graph, recreating the PrimeKG pipeline in a Dataiku Flow and rendering
it with the Visual Graph plugin.

**Part 2 (stretch / follow-on):**
- Train an ML model on graph-derived features to prioritize targets.
- Visualize/contextualize predictions on the graph.
- Cross-reference targets with literature, trial registries, and patents
  (PubMed, ClinicalTrials.gov — optional).

## 5. Data sources

PrimeKG integrates ~20 public resources into a graph of ~17k disease nodes and
~4M relationships across vertex types: gene/protein, drug, disease, phenotype,
anatomy, GO biological-process / molecular-function / cellular-component, pathway,
exposure, and side-effect.

**Two ways to obtain the data:**
- **Pre-built graph** — `kg.csv` from Harvard Dataverse
  (`https://dataverse.harvard.edu/api/access/datafile/6180620`), no credentials.
  Fast path to a working Visual Graph demo; kept as a fallback.
- **Build from scratch (chosen path)** — run PrimeKG's per-source processors + the
  `knowledge_graph/` assembly in a Dataiku Flow. This is what showcases the
  pipeline-recreation story (highlight #1). Several sources are credential-gated or
  have shifted access since PrimeKG was published — resolved source-by-source in §6.

**POC build strategy:** freely-downloadable sources + **UMLS 2024AB** (on hand) +
**Menche PPI** (downloaded) + **Open Targets** for gene–disease (replacing DisGeNET).
**DrugBank is dropped** (no drug layer); OMIM deferred. This covers both personas.
Scoping doc also lists Hetionet and Open Targets as alternative/complementary graphs.

## 6. Source-by-source status & access ⚠️

Findings from auditing PrimeKG's `datasets/primary_data_resources.sh` + notebooks,
**with live URL checks performed 2026-06 (HTTP status + content-type verified).**

### Freely downloadable (no key) — verified live

All reachable over HTTP(S) (none actually FTP), so each is fetchable inside a DSS
Python/Download recipe. `.gz` sources need decompression in the recipe.

| Source | Feeds | Format | Live? |
|--------|-------|--------|-------|
| **HGNC** (genenames custom download) | `gene_names.csv` (gene/protein identity: symbol↔Entrez) | tab-text | ✅ 200 |
| **MONDO** (`MONDO.obo`) | disease nodes + `mondo_references.csv` | obo (~52 MB) | ✅ 200 |
| **HPO** (`hp.obo`, `phenotype.hpoa`) | phenotype nodes + disease–phenotype | obo / tsv | ✅ 200 |
| **GO** (`go-basic.obo`) + **NCBI gene2go** | GO terms + protein–GO | obo / `.gz` | ✅ 200 |
| **Reactome** (3 files) | pathway nodes/edges + NCBI↔pathway | txt | ✅ 200 |
| **UBERON** (`ext.obo`) + **Bgee** | anatomy + anatomy–gene expression | obo / `.gz` | ✅ 200 |
| **CTD** (`CTD_exposure_events`) | exposure edges | `.gz` | ✅ 200 |
| **SIDER** (`meddra_all_se`, `drug_atc`) | side-effect edges | `.gz` / tsv | ✅ 200 |

### Access-changed / credential-gated — current decisions

| Source | Gate / change | Decision |
|--------|---------------|----------|
| **DisGeNET** | Legacy static URL now returns an **HTML login page** (portal moved to paid/API model 2023). | **REPLACED by Open Targets** for gene–disease edges. See §7. |
| **DrugBank** | Account + **license**; manual download. | **DROPPED.** Removes the drug layer (`drug_protein`, `drug_drug`, `drugbank_vocabulary`, `drugbank_atc_codes` + 12 feature files). Neither persona needs drug nodes. *(If re-added later: via the Snowflake Marketplace **"DrugBank: Biomedical Knowledge"** listing `GZTYZJ6Q7W0` — relational tables, not the XML PrimeKG parses, so it'd be new SQL recipes.)* |
| **UMLS Metathesaurus** | UMLS license via UTS. | **AVAILABLE — full 2024AB on hand.** Powers the UMLS↔MONDO disease crosswalk. See §7. |
| **PPI** | No download URL in the script ("copy manually"). | **Menche et al. 2015 interactome** (downloaded). See §7. |
| **DrugCentral** | `drug_disease.csv` lives in the `omop_relationship` table; full DB dump is ~4.5 GB. | **Use the DrugCentral REST API** (`/omop_relationship/relationship_name/{type}`) — no download, no DB. ~70k edges, carries `umls_cui` + `struct_id`. Public Postgres is a fallback. Drug→target comes from a separate flat file. See §7. |
| **OMIM** | **API key** (free at omim.org/api). | Deferred. Loses OMIM Mendelian-disease enrichment (`append_omim.ipynb`). |

### Data inventory — what's already in `data/`

| Path | Source | Status |
|------|--------|--------|
| `data/umls_for_primekg.rrf` (430 MB) | UMLS 2024AB MRCONSO, pre-filtered | ✅ ready → `umls_mondo` |
| `data/PPI/DataS1_interactome.tsv` (3.3 MB) | Menche 2015 PPI | ✅ ready → `protein_protein` |
| `data/PPI/DataS2–4_*.tsv` | Menche disease-genes / extras | bonus, not required |
| `data/drug.target.interaction.tsv` (4.3 MB, 19,379 rows) | DrugCentral drug→target | ✅ DrugBank-free drug–protein substitute |
| `data/DisGeNET/items.csv` + `interactions.csv` | **RNA-centric KG** (NOT DisGeNET classic) | optional enrichment only — see §7 |

**Still to fetch (free, verified live):** HGNC, MONDO, HPO, GO, gene2go, Reactome,
UBERON, Bgee, CTD, SIDER, **Open Targets** (association_overall_direct + target + disease).

**Hard-blocker dependencies:** **MONDO** (disease backbone *and* the MONDO half of the
UMLS crosswalk) and **HGNC** (`gene_names.csv` — every gene-touching edge joins on it)
must be fetched before anything assembles.

## 7. Resolved source schemas & decisions

> **Migrated to [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md).** The per-source extraction,
> grounding, and schema detail (Open Targets gene–disease + drug layer, PPI/Menche, the
> MONDO vs UMLS roles + why UMLS is parked, disgenet.cn RNA-KG, DrugCentral fallback)
> now lives in the mapping doc §2 and §5, alongside the reuse/ETL strategy. See also
> the per-source ETL/zone design (§4) and open decisions (§7) there.

## 7b. Build status — Part 1 core slice (DONE, on DSS project KNOWLEDGE_GRAPH_PRIMEKG)

> ⚠️ The original core slice (`graph_nodes`/`graph_edges`) used a simplified custom
> schema. It has been **superseded by the conformant build below** (§7c). Strategy:
> [PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md).

## 7c. Conformant build — PrimeKG-exact schema + harmonization (DONE, core)

`compute_kg.py` is a faithful port of `build_graph.ipynb` for the core sources.
Outputs match the published PrimeKG schema:
- **`primekg_nodes`** (45,193): `node_index, node_id, node_type, node_name, node_source`
  — 17,406 NCBI gene/protein · 2,870 REACTOME pathway · 23,670 MONDO + 1,247
  **MONDO_grouped** disease. Native ids (Entrez; **bare-integer MONDO** e.g. `2816`;
  grouped = underscore-joined). 4-tuple identity; emergent node_index.
- **`primekg`** (603,762 edges): `relation, display_relation, x_index, x_id, x_type,
  x_name, x_source, y_index, y_id, y_type, y_name, y_source`. Relation vocab:
  protein_protein/ppi · disease_protein/"associated with" · pathway_protein/"interacts
  with" · disease_disease/parent-child · pathway_pathway/parent-child.
- **`primekg_edges`** (603,762): slim `relation, display_relation, x_index, y_index`.

Harmonization reused from PrimeKG: `clean_edges` grounding-drop; **reverse-ALL edges**
(undirected); **disease grouping** applied from PrimeKG's published map
(`disease_group_map` ← Dataverse datafile 6180623, 6,392 diseases → MONDO_grouped);
**giant-component** filter (networkx; 50,675→45,193 nodes). MONDO ids reconciled to
bare-integer; Open Targets `MONDO_x`→int.

**Visual Graph Editor** (`lVWgU2m`) repointed to `primekg_nodes`/`primekg`, backend
healthy. UI schema mapping: node group → id=`node_index`, name=`node_name`, group by
`node_type`/`node_source`; edge group → source=`x_index`, target=`y_index`, properties
`relation`/`display_relation`.

**Flow reworked into per-source zones (hybrid Python+visual).** Each source = its own
flow zone: Python `extract_*` (load + parse to native ids) → visual `harmonize_*`
(Prepare; + visual Join recipes for Open Targets id-remap) → 8-col name-free `*_edges`.
The Python `compute_kg` assembly stacks all `*_edges`, attaches names from vocab,
reverses, groups, giant-components. 8 zones (Genes, Diseases, PPI, Open Targets ref,
Gene-Disease, Pathways, Drugs, Assembly). Rebuilt result: 50,491 nodes / 699,440 edges
(matches the pre-rework build). Full zone/recipe map + build gotchas in
[PRIMEKG_MAPPING.md](PRIMEKG_MAPPING.md) §4/§8.

**Drug layer (DONE) — Open Targets, replacing DrugBank.** `compute_drug_ot.py` reads OT
`drug_molecule` (ChEMBL→DrugBank ID via `crossReferences`), `drug_mechanism_of_action`
(drug→ENSG targets+actionType), `clinical_indication` (drug→EFO/MONDO+phase) → parsed
`drug_target` (7,959) + `drug_indication` (40,044). Folded into `compute_kg`:
- 5,282 **drug** nodes (`node_source='DrugBank'`, DrugBank-ID keyed).
- `drug_protein` edges 15,918 (`display_relation`=action type).
- **drug–disease split by `maxClinicalStage`** (correction — `clinical_indication`
  aggregates all trial stages, only ~13% approved): `indication` (approved, 9,418) vs
  `drug_investigated_for` (in-trial/hypothesis, 69,682; stage in `display_relation`).
- Graph 50,491 nodes / 700,462 edges. No DDI (DrugBank-only); no contraindication/
  off-label (DrugCentral-only) — see PRIMEKG_MAPPING §5/§7.

> **Note on OT semantics:** the `score` lives only on gene–disease
> (`association_overall_direct`) and is a **computed prioritization heuristic**, not a
> confidence/curated fact (OT: "should not be interpreted as a confidence score"). The
> drug–disease `clinical_indication` dataset has **no score** — only `maxClinicalStage`.

**Not yet in conformant build** (remaining task 10): HPO phenotype + HP↔MONDO
reclassification, GO/gene2go (protein–GO), UBERON/Bgee anatomy, CTD exposure, SIDER
drug–side-effect. All follow the same edge-frame pattern in `compute_kg`.


Instance `design.solutions.dataiku-dss.io` (DSS 14.7). Code env `primekg_kg`
(py3.11: pandas, pyarrow, requests, obonet). All datasets on `filesystem_managed`.

| Recipe (in `dss_recipes/`) | Output(s) | Rows |
|---|---|---|
| `compute_gene_names.py` | `gene_names` | 44,382 genes |
| `compute_mondo.py` | `mondo_terms` / `mondo_parents` / `mondo_references` | 30,172 / 43,912 / 142,797 |
| `compute_gene_disease.py` | `gene_disease` (Open Targets 26.06, score≥`ot_score_min`=0.3) | 77,971 |
| `compute_ppi.py` | `protein_protein` (Menche, folder `raw_files`) | 141,296 |
| `compute_reactome.py` | `reactome_terms` / `reactome_relations` / `reactome_ncbi` | 2,870 / 2,886 / 48,659 |

> The original `compute_graph.py` → `graph_nodes`/`graph_edges` (simplified schema) and
> the `compute_ot_drug_probe` throwaway have been **deleted** from the flow. The
> conformant assembly (§7c) is the single graph builder.

**Unified model:** `node_id = "<type>:<native>"` (`gene:<entrez>`, `disease:MONDO:x`,
`pathway:R-HSA-x`). Nodes: 17,929 gene/protein · 29,876 disease · 2,870 pathway.
Edges: protein_protein 141,296 · gene_associated_with_disease 77,921 ·
gene_in_pathway 48,659 · disease_parent_of 43,912 · pathway_parent_of 2,886.
Persona genes verified present with associations (PIK3CA 136, PTEN 108, ESR1 99,
AKT1 54, MTOR 64, TNF 34, IL6 24, IL1B 22, LEP 2).

**Visual Graph Editor webapp:** id `lVWgU2m` ("PrimeKG Graph Editor"), type
`webapp_visual-graph_visual-graph-editor`, pointed at `graph_nodes`/`graph_edges`,
backend healthy (runs as local process — `containerMode=NONE`, since the plugin
code-env container image isn't built on this instance). Schema-group mapping to set
in the editor UI: node group → id=`node_id`, name=`node_name`, group/filter by
`node_type`; edge group → source=`source`, target=`target`, property=`relation`.
Created via `scripts/create_vg_webapp.py` pattern + `dku webapp set-definition`
(CLI can't create plugin webapps directly).

## 7d. Reference comparison vs published PrimeKG

Reference: PrimeKG paper (Chandak et al., *Sci Data* 2023), Tables 2–3
([nodes](https://www.nature.com/articles/s41597-023-01960-3/tables/2),
[edges](https://www.nature.com/articles/s41597-023-01960-3/tables/3)). Both PrimeKG
and our `primekg` are **undirected (reverse edges included)**, so counts are directly
comparable. "Current" = our conformant build as of the drug-layer milestone.

### Nodes

| Node type | PrimeKG | Current | Notes |
|---|--:|--:|---|
| Biological process (GO) | 28,642 | 0 | GO/gene2go not built |
| Protein (gene/protein) | 27,671 | 17,407 | rises once GO/Bgee/anatomy proteins added |
| Disease | 17,080 | 24,917 | higher: OT + full MONDO hierarchy; less grouping/pruning |
| Phenotype (HPO) | 15,311 | 0 | HPO not built |
| Anatomy (UBERON) | 14,035 | 0 | UBERON/Bgee not built |
| Molecular function (GO) | 11,169 | 0 | not built |
| Drug | 7,957 | 5,282 | OT drugs w/ DrugBank xref vs full DrugBank |
| Cellular component (GO) | 4,176 | 0 | not built |
| Pathway | 2,516 | 2,870 | close (Reactome version) |
| Exposure (CTD) | 818 | 0 | CTD not built |
| **Total** | **129,375** | **50,476** | |

### Edges (undirected counts)

| Relation | PrimeKG | Current | Status |
|---|--:|--:|---|
| anatomy–protein (present) | 3,036,406 | 0 | Bgee — not built |
| drug–drug | 2,672,628 | 0 | DrugBank-only (DDI) — out of scope |
| protein–protein | 642,150 | 275,724 | Menche only (PrimeKG adds BioGRID+STRING) |
| disease–phenotype (pos) | 300,634 | 0 | HPO — not built |
| biological process–protein | 289,610 | 0 | gene2go — not built |
| cellular component–protein | 166,804 | 0 | gene2go — not built |
| disease–protein | 160,822 | 149,012 | **OT (score≥0.3) vs DisGeNET — comparable** |
| molecular function–protein | 139,060 | 0 | gene2go — not built |
| drug–phenotype | 129,568 | 0 | SIDER — not built |
| biological process–biological process | 105,772 | 0 | GO — not built |
| pathway–protein | 85,292 | 95,962 | **close** |
| disease–disease | 64,388 | 77,292 | higher (MONDO version) |
| drug–disease (contraindication) | 61,350 | 0 | DrugCentral-only — not in OT |
| drug–protein | 51,306 | 15,918 | OT mechanism vs DrugBank (all target roles) |
| anatomy–protein (absent) | 39,774 | 0 | Bgee — not built |
| phenotype–phenotype | 37,472 | 0 | HPO — not built |
| anatomy–anatomy | 28,064 | 0 | UBERON — not built |
| molecular function–molecular function | 27,148 | 0 | GO — not built |
| drug–disease (indication, approved) | 18,776 | 9,418 | OT `clinical_indication` filtered to APPROVAL/PREAPPROVAL |
| drug–disease (investigational) | — | 69,682 | `drug_investigated_for` — OT in-trial stages (PrimeKG has no equivalent) |
| cellular component–cellular component | 9,690 | 0 | GO — not built |
| phenotype–protein | 6,660 | 0 | DisGeNET phenotype — not built |
| drug–disease (off-label) | 5,136 | 0 | DrugCentral-only — not in OT |
| pathway–pathway | 5,070 | 5,772 | **close** |
| exposure–* (6 relations) | 14,532 | 0 | CTD — not built |
| disease–phenotype (negative) | 2,386 | 0 | HPO — not built |
| **Total** | **8,100,498** | **697,758** | |

**Reading this:** where we have the layer, counts are in the right ballpark
(disease–protein, pathway–protein, pathway–pathway) or intentionally different
(indication higher — OT broader; drug–protein lower — OT mechanism vs DrugBank's
target/enzyme/carrier/transporter; PPI lower — Menche only). The bulk of the gap is
**unbuilt layers** (GO, HPO, anatomy, exposure) and **deliberately-excluded** ones
(drug–drug DDI; contraindication/off-label — see §7, PRIMEKG_MAPPING §7).

## 8. Platform building blocks (Dataiku)

- **Flow + Flow zones** — one zone per source group (download → parse → node/edge CSVs)
  feeding a "graph assembly" zone, recreating the PrimeKG structure.
- **Code recipes** — reuse PrimeKG's Python parsers (OBO parsers, per-source processors).
- **Visual Graph plugin** — render and explore the harmonized graph (highlight #2).
- **Code env** — Python env mirroring PrimeKG's `requirements.txt`.
- **Plugins** — Visual Graph (+ any others added during build).
- **Supported connections (per scoping):** PostgreSQL ✅, Snowflake ✅, MSSQL ✅(dates parsed),
  Redshift ✅(needs S3 fallback), S3 ✅, Azure Blob ✅. Not targeted: Synapse, BigQuery, GCS.

## 9. Open questions

- **Open Targets scope:** full association set with a `score` threshold, or
  pre-filter to the persona-disease MONDO subtrees to keep the POC graph small?
- Which subset of node/edge types is the minimum to make persona stories #1 and #2 land?
- Is Part 2 (ML target prioritization) in scope for this POC or a follow-on?
- DrugCentral `drug_disease` — include it via the REST API (~70k edges, drug nodes
  consistent with the drug→target layer), or leave the drug–disease edge out? Pure
  scope decision; no infra/download cost either way.

**Resolved:** DisGeNET → replaced by Open Targets · DrugBank → dropped · UMLS →
available (2024AB) · PPI → Menche (downloaded) · build path → from-scratch in DSS.

## References

- PrimeKG repo & build guide: https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg
- PrimeKG (Robert Haas overview): https://robert-haas.github.io/awesome-biomedical-knowledge-graphs/notebooks/primekg.html
- Hetionet: https://github.com/hetio/hetionet
- Open Targets: https://platform-docs.opentargets.org/getting-started
