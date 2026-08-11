# PrimeKG → Our Build: Source Mapping, Schema & ETL Strategy

> **Companion to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)** (project view: why / who / scope /
> node-edge counts / PrimeKG comparison). This is the *engineering* view: how each source is
> extracted, grounded, and harmonized to PrimeKG's schema, and how the flow is organized.
> **Part 2** — the analytical layer on top — is [TARGET_PRIORITIZER.md](TARGET_PRIORITIZER.md).
>
> Decisions are logged in the **appendix**, not inline.

## 0. Approach — two principles

1. **PrimeKG's `processing_scripts/` + `build_graph.ipynb` are the REFERENCE, not code to
   port verbatim.** We replace both DrugBank and DisGeNET with Open Targets and pull sources
   over HTTP/parquet/API rather than PrimeKG's on-disk layout, so the original scripts don't
   run as-is. Per source we use a **hybrid**: a **Python recipe** extracts (fetch → parse to
   native ids → flat `raw_<source>` table), then **visual recipes** harmonize to the edge
   schema (rename/cast/filter, ground via Join, add relation constants).
2. **Conform to PrimeKG's exact node/edge schema** so output is comparable to the published
   `kg.csv` (counts in [PROJECT_CONTEXT §8](PROJECT_CONTEXT.md)).

## 1. Target schema (PrimeKG-exact)

**`graph_nodes`:** `node_index, node_id, node_type, node_name, node_source`
- `node_index` = 0..N-1 over the **deduplicated union of edge endpoints** — nodes are
  *emergent* from edges (no surviving edge ⇒ no node). **Not stable across rebuilds.**
- **Node identity = the 4-tuple** `(node_id, node_type, node_name, node_source)`.
- `node_id` = source-native: Entrez (gene), **bare-integer MONDO** e.g. `2816` (disease;
  grouped = underscore-joined), HPO/GO/Reactome id, **DrugBank ID** (drug).
- `node_source` ∈ `NCBI | MONDO | MONDO_grouped | HPO | GO | REACTOME | DrugBank`.

**`kg`:** `relation, display_relation, x_index, x_id, x_type, x_name, x_source, y_index,
y_id, y_type, y_name, y_source`.
**`graph_edges`:** slim `relation, display_relation, x_index, y_index`.
**`edge_metadata`:** `x_index, y_index, relation, datatypes, ppi_sources` — provenance kept
*off* the PrimeKG-exact tables so they stay conformant.

## 2. The disease coordinate system: MONDO vs UMLS

**MONDO — the disease coordinate system.** Every disease node *is* a MONDO term. Provides
(1) disease nodes, (2) the `is_a` hierarchy → `disease_disease`, and (3) **a cross-reference
hub** (`mondo_references`: MONDO ↔ MESH / OMIM / Orphanet / HP / DOID / UMLS …) — the
mechanism that pulls every other source's diseases onto MONDO.

**UMLS — parked.** No UMLS nodes exist; UMLS was only a CUI→MONDO translator for DisGeNET and
DrugCentral. Both were replaced by Open Targets, which is EFO/MONDO-native, so there is
nothing left to translate. Later layers ground through MONDO's own xrefs (HPO via
OMIM/ORPHA/DECIPHER; Hetionet via DOID). UMLS returns only if DrugCentral
contraindication/off-label is added. Recipes kept in repo, retired from the active flow.

## 3. Reusable harmonization logic

The scientific value in `build_graph.ipynb`, reproduced in `compute_kg`:

- **`clean_edges`** — select the 8 canonical columns, `dropna` (**grounding-drop**: a failed
  crosswalk silently discards the row), `drop_duplicates`, drop self-loops.
- **Reverse-all** — undirected by duplicating every edge x↔y, relation strings unchanged.
  Metadata columns are carried through unchanged (they describe the edge, not an endpoint).
- **Vocab anchors** for grounding joins: `gene_names` (Entrez↔symbol), `mondo_terms`,
  `mondo_references`, `reactome_terms`, `drug_vocab`, `go_terms`, `hpo_terms`.
- **HP↔MONDO reclassification** — a term that is *both* an HPO phenotype and a MONDO disease
  resolves to the MONDO node; affected `disease_phenotype` edges become `disease_disease` and
  `phenotype_protein` become `disease_protein`. 555 overlap terms.
- **Disease grouping** — PrimeKG's **published** map (Dataverse datafile 6180623): grouped
  MONDO nodes get an underscore-joined `node_id`, the group name, and
  `node_source='MONDO_grouped'`. Deterministic; no BERT needed.
- **Giant-component filter** — keep the largest connected component (networkx).

## 4. Flow design — one zone per source

Pattern per zone: **`extract_*`** (Python: fetch + parse to native ids) → **`harmonize_*`**
(visual Prepare, + visual Join where grounding needs a lookup) → **8-col name-free `*_edges`**
(`x_id, y_id, x_type, y_type, x_source, y_source, relation, display_relation`, all string).
Names are resolved once, in assembly.

| Zone | Extract | Harmonize | Output edges |
|---|---|---|---|
| Genes (HGNC) | `compute_gene_names` | — | *(vocab only)* |
| Diseases (MONDO) | `extract_mondo` | `harmonize_disease_disease` | `mondo_edges` |
| PPI | `extract_ppi`, `extract_huri`, `extract_string` → `compute_ppi_merged` | `harmonize_ppi` | `ppi_edges` |
| Open Targets (ref) | `extract_ot_assoc`, `extract_ot_maps` | — | *(shared maps)* |
| Gene-Disease (OT) | — | `join_gd_maps` → `join_gd_genes` → `harmonize_gene_disease` | `gene_disease_edges` |
| Pathways (Reactome) | `extract_reactome` | `harmonize_pathway_protein` / `_pathway` | `reactome_gp_edges`, `reactome_pp_edges` |
| Drugs (OT) | `extract_drug_ot` | `join_dp_*` → `harmonize_drug_protein`, `harmonize_drug_disease` | `drug_protein_edges`, `drug_disease_edges` |
| GO (gene2go) | `compute_go_terms` | `harmonize_go_protein` / `_hierarchy` | `go_protein_edges`, `go_hierarchy_edges` |
| HPO | `extract_hpo` | `harmonize_phenotype_*`, `harmonize_disease_phenotype`, + HP↔MONDO reclassification, + Distinct | `phenotype_protein_edges_distinct`, `disease_phenotype_edges_distinct`, `phenotype_hierarchy_edges` |
| Assembly | `compute_kg` (Python) | — | `kg`, `graph_nodes`, `graph_edges`, `edge_metadata` |
| Visual Graph | `build-graph-gFdnaU` | — | Kuzu folder `enriched_clean-gFdnaU` |

Part 2 zones (`enriched_graph features_1`, `enriched_resampling_1`, `validation`,
`family validation`, `persona`) are documented in TARGET_PRIORITIZER.

### Build gotchas

| Gotcha | Fix |
|---|---|
| DSS re-infers digit-only string ids as **bigint**, breaking the cross-source stack | after harmonize, `dataset set-schema` all-string, then build **without** `--auto-update-schema` |
| GREL `"" + col` and `concat("HP:", col)` **numerically coerce** digit-only strings, stripping leading zeros | do the concatenation in Python with `get_dataframe(infer_with_pandas=False)` — pandas' own sniffer strips them too |
| Multi-input visual Join is a **star** (all inputs join to input 0) | chained lookups (ENSG→symbol→Entrez) need sequential joins |
| Stale output dataset blocks recipe recreation | delete the dataset first (create silently no-ops otherwise) |
| `dku dataset delete` **cascade-deletes consuming recipes** | re-list recipes after any dataset delete |
| Manually-created datasets fail builds with *"Clearing external datasets is forbidden"* | set `"managed": true` |
| Many-to-one MONDO grounding creates duplicate edges | add a Distinct recipe (hit on `disease_phenotype`, 18,950 dupes) |

## 5. Entity → source mapping

Which source is the system of record for each node and edge type, and how it grounds onto
the PrimeKG coordinate system.

| Entity / relation | Source & file | Native id | Grounding route |
|---|---|---|---|
| `gene/protein` | HGNC custom download | Entrez | authoritative vocab (`gene_names`) |
| `disease` | MONDO `MONDO.obo` | bare-integer MONDO | authoritative; `mondo_references` is the xref hub |
| `disease_disease` | MONDO `is_a` | — | direct |
| `pathway`, `pathway_protein`, `pathway_pathway` | Reactome `ReactomePathways`, `NCBI2Reactome`, `ReactomePathwaysRelation` | Reactome stable id | human-only filter; NCBI id → Entrez |
| `biological_process` / `molecular_function` / `cellular_component` + `*_protein` + hierarchies | GO `go-basic.obo` + NCBI `gene2go` | GO id | namespace → node_type; gene2go is already Entrez |
| `effect/phenotype`, `phenotype_phenotype` | HPO `hp.obo` | HP id | direct |
| `disease_phenotype_positive` / `_negative` | HPO `phenotype.hpoa` | OMIM/ORPHA/DECIPHER | → MONDO via `mondo_references`; `NOT` qualifier splits ± |
| `phenotype_protein` | HPO `genes_to_phenotype.txt` | HP id + Entrez | direct *(replaces PrimeKG's DisGeNET source)* |
| `protein_protein` | Menche `DataS1_interactome` + HuRI `HI-union` + STRING `links.detailed` | Entrez / ENSG / STRING id | HuRI ENSG→Entrez via NCBI `gene2ensembl`; STRING via aliases, filtered to `experimental≥700 OR database≥700`; merged on canonical unordered pair |
| `disease_protein` | OT `association_by_datatype_direct` | ENSG + EFO/MONDO | datatypes `genetic_association` + `somatic_mutation` @ score ≥ 0.3; ENSG→Entrez, EFO→MONDO |
| `drug` | OT `drug_molecule` | ChEMBL → **DrugBank ID** | drugs without a DrugBank xref are dropped |
| `drug_protein` | OT `drug_mechanism_of_action` | ChEMBL × ENSG | action type → `display_relation` |
| `indication` / `drug_investigated_for` | OT `clinical_indication` | ChEMBL × EFO | **split on `maxClinicalStage`**: APPROVAL/PREAPPROVAL → `indication`; all other stages → `drug_investigated_for` (stage in `display_relation`) |
| *(split control — not in the graph)* | Hetionet `hetionet-v1.0-nodes.tsv`, `kind=="Disease"` | DOID | DOID→MONDO via `mondo_references`; feeds `disease_family_id` |

### Source notes that matter

- **Open Targets is the single biggest substitution.** It replaces DisGeNET (gene–disease)
  *and* DrugBank (drug layer), and is EFO/MONDO-native, which is what let UMLS be parked.
  `associationScore` is a computed prioritization heuristic, not a curated confidence — it is
  used **only** as a threshold, never as a feature.
- **`clinical_indication` must not be flattened.** Only ~13% of rows are `APPROVAL`; ~87% are
  in-trial/preclinical/unknown. Collapsing them all to "indication" would badly overstate
  approved evidence.
- **`somatic_mutation` was added for the cancer persona** (Cancer Gene Census, IntOGen,
  ClinVar somatic) — it surfaces tumour drivers (PIK3CA, GATA3, MAP3K1, CDH1) complementary
  to `genetic_association`'s germline-risk genes (BRCA1/2, ATM, PALB2, CHEK2).
- **Inflammation coverage remains a known gap.** TNF/IL6/IL1B's obesity links are
  *literature*-datatype evidence, which we deliberately exclude (text-mining). Addressed on
  the feature side via GO functional similarity, not by widening the edge set.
- **Hetionet DO Slim reads `raw_disease_disease`, not `graph_edges`** — `compute_kg`
  reverse-alls every relation, destroying parent→child direction. The pre-reversal extract
  keeps `parent_id`/`child_id`, so the upward walk to the nearest anchor runs in
  pandas/networkx against that. See TARGET_PRIORITIZER §6.

## 6. Disambiguation / conformance notes

- Node identity is the **4-tuple**; `node_id` alone is not unique across types/sources.
- `.dropna()` in `clean_edges` is a **silent** grounding-drop (no logging).
- MONDO is stored **bare-integer** (`MONDO:0002816` → `2816`); OT's `MONDO_x` form must be
  reconciled.
- Disease grouping changes `node_id` **and** `node_source` together; only `MONDO`-source
  diseases are eligible.
- `node_index` is **positional and unstable** — it is reassigned on every `compute_kg` run.
  Any cross-build comparison must join on `(node_id, node_type, node_source)`.

---

## Appendix — decision log

| Date | Decision |
|---|---|
| 2026-06 | **Hybrid ETL** — Python extracts (native ids only), visual recipes harmonize. One flow zone per source, each with a metadata description. |
| 2026-06 | **Conform to PrimeKG's exact schema** so counts are directly comparable to the published `kg.csv`. |
| 2026-06 | **Assembly stays Python** — giant-component, `node_index` assignment and name attachment aren't expressible visually. |
| 2026-06 | **UMLS retired** from the active flow (recipes kept); MONDO xrefs cover all grounding under an OT-only design. |
| 2026-07 | **PPI = Menche only** (~276k undirected) for the first build. |
| 2026-08-05 | **Task 10:** add GO+gene2go and HPO. `phenotype_protein` sourced from HPO's own `genes_to_phenotype` (DisGeNET dropped, OT has no equivalent). |
| 2026-08-06 | **HP↔MONDO overlap harmonized** — 555 terms that are both phenotype and disease resolve to the MONDO node; affected edges reclassify rather than duplicate. |
| 2026-08-06 | **PPI augmented to Menche + HuRI + STRING** as **one** `protein_protein` relation with `ppi_sources` provenance, not separate relations — keeps the metapath feature set unchanged while closing the coverage gap (276k → 520k). |
| 2026-08-06 | **`edge_metadata` side table introduced** so provenance (`datatypes`, `ppi_sources`) survives assembly without polluting the PrimeKG-exact `kg`/`graph_edges` schema. |
| 2026-08-08 | **Hetionet DO Slim** ingested as a split-control vocabulary only — no nodes, no edges. |
| 2026-08-09 | **Storage → S3 `dataiku-managed-storage`, parquet** (Spark engine). |
