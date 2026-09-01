<script setup lang="ts">
  /**
   * Act 1 — the evidence base.
   *
   * "What went in?" — public biomedical knowledge, assembled, with provenance
   * on every node and edge.
   *
   * Two things this act must NOT do:
   *  - claim quality. Faithful assembly is a lineage property, not an accuracy
   *    one; whether the ranking is any good is act 2's job.
   *  - imply discovery. The opening card states the reconstruction claim and
   *    the five things we are explicitly not claiming, because that framing is
   *    what keeps the rest of the demo honest.
   */
  import { computed, onMounted, ref } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActDonut from '@/components/act/ActDonut.vue'
  import ActGraph from '@/components/act/ActGraph.vue'
  import ActInfo from '@/components/act/ActInfo.vue'
  import ActTabs from '@/components/act/ActTabs.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Database, GitBranch, Layers, FileText, Search, Loader2, Play } from 'lucide-vue-next'

  defineOptions({ name: 'EvidenceView' })

  interface Bar { label: string; count: number }
  interface Payload {
    node_types: Bar[]; relations: Bar[]; node_sources: Bar[]
    ppi_provenance: Bar[]; label_evidence: Bar[]
    totals: Record<string, number>
  }

  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)

  /* ── Explore the graph ──────────────────────────────────────────────────────
     The search box speaks to the visual-graph plugin's own agent tool, which
     accepts EITHER English or literal Cypher on the same key. The starters are
     pinned Cypher and deterministic; anything typed goes through the LLM. That
     difference is surfaced rather than hidden, because the NL path can and does
     return nothing: edges are stored protein->disease, so a generated
     `(disease)-[:disease_protein]->(protein)` matches zero rows. */
  interface Starter { id: string; label: string; shows: string; measured: string; query: string }
  interface ResultTable {
    columns: string[]; rows: (string | number | null)[][]
    n_rows: number; truncated: boolean
  }
  interface GraphResult {
    mode: 'graph' | 'table' | 'empty'
    nodes: { id: string; label: string; group_name: string }[]
    edges: { id: string; src: string; dst: string; group_name: string }[]
    n_nodes: number; n_edges: number
    truncated: boolean; dropped_nodes?: number
    empty: boolean
    /* The agent's own prose. New with the agent route -- a bare tool call
       returned records and nothing else. It leads the result, because it is the
       part that says what the picture means and what it does not claim. */
    answer: string | null
    /* The Cypher that ran. For /cypher it is what was typed; for /search it is
       recovered from the agent's trace. Either way it seeds the editable panel,
       so an LLM-written query can be corrected and re-run without the LLM. */
    cypher: string | null
    table: ResultTable | null
  }

  const starters = ref<Starter[]>([])
  const graph = ref<GraphResult | null>(null)
  const graphBusy = ref(false)
  const graphError = ref<string | null>(null)
  const graphQuery = ref('')
  const ranStarter = ref<string | null>(null)
  const cypherDraft = ref('')
  const cypherOpen = ref(false)
  /* Graph or table. A subgraph answer offers both -- the canvas for shape, the
     edge list for exact reading -- the way the graph explorer pairs them. An
     aggregation has no graph to show, so the toggle is not offered. */
  const graphTab = ref<'graph' | 'table'>('graph')

  /* Two endpoints, one shape back. `/cypher` executes literal Cypher with no LLM
     in the path — deterministic, ~2.5s, free — and is what the starters and the
     Cypher panel use. `/search` goes through the agent and is only for questions
     asked in English. */
  async function runGraph(query: string, opts: { starterId?: string | null; literal?: boolean } = {}) {
    if (!query.trim() || graphBusy.value) return
    graphBusy.value = true
    graphError.value = null
    ranStarter.value = opts.starterId ?? null
    try {
      const res = await fetch(apiUrl(opts.literal ? '/api/graph/cypher' : '/api/graph/search'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      if (!res.ok) {
        const detail = await res.json().catch(() => null)
        throw new Error(detail?.detail ?? `HTTP ${res.status}`)
      }
      graph.value = await res.json()
      cypherDraft.value = graph.value?.cypher ?? ''
      graphTab.value = graph.value?.mode === 'table' ? 'table' : 'graph'
    } catch (e) {
      graphError.value = e instanceof Error ? e.message : String(e)
      graph.value = null
    } finally {
      graphBusy.value = false
    }
  }

  function runStarter(s: Starter) {
    graphQuery.value = ''
    // Starters are pinned Cypher: straight to the engine, no LLM.
    runGraph(s.query, { starterId: s.id, literal: true })
  }

  const NOT_CLAIMING: [string, string][] = [
    ['That we discover novel targets',
     'The model ranks not-yet-annotated genes above chance. It is not what we are asking you to believe today.'],
    ['That this beats your in-house method',
     'We have not seen your method. This is a reconstruction test on public data.'],
    ['Any safety or toxicity assessment',
     'We have none. The flags we carry are public annotations — act 4 shows why they are not a filter.'],
    ['That the ranking is a research plan',
     'It is a starting list you filter on your own thresholds.'],
    ['Domain expertise in your therapeutic area',
     'You have that. We built the machine that makes your expertise testable.'],
  ]

  const fmt = (n: number) => n.toLocaleString()

  // v3 colours these two cards by GROUP, not by a cycle:
  //   PPI provenance  — corroborated by 2+ interactomes vs a single source
  //   node sources    — the six external vocabularies vs the one we derived
  const ppiRows = computed(() => (data.value?.ppi_provenance ?? []).map((r) => ({
    ...r, colour: r.label.includes('+') ? 'var(--chart-2)' : 'var(--chart-1)',
  })))
  const sourceRows = computed(() => (data.value?.node_sources ?? []).map((r) => ({
    ...r, colour: /grouped/i.test(r.label) ? 'var(--muted-foreground)' : 'var(--chart-2)',
  })))

  onMounted(async () => {
    try {
      const res = await fetch(apiUrl('/api/evidence'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load the evidence base: ${e instanceof Error ? e.message : String(e)}`
    }

    // Starters are cheap metadata; the graph itself is not fetched until asked.
    // Each tool call costs ~2-3s, so nothing runs on page load.
    try {
      const res = await fetch(apiUrl('/api/graph/defaults'))
      if (res.ok) starters.value = (await res.json()).defaults
    } catch {
      /* the search box still works without starters */
    }
  })

  const totals = computed(() => data.value?.totals)
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 1 of 4 · The evidence base
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">What went in?</h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Public biomedical knowledge, assembled from six external sources and accepted against a
        frozen reference. No model yet — this act is about what the machine can see, and about the
        fact that every node and edge can name where it came from.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <ActCard span="col-span-12" title="The graph, in four numbers" :icon="Database"
               :chips="[['live', 'live']]"
               :src="['graph_node_type_counts', 'graph_relation_counts', 'graph_ppi_provenance']">
        <div v-if="totals" class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <ActStat v-for="[k, label, sub] in [
                 ['nodes', 'Nodes', `${totals.node_types} types`],
                 ['edges', 'Edges', `${totals.relations} relations`],
                 ['edges_with_provenance', 'PPI edges with provenance', 'explicit source recorded'],
                 ['sources', 'External sources', 'GO · MONDO · NCBI · HPO · DrugBank · REACTOME'],
               ] as [string, string, string]" :key="k"
               :label="label" :value="fmt(totals[k])" :sub="sub" />
        </div>
        <p v-else class="py-4 text-center text-sm text-muted-foreground">Loading…</p>
      </ActCard>

      <!-- Explore the graph. TWO paths, and the difference is the point:
           the starters and the Cypher panel POST to /api/graph/cypher, which
           runs literal Cypher with no LLM at all (~2.5s, deterministic, free);
           free text POSTs to /api/graph/search, which asks the DSS agent
           `graph_explorer` to write the query (~7s, and it may return nothing).
           That is why the starters are labelled reproducible and free text is
           not, and why the Cypher panel is editable — an LLM-written query can
           be corrected and re-run on the deterministic path. -->
      <ActCard span="col-span-12" title="Explore the graph" :icon="Search"
               accent="var(--chart-2)"
               desc="Ask the graph directly. The four starters are pinned queries that reproduce exactly; free text is translated to Cypher by an LLM, so it explores rather than proves."
               :chips="[['live', 'live'], ['agent', 'muted']]"
               :src="['Kuzu folder (ytvuniN8)', 'agent graph_explorer', 'tool b6Rpbve']">

        <div class="flex flex-col gap-3">
          <!-- pinned starters -->
          <div class="flex flex-wrap gap-2">
            <button v-for="s in starters" :key="s.id" type="button"
                    :disabled="graphBusy"
                    class="rounded-md border px-2.5 py-1 text-left text-xs transition-colors
                           disabled:opacity-50"
                    :class="ranStarter === s.id
                      ? 'border-primary bg-primary/15 text-primary-foreground'
                      : 'border-border bg-muted/30 text-muted-foreground hover:bg-muted/60'"
                    @click="runStarter(s)">
              {{ s.label }}
              <ActInfo :text="`${s.shows}. Pinned Cypher — returns ${s.measured} every time.`" />
            </button>
          </div>

          <!-- free text -->
          <form class="flex flex-wrap items-center gap-2" @submit.prevent="runGraph(graphQuery)">
            <input v-model="graphQuery" type="search"
                   placeholder="Ask in plain English, or paste Cypher…"
                   class="min-w-64 flex-1 rounded-md border border-input bg-background px-2.5 py-1.5 text-sm" />
            <button type="submit" :disabled="graphBusy || !graphQuery.trim()"
                    class="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm
                           text-primary-foreground disabled:opacity-50">
              <Loader2 v-if="graphBusy" class="size-3.5 animate-spin" />
              <Search v-else class="size-3.5" />
              Search
            </button>
            <ActInfo text="Plain English is translated to Cypher by an LLM, which is not deterministic here: this graph stores association edges protein→disease, and a generated query in the other direction matches nothing. An empty result usually means that, not an absent fact. Paste Cypher to bypass translation." />
          </form>

          <p v-if="graphError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {{ graphError }}
          </p>

          <p v-else-if="graphBusy" class="font-mono text-[11px] text-muted-foreground">
            querying the graph…
          </p>

          <template v-else-if="graph">
            <!-- The agent's answer leads, whatever came back with it. A declined
                 global count and a genuinely empty match both arrive as
                 mode='empty'; only the second one is "no match". -->
            <p v-if="graph.answer"
               class="rounded-md border border-border bg-muted/30 px-3 py-2 text-sm text-foreground">
              {{ graph.answer }}
            </p>
            <p v-else-if="graph.mode === 'empty'"
               class="rounded-md border border-dashed border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
              <b class="text-primary-foreground">No match.</b> The query ran and returned zero rows —
              that is an answer, not a failure.
            </p>
            <template v-if="graph.mode !== 'empty'">
              <!-- Only a subgraph answer has two views worth switching between.
                   An aggregation returns rows and no nodes, so it shows the
                   table alone rather than an empty canvas. -->
              <div v-if="graph.mode === 'graph' && graph.table" class="flex">
                <ActTabs v-model="graphTab"
                         :options="[{ value: 'graph', label: 'Graph' },
                                    { value: 'table', label: `Table (${graph.table.n_rows})` }]" />
              </div>

              <ActGraph v-if="graph.mode === 'graph' && graphTab === 'graph'"
                        :nodes="graph.nodes" :edges="graph.edges" :height="440" />

              <div v-else-if="graph.table" class="max-h-[440px] overflow-auto rounded-md border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead v-for="c in graph.table.columns" :key="c" class="font-mono text-[10.5px]">
                        {{ c }}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow v-for="(row, i) in graph.table.rows" :key="i">
                      <TableCell v-for="(cell, j) in row" :key="j"
                                 class="font-mono text-[11px] whitespace-nowrap">
                        {{ typeof cell === 'number' ? cell.toLocaleString() : (cell ?? '—') }}
                      </TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </div>

              <div class="flex flex-wrap items-baseline gap-x-4 gap-y-1 font-mono text-[10.5px] text-muted-foreground">
                <span v-if="graph.mode === 'graph'">
                  <b class="text-primary-foreground">{{ graph.n_nodes }}</b> nodes ·
                  <b class="text-primary-foreground">{{ graph.n_edges }}</b> edges
                </span>
                <span v-else-if="graph.table">
                  <b class="text-primary-foreground">{{ graph.table.n_rows }}</b> rows
                </span>
                <span v-if="graph.truncated" class="text-destructive">
                  capped — {{ graph.dropped_nodes }} further nodes not drawn
                </span>
                <span v-if="graph.table?.truncated" class="text-destructive">
                  table capped at {{ graph.table.rows.length }} of {{ graph.table.n_rows }} rows
                </span>
              </div>

              <!-- The Cypher panel. Editable and runnable, and its Run goes to
                   /api/graph/cypher — no LLM, so a query the agent wrote can be
                   corrected and re-run deterministically. -->
              <div v-if="cypherDraft" class="rounded-md border border-border">
                <button type="button"
                        class="flex w-full items-center justify-between px-2.5 py-1.5 font-mono
                               text-[10.5px] text-muted-foreground hover:bg-muted/40"
                        @click="cypherOpen = !cypherOpen">
                  <span>{{ cypherOpen ? '▾' : '▸' }} the Cypher that ran — editable</span>
                  <span class="text-[10px]">{{ cypherOpen ? 'hide' : 'edit &amp; re-run' }}</span>
                </button>
                <div v-if="cypherOpen" class="border-t border-border p-2">
                  <textarea v-model="cypherDraft" rows="4" spellcheck="false"
                            class="w-full resize-y rounded-md border border-input bg-background p-2
                                   font-mono text-[11px]" />
                  <div class="mt-1.5 flex flex-wrap items-center gap-2">
                    <button type="button" :disabled="graphBusy || !cypherDraft.trim()"
                            class="flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1
                                   text-xs text-primary-foreground disabled:opacity-50"
                            @click="runGraph(cypherDraft, { literal: true })">
                      <Loader2 v-if="graphBusy" class="size-3 animate-spin" />
                      <Play v-else class="size-3" />
                      Run
                    </button>
                    <button type="button" :disabled="graphBusy || cypherDraft === graph.cypher"
                            class="rounded-md border border-border px-2.5 py-1 text-xs
                                   text-muted-foreground disabled:opacity-40 hover:bg-muted/40"
                            @click="cypherDraft = graph.cypher ?? ''">
                      Reset
                    </button>
                    <span class="font-mono text-[10px] text-muted-foreground">
                      runs directly against the graph — no LLM
                    </span>
                  </div>
                </div>
              </div>
            </template>
          </template>

          <p v-else class="font-mono text-[11px] text-muted-foreground">
            Pick a starter above, or ask your own question.
          </p>
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" title="8 node types" :icon="Layers"
               desc="What kinds of thing the graph knows about." :chips="[['live', 'live']]"
               :src="['graph_node_type_counts']">
        <ActBar v-if="data" :rows="data.node_types" color="var(--chart-2)" />
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" title="18 relations" :icon="GitBranch"
               desc="Every relation and its count. The seven largest match GRAPH_BUILDING.md §7.1 exactly."
               :chips="[['live', 'live']]" :src="['graph_relation_counts']">
        <ActBar v-if="data" :rows="data.relations" color="var(--chart-3)" />
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" title="Where the nodes came from" :icon="Database"
               desc="Six external vocabularies, and one grouping we derived ourselves."
               :chips="[['live', 'live']]" :src="['graph_node_source_counts']">
        <ActBar v-if="data" :rows="sourceRows" />
        <div class="mt-3 rounded-lg border-l-2 border-destructive bg-destructive/10 px-3.5 py-2.5 text-[13px] leading-relaxed">
          <b>Say six sources, not seven.</b> One of these is a grouping we derived ourselves, not an
          external vocabulary — it is shown in grey.
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" title="Every edge knows where it came from"
               :icon="GitBranch" accent="var(--chart-3)"
               desc="Which interaction databases asserted each PPI edge. This is the lineage claim, made concrete."
               :chips="[['live', 'live']]" :src="['graph_ppi_provenance']">
        <ActBar v-if="data" :rows="ppiRows" />
        <div class="mt-2 flex gap-4 font-mono text-[10.5px] text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-1)"></span>single source</span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-2)"></span>corroborated by 2+ interactomes</span>
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="What the association evidence is"
               :icon="FileText" accent="var(--chart-4)"
               desc="Every association in the graph carries an evidence type. These are the three that exist here, and they are not equally strong — Act 5 returns to this."
               :chips="[['live', 'live']]" :src="['graph_label_evidence']">
        <ActDonut v-if="data" :rows="data.label_evidence" />
      </ActCard>

      </div>
  </div>
</template>
