# Graph Building — `DEMO_KG_LS`

> **Lifecycle:** Canonical · **Audience:** Part 1 builders and reviewers · **Authority:** accepted graph
> construction method and contract · **Update when:** sources, schema, pipeline or acceptance contract
> changes · **Generated dependencies:** none; measurements are re-derived from the flow · **Excludes:**
> Part 2 modelling and routine job/build logs.

> Technical documentation for the **data pipeline and graph-building webapp**: what goes in, how it
> is harmonized, the schema it conforms to, and what comes out.
>
> Companion documents: **[PROJECT_CONTEXT.md](../overview/PROJECT_CONTEXT.md)** (why / who / how the two
> projects fit) · **[TARGET_PRIORITIZER.md](../prioritizer/TARGET_PRIORITIZER.md)** (the modelling project that
> consumes this graph).
>
> **Status: complete.** 113,497 nodes / 2,853,534 edges / 19 relations, rebuilt from the pinned
> 2026-11-08 source pull (graph revision, 2026-11-10; 113,391 / 2,851,510 / 18 when accepted against the
> frozen reference, §7.2). Decisions are logged in the **appendix**.

## 1. Scope and approach

Create a PrimeKG-like pipeline as a governed Dataiku flow: ingest public biomedical sources,
harmonize them onto one identifier system, and assemble a knowledge graph that conforms to
PrimeKG's published schema so the output is directly comparable to it.

Two principles govern every design choice:

1. **PrimeKG's own scripts are the *reference*, not code to port.** Two of its sources were
   replaced (§2), and we pull over HTTP rather than from its on-disk layout, so its scripts do not
   run as-is. Per source we use a **hybrid**: a Python recipe *extracts* (fetch → parse to
   source-native identifiers → flat table), then **visual recipes** *harmonize* (rename, cast,
   filter, ground via joins, add relation constants).
2. **Conform to the published schema exactly**, so node and edge counts are comparable to the
   reference implementation and to the paper (§7).

**Why the split matters in practice:** extraction is where the messy, source-specific work lives
and it belongs in code; harmonization is table-shaped and belongs in visual recipes where it is
inspectable. Grounding failures are the single largest source of silent data loss in this pipeline
(§4.3), and keeping them in visual joins makes them countable.

## 2. Input data

Every source is freely downloadable over HTTP(S) with no credentials, fetched inside a Python
recipe. **The project holds zero source datasets** — all 47 recipes bootstrap from code, with one
uploaded file (the Menche interactome) and one snapshot (§3.2).

| Source | Provides | Node types contributed | Edge relations contributed |
|---|---|---|---|
| **HGNC** | gene identity vocabulary (symbol ↔ Entrez ↔ UniProt) | — *(vocabulary; every gene-touching edge joins on it)* | — |
| **MONDO** (`MONDO.obo`) | disease backbone + cross-reference hub | `disease` (25,906 MONDO + 1,247 grouped) | `disease_disease` |
| **Open Targets** (26.06) | gene–disease associations + the entire drug layer | `drug` (5,282) | `disease_protein`, `drug_protein`, `indication`, `drug_investigated_for` |
| **PPI: Menche + HuRI + STRING** | protein interactome, merged with provenance retained | `gene/protein` (20,861) | `protein_protein` |
| **Reactome** | curated pathways | `pathway` (2,883) | `pathway_protein`, `pathway_pathway` |
| **GO + NCBI `gene2go`** | functional annotation, 3 namespaces | `biological_process` (23,974), `molecular_function` (10,041), `cellular_component` (4,077) | `bioprocess_protein`, `molfunc_protein`, `cellcomp_protein` + 3 hierarchies |
| **HPO** (`hp.obo`, `phenotype.hpoa`, `genes_to_phenotype`) | phenotype layer | `effect/phenotype` (19,120) | `disease_phenotype_positive`/`_negative`, `phenotype_protein`, `phenotype_phenotype`, `disease_phenotype_disease`; gene links on reclassified terms land in `disease_protein` |

### 2.1 Sources deliberately excluded

| Source | Gate | Decision |
|---|---|---|
| Gene–disease association portal | moved to a paid API in 2023; the legacy URL returns a login page | **replaced by Open Targets** |
| Drug database | account + commercial licence, manual download | **replaced by the Open Targets drug layer** (its identifiers are retained as our drug `node_id` via cross-reference) |
| Clinical terminology metathesaurus | licence required | **parked** — both sources that spoke it were replaced by Open Targets, which is native to our disease vocabulary, so nothing is left to translate |
| Mendelian disease catalogue | free API key required | deferred — loses Mendelian-disease enrichment |
| Drug-centric database | ~4.5 GB dump; REST API viable | fallback only — the sole route to contraindication / off-label edges, which Open Targets lacks |
| Anatomy + expression atlas | free but heavy | optional stretch — would add ~3M anatomy–protein edges |
| Exposure and side-effect databases | free | optional stretch |

**The single biggest substitution is Open Targets.** It replaces *both* the gene–disease source and
the drug source, and because it is native to our disease vocabulary it is what allowed the licensed
clinical terminology to be dropped entirely. Two caveats we enforce:

- Its association score is a **computed prioritisation heuristic, not a curated confidence**. It is
  used **only** as a threshold, never as a model feature.
- Its clinical-indication table **must not be flattened**. Only ~13% of rows are approvals; ~87%
  are in-trial or preclinical. Collapsing them would badly overstate approved evidence, so they
  split into two distinct relations.

### 2.2 Source versions and reproducibility

Each source recipe carries a `SOURCE PROVENANCE` header recording the version in use and how to
freeze it. **Since 2026-11-08 every source is pinned.** Extraction lives in `DEMO_KG_PREP`: Open Targets
and STRING are versioned in their URL, and recipe `compute_pinned_sources` downloads every unversioned
source once into folder `pinned_sources`, never overwrites a file there, and records URL, retrieval
time, size, SHA-256, `Last-Modified` and release in `MANIFEST.json`. To take a new release, delete the
file and rebuild `compute_pinned_sources` and its reader.

| Source | Version in the current graph (2026-11-08 pull) | Pinned how | August build used |
|---|---|---|---|
| Open Targets | **26.06** | in the URL | 26.06 |
| STRING | **v12.0** | in the URL | v12.0 |
| Published disease-grouping map | pinned id, but **returns 0 bytes** | snapshot (§3.2) | same |
| MONDO | `releases/2026-11-03` | `pinned_sources` | `releases/2026-08-04` |
| HPO | `releases/2026-09-01` | `pinned_sources` | `releases/2026-06-23` |
| GO | `releases/2026-07-26` | `pinned_sources` | same release |
| Reactome | release 98 | `pinned_sources` | release 97 |
| HGNC | live query, retrieved 2026-11-08 | `pinned_sources` | 2026-08-13 |
| NCBI gene2go, gene↔Ensembl map | files dated 2026-11-08 | `pinned_sources` | early August |
| HuRI interactome | file dated 2020-04-12 | `pinned_sources` | same file |
| Menche interactome | uploaded file | local | same |

The paragraphs below describe the August state that made pinning necessary.

**All three ontologies were verified still at their build release** using a three-way check rather
than a count coincidence: the parser keeps live terms *plus* bare placeholder nodes for obsolete
terms still referenced by others, so `named == live` **and** `unnamed ⊆ obsolete` must both hold.

**The gene↔Ensembl map is the least reproducible input in the flow** — the provider rewrites it
continuously (279 MB, modified the same day the audit ran), so the copy that built the current graph
no longer exists. Anything depending on it cannot be reproduced byte-for-byte without a snapshot.

**⚠ GO has already drifted, and the frozen reference is the stale side.** Both projects hold 38,092
GO terms, but the reference's `graph_nodes` carries **38,245** GO nodes — 153 more than any GO
release either project still has. So the reference was built from a superseded GO release and is
inconsistent with its own upstream. This is the entire source of the acceptance delta in §7.2, and
the intuitive reading ("the rebuild drifted") is backwards.

## 3. Graph schema

Conformant to PrimeKG's published schema, so counts are directly comparable.

**`graph_nodes`** — `node_index, node_id, node_type, node_name, node_source`

- **Node identity is the 4-tuple** `(node_id, node_type, node_name, node_source)`. `node_id` alone
  is not unique across types and sources. Any cross-build or cross-project comparison must key on
  this, never on the integer.
- `node_id` is **source-native**: gene = Entrez; disease = bare-integer MONDO (`MONDO:0002816` →
  `2816`, grouped nodes underscore-joined); phenotype / GO / pathway = their own accession; drug =
  the drug-database identifier obtained via cross-reference.
- `node_source` ∈ `NCBI | MONDO | MONDO_grouped | HPO | GO | REACTOME | DrugBank`.
- Nodes are **emergent from edges** — the deduplicated union of surviving edge endpoints. No
  surviving edge means no node.

**`node_index` is deterministic, and this is new.** It is assigned by a visual **Window** recipe
ordering on `(node_type, node_source, node_id, node_name)`, making it a pure function of the node
key. Verified by two independent full builds producing byte-identical indices across all 113,391
nodes. The reference implementation assigned it positionally instead, so **every rebuild there
silently renumbered the entire graph** — the defect this replaced.

> **⚠ Two other things changed with it.** Both are harmless internally and both bite a consumer that
> assumes continuity with the reference:
>
> 1. **The origin.** This project is **1-based** (1…113,391); the reference is **0-based**
>    (0…113,543), as is the published schema — the Window row number starts at 1.
> 2. **The column order.** Here `node_index` is **last** (`node_id, node_type, node_name,
>    node_source, node_index`) because it is appended by the Window recipe; in the reference it is
>    **first**. Every consumer that names its columns is fine; anything positional is not. This is
>    what makes three downstream name-join recipes report a schema mismatch until they are rebuilt
>    with schema update enabled.
>
> Together with the renumbering, these are the three reasons the modelling project cannot carry
> hardcoded integers or positional assumptions across the migration.

**`kg`** — the full edge table: `relation, display_relation, x_index, x_id, x_type, x_name,
x_source, y_index, y_id, y_type, y_name, y_source`.
**`graph_edges`** — slim: `relation, display_relation, x_index, y_index`.
**`edge_metadata`** — `x_index, y_index, relation, datatypes, ppi_sources`. Provenance is kept
*off* the schema-conformant tables so they stay conformant.

### 3.1 The disease coordinate system

**Every disease node is a MONDO term.** MONDO provides three things: the disease nodes, the `is_a`
hierarchy that becomes `disease_disease`, and — most importantly — **a cross-reference hub** mapping
MONDO to every other vocabulary. That hub is the mechanism that pulls every other source's diseases
onto a single coordinate system, and it is why no licensed clinical terminology is needed.

### 3.2 One source needs a snapshot, permanently

The published disease-grouping map is fetched from a pinned archive endpoint that now returns an
empty body. It is **load-bearing**: it creates the 1,247 grouped disease nodes, which are 883 of the
6,821 modelled diseases and 115 of 588 scored validation diseases. Deleting the recipe would remove
a fifth of the validation population.

**Fix in place:** the recipe reads a 6,392-row snapshot from the `upload` managed folder (in
`DEMO_KG_PREP` since 2026-11-08) via a download stream, with the recipe pinned to run on the DSS
engine. Never delete this recipe; if the
snapshot is lost, the graph cannot be rebuilt as specified.

## 4. Data pipeline

### 4.1 Flow zones — grouped by biological domain

**Since 2026-11-08 (graph revision R3/R4) extraction lives in its own project.**
- **`DEMO_KG_PREP`** downloads the sources, in four domain zones plus **Pinned downloads**. There,
  `compute_pinned_sources` saves each unversioned source once (decision D9).
- **`DEMO_KG_LS`** keeps one loading zone per domain, now made of sync recipes
  (`compute_DEMO_KG_PREP_<name>_copy`). Each sync copies a `DEMO_KG_PREP` output under its original
  name, and sits in the loading zone with its input and its copy. Part 2's sync recipes therefore
  read `DEMO_KG_LS` unchanged (decision D8).

| Project · zone | Contents |
|---|---|
| `DEMO_KG_PREP` · Pinned downloads | `compute_pinned_sources` → folder `pinned_sources` (+ `MANIFEST.json`) |
| `DEMO_KG_PREP` · Gene & interactome | HGNC vocabulary and identity; HuRI, STRING, Menche extracts; folder `raw_files` |
| `DEMO_KG_PREP` · Disease & phenotypes | MONDO, HPO, disease-grouping snapshot (folder `upload`) |
| `DEMO_KG_PREP` · Function & pathways | GO terms, hierarchy and gene annotations; Reactome |
| `DEMO_KG_PREP` · Open Targets | associations, id maps, drugs, druggability, safety, known drugs |
| `DEMO_KG_LS` · Gene & interactome (HGNC, PPI) | 5 syncs: gene names, HGNC identity, HuRI, STRING, Menche |
| `DEMO_KG_LS` · Genes & interactome harmonisation | → `ppi_edges` |
| `DEMO_KG_LS` · Disease & phenotypes (MONDO, HPO) | 8 syncs: MONDO, HPO, disease grouping |
| `DEMO_KG_LS` · Diseases & phenotypes harmonisation | → overlap resolution, grounding, deduplication |
| `DEMO_KG_LS` · Function & pathways (GO, Reactome) | 6 syncs: GO and Reactome |
| `DEMO_KG_LS` · Function & pathways harmonisation | → GO and Reactome edges |
| `DEMO_KG_LS` · Drugs & gene-disease (Open Targets) | 9 syncs, including the druggability, safety and known-drug copies Part 2 reads |
| `DEMO_KG_LS` · Drugs & gene-disease harmonisation | → drug and gene–disease edges |
| `DEMO_KG_LS` · Graph build | the 4 assembly recipes and their outputs |
| `DEMO_KG_LS` · Graph Snapshots | one Kuzu build per saved snapshot, Visual Graph support datasets |

*Before 2026-11-08* the `DEMO_KG_LS` loading zones held the extract recipes themselves, and
`Function & pathways (GO, Reactome)` held extraction and harmonisation together.

**Why domains rather than pipeline phases.** A phase-based scheme (all sources → all harmonisation →
all relationships → build) was drafted and rejected: it puts every source in one large box, so the
flow stops answering the question a reader actually has, which is *"where does the disease data come
from?"* Grouping by domain keeps each biological story traceable end to end, and pairing each domain
with its own harmonisation zone keeps the extract/harmonise seam visible. The seam is now also a
project boundary.

### 4.2 The per-source pattern

**`extract_*`** (Python: fetch + parse to native identifiers) → **`harmonize_*`** (visual Prepare,
plus visual Joins where grounding needs a lookup) → an **8-column, name-free edge table**
(`x_id, y_id, x_type, y_type, x_source, y_source, relation, display_relation`, all strings). Names
are resolved once, in assembly.

| Stage | Extract | Harmonize | Output |
|---|---|---|---|
| Genes | gene vocabulary | — | *(vocabulary only)* |
| Diseases | disease ontology | hierarchy → edges | `mondo_edges` |
| Interactome | three sources → merge | | `ppi_edges` |
| Gene–disease | association table | grounding joins | `gene_disease_edges` |
| Pathways | pathway files | protein + hierarchy | `reactome_gp_edges`, `reactome_pp_edges` |
| Drugs | drug molecule, mechanism, indication | grounding joins | `drug_protein_edges`, `drug_disease_edges` |
| Function | ontology + gene annotation | protein + hierarchy | `go_protein_edges`, `go_hierarchy_edges` |
| Phenotypes | ontology + annotations + gene links | overlap resolution + deduplication | 3 phenotype edge tables |
| Assembly | 4 recipes (§4.4) | — | `kg`, `graph_nodes`, `graph_edges`, `edge_metadata` |
| Graph build | one Kuzu build recipe per saved snapshot: current `build-graph-ZKGaRg` (2026-11-08) | — | Kuzu folder `kg_ls_v0-2-ZKGaRg` (read by Part 2). Earlier snapshots are kept as references and not rebuilt: `build-graph-Mp25kL` → `published_kg_ls-Mp25kL` (pre-R2; the Explorer serves it). The older `6bRVGs` build is gone; its saved configuration row remains |

### 4.3 Harmonization logic — the scientific content

- **Edge cleaning** — select the 8 canonical columns, drop rows with a null endpoint, deduplicate,
  drop self-loops. ⚠ **The null-drop is a silent grounding failure**: a crosswalk that fails to
  resolve discards the row with no log line. This is the largest source of quiet data loss here.
- **Reverse-all** — the graph is undirected, implemented by duplicating every edge in both
  directions with the relation string unchanged. Metadata columns carry through unchanged, since
  they describe the edge rather than an endpoint.
  > ⚠ **This destroys hierarchy direction.** Any consumer that needs parent→child must read the
  > **pre-reversal** `raw_*` table, never the assembled graph. The modelling project's split-control
  > logic depends on this, which is why `raw_disease_disease` is a shared object.
- **Vocabulary anchors for grounding joins** — the gene, disease, cross-reference, pathway, drug,
  function and phenotype term tables.
- **Phenotype↔disease reclassification** — a term that is *both* a phenotype and a disease resolves
  to the disease node; affected edges reclassify rather than duplicate. **555** overlap terms (557
  raw identifiers collapse to 555 once two multi-mapped ids are resolved). A phenotype gene link on
  such a term becomes a `disease_protein` edge, so that relation mixes Open Targets evidence with
  phenotype-annotation links that carry no Open Targets evidence type. A disease→phenotype
  annotation on such a term becomes a `disease_phenotype_disease` edge (label `phenotype
  annotation (disease term)`), **not** `disease_disease`, which is reserved for the MONDO hierarchy;
  a negated (`NOT`) annotation on such a term is dropped, because there is no negative
  disease–disease relation to carry it.
- **Disease grouping** — the published grouping map assigns grouped nodes an underscore-joined
  identifier, the group name, and a distinct node source. Deterministic; no language model needed.
- **Giant-component filter** — keep the largest connected component only.

### 4.4 Assembly — four recipes, two of them visual

| # | Recipe | Type | Does | Output |
|---|---|---|---|---|
| 1 | `stack_edge_sources` | **Stack** (12 in) | union the 12 edge tables, deduplicate, drop self-loops | `kg_stacked` — 1,475,437 |
| 2 | `compute_kg_edges` | Python (8 in) | reverse-all, attach names, ground, disease grouping, giant component | `kg_grounded` 2,856,740 + unindexed nodes 113,497 |
| 3 | `assign_node_index` | **Window** | `node_index` over an explicit sort | `graph_nodes` — 113,497 |
| 4 | `attach_node_index` | Python (5 in) | join indices back onto both endpoints; rewrite `display_relation` into readable labels | `kg` 2,856,740 · `graph_edges` 2,853,534 · `edge_metadata` 844,000 |

All four outputs match the pre-split monolithic recipe exactly. What the decomposition bought:

1. **Determinism** — step 3 replaced positional index assignment (§3).
2. **Legibility** — the twelve edge sources now converge on a visible Stack rather than inside a
   code list literal, and step 2's input count dropped from 19 to 8.

**Two things stay in Python deliberately.** The giant-component filter has no visual equivalent, and
the plugin cannot substitute because it needs a *built* graph whereas this filter *decides* which
graph exists. Step 4 stays in Python by choice: it is two joins and three column selections, already
validated, and visual recipe semantics produced silently wrong output twice during this refactor.

> **⚠ Translating working code into visual recipes is not behaviour-preserving.** Three traps
> surfaced in this one refactor, each of which yields a *plausible* graph rather than an error:
> a Stack in intersect mode would have silently emptied `edge_metadata`; a null-drop that was **dead
> code** (an earlier string cast had already turned nulls into the literal text `"nan"`) would have
> been "fixed" into a behaviour change; and casting the metadata columns to string would have made
> `"nan"` a real value and broken the metadata filter. **Anchor every migrated step on a row count
> from the previous implementation.**

**Display labels.** `display_relation` is the edge label people read in the Graph Explorer. The
per-source recipes set it to fixed text or raw source values; step 4 rewrites it once, at assembly.
`relation` is never changed, so Part 2 features and training labels are unaffected. Each rule gives
one label per link or maps one raw value to one new value, so `kg`, `graph_edges` and the built graph
keep their counts; the recipe asserts this. The per-source tables keep their raw values, because
Part 2's drug evidence reads `drug_protein_edges` and `drug_disease_edges` directly.

| Relation | Raw value | Label in the graph |
|---|---|---|
| `disease_protein` | associated with | by the Open Targets evidence types pooled over the link (`datatypes`): `germline genetic association` · `somatic mutation association` · `germline + somatic association` · `linked via phenotype annotation` (no Open Targets type: the link comes only from a reclassified phenotype gene link) |
| `disease_disease` | parent-child | unchanged: MONDO hierarchy only |
| `disease_phenotype_disease` | phenotype annotation (disease term) | unchanged: set at source by `harmonize_disease_phenotype` (§4.3) |
| `protein_protein` | ppi | `interacts with` |
| `pathway_protein` | interacts with | `member of pathway` (Reactome membership, not a physical interaction) |
| `phenotype_protein` | has phenotype | `linked to phenotype (via disease)` |
| `indication` / `drug_investigated_for` | highest clinical stage (APPROVAL, PHASE_2, …) | readable stage: `approved for`, `filed for approval for`, `in phase 1 … 3 trials for`, `IND filed for`, `preclinical for`, `investigated for (stage unknown)` |
| all others | unchanged | `drug_protein` keeps the ChEMBL action type; GO, disease–phenotype and hierarchy labels are already standard |

Same-type relations are stored in both directions with the same label, so their labels are worded
to read either way; `parent-child` cannot say which end is the parent.

### 4.5 Identifier-integrity rules

These caused real defects and are non-negotiable:

- **Read with type inference disabled and cast join keys to string explicitly.** The platform infers
  dtypes *per data chunk*, so a digit-only identifier column can come back as an integer for some
  chunks and text for others — joins then silently miss on exactly those chunks. One occurrence cost
  983,040 unresolved rows and produced no error.
- **Never build identifier strings in a visual formula.** Concatenation numerically coerces
  digit-only strings and strips leading zeros. Do it in code with inference disabled — the dataframe
  library's own sniffer strips them too.
- **After harmonizing, force the schema to all-string and build without schema auto-update**, or
  numeric-looking identifiers re-infer as integers and break the cross-source union.
- **Many-to-one grounding creates duplicate edges** — add an explicit deduplication step. One case
  produced 18,950 duplicates.
- **Multi-input visual joins are a star**, all inputs joining to input 0, so chained lookups need
  sequential joins.

## 5. Entity → source mapping

Which source is the system of record for each node and edge type, and how it grounds.

| Entity / relation | Source | Native id | Grounding route |
|---|---|---|---|
| `gene/protein` | gene vocabulary | Entrez | authoritative |
| `disease`, `disease_disease` | disease ontology | bare-integer MONDO | authoritative; cross-reference hub for everything else |
| `pathway`, `pathway_protein`, `pathway_pathway` | pathway database | stable pathway id | human-only filter; gene id → Entrez |
| `biological_process` / `molecular_function` / `cellular_component` + links + hierarchies | function ontology + gene annotation | GO id | namespace → node type; annotation file is already Entrez; negated (`NOT`) annotations dropped |
| `effect/phenotype`, `phenotype_phenotype` | phenotype ontology | HP id | direct |
| `disease_phenotype_positive` / `_negative` | phenotype annotations | Mendelian / rare-disease ids | → MONDO via the cross-reference hub; a negation qualifier splits ± |
| `disease_phenotype_disease` | phenotype annotations on terms that are also diseases (§4.3) | as above | positive annotations only; `NOT` dropped |
| `phenotype_protein` | phenotype gene links | HP id + Entrez | direct — *replaces the reference's now-paid source* |
| `protein_protein` | three interactomes | Entrez / Ensembl / internal | Ensembl→Entrez via the gene map; third source filtered to experimental or database evidence ≥ 700; merged on a canonical unordered pair |
| `disease_protein` | association table + reclassified phenotype gene links | Ensembl + disease id; HP id + Entrez | genetic-association + somatic-mutation types at score ≥ 0.3, both ids remapped; plus phenotype gene links whose term reclassifies to a disease (§4.3), which have no `datatypes` in `edge_metadata` |
| `drug` | drug molecule table | internal → cross-referenced id | drugs without a cross-reference are dropped |
| `drug_protein` | mechanism of action | internal × Ensembl | action type → display relation |
| `indication` / `drug_investigated_for` | clinical indication | internal × disease id | **split on maximum clinical stage** — approved vs everything else |

**Two source notes that shape the results:**

- **Somatic mutations were added for the oncology persona.** They surface tumour drivers
  complementary to the germline-risk genes that genetic association alone returns.
- **Inflammation coverage is a known gap.** The obesity links for the classic inflammatory genes are
  *literature*-derived evidence, which we deliberately exclude as text-mining. This is addressed on
  the modelling side via functional-similarity features, not by widening the edge set.

## 6. The graph-building webapp

The assembled node and edge tables are materialized into a **Kuzu** graph database by a plugin
recipe, written to the managed folder `published_kg_ls-Mp25kL`. An interactive explorer
webapp reads the same tables and renders the graph for exploration; it runs as a local process
rather than in a container.

Schema mapping: node id = `node_index`, label = `node_name`, grouping by `node_type` and
`node_source`; edge source = `x_index`, target = `y_index`.

**Build caveats, both learned by losing edges silently:**

- A node type whose primary key is not `node_index` has **all of its edges silently dropped**.
- **Every relation needs its own edge group with an explicit relation filter.** A missing filter
  drops that relation without an error — this happened twice.

The Kuzu folder is the **primary shared deliverable** to the modelling project, and since 2026-09-03
it is delivered one way: `published_kg_ls-Mp25kL` is merged into the modelling project's local `graph`
folder (`ytvuniN8`) by `compute_ytvuniN8`, and **both** the Graph Explorer webapp and all 10 Cypher
feature recipes read that local folder. Nothing in `DEMO_TARGET_IDENTIFICATION` reads a Kuzu folder
across the project boundary any more (PROJECT_CONTEXT §4.3).

> ⚠ **A graph-definition change gets a new snapshot, saved from the Visual Graph editor; a source
> refresh reruns the current one (2026-11-09). Older snapshots are kept as references.**
> `kg_ls_v0-2-ZKGaRg` (`build-graph-ZKGaRg`, created in R2, rerun on the R5 tables 2026-11-10) is what
> Part 2 reads through `compute_ytvuniN8`. It keeps `Mp25kL`'s configuration, including the saved queries behind the
> webapp demo narratives, and adds `disease_phenotype_disease`. `published_kg_ls-Mp25kL` (`build-graph-Mp25kL`,
> 2026-09-03) is the pre-R2 reference, and the Explorer still serves it.
> *History:* `enriched_index_freezed-6bRVGs` (`build-graph-6bRVGs`,
> 2026-08-14) is the snapshot every published feature number was **originally** derived from. It is now
> referenced by nothing. It was kept as a provenance record, but its build and folder are no longer
> in the flow (checked 2026-11-08); only its saved configuration row remains.
>
> **The two graphs were verified equivalent before the switch, and the equivalence is why the numbers
> did not have to move.** Both build recipes read the same `graph_nodes` and `graph_edges`, and the
> `nodes`, `nodes_view`, `edges` and `edges_view` blocks of `configuration.json` are byte-identical
> (SHA-256 match on all four), so all 18 relation filters are provably unchanged — the silent
> edge-dropping failure above cannot have fired. Only `cypher_queries` (2 → 8), `comment`, `id` and
> `epoch_ms` differ. The folders are nonetheless not byte-equal (`db.kz` 87.6 MB against 88.7 MB),
> which is Kuzu storage overhead from a fresh load rather than graph payload.
>
> Rebuilding all 10 feature datasets from the new folder confirmed it over 18,510,084 rows: row counts
> unchanged, and every count/min/max/sum identical across all 34 numeric columns. Five outputs were
> bit-identical; the five carrying order-dependent float aggregation (the three DWPC metapaths,
> guilt-by-association and node centrality) matched to **6 decimal places**, which is float
> accumulation order, not content. Full record and machine-readable fingerprints:
> [`GRAPH_SNAPSHOT_SWITCH_2026-09-03.md`](../../archive/GRAPH_SNAPSHOT_SWITCH_2026-09-03.md) (archived).
>
> The older `enriched_clean-gFdnaU` named in earlier revisions of this section **has since been
> deleted**; the graph project now holds these two Kuzu folders and no third.

## 7. Final graph statistics

### 7.1 Nodes and edges

| Node type | Count | Source of record |
|---|--:|---|
| disease | 27,192 | disease ontology (25,945 + 1,247 grouped) |
| biological_process | 23,974 | function ontology |
| gene/protein | 20,862 | gene vocabulary |
| effect/phenotype | 19,180 | phenotype ontology |
| molecular_function | 10,041 | function ontology |
| drug | 5,282 | drug layer via cross-reference |
| cellular_component | 4,077 | function ontology |
| pathway | 2,889 | pathway database |
| **Total** | **113,497** | |

| Relation | Count | Provenance |
|---|--:|---|
| protein_protein | 520,378 | three interactomes merged; sources retained in `edge_metadata` |
| phenotype_protein | 488,694 | phenotype gene links |
| disease_phenotype_positive | 381,404 | phenotype annotations |
| disease_protein | 378,940 | genetic association + somatic mutation @ ≥ 0.3; reclassified phenotype gene links |
| bioprocess_protein | 251,236 | function ontology + gene annotation |
| cellcomp_protein | 186,848 | as above |
| molfunc_protein | 155,542 | as above |
| disease_disease | 82,942 | disease hierarchy (MONDO only) |
| pathway_protein | 96,876 | pathway database |
| bioprocess_bioprocess | 80,972 | function hierarchy |
| drug_investigated_for | 69,658 | clinical indication, in-trial stages |
| phenotype_phenotype | 46,024 | phenotype hierarchy |
| molfunc_molfunc | 24,548 | function hierarchy |
| drug_protein | 15,918 | mechanism of action |
| indication | 9,418 | clinical indication, approved stages |
| cellcomp_cellcomp | 9,392 | function hierarchy |
| pathway_pathway | 5,810 | pathway hierarchy |
| disease_phenotype_disease | 47,738 | phenotype annotations on terms that are also diseases (§4.3) |
| disease_phenotype_negative | 1,196 | phenotype annotations, negation qualifier |
| **Total** | **2,853,534** | undirected; reverse edges included |

**Validated (rebuild of 2026-11-09):** 0 full-row duplicates, 0 self-loops, every edge has its reverse,
no unknown endpoint, no isolated node. The 862 duplicate `(relation, x_index, y_index)` triples in
`disease_protein`, which carry distinct evidence metadata, are unchanged. The Kuzu build of snapshot
`ZKGaRg` (Visual Graph 1.6.0) matches these tables on all 8 node labels and 19 relations; earlier
plugin versions silently dropped nodes whose name contains a comma, so count Kuzu after every build.
*(At the 2026-08-14 acceptance `kg` held 2,855,116 rows, 3,244 more than `graph_edges`, for the same
reason; the reference build shows the same difference.)*

### 7.2 Accepted against the frozen reference

Rebuilt from live sources and compared to the frozen reference on the structural criterion
(PROJECT_CONTEXT §4.4 / appendix). **The criterion is met.**

| Surface | Reference | This build | Delta |
|---|--:|--:|--:|
| `graph_nodes` | 113,544 | 113,391 | **−153 (−0.13%)** |
| `graph_edges` | 2,852,298 | 2,851,510 | **−788 (−0.03%)** |
| `kg` | 2,855,542 | 2,854,754 | −788 |
| `edge_metadata` | 844,166 | 844,166 | **0** |
| node type × source groups | 9 | 9 | identical inventory |
| relations | 18 | 18 | identical inventory |

**Every delta is a functional-annotation node, and nothing else moved.** Seven of nine node groups
are identical **to the row** — disease 25,906 + 1,247, gene 20,861, phenotype 19,120, drug 5,282,
pathway 2,883. On the edge side **14 of 18 relations reproduce exactly**, including all five of the
largest. The four that move are all function-ontology derived.

**And the drift is in the reference, not the rebuild** (§2.2). Alongside the graph outputs, **55 of
57 upstream intermediates match exactly**; the two that differ are stale in the reference too
(arithmetically incompatible with the table they feed). Eleven datasets in the reference's phenotype
branch are unbuilt, so for those the only comparison surface is the graph-level phenotype counts —
which match exactly.

> **⚠ The in-flow comparison harness does not work.** A recipe cannot read a dataset from another
> project unless it has been explicitly shared, so the comparison recipe fails on all 58 datasets.
> Every number above was produced **outside the flow**. Baselines are captured in
> [reference_baseline.json](../../reference_baseline.json).

### 7.3 Versus published PrimeKG

Reference: Chandak et al., *Sci Data* 2023. Both undirected.

| Node type | Published | Ours | Note |
|---|--:|--:|---|
| Biological process | 28,642 | 23,974 | close |
| Protein | 27,671 | 20,861 | no anatomy/exposure proteins |
| Disease | 17,080 | 27,153 | higher — full ontology, less grouping |
| Phenotype | 15,311 | 19,120 | higher — full ontology |
| Anatomy | 14,035 | 0 | not built |
| Molecular function | 11,169 | 10,041 | close |
| Drug | 7,957 | 5,282 | only drugs with a cross-reference |
| Cellular component | 4,176 | 4,077 | close |
| Pathway | 2,516 | 2,883 | close |
| Exposure | 818 | 0 | not built |
| **Total** | **129,375** | **113,391** | |

| Relation | Published | Ours | Note |
|---|--:|--:|---|
| anatomy–protein | 3,076,180 | 0 | not built |
| drug–drug | 2,672,628 | 0 | out of scope |
| protein–protein | 642,150 | 520,380 | **gap closed** — was 276k with one source |
| disease–phenotype (pos) | 300,634 | 380,280 | higher — full ontology |
| biological process–protein | 289,610 | 251,808 | close |
| cellular component–protein | 166,804 | 186,806 | close |
| disease–protein | 160,822 | 378,888 | higher — genetic + somatic + reclassified phenotype links |
| molecular function–protein | 139,060 | 156,246 | close |
| drug–phenotype | 129,568 | 0 | not built |
| bioprocess–bioprocess | 105,772 | 80,972 | close |
| pathway–protein | 85,292 | 97,618 | close |
| disease–disease | 64,388 | 129,606 | higher — ontology version |
| drug–disease (contraindication) | 61,350 | 0 | source not built |
| drug–protein | 51,306 | 15,918 | mechanism-of-action only vs all roles |
| phenotype–phenotype | 37,472 | 45,912 | close |
| molfunc–molfunc | 27,148 | 24,548 | close |
| drug–disease (indication) | 18,776 | 9,418 | approved stages only |
| drug–disease (investigational) | — | 69,682 | **no published equivalent** |
| cellcomp–cellcomp | 9,690 | 9,392 | close |
| phenotype–protein | 6,660 | 487,054 | **far higher** — the phenotype project's own gene file is much denser than the published graph's source |
| pathway–pathway | 5,070 | 5,798 | close |
| disease–phenotype (neg) | 2,386 | 1,184 | lower |
| **Total** | **8,100,498** | **2,851,510** | |

**Reading this:** every layer we build is in the right ballpark or intentionally different. The
remaining gap is almost entirely **unbuilt layers** (anatomy ~3.1M, drug–drug 2.7M, side-effect,
exposure), not under-coverage of what we do build.

---

## Appendix — decision log

| Date | Decision |
|---|---|
| 2026-06 | **Hybrid ETL** — Python extracts to native identifiers only, visual recipes harmonize. Grounding failures are the biggest silent-loss risk, and visual joins make them countable. |
| 2026-06 | **Conform to the published schema exactly**, so counts are directly comparable to the reference graph. |
| 2026-06 | **Assembly stays in Python** — giant-component, index assignment and name attachment judged not expressible visually. *(Partly reversed 2026-08-14: stacking and index assignment turned out to be expressible; the giant component still is not.)* |
| 2026-06 | **Licensed clinical terminology retired** from the flow — the ontology's own cross-references cover all grounding once both sources that needed it were replaced. |
| 2026-07 | **Interactome = one source** (~276k edges) for the first build. |
| 2026-08-05 | **Add functional annotation and the phenotype layer.** Phenotype–gene edges sourced from the phenotype project's own gene file, since the reference's source went paid and Open Targets has no equivalent. |
| 2026-08-06 | **Phenotype↔disease overlap harmonized** — 555 terms that are both resolve to the disease node; affected edges reclassify rather than duplicate. |
| 2026-08-06 | **Interactome augmented to three sources as ONE relation** with provenance retained, not as separate relations — this closes the coverage gap (276k → 520k) while leaving the downstream feature set unchanged. |
| 2026-08-06 | **`edge_metadata` side table introduced** so evidence provenance survives assembly without polluting the schema-conformant tables. |
| 2026-08-05 | **Clinical indications split on clinical stage** into approved vs investigational, rather than flattened — only ~13% are approvals, so flattening would badly overstate approved evidence. |
| 2026-08-09 | **Storage moved to S3 parquet** to enable the distributed engine; all new datasets go there. |
| 2026-08-13 | **Graph construction moved into its own project**, rebuilt from source. Each source recipe gained a provenance header recording its version and freeze instructions. |
| 2026-08-13 | **Sources stay live rather than pinned.** Pinning all of them would have ended the pipeline's ability to bootstrap itself from public URLs, in exchange for a byte-exact diff. Freezing becomes a deliberate act when a release must be reproduced. |
| 2026-08-14 | **Zones grouped by biological domain, not pipeline phase** (§4.1). **Rejected:** a phase-based scheme, which puts every source in one box and stops the flow answering "where does the disease data come from?". |
| 2026-08-14 | **Assembly decomposed into 4 recipes**, two visual (§4.4). All outputs reproduce the monolith exactly. **`node_index` is now deterministic** — verified by two independent builds producing byte-identical indices across 113,391 nodes. **Kept in Python:** the giant-component filter (no visual equivalent) and the final index joins (already validated; visual semantics had produced silently wrong output twice). |
| 2026-08-14 | **Accepted the 1-based index origin** rather than patching it to match the published 0-based schema (§3). It is internally consistent, and the modelling project must re-derive its integers at migration regardless. |
| 2026-08-14 | **Rule: anchor every migrated step on a row count from the previous implementation.** Literal translation of code into visual recipes is not behaviour-preserving — three traps in one refactor, each producing a plausible graph rather than an error. |
| 2026-08-14 | **Reconstruction accepted** (§7.2). 7 of 9 node groups and 14 of 18 relations reproduce **to the row**; total delta −0.03% of edges, all function-ontology. Root cause traced to the *reference* being stale, not the rebuild. |
| 2026-08-17 | **The graph-building webapp and Kuzu snapshot belong to this project**, and the snapshot is shared out as the modelling project's primary input. |
| 2026-11-06 | **Relation corrections and readable labels.** Disease→phenotype annotations on terms that are also diseases moved out of `disease_disease` into a new `disease_phenotype_disease` relation (they were 36% of `disease_disease` links, labelled `parent-child`); negated GO and reclassified phenotype annotations dropped; `display_relation` rewritten into readable labels at assembly. Edges stay stored in both directions. **Rejected:** dropping the reclassified links (loses information) and one-way storage (5 of 14 champion features assume two-way). *Built 2026-11-08 (workplan R2): the relation move, the `NOT` drop and the labels; §7.1 reflects it. Before it, `disease_disease` held 129,606 rows and the graph 2,851,510. The negated-GO drop waits for the source rebuild (R5).* |
| 2026-11-06 | **Pin every source at the next pull** (graph-revision D9), superseding the 2026-08-13 choice to keep sources live: a rebuild must be reproducible, and the August GO and gene-map drift showed what "latest" costs. **Extraction moves to its own project, `DEMO_KG_PREP`** (D6), shared into this project through sync copies so the graph project's dataset names stay unchanged (D8). *Built 2026-11-08 (R3, R4).* |
| 2026-11-09 | **A source refresh reruns the current snapshot; a graph-definition change gets a new one.** A saved Visual Graph snapshot holds only the definition, and each build replaces its `built-graphs/<id>/` folder, so `build-graph-ZKGaRg` was rerun on the refreshed tables. `Mp25kL` is kept and never rebuilt. |
| 2026-11-10 | **Rebuilt from the pinned pull** (R5): 113,497 nodes and 2,853,534 edges, every count change traced to a source release, the negated-GO drop applied. The Kuzu build waited for Visual Graph 1.6.0, which fixes the comma-node drop found during R5; it then matched the tables exactly. A rebuild renumbers `node_index` (76,786 nodes this time), so the modelling project rebuilt its copies, features and model together (R6). |

## References

- PrimeKG repository & build guide: https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg
- PrimeKG paper: Chandak et al., *Sci Data* 2023
- Open Targets: https://platform-docs.opentargets.org/getting-started
- Unbiased interactome — Luck et al., *Nature* 2020
- Functional-association network — Szklarczyk et al., *NAR* 2023
