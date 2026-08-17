# Dataiku DSS — platform behaviours & CLI patterns

> Findings from building a large multi-project flow (≈160 recipes, 2.9M-edge graph, Visual ML,
> plugin recipes, cross-project sharing). **Written generically** — nothing here depends on this
> POC's domain, so it should transfer to any DSS project.
>
> Ordered by how expensive the lesson was. The first section is the one worth reading twice: those
> failures produce **plausible output rather than an error**.

## 1. Silent-wrong-answer class

These do not fail. They produce a result that looks right and is wrong.

### Dataframe reads infer dtypes *per chunk*, not per column

`get_dataframe()` reads in fixed-size chunks (65,536 rows) and infers each column's type **within
each chunk independently**. A digit-only identifier column comes back as an integer for chunks whose
values happened to all be numeric, and as text for the rest. Joins then miss on exactly those chunks
and report nothing.

> One occurrence silently dropped **983,040 rows = 15 × 65,536** — the chunk-size multiple is the
> tell. If an unresolved-row count is a clean multiple of 65,536, this is why.

**Always:** read with pandas inference disabled *and* cast every join key to string explicitly.
Then assert on unresolved rows rather than trusting the join.

### Visual recipes accept a payload and silently ignore parts of it

A Group recipe accepted a definition containing a pre-filter and a computed column, wrote and
validated cleanly, and **ignored both** — collapsing 555 output rows to 1 (an empty key with a global
minimum). Unknown or misplaced payload keys are treated as no-ops, not errors.

**Rule: verify a visual recipe by its output row count, never by the definition being accepted.**

### A join can do renames, selection and ordering — but not the way the payload suggests

A join recipe can absorb a whole tail of alternating join/prepare steps, which is worth knowing
because those tails accumulate. Three non-obvious rules, each learned by a build that succeeded and
produced the wrong columns:

| Goal | Works | Does **not** work |
|---|---|---|
| rename an output column | a `computedColumns` entry on the input (GREL passthrough of the source column) | `"rename"` inside `selectedColumns` — it round-trips in the payload and is **ignored at execution** |
| drop columns | per-input `MANUAL` `selectedColumns` | top-level `selectedColumns` — it sets *order* and restricts nothing |
| set output column order | top-level `selectedColumns` | — but order cannot **interleave across inputs**; each input's columns are emitted as a block |

**And the same dataset cannot be joined twice in one recipe.** Listing it twice is accepted by
`set-definition` and round-trips cleanly; validation then rejects it with *"Dataset appears several
times in inputs"*. So a fan-out to N lookups collapses into one recipe only if the N lookups are N
distinct datasets.

> The pattern across all four: **the payload accepting a field is not evidence the engine honours it.**
> Verify by building and diffing the output columns, not by reading the definition back.

### Creating a managed dataset by hand needs a path, not just a flag

`dataset create` makes a **non-managed** dataset, which then fails any build with *"Clearing external
(i.e., non-managed) datasets … is forbidden"*. Setting `managed: true` alone then fails with
*"Placing a managed dataset at the root of a connection is not permitted"* — a managed dataset also
needs a `params.path` (and metastore name). Copy both from a sibling managed dataset in the same
project. Easier still: let `recipe create --output-ds NEW` create it for you.

Related: **`dataset set-definition` takes the FULL definition, not a partial merge** (unlike
`recipe set-definition`, which shallow-merges top-level keys). Passing one key returns
*"Required field 'projectKey' is missing"*. Read it, modify it, send all of it.

### A join's MANUAL column selection can select nothing

A join input set to manual column selection, with a valid `selectedColumns` list of columns that
demonstrably exist in that input's schema, produced **no columns at all** — the recipe status said
*"No column from '<dataset>' is selected"* while the payload plainly listed four. The identical
encoding works on another join in the same project. Switching that input to automatic
(non-conflicting) selection fixed it immediately.

**Don't debug the payload — check the recipe status message and switch selection mode.** And note the
failure shape: the build *succeeds*, the output is just missing columns.

### A new output column needs a schema-updating build, twice

Adding a column to a visual recipe is a two-part change: the payload, and the output dataset's
schema. A normal build writes the new column into the *old* schema and silently drops it — the job
succeeds and the column is simply absent. Build with schema auto-update.

Then note the follow-on: a schema change **clears downstream datasets**, so the next recipe fails with
*"Error while connecting to dataset X"* / *"dataset is not ready"*. That is not a new bug; rebuild the
chain in dependency order, each step with schema update.

### An auto-selected engine can fail where the default succeeds

Enabling partitioning on a window recipe changed the auto-selected engine to Spark, which then died in
Hadoop delegation-token setup — surfacing as
`NullPointerException: Cannot invoke "String.toCharArray()" because "string" is null`, a stack trace
with no connection to the recipe's configuration.

Two things worth knowing: the fix is `engineType` in the recipe **payload** (setting it in
`params` is silently ignored and reads back as `{}`), and a payload NPE deep in an engine's
initialisation is usually engine selection, not the payload you just wrote. If a recipe worked before
a config change and now throws inside framework code, force the DSS engine first and re-test.

### Stack recipes drop columns that aren't on every input

A Stack in *intersect* mode keeps only columns common to all inputs. With columns present on 2 of 12
inputs, intersect mode silently emptied a downstream provenance table. Use **union** mode whenever
inputs have differing schemas.

### Imputation runs *before* per-feature handling in Visual ML

The platform fills missing values before per-feature preprocessing sees the data. So a
"replace by a 0/1 flag indicating presence" handler, or custom preprocessing, **cannot observe
nullness** — every presence flag becomes 1, all inputs become constant, and the model emits a single
value for every row.

Proven, not inferred: a custom preprocessor written to raise if it ever saw a null was attached to a
32%-null feature and never raised.

**To test whether missingness carries signal**, materialize explicit `<feature>_isnull` columns
upstream, or answer the question in a code recipe. Also note the platform **auto-rejects
high-null features at guess time**, independently of the handling you chose.

### Visual ML's per-feature guesses are inconsistent between deploys

Deploying two models from the same lab on identical data produced different rescaling and
missing-value handling — one came back with 9 of 12 features on non-default settings, the next
mostly correct. **Audit the per-feature configuration after every deploy**, and set an explicit
project-wide standard rather than relying on the guess.

Related: **a lab retains whatever per-feature configuration an experiment left behind.** A lab left
on an experimental handling mode will silently apply it to the next model trained from it.

### Filter expressions can be ignored when the UI mode is inconsistent

A visual filter whose UI mode is set to rule-based while carrying a half-configured condition block
silently ignores the expression shown on screen. Set the mode explicitly to custom. One instance
caused a 2.2× row-count discrepancy that survived repeated clean rebuilds.

### Renaming a dataset updates code call sites but not string collections

Renaming propagates into `Dataset("name")` call sites, but **not** into names held in variables, list
literals, or dictionaries. A rename left one recipe's model list pointing at four deleted datasets
while six sibling recipes silently followed the rename.

**Grep the codebase for the old name after any rename.** (Renames *do* preserve managed data —
verified by identical row counts before and after — and the platform annotates the edited code with
an audit comment.)

### A plausible row count is not evidence a rebuild happened

This trap recurred **three times**, most expensively as an apparent metric disagreement: two
datasets computing the same statistic from the same input with the same formula returned different
values. The cause was neither implementation — one had simply been built *before* its input was
refreshed, so it held a previous model's numbers.

**Verify a rebuild by job history, not row count.** Two recipes disagreeing and one recipe running on
stale input look identical from the outside and have completely different fixes. Diagnose with the
job list before diffing code.

### Rules that key on integer *order* are not migration-safe

Remapping an identifier's literal values is only half the job. Any rule that **ranks, mods, or
minimises** on that identifier changes behaviour when the identifiers are reassigned, even though the
mapping itself is perfectly correct.

Three instances surfaced in one migration, all with the same root cause and only one anticipated:

| Rule | Depends on | Effect of renumbering |
|---|---|---|
| assign a split by `mod(id, 10)` | the integer's residue | 58.8% of records changed split |
| pick the nearest ancestor, ties on lowest id | ordering among ties | 0.3% of records changed group |
| pick among multiple parents by lowest id | ordering among parents | whole subtrees regrouped, which silently broke a downstream diagnostic that selected on the old grouping |

None is a defect — the tie was arbitrary either way — but each moves results. **Audit every rule that
consumes the identifier as a number, not just the places where it appears as a literal.** Where the
outcome matters, force it explicitly rather than relying on the arbitrary rule to land the right way.

### Two levels in one output table will fake a metric disagreement

A recipe that emits both a fine-grained and an aggregated level into one dataset, distinguished by a
`level` column, is convenient — and a trap for anything that joins to it. Joining without filtering
mixes the levels and produces a large, entirely artificial discrepancy. Filter on the level column
before comparing to any other implementation.

### An orchestration failure looks like a recipe failure

On a containerised install, a scheduler or pod-creation error surfaces in the job list identically to
a recipe error. The log distinguishes them: orchestration errors mention pods, `kubectl`, or quota,
and carry no user-code traceback. **Those are worth a plain retry, not a debugging session** — one
batch here failed on pod creation and the identical rerun succeeded.

### Recursive build types reach further than you think

A forced recursive build on a downstream dataset walks the *entire* upstream — including into a zone
you consider frozen. In a single-project flow this let a downstream experiment trigger a rebuild of
the foundational data.

**Build one named target at a time**, or separate volatile and stable work into different projects.
This behaviour was the primary motivation for splitting one flow into two projects.

## 2. Cross-project sharing

- **A recipe cannot read a dataset from another project unless it has been explicitly shared**, even
  with full permissions. Reading `OTHER_PROJECT.dataset` otherwise raises *"cannot be used: declare
  it as input or output of your recipe"*.
- Sharing is a setting on the **source** project (`exposedObjects`), listing per-object rules that
  name the target project. **The CLI has no verb for it**, and it is not exposed via project
  inspect/permissions. Two routes: the UI's *Share to another project*, or the Python API
  (`project.get_settings()` → `exposedObjects` → `save()`), which can be driven from a scenario step
  without touching the flow.
- **Repointing a consumer takes two edits, and one alone is not enough.** The recipe *definition*
  governs the flow edge and build dependency; the recipe *code* governs what is read at runtime.
  Patch only the definition and you get a recipe that looks correctly wired and fails on execution.
- Visual recipe payloads are **index-based, not name-based** — join conditions reference input
  positions, so repointing an input does not invalidate them. Dataset names appearing in a payload
  are display labels only. Verify rather than assume.
- **Plugin recipes reference inputs by role**, with configuration held separately; repointing is
  usually just the input reference.
- `dku flow move` **cannot resolve a foreign object**, and zone listings **count only local items**,
  so a zone holding nothing but shared objects reports as empty. Foreign objects are placed via the
  Python API's shared-item list, or by dragging in the UI.

## 3. Managed folders

- **Container-run recipes cannot access a folder path.** `Folder.get_path()` fails with *"Python
  process is running remotely, direct access to folder is not possible"*. Two fixes, both valid: use
  a download stream, which works locally *and* remotely, or set the recipe's container mode to none
  so it runs on the DSS engine.
- Folder paths are **project-key namespaced**, so duplicating a project gives the copy its own
  physical storage even though the folder id is preserved. Verify the path template before deleting
  a folder in a duplicated project.
- **Deleting a folder does not delete the bytes** — the platform reports *"File contents were NOT
  deleted from underlying storage"*. Deleted folders leave orphaned data on the connection.

## 4. Schemas and identifiers

- **Digit-only string identifiers re-infer as integers** on build, breaking cross-source unions.
  After a harmonization step, force the schema to all-string and build **without** schema
  auto-update.
- **Visual formula string concatenation numerically coerces** digit-only values and strips leading
  zeros. Build identifier strings in code with inference disabled — the dataframe library's own
  sniffer strips them too.
- **Many-to-one grounding joins create duplicate rows.** Add an explicit deduplication step; do not
  assume the join is one-to-one.
- **Multi-input visual joins are a star topology** — every input joins to input 0. Chained lookups
  (A→B→C) need sequential join recipes.
- **Manually created datasets fail builds** with *"Clearing external datasets is forbidden"* unless
  marked as managed.
- A **Window** recipe's row-number output column is named `rownumber`. A column-rename override keyed
  on any other spelling is a silent no-op. Row numbering starts at **1**, whereas a dataframe index
  reset starts at 0 — an off-by-one when migrating between the two.

## 5. CLI patterns

### Flags and shapes

- **Get exact flags from `--help`**, which returns machine-readable JSON per command. Never guess;
  flag names are not consistent across nouns.
- **Repeated `--output-ds` flags do not accumulate** — only the last registers. Create a
  multi-output recipe with one output, then patch its definition JSON.
- **Move/assign commands take one item per call.** A comma-separated list silently becomes one
  invalid name.
- **Destructive commands are guarded** and require an explicit confirmation flag per command.
- **Deleting a dataset cascade-deletes the recipes that consume it**, with no prompt. Re-list
  recipes after any dataset delete. When decommissioning a subgraph, **delete recipes first, then
  datasets** — the reverse order cascades into recipes you meant to keep.
- **Descriptions are not settable via the CLI** for recipes or datasets (merge flags leave the field
  null). A flow **zone** description *is* settable, but only in the UI. Flow-level caveats therefore
  have to live in version-controlled markdown.
- **Project import advertises a target-key argument but wires no flag for it**, so a bare import
  recreates the *original* key and can overwrite an existing project. To re-key, patch the key in the
  archive manifest and re-zip.

### Composition that saves round-trips

```bash
# definition round-trip: read as JSON, patch one key, write back
dku --format json recipe get-definition R -P PROJ | jq '...' | dku recipe set-definition R -d - -P PROJ

# bulk operation driven by a list
dku --format ids dataset list -P PROJ | while read ds; do ... ; done

# pull data out for local analysis when in-flow comparison is not possible
dku dataset download DS ./out.csv -P PROJ
```

- **Definition updates shallow-merge at the top level**, so passing one top-level key replaces that
  key entirely and preserves its siblings. Use a deep merge to patch a nested field.
- **`get-definition` can be lossy** for some object types (scenario steps, app sections). Round-trip
  the full payload and re-read to diff; never reconstruct from memory.
- **Arbitrary Python without polluting the flow:** create a step-based scenario with an inline Python
  step, run it, read the run log, delete the scenario. This is the escape hatch for anything the CLI
  does not cover — project settings, cross-project exposure, flow-zone membership. **Print
  structured, greppable lines** (`KEY|field|field`), because the run log interleaves platform output.
- **Read back from a fresh handle after saving settings.** A successful save is not proof the change
  persisted in the shape you intended.
- Prefer the **highest-level capability that fits**: visual recipe → visual ML → scenario → SQL →
  code recipe. Code recipes are the last rung, not the first.

## 6. Verification habits that caught real defects

1. **Anchor every migration step on a row count from the previous implementation.** Literal
   translation between code and visual recipes is not behaviour-preserving.
2. **Check what the dumbest possible predictor scores** before treating a metric as a target. A
   benchmark a lookup table wins is measuring the lookup, not the model.
3. **Assert on join resolution**, not just on row count — a join can preserve the row count and
   resolve nothing.
4. **Before diagnosing a metric disagreement, compare build timestamps.**
5. **Exit code 0 is not success, and an empty result is data, not success.** Check row counts, schema
   and sample values.
6. **When two implementations of a statistic agree to ~1e-4, that validates the metric.** Residual
   differences are usually tie handling in ranking — different rank functions split ties differently.
