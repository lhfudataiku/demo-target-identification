# Graph Building — `DEMO_KG_LS`

> Technical documentation for the **data pipeline and graph-building webapp**: what goes in, how it
> is harmonized, the schema it conforms to, and what comes out.
>
> Companion documents: **[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)** (why / who / how the two
> projects fit) · **[TARGET_PRIORITIZER.md](TARGET_PRIORITIZER.md)** (the modelling project that
> consumes this graph) · **[DSS_CHEATSHEET.md](DSS_CHEATSHEET.md)** (platform behaviours).
>
> **Status: complete.** 113,391 nodes / 2,851,510 edges / 18 relations, rebuilt from source and
> accepted against the frozen reference (§7). Decisions are logged in the **appendix**.

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
| **HPO** (`hp.obo`, `phenotype.hpoa`, `genes_to_phenotype`) | phenotype layer | `effect/phenotype` (19,120) | `disease_phenotype_positive`/`_negative`, `phenotype_protein`, `phenotype_phenotype` |

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
freeze it. **Only 3 of 11 sources are pinned**; the rest resolve to "latest".

| Source | Version at build | Pinned? | How to freeze |
|---|---|---|---|
| Open Targets | **26.06** | **yes**, in the path | — |
| STRING | **v12.0** | **yes**, in the path | — |
| Published disease-grouping map | pinned id, but **returns 0 bytes** | yes, and broken | snapshot — done (§3.2) |
| MONDO | `releases/2026-08-04` | no | dated permanent URL, **verified working** |
| HPO | `hp/releases/2026-06-23` | no | dated permanent URL, **verified working** |
| GO | `releases/2026-07-26` | no | **no working archive** — snapshot the file |
| Reactome | release 97 | no — path is literally `current/` | per-release archive exists; verify before relying on it |
| HGNC | live query, retrieved 2026-08-13 | no | no archive — snapshot |
| NCBI gene↔Ensembl map | rewritten continuously | no | **already drifted** — see below |
| HuRI interactome | unversioned URL | no | snapshot |
| Menche interactome | uploaded file | local | already frozen |

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

**Fix in place:** the recipe reads a 6,392-row snapshot from the `raw_files` managed folder via a
download stream, with the recipe pinned to run on the DSS engine. Never delete this recipe; if the
snapshot is lost, the graph cannot be rebuilt as specified.

## 4. Data pipeline

### 4.1 Flow zones — grouped by biological domain

Four biological domains, each split into an extract zone and a harmonisation zone, plus assembly.

| Zone | Items | Contents |
|---|--:|---|
| `Gene & interactome (HGNC, PPI)` | 7 | gene vocabulary + three interactome sources and their merge |
| `Genes & interactome harmonisation` | 6 | → `ppi_edges` |
| `Disease & phenotypes (MONDO, HPO)` | 12 | disease backbone + cross-reference hub; phenotype ontology, annotations, gene links |
| `Diseases & phenotypes harmonisation` | 28 | phenotype↔disease overlap resolution, grounding, deduplication |
| `Function & pathways (GO, Reactome)` | 16 | functional annotation and pathways — extraction *and* harmonisation |
| `Drugs & gene-disease (Open Targets)` | 9 | one extraction serving both the drug layer and gene–disease |
| `Drugs & gene-disease harmonisation` | 14 | → drug and gene–disease edges |
| `Graph build` | 24 | the 4 assembly recipes, their outputs, the Kuzu build, webapp plumbing |

**Why domains rather than pipeline phases.** A phase-based scheme (all sources → all harmonisation →
all relationships → build) was drafted and rejected: it puts every source in one large box, so the
flow stops answering the question a reader actually has, which is *"where does the disease data come
from?"* Grouping by domain keeps each biological story traceable end to end, and pairing each domain
with its own harmonisation zone keeps the extract/harmonise seam visible.

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
| Graph build | Kuzu build recipe | — | Kuzu folder `enriched_index_freezed-6bRVGs` |

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
  raw identifiers collapse to 555 once two multi-mapped ids are resolved).
- **Disease grouping** — the published grouping map assigns grouped nodes an underscore-joined
  identifier, the group name, and a distinct node source. Deterministic; no language model needed.
- **Giant-component filter** — keep the largest connected component only.

### 4.4 Assembly — four recipes, two of them visual

| # | Recipe | Type | Does | Output |
|---|---|---|---|---|
| 1 | `stack_edge_sources` | **Stack** (12 in) | union the 12 edge tables, deduplicate, drop self-loops | `kg_stacked` — 1,474,753 |
| 2 | `compute_kg_edges` | Python (8 in) | reverse-all, attach names, ground, disease grouping, giant component | `kg_grounded` 2,854,754 + unindexed nodes 113,391 |
| 3 | `assign_node_index` | **Window** | `node_index` over an explicit sort | `graph_nodes` — 113,391 |
| 4 | `attach_node_index` | Python (3 in) | join indices back onto both endpoints | `kg` 2,854,754 · `graph_edges` 2,851,510 · `edge_metadata` 844,166 |

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
| `biological_process` / `molecular_function` / `cellular_component` + links + hierarchies | function ontology + gene annotation | GO id | namespace → node type; annotation file is already Entrez |
| `effect/phenotype`, `phenotype_phenotype` | phenotype ontology | HP id | direct |
| `disease_phenotype_positive` / `_negative` | phenotype annotations | Mendelian / rare-disease ids | → MONDO via the cross-reference hub; a negation qualifier splits ± |
| `phenotype_protein` | phenotype gene links | HP id + Entrez | direct — *replaces the reference's now-paid source* |
| `protein_protein` | three interactomes | Entrez / Ensembl / internal | Ensembl→Entrez via the gene map; third source filtered to experimental or database evidence ≥ 700; merged on a canonical unordered pair |
| `disease_protein` | association table | Ensembl + disease id | genetic-association + somatic-mutation types at score ≥ 0.3; both ids remapped |
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
recipe, written to the managed folder `enriched_index_freezed-6bRVGs`. An interactive explorer
webapp reads the same tables and renders the graph for exploration; it runs as a local process
rather than in a container.

Schema mapping: node id = `node_index`, label = `node_name`, grouping by `node_type` and
`node_source`; edge source = `x_index`, target = `y_index`.

**Build caveats, both learned by losing edges silently:**

- A node type whose primary key is not `node_index` has **all of its edges silently dropped**.
- **Every relation needs its own edge group with an explicit relation filter.** A missing filter
  drops that relation without an error — this happened twice.

The Kuzu folder is the **primary shared deliverable** to the modelling project: all of its Cypher
feature recipes read it (PROJECT_CONTEXT §4.3).

> ⚠ **Two Kuzu snapshots exist.** `enriched_index_freezed-6bRVGs` is current, built on the
> deterministic index. An older `enriched_clean-gFdnaU` remains and should be retired so there is no
> ambiguity about which graph the features were derived from.

## 7. Final graph statistics

### 7.1 Nodes and edges

| Node type | Count | Source of record |
|---|--:|---|
| disease | 27,153 | disease ontology (25,906 + 1,247 grouped) |
| biological_process | 23,974 | function ontology |
| gene/protein | 20,861 | gene vocabulary |
| effect/phenotype | 19,120 | phenotype ontology |
| molecular_function | 10,041 | function ontology |
| drug | 5,282 | drug layer via cross-reference |
| cellular_component | 4,077 | function ontology |
| pathway | 2,883 | pathway database |
| **Total** | **113,391** | |

| Relation | Count | Provenance |
|---|--:|---|
| protein_protein | 520,380 | three interactomes merged; sources retained in `edge_metadata` |
| phenotype_protein | 487,054 | phenotype gene links |
| disease_phenotype_positive | 380,280 | phenotype annotations |
| disease_protein | 378,888 | genetic association + somatic mutation @ ≥ 0.3 |
| bioprocess_protein | 251,808 | function ontology + gene annotation |
| cellcomp_protein | 186,806 | as above |
| molfunc_protein | 156,246 | as above |
| disease_disease | 129,606 | disease hierarchy |
| pathway_protein | 97,618 | pathway database |
| bioprocess_bioprocess | 80,972 | function hierarchy |
| drug_investigated_for | 69,682 | clinical indication, in-trial stages |
| phenotype_phenotype | 45,912 | phenotype hierarchy |
| molfunc_molfunc | 24,548 | function hierarchy |
| drug_protein | 15,918 | mechanism of action |
| indication | 9,418 | clinical indication, approved stages |
| cellcomp_cellcomp | 9,392 | function hierarchy |
| pathway_pathway | 5,798 | pathway hierarchy |
| disease_phenotype_negative | 1,184 | phenotype annotations, negation qualifier |
| **Total** | **2,851,510** | undirected; reverse edges included |

**Validated:** 0 duplicate rows, 0 self-loops, 0 dangling endpoints, reverse-all symmetry holds on
every sampled relation. `kg` holds 2,854,754 rows — 3,244 more than `graph_edges`, which are
duplicate `(relation, x_index, y_index)` triples in `disease_protein` carrying distinct evidence
metadata. That difference is identical in the reference build.

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
> [reference_baseline.json](reference_baseline.json).

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
| disease–protein | 160,822 | 378,888 | higher — genetic + somatic |
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

## References

- PrimeKG repository & build guide: https://github.com/mims-harvard/PrimeKG#building-an-updated-primekg
- PrimeKG paper: Chandak et al., *Sci Data* 2023
- Open Targets: https://platform-docs.opentargets.org/getting-started
- Unbiased interactome — Luck et al., *Nature* 2020
- Functional-association network — Szklarczyk et al., *NAR* 2023
