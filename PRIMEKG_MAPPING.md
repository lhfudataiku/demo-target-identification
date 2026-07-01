# PrimeKG → Our Build: Source Mapping, Schema & ETL Strategy

> **Companion to [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md).** That doc is the *project*
> view (why / who / scope / build status / reference comparison §7d). This is the
> *engineering* view: how each source is extracted, grounded, and harmonized to
> PrimeKG's schema, and how the flow is organized.

## 0. Approach — two principles

1. **PrimeKG's `processing_scripts/` + `build_graph.ipynb` are the REFERENCE, not code
   to port verbatim.** Because we replace **both DrugBank and DisGeNET with Open
   Targets**, and pull sources over HTTP/parquet/API rather than PrimeKG's on-disk
   layout, the original scripts don't run as-is. Instead, per source we use a **hybrid**:
   - a **Python recipe** *extracts* + does high-level transform (fetch URL / parquet /
     OBO / REST API → a flat `raw_<source>` table) — the part visual recipes can't do;
   - **visual recipes** (Prepare + Join) *harmonize* `raw_<source>` to the 12-column
     PrimeKG edge schema (rename/cast/filter, ground via Join to vocab, add relation
     constants).
   - Each source gets its **own flow zone** with a **metadata description**.
2. **Conform to PrimeKG's exact node/edge schema** so output is comparable to the
   published `kg.csv` (counts tracked in [PROJECT_CONTEXT §7d](PROJECT_CONTEXT.md)).

## 1. Target schema (PrimeKG-exact)

**`nodes`:** `node_index, node_id, node_type, node_name, node_source`
- `node_index` = 0..N-1 over the **deduplicated union of edge endpoints** (nodes are
  *emergent* from edges — no surviving edge ⇒ no node).
- **Node identity = the 4-tuple** `(node_id, node_type, node_name, node_source)`.
- `node_id` = source-native id: Entrez (gene), **bare-integer MONDO** e.g. `2816`
  (disease; grouped = underscore-joined), HPO/GO/UBERON/Reactome/CTD id, **DrugBank ID**
  (drug). 
- `node_source` ∈ `NCBI | MONDO | MONDO_grouped | HPO | GO | REACTOME | UBERON | CTD | DrugBank`.

**`kg`:** `relation, display_relation, x_index, x_id, x_type, x_name, x_source,
y_index, y_id, y_type, y_name, y_source`. **`edges`** = slim
`relation, display_relation, x_index, y_index`.

## 2. The disease coordinate system: MONDO vs UMLS

Different roles — one is a node vocabulary, the other a translation table.

**MONDO — the disease coordinate system.** Every disease node *is* a MONDO term. Provides:
1. **disease nodes** (id → name); 2. **disease hierarchy** (`is_a` → `disease_disease`
parent-child edges); 3. **a cross-reference hub** (`mondo_references`: MONDO ↔ MESH /
OMIM / Orphanet / HP / DOID / UMLS …) — the mechanism that pulls other sources' diseases
onto MONDO.

**UMLS — a bridge, not a node type.** No "UMLS nodes" exist. UMLS is used only to
translate diseases that a source identifies by **UMLS CUI** into MONDO. In original
PrimeKG two sources spoke UMLS: **DisGeNET** (gene–disease) and **DrugCentral**
(drug–disease). The `umls_mondo` crosswalk is purely that CUI→MONDO translator.

**Why UMLS is PARKED for us.** We replaced both UMLS-speaking sources with **Open
Targets**, which codes diseases in **EFO/MONDO natively** → nothing left to translate,
so `compute_umls*` (and the 430 MB MRCONSO) have no consumer. It stays parked even as we
extend: the pending layers ground through **MONDO's own xrefs**, not UMLS — HPO
`phenotype.hpoa` (OMIM/ORPHA/DECIPHER → `mondo_references`) and CTD (MESH →
`mondo_references`). UMLS returns only if we add DrugCentral contraindication/off-label
or another UMLS-only source. **Decision: retire from the active flow (recipes kept in
repo).**

## 3. Reusable harmonization logic (reproduce as reference, not port)

The scientific value in `build_graph.ipynb` — reproduce this behavior in the assembly
zone (visual where possible, Python where not):
- **`clean_edges`** — coerce to 12 cols, `dropna` (**grounding-drop**: failed crosswalk
  ⇒ row discarded), `drop_duplicates`, drop self-loops. Visual = Distinct + Filter, or a
  shared Python util.
- **Reverse-all edges** — undirected by duplicating every edge x↔y (relation strings
  unchanged). PrimeKG reverses *all* relations.
- **Vocab anchors** for grounding joins: `gene_names` (Entrez↔symbol), `mondo_terms`
  (id→name), `mondo_references` (MONDO↔ext ontology). (`umls_mondo` parked — see §2.)
- **HP↔MONDO reclassification** (when HPO added): terms that are both HPO phenotype and
  MONDO disease resolve to the MONDO node; phe/prot edges reclassify to `disease_*`.
- **Giant-component filter** — keep the largest connected component. Not expressible
  visually → Python/networkx (or the `graph-analytics` plugin).
- **Disease grouping** — apply PrimeKG's **published** map (`disease_group_map` ←
  Dataverse datafile 6180623): disease MONDO nodes in a group get the underscore-joined
  `node_id` + group name + `node_source='MONDO_grouped'`. Deterministic; no BERT needed.

## 4. Per-source ETL design (hybrid + zones) — BUILT

Each source is its own flow **zone**: `extract` (Python, native ids) → `harmonize`
(visual Prepare, +visual Join for OT). Per-source edges are **8-col, name-free**
(`x_id, y_id, x_type, y_type, x_source, y_source, relation, display_relation`, all
string); names resolved once at the assembly.

**Zones & recipes:**
- **Genes (HGNC):** `compute_gene_names` → `gene_names` (vocab).
- **Diseases (MONDO):** `extract_mondo` → `mondo_terms`(vocab)/`raw_disease_disease`;
  `harmonize_disease_disease` → `mondo_edges`.
- **PPI (Menche):** `extract_ppi` → `raw_ppi`; `harmonize_ppi` → `ppi_edges`.
- **Open Targets (ref):** `extract_ot_assoc`→`raw_ot_assoc`; `extract_ot_maps`→
  `ot_target_map`/`ot_disease_map` (shared by Gene-Disease + Drugs).
- **Gene-Disease (OT):** `join_gd_maps` (star: assoc⋈target⋈disease) → `join_gd_genes`
  (⋈gene_names) → `harmonize_gene_disease` → `gene_disease_edges`.
- **Pathways (Reactome):** `extract_reactome` → `reactome_terms`(vocab)/`raw_pathway_*`;
  `harmonize_pathway_protein`/`_pathway` → `reactome_gp_edges`/`reactome_pp_edges`.
- **Drugs (OT):** `extract_drug_ot` → `drug_vocab`/`raw_drug_*`; `join_dp_target`→
  `join_dp_genes`→`harmonize_drug_protein`→`drug_protein_edges`; `harmonize_drug_indication`
  →`drug_indication_edges`.
- **Assembly:** `compute_disease_group_map`→`disease_group_map`; `compute_kg` (Python)
  stacks *_edges → clean → reverse-all → attach names → grouping → giant component →
  `node_index` → `primekg`/`primekg_nodes`/`primekg_edges`.

**Build gotchas:** (a) after harmonize, `set-schema` all-string then build **without**
`--auto-update-schema` (DSS re-infers numeric ids as bigint → breaks the stack).
(b) DSS multi-input Join is a **star** (all inputs join to input 0) — chained lookups
(ENSG→symbol→Entrez) need two sequential joins. (c) delete a stale output dataset before
recreating its recipe (create silently no-ops otherwise).

**Built & conformant (7 relations):** Genes(HGNC vocab), Diseases(MONDO)→disease_disease,
PPI(Menche)→protein_protein, Gene-Disease(OT)→disease_protein, Pathways(Reactome)→
pathway_protein+pathway_pathway, Drugs(OT)→drug_protein+indication, Assembly→primekg.

**Pending (task 10, same pattern):** GO+gene2go (bioprocess/molfunc/cellcomp +_protein
+hierarchy), HPO (phenotype + disease_phenotype±, HP↔MONDO reclassify). Optional/stretch:
UBERON+Bgee anatomy (heavy), CTD exposure, SIDER drug_effect.

## 5. Per-source reference detail (schemas & grounding)

### Open Targets — gene–disease + drug layer (release 26.06, no credentials)
Parquet at `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/`.
- **gene–disease** → `disease_protein` / "associated with":
  **`association_by_datatype_direct` filtered to `aggregationValue=="genetic_association"`**
  (the DisGeNET-curated analog — expert genetic/clinical evidence: GWAS Catalog, ClinVar,
  Genomics England, Gene2Phenotype, UniProt, Orphanet, ClinGen; **excludes** the
  `literature` text-mining and `animal_model` datatypes). `targetId` ENSG, `diseaseId`
  EFO/MONDO, `associationScore` (per-datatype harmonic sum, threshold `ot_score_min`=0.3)
  → ground ENSG→Entrez/symbol (`target` + `gene_names`) and EFO→MONDO. Bypasses UMLS.
  After grounding to MONDO+Entrez, ~89k edges (non-disease GWAS traits drop out) —
  comparable in scale to DisGeNET curated (~82k). Note: score is still a computed
  prioritization heuristic (not a confidence/curated value), kept only as a threshold.
  Tradeoff vs the old `association_overall_direct`: higher precision (no text-mining), so
  some genes with mainly literature evidence lose edges (e.g. TNF 34→1).
- **drug nodes**: `drug_molecule` (`id` ChEMBL, `name`, `crossReferences`→**DrugBank
  ID**). node_id = DrugBank ID; ChEMBL drugs w/o DrugBank xref drop.
- **drug→target** → `drug_protein` (display = action type): `drug_mechanism_of_action`
  (`chemblIds[]` × `targets[]` ENSG + `actionType`) → Entrez via `gene_names`.
- **drug→disease** → **split by `maxClinicalStage`** (⚠ correction): `clinical_indication`
  has NO score, only `maxClinicalStage`, and **aggregates all development stages** — only
  ~13% are `APPROVAL`; ~87% are in-trial (Phase I–III), preclinical, or unknown. We must
  NOT label all as "indication". Mapping: `APPROVAL`/`PREAPPROVAL` → relation `indication`
  (~4.7k pairs); all other stages → relation `drug_investigated_for` (hypothesis-level,
  ~35k pairs) with `maxClinicalStage` in `display_relation`. Disease EFO→MONDO as above.
- Caveats: nested arrays (explode); `associationScore` (not `score`); snake_case dirs;
  keep `maxClinicalStage` — do NOT flatten indications to one relation.

### PPI — Menche interactome
`DataS1_interactome.tsv` (Menche 2015): `gene_ID_1, gene_ID_2, data_source(s)`, ~141k
Entrez pairs, 23-line `#` header. → `protein_protein` / "ppi". PrimeKG additionally used
BioGRID+STRING (642k vs our 276k — see §7d); Menche-only is the POC choice.

### UMLS → MONDO crosswalk — PARKED (see §2)
`umls_mondo` = (`umls_id`, `mondo_id`). Built by `compute_umls` (MRCONSO ENG, 6 SABs via
`scripts/filter_mrconso.sh`) + `compute_umls_mondo` (join MONDO xrefs: direct UMLS xrefs
+ indirect via OMIM/NCI/MSH/MDR/ICD10/SNOMEDCT). No active consumer under OT-only design.

### disgenet.cn RNA-KG — optional enrichment (NOT DisGeNET)
`items.csv`/`interactions.csv` = an RNA-centric network (miRTarBase/STRING/HMDD/ENCORI/
RNADisease/OMIM), MONDO-keyed. Gene–disease only 5,959 (OMIM) → **not** a DisGeNET
substitute. Optional: adds miRNA/lncRNA layers PrimeKG lacks. Parse with a real CSV
reader (BOM, quoted commas, pipe multi-values).

### DrugCentral — fallback only (superseded by Open Targets)
If contraindication/off-label edges are later wanted (OT has neither): DrugCentral REST
API `/omop_relationship/relationship_name/{type}` (struct_id, umls_cui) — would re-need
the UMLS crosswalk. `struct_id → DrugBank ID` via `/identifier` (`DRUGBANK_ID`). Public
read-only Postgres `unmtid-dbs.net:5433` (`drugcentral`/`drugman`/`dosage`) as bulk route.

## 6. Disambiguation / conformance notes

- Node identity is the **4-tuple**; `node_id` alone isn't unique across types/sources.
- `.dropna()` in `clean_edges` is the **silent** grounding-drop (no logging).
- MONDO stored **bare-integer** (`MONDO:0002816` → `2816`); reconcile OT `MONDO_x`.
- Disease grouping changes `node_id` (underscore-join) **and** `node_source`
  (`MONDO_grouped`) together; only `source=='MONDO'` diseases are eligible.

## 7. Resolved decisions (all "lean" options taken)

1. **Scope order** — reworked the 6 built sources into zoned hybrid first (piloted PPI). ✅
2. **Layers to add next** — GO + HPO (task 10); anatomy/CTD/SIDER optional/stretch.
3. **Assembly** — Python (giant-component/node_index/name-attachment); per-source ETL visual.
4. **PPI** — Menche only (~276k undirected). ✅
5. **Storage** — `filesystem_managed`. ✅
6. **UMLS** — retired from active flow (recipe files kept in repo). ✅

## 8. Reference comparison

Node/edge counts vs published PrimeKG (Tables 2–3): see
[PROJECT_CONTEXT.md §7d](PROJECT_CONTEXT.md).
