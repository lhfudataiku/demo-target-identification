# PrimeKG Scripts → Our Build: Reuse/Modify Strategy & Schema Conformance

Goal: faithfully recreate PrimeKG's *scientific* pipeline (highlight #1) under our
constraints (Open Targets instead of DisGeNET, DrugBank dropped, DrugCentral via API,
UMLS 2024AB on hand). Two principles:

1. **Reuse PrimeKG's harmonization/disambiguation logic verbatim** where it carries
   scientific meaning (entity resolution, grounding, grouping). Port the code; adapt
   only I/O.
2. **Conform to PrimeKG's exact node/edge schema** so the output is comparable to the
   published `kg.csv`.

This is the blueprint that supersedes the simplified core-slice schema in §7b of
PROJECT_CONTEXT.md (which must be refactored — see "Gaps in current build").

---

## 1. Target schema (PrimeKG-exact)

**`nodes.csv`:** `node_index, node_id, node_type, node_name, node_source`
- `node_index` = 0..N-1 positional index over the **deduplicated union of all edge
  endpoints** (nodes are *emergent* from edges — a node with no surviving edge does
  not exist).
- **Node identity is the 4-tuple `(node_id, node_type, node_name, node_source)`** — not
  `node_id` alone. Same id under two sources/names = two nodes.
- `node_id` = source-native id: Entrez (gene), **bare MONDO integer** e.g. `0005148`
  (disease), HPO/GO/UBERON/Reactome/CTD id. Grouped diseases → underscore-joined ids.
- `node_source` ∈ `NCBI | MONDO | MONDO_grouped | HPO | GO | REACTOME | UBERON | CTD | DrugCentral*`
  (*PrimeKG uses `DrugBank`; we substitute — see §4).

**`kg.csv`:** `relation, display_relation, x_index, x_id, x_type, x_name, x_source,
y_index, y_id, y_type, y_name, y_source`. **`edges.csv`** = slim
`relation, display_relation, x_index, y_index`.

## 2. The two load-bearing primitives — REUSE VERBATIM

- **`clean_edges(df)`** — coerce to the 10 `x_*/y_*/relation/display_relation` cols,
  `.dropna()` (**this is the silent grounding-drop**: a failed crosswalk merge leaves
  NaN → row discarded), `.drop_duplicates()`, drop self-loops. Applied to every edge df.
- **Reverse-all-edges** — PrimeKG makes the graph **undirected by duplicating every
  edge** with x/y swapped (relation strings unchanged, so relation names are
  direction-agnostic). *This settles the earlier directionality question: PrimeKG
  reverses ALL relations, not just symmetric ones.* Our current `directed`-flag idea is
  dropped in favor of PrimeKG's convention.
- **Canonical vocab anchors** (loaded once, used for grounding): `gene_names`
  (Entrez→symbol), `umls_mondo` (UMLS↔MONDO), `mondo_terms` (id→name), `mondo_references`
  (MONDO↔ext ontology), `hp_references` (HPO↔ext).

## 3. Per-component mapping (reuse / modify / drop)

| PrimeKG component | What it does (scientific?) | Our decision |
|---|---|---|
| `mondo_obo_parser.py` + `mondo.py` | parse MONDO.obo → terms/parents/refs/subsets/defs | **Port verbatim** (replaces my obonet `compute_mondo`); add `is_obsolete/replacement_id`, `subsets`, `definitions`. Use **bare-integer** MONDO ids. |
| `hpo_obo_parser.py` + `hpo.py` + `hpoa.py` | HPO terms/parents/refs + disease–phenotype ± | **Port verbatim** (phenotype layer). |
| `go.py`, `ncbigene.py` | GO terms/relations + protein–GO | **Port verbatim.** |
| `reactome.py` | pathway terms/relations + NCBI→pathway | **Port** (replaces my `compute_reactome`; logic ~identical). |
| `uberon.py`, `bgee.py` | anatomy + anatomy–gene (gene grounded by **symbol**) | **Port verbatim.** |
| `ctd.py` | exposure + exposure–disease/protein/GO | **Port verbatim.** |
| `sider.py` | drug–side-effect (ATC→DrugBank) | **Modify** — drug grounding changes (no DrugBank, see §4); or defer (low value w/o drug layer). |
| `umls.py` + `map_umls_mondo.py` | MRCONSO → `umls.csv`; UMLS↔MONDO crosswalk | **Already ported** (`compute_umls*`); used by DrugCentral grounding. |
| HGNC download (`gene_names`) | gene identity (Entrez↔symbol) | **Keep** my `compute_gene_names` (matches PrimeKG's vocab role). |
| `drugbank_*` (drug_protein, drug_drug) | DrugBank drug layer | **DROP** (no `drug_drug`; drug→target substituted, §4). |
| `disgenet.py` (in build_graph cells 14/21) | gene–disease + gene–phenotype, UMLS→MONDO grounding | **Replace with Open Targets** (§4). |
| DrugCentral cell 12 | drug–disease (CAS→DrugBank, UMLS→MONDO) | **Modify** for API + struct_id drug id (§4). |
| **`build_graph.ipynb` harmonization** | `clean_edges`, HP↔MONDO reclassify, reverse-all, giant-component, **disease grouping** | **Port the deterministic parts verbatim**; handle BERT pass specially (§5). |

## 4. Substitution grounding specs (must hit the SAME node space)

**Open Targets gene–disease** (replaces DisGeNET disease rows → `disease_protein` /
`associated with`):
- `x_id` = **Entrez** (need ENSG→Entrez; we map ENSG→approvedSymbol→Entrez via
  `gene_names`), `x_type='gene/protein'`, `x_source='NCBI'`, `x_name`=HGNC symbol.
- `y_id` = **bare MONDO integer** (strip `MONDO_`/`MONDO:` prefix from OT id),
  `y_type='disease'`, `y_source='MONDO'`, `y_name`=`mondo_terms` name.
- OT is already MONDO → **skip the UMLS crosswalk** for this edge.
- *Refactor of current `compute_gene_disease`: re-emit in the 12-col edge schema with
  bare-integer MONDO + `disease_protein`/`associated with`.*

**Drug node-id authority (DrugBank dropped):** standardize drug nodes on **DrugCentral
`struct_id`** → `node_source='DrugCentral'`, `node_id=struct_id`, `node_name=DRUG_NAME`.
Both drug edges share this key → consistent drug identity:
- **drug→target** (from `drug.target.interaction.tsv`): `x`=drug(struct_id),
  `y`=gene grounded via `GENE`/`ACCESSION`→Entrez (`gene_names`); `relation='drug_protein'`,
  `display_relation`=`ACTION_TYPE`/target class. Filter `ORGANISM=='Homo sapiens'`.
- **drug→disease** (DrugCentral API): `x`=drug(struct_id); `y`=`umls_cui`→MONDO via
  `umls_mondo` → bare-integer MONDO; `relation`=`relationship_name`
  (indication/contraindication/off-label use) into both relation+display.
- *Deviation from PrimeKG (DrugBank-keyed drugs) — documented & internally consistent.*

## 5. Disambiguation steps to preserve (the "scientific work")

1. **`clean_edges` grounding-drop** — keep (it enforces that every edge is fully
   grounded to canonical ids).
2. **HP↔MONDO reclassification** (build_graph cells 28–32) — terms that are both HPO
   phenotypes and MONDO diseases are resolved to the MONDO node; phe-phe/prot-phe edges
   get reclassified to disease_* accordingly; negative disease-phenotype dropped.
   **Reuse verbatim** when the phenotype layer is added.
3. **HPOA ontology-consistency filter** — keep.
4. **Giant-component filter** (cell 73) — keep only the largest connected component.
   **Recommend keep** (fidelity; drops orphans). Optional for POC.
5. **Disease grouping** (cells 79–90) — merges multiple MONDO ids into one node:
   - **Pass A — name-suffix grouping** (`same_words`, roman/numeric suffix, chromosomal
     exclusions): **deterministic → port verbatim.**
   - **Pass B — Bio_ClinicalBERT @0.98 cosine + interactive `input()` confirmation**:
     **not headless-reproducible.** Options: (a) skip Pass B (keep Pass A only) for the
     POC; (b) make it non-interactive (auto-accept ≥0.98 with the existing blocklist);
     (c) persist a curated group map and apply deterministically. **Recommend (a) now,
     (b) later** — and surface the count of groups affected so the deviation is explicit.
6. **Second reverse+dedup pass** after grouping — keep.

## 6. Gaps in current core-slice build (to refactor)

My verified core slice works but is **non-conformant**; to align:
- Node id: composite `gene:7105` / `disease:MONDO:x` → **native ids** (`7105`,
  bare-integer MONDO) + `node_type/node_source/node_index`, 4-tuple identity.
- Edge schema: `source,target,relation` → full `relation, display_relation, x_*, y_*`.
- Relations: my labels (`gene_associated_with_disease`, `gene_in_pathway`, …) →
  PrimeKG vocab (`disease_protein`/`associated with`, `pathway_protein`/`interacts with`,
  `disease_disease`/`parent-child`, `protein_protein`/`ppi`, …).
- Reverse **all** edges (not the symmetric-only idea).
- Adopt `clean_edges` + giant-component + disease-grouping Pass A.
- MONDO id format → bare integer (strip curie); reconcile Open Targets `MONDO_` ids.

## 7. Resolved decisions

- **Drug node-id authority = DrugBank ID** (matches PrimeKG). Obtained credential-free
  from **DrugCentral's `/identifier` API** (`id_type=DRUGBANK_ID`: struct_id→DrugBank ID,
  4,368 drugs, e.g. struct_id 5391→DB12893). No DrugBank download. Drug nodes:
  `node_id`=DrugBank ID, `node_source`='DrugBank', `node_name`=drug name. struct_ids with
  no DrugBank mapping drop out (matches PrimeKG's CAS→DrugBank behavior).
- **Disease grouping = reuse PrimeKG's published map.** Download
  `kg_grouped_diseases_bert_map.tab` (Harvard Dataverse datafile **6180623**, doi
  10.7910/DVN/IXA7BM) and apply deterministically — gives PrimeKG's exact BERT-grouped
  diseases (`node_source='MONDO_grouped'`, underscore-joined ids) with no model/interaction.
  Also available: `kg_grouped_diseases.tab` (6180624) for cross-check.
- **Giant-component filter = KEEP** (igraph, collapse-undirected, keep largest component).

### Drug layer data flow — UPDATED: Open Targets drives the drug layer
Decision: the drug layer comes from **Open Targets** (ChEMBL-derived), not DrugCentral —
it shares our ENSG/EFO-MONDO ID spaces (cleanest integration), is fully open, and keeps
the whole graph on one source. DrugCentral drug plan is superseded.
- **drug nodes:** OT `drug_molecule` (ChEMBL id, name, `crossReferences`→**DrugBank ID**).
  node_id = DrugBank ID (via xref), node_source='DrugBank', node_name = drug name.
- **drug→target** (`drug_protein` / action type): OT `drug_mechanism_of_action`
  (ChEMBL drug → ENSG targets + actionType) → ground ENSG→Entrez via `gene_names`.
- **drug→disease** (indication): OT `clinical_indication` (ChEMBL drug → EFO/MONDO +
  trial phase) → MONDO via the same EFO→MONDO path as gene–disease.
- **Not covered:** drug–drug interactions (DDI) — DrugBank-only, absent from both OT and
  DrugCentral; out of scope unless DrugBank is acquired. Contraindication/off-label —
  DrugCentral-only (OT has indications + phase); not included under this decision.
- Superseded: DrugCentral `/identifier`, `drug.target.interaction.tsv`,
  `/omop_relationship` (kept as fallback if contraindication/off-label later wanted).

## 8. Implementation shape in DSS

- Put PrimeKG's pure-python parsers + `clean_edges`/`same_words`/grouping helpers in the
  **project code library** (`python/`), imported by thin recipes — this is the literal
  "reuse the scripts" deliverable.
- Each per-source recipe emits the **12-col edge schema** (already grounded).
- One **assembly recipe** = concat all edge dfs → `clean_edges` → reverse-all → grouping
  (Pass A) → giant component → derive `nodes` + `node_index` → write `kg`/`nodes`/`edges`.
- Visual Graph Editor points at the conformed `nodes`/`kg` (edge `x_index`/`y_index`).
