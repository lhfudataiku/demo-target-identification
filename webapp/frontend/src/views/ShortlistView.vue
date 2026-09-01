<script setup lang="ts">
  /**
   * Act 4 — the list, and the eyeball test.
   *
   * The act this demo exists for: open a disease you know, judge the top of the
   * list yourself, then narrow it on your own thresholds.
   *
   * Card structure follows DASHBOARD_MOCKUP_V3.html; styling is the Dataiku
   * design system rather than the mockup's standalone one.
   *
   * Guardrails enforced here, not merely documented:
   *  - drug badges and the liability flag RENDER but are never filter controls
   *    (the badges are the ground truth the enrichment is measured against;
   *    filtering the liability flag deletes ERBB2 from its own disease's list);
   *  - `prediction` is never fetched or shown;
   *  - every funnel count renders its rank cut-off, so a count cannot acquire
   *    two values;
   *  - no discovery-enrichment figure appears on a summary tile;
   *  - the detail card shows the CHAMPION'S features, never whichever columns
   *    the dataset happens to carry, and names the one it cannot show;
   *  - a feature's percentile is ranked in the direction that feature counts,
   *    so the best possible hop distance does not draw an empty bar.
   */
  import { computed, nextTick, onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import { EaSelect, EaEmpty } from '@/components/ui'
  import ActTabs from '@/components/act/ActTabs.vue'
  import ActInfo from '@/components/act/ActInfo.vue'
  import ActGraph from '@/components/act/ActGraph.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Check, Copy, ListFilter, Loader2, Microscope, Network, Play } from 'lucide-vue-next'

  defineOptions({ name: 'ShortlistView' })

  interface Disease { disease_index: number; disease_name: string; n_candidates: number; n_known: number }
  interface Row {
    gene_index: number
    gene_name: string; rank_in_disease: number; rank_percentile: number | null
    score: number; is_target: number
    top_shap_drivers: string | null; druggability_class: string | null; ot_class_l1: string | null
    ot_sm_tractable: number; ot_ab_tractable: number
    has_safety_liability: number; approved_for_disease: number; investigational_for_disease: number
  }
  interface Payload { disease_name: string; funnel: { step: string; n: number }[]; rows: Row[]; returned: number }

  /** One model feature, placed against this disease's own pool.
      `percentile` is the share of the pool this candidate is STRONGER than,
      measured in whichever direction the feature counts — `direction: 'lower'`
      means fewer is stronger, which is true of hop distance and nothing else. */
  interface Feature {
    key: string; label: string; kind: string
    direction: 'higher' | 'lower'
    value: number; percentile: number
  }
  interface Detail {
    gene_index: number; pool_size: number | null; safety_events: string | null
    features: Feature[]
    /** Champion inputs `dashboard_candidates` does not carry — named, not hidden. */
    missing_features: string[]
  }

  const diseases = ref<Disease[]>([])
  const selected = ref<number | undefined>()
  // EaSelect models strings; disease_index is numeric.
  const selectedStr = computed<string | undefined>({
    get: () => (selected.value === undefined ? undefined : String(selected.value)),
    set: (v) => { selected.value = v === undefined ? undefined : Number(v) },
  })
  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  const novelOnly = ref(false)
  const tractableOnly = ref(false)
  const excludeSecreted = ref(false)
  const maxRank = ref(200)

  // The table's own controls, as v3 has them. These filter the rows already
  // loaded rather than refetching: the funnel above describes the population,
  // this describes what is on screen.
  const search = ref('')
  const tract = ref('')          // '' | sm | ab | either
  const klass = ref('')
  const liab = ref(false)        // strike out, never remove — see the safety card

  // Paging. 20 rows is what a person can actually scan; the funnel above still
  // reports the true totals, so paging never hides how big the list is.
  const PAGE = 20
  const page = ref(1)

  const classes = computed(() =>
    [...new Set((data.value?.rows ?? []).map((r) => r.ot_class_l1).filter(Boolean))].sort() as string[])

  const shown = computed(() => (data.value?.rows ?? []).filter((r) => {
    if (search.value && !r.gene_name.toLowerCase().includes(search.value.toLowerCase())) return false
    if (tract.value === 'sm' && !r.ot_sm_tractable) return false
    if (tract.value === 'ab' && !r.ot_ab_tractable) return false
    if (tract.value === 'either' && !(r.ot_sm_tractable || r.ot_ab_tractable)) return false
    if (klass.value && r.ot_class_l1 !== klass.value) return false
    return true
  }))
  const pageCount = computed(() => Math.max(1, Math.ceil(shown.value.length / PAGE)))
  const paged = computed(() =>
    shown.value.slice((page.value - 1) * PAGE, page.value * PAGE))
  // Any change to the filters or the disease puts you back on page 1 — staying
  // on page 7 of a list that now has two pages reads as an empty table.
  watch([search, tract, klass, selected, novelOnly, tractableOnly, excludeSecreted, maxRank],
        () => { page.value = 1 })

  const tractLabel = (r: Row) =>
    [r.ot_sm_tractable ? 'SM' : '', r.ot_ab_tractable ? 'Ab' : ''].filter(Boolean).join(' + ') || '—'

  const current = computed(() => diseases.value.find((d) => d.disease_index === selected.value))

  /* ── The selected candidate ────────────────────────────────────────────────
     Both cards below the table read one selection rather than owning separate
     pickers: the act's move is "judge a row, then ask why that row", and two
     independent selectors would let the drawer and the subgraph describe
     different genes at the same time. */
  const sel = ref<Row | null>(null)
  const detail = ref<Detail | null>(null)
  const detailBusy = ref(false)
  const detailError = ref<string | null>(null)

  async function selectRow(r: Row) {
    if (selected.value === undefined) return
    sel.value = r
    // The subgraph is per-gene and costs a DSS round-trip, so it is NOT
    // refetched here — it waits for its own button. Clearing it keeps a stale
    // picture of the previous gene from sitting under the new gene's name.
    graph.value = null
    graphError.value = null
    copied.value = false
    detail.value = null
    detailError.value = null
    detailBusy.value = true
    const forGene = r.gene_index
    try {
      const q = new URLSearchParams({ disease: String(selected.value), gene: String(r.gene_index) })
      const res = await fetch(apiUrl(`/api/candidates/gene?${q}`))
      if (!res.ok) {
        const d = await res.json().catch(() => null)
        throw new Error(d?.detail ?? `HTTP ${res.status}`)
      }
      const payload: Detail = await res.json()
      // A slower earlier request must not overwrite a later selection.
      if (sel.value?.gene_index !== forGene) return
      detail.value = payload
    } catch (e) {
      if (sel.value?.gene_index !== forGene) return
      detailError.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (sel.value?.gene_index === forGene) detailBusy.value = false
    }
    // Bring the answer to the reader. The card is always mounted, so this is a
    // scroll rather than a reveal — but it waits a tick so the height it
    // scrolls to is the height with this gene's content in it.
    await nextTick()
    revealWhyCard()
  }

  /* Scroll the detail card into view, and MAKE SURE IT ARRIVES.

     Deliberately arithmetic rather than `scrollIntoView`. Two things went wrong
     with the built-in here, both observed in this app's own layout:

      - `behavior: 'smooth'` is not always honoured. A smooth request moved this
        container 11px and stopped, and `scrollTo({behavior:'smooth'})` on the
        same element moved nothing at all, while an instant scroll worked every
        time. Landing on the card is the requirement; the animation is a nicety.
      - `scrollIntoView({block:'start'})` did not reliably put the card at the
        top: from a cold page load it left the container pinned at its maximum
        scroll with the card 468px above the fold, i.e. showing the FOOTNOTE of
        the answer instead of the gene's name.

     So: find the element that actually scrolls, compute the offset, set it, and
     only use smooth when the browser proves it is doing something. */
  function scrollParent(el: HTMLElement): HTMLElement {
    for (let n = el.parentElement; n; n = n.parentElement) {
      const oy = getComputedStyle(n).overflowY
      if ((oy === 'auto' || oy === 'scroll') && n.scrollHeight > n.clientHeight) return n
    }
    return (document.scrollingElement as HTMLElement | null) ?? document.documentElement
  }

  function revealWhyCard() {
    const card = document.getElementById('why-this-gene')
    if (!card) return
    const scroller = scrollParent(card)
    const target = Math.max(0,
      card.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop)
    const start = scroller.scrollTop
    if (Math.abs(target - start) < 1) return
    scroller.scrollTo({ top: target, behavior: 'smooth' })
    // A real animation has moved by now; a no-op has not. Only then, jump.
    window.setTimeout(() => {
      if (scroller.scrollTop === start) scroller.scrollTop = target
    }, 200)
  }

  /* `top_shap_drivers` is a rendered STRING, not structured data:
     "dwpc_GGD (+0.21), rwr_score (-0.04)" — see compute_top_shap_drivers_1.py,
     which formats the top 2 by |contribution| and keeps the sign. Parsed back
     apart here so the card can show the evidence route rather than the column
     name, and so a negative driver reads as one. A part that does not match the
     shape is passed through verbatim rather than dropped. */
  const drivers = computed(() => {
    const raw = sel.value?.top_shap_drivers
    if (!raw) return []
    return raw.split(/,\s*/).map((part) => {
      const m = part.match(/^(.*?)\s*\(([+-])([\d.]+)\)\s*$/)
      if (!m) return { key: part, label: null as string | null, sign: '', value: '' }
      const key = m[1].trim()
      return { key, label: labelFor(key), sign: m[2], value: m[3] }
    })
  })

  /* The evidence route a feature measures. Sourced from the detail payload so
     the wording has exactly one definition (backend/feature_glossary.py) and
     act 2's glossary cannot drift away from act 4's drawer. */
  function labelFor(key: string): string | null {
    return detail.value?.features.find((f) => f.key === key)?.label ?? null
  }

  /* Open Targets packs several observed effects into one pipe-delimited cell
     ("cardiotoxicity|heart disease|..."). Shown as a list, not as the raw cell. */
  const safetyEvents = computed(() =>
    (detail.value?.safety_events ?? '').split('|').map((s) => s.trim()).filter(Boolean))

  /* Small values go exponential rather than rounding to a misleading 0.000 —
     several path weights live at 1e-4. */
  function fmtValue(v: number): string {
    if (v === 0) return '0'
    return Math.abs(v) < 0.01 ? v.toExponential(2) : v.toFixed(3)
  }

  const KIND_ORDER = ['path', 'proximity', 'topology', 'provenance']
  const featureGroups = computed(() => {
    const fs = detail.value?.features ?? []
    return KIND_ORDER
      .map((kind) => ({ kind, features: fs.filter((f) => f.kind === kind) }))
      .filter((g) => g.features.length)
  })

  /* ── The mechanism, on the graph ───────────────────────────────────────────
     FIVE evidence routes from this candidate to this disease, merged into one
     subgraph by the backend. Four of them are the champion's own path features
     (dwpc_GGD / GPGD / GFGD / GBGD); the fifth is the drug route, which is NOT
     a feature — see the caveat rendered on the card.

     The obvious single query — one OPTIONAL MATCH per route — does not work on
     this engine: consecutive OPTIONAL MATCH clauses multiply rows instead of
     adding them, so the four graph routes join to ~16M rows for a well-connected
     gene and the engine kills the query (measured: 173s, then Interrupted).
     LIMIT bounds the output, not the join. So the routes run as separate
     queries, concurrently, and POST /api/graph/mechanism merges them. Every
     query it ran comes back with the result and is shown below the canvas. */
  interface GraphNode { id: string; label: string; group_name: string }
  interface GraphEdge { id: string; src: string; dst: string; group_name: string }
  interface MechRoute {
    key: string; label: string
    /** The champion feature this route is the graph form of; null for drugs. */
    feature: string | null
    n_edges: number; row_limit: number; error: string | null
  }
  interface GraphResult {
    mode: 'graph' | 'empty'
    nodes: GraphNode[]; edges: GraphEdge[]; n_nodes: number; n_edges: number
    truncated: boolean; dropped_nodes: number
    routes: MechRoute[]
    queries: { key: string; label: string; cypher: string }[]
    /** The five routes as ONE query — for the Visual Graph Explorer, not for here. */
    explorer_cypher: string
  }

  const graph = ref<GraphResult | null>(null)
  const graphBusy = ref(false)
  const graphError = ref<string | null>(null)
  const copied = ref(false)
  const queriesOpen = ref(false)

  /* Deliberately NOT automatic on row select. Five concurrent tool calls is a
     real DSS round-trip (~4s warm), and firing that per row while someone scans
     the list spends most of them on genes nobody looked at.

     NB the FIRST call after the graph tool has been idle costs far more — 147s
     measured cold against 4s warm. Act 1 uses the same tool, so a run-through
     that opens the evidence base first arrives here warm. */
  async function runMechanism() {
    if (!sel.value || selected.value === undefined || graphBusy.value) return
    graphBusy.value = true
    graphError.value = null
    try {
      const res = await fetch(apiUrl('/api/graph/mechanism'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          disease: selected.value, gene: sel.value.gene_index,
          disease_name: current.value?.disease_name ?? 'this disease',
          gene_name: sel.value.gene_name,
        }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => null)
        throw new Error(d?.detail ?? `HTTP ${res.status}`)
      }
      graph.value = await res.json()
    } catch (e) {
      graphError.value = e instanceof Error ? e.message : String(e)
      graph.value = null
    } finally { graphBusy.value = false }
  }

  /* Routes that found something, and routes that found nothing — both are the
     answer. "No pathway route" is a fact about this candidate, not a gap. */
  const routesFound = computed(() => (graph.value?.routes ?? []).filter((r) => r.n_edges > 0))
  const routesEmpty = computed(() =>
    (graph.value?.routes ?? []).filter((r) => r.n_edges === 0 && !r.error))
  const routesFailed = computed(() => (graph.value?.routes ?? []).filter((r) => r.error))

  /* "100 per route" would be false for three of the five, so report the range
     when they differ and the single value when they do not. */
  const routeBounds = computed(() => {
    const ls = [...new Set((graph.value?.routes ?? []).map((r) => r.row_limit))].sort((a, b) => a - b)
    if (!ls.length) return '—'
    return ls.length === 1 ? `${ls[0]} paths per route` : `${ls[0]}–${ls[ls.length - 1]} paths per route`
  })

  const allCypher = computed(() =>
    (graph.value?.queries ?? [])
      .map((q) => `// ${q.label}\n${q.cypher}`)
      .join('\n\n'))

  /* Copy hands over the ONE-query form, not the five this backend ran. That is
     the form a person wants in the Explorer, where it returns in about a second
     — the split exists only because the agent tool's Kuzu cannot hold the join.
     Copying five queries someone then has to run one at a time would be
     exporting our constraint rather than the answer. */
  async function copyCypher() {
    const text = graph.value?.explorer_cypher
    if (!text) return
    try {
      await navigator.clipboard.writeText(text)
      copied.value = true
      setTimeout(() => { copied.value = false }, 1600)
    } catch { /* clipboard blocked in the iframe — the query is on screen to select */ }
  }


  async function loadDiseases() {
    try {
      const res = await fetch(apiUrl('/api/candidates/diseases'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      diseases.value = await res.json()
      // The spine disease: a clinician recognises its top ranks on sight.
      // Falls back to the largest pool if the name does not carry "HER2".
      selected.value = (diseases.value.find((d) => /HER2/i.test(d.disease_name))
        ?? diseases.value[0])?.disease_index
    } catch (e) {
      error.value = `Could not load diseases: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function loadCandidates() {
    if (selected.value === undefined) return
    loading.value = true; error.value = null
    try {
      const q = new URLSearchParams({
        disease: String(selected.value), novel_only: String(novelOnly.value),
        tractable_only: String(tractableOnly.value), exclude_secreted: String(excludeSecreted.value),
        max_rank: String(maxRank.value),
      })
      const res = await fetch(apiUrl(`/api/candidates?${q}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load candidates: ${e instanceof Error ? e.message : String(e)}`
      data.value = null
    } finally { loading.value = false }
  }

  onMounted(loadDiseases)
  watch([selected, novelOnly, tractableOnly, excludeSecreted, maxRank], loadCandidates)

  // Only the DISEASE invalidates a selection. The view filters do not: the
  // percentiles are computed against the disease's whole pool, not the filtered
  // one, so narrowing the table does not change what the detail card says.
  watch(selected, () => {
    sel.value = null
    detail.value = null
    detailError.value = null
    graph.value = null
    graphError.value = null
  })
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 4 of 4 · The list
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">Does this look right to you?</h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        One disease, all the way down — and the act this demo exists for. Open a disease you know and
        judge the top of the list yourself; the scientist is the instrument. Then take the controls:
        nothing is pre-filtered, and you narrow it on your own thresholds.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <!-- The contract, stated before the list appears. -->
      <!-- Your thresholds, not ours. -->
      <!-- The ranked list. -->
      <ActCard span="col-span-12" :icon="ListFilter"
               :title="`The ranked list${current ? ' — ' + current.disease_name : ''}`"
               :chips="[['live', 'live']]"
               desc="Every control for this act lives here. Nothing is pre-cut — you set the cut-offs, and the funnel shows what each one costs."
               :src="['dashboard_candidates']">
        <!-- population controls: these refetch, because they change what is scored -->
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-64 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Disease
              <ActInfo text="One of the 13 diseases scored into a ranked candidate list." />
            </span>
            <EaSelect v-model="selectedStr" placeholder="— Select a disease —"
                      :options="diseases.map((d) => ({ value: String(d.disease_index),
                                 label: `${d.disease_name} (${d.n_candidates.toLocaleString()})` }))" />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="novelOnly" type="checkbox" class="size-4 accent-primary" /> Novel only
            <ActInfo text="Drops genes already annotated as targets for this disease, so what remains is what the model surfaced rather than reproduced." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="tractableOnly" type="checkbox" class="size-4 accent-primary" /> Tractable
            <ActInfo text="Open Targets judges the protein reachable by a small molecule or an antibody." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="excludeSecreted" type="checkbox" class="size-4 accent-primary" /> Not secreted
            <ActInfo text="Excludes proteins released between cells. Harder to drug than ones sitting on a membrane." />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Rank ≤
              <ActInfo text="How far down the ranked list to go. Every count below carries this cut-off, so a number can never mean two things." />
            </span>
            <input v-model.number="maxRank" type="number" min="1" max="5000"
                   class="w-24 rounded-md border border-input bg-background px-2 py-1.5" />
          </label>
        </div>

        <div v-if="data" class="mt-3 flex flex-wrap items-center gap-1.5">
          <template v-for="(f, i) in data.funnel" :key="f.step">
            <span class="rounded-md px-2.5 py-1 font-mono text-xs"
                  :class="i === data.funnel.length - 1
                    ? 'bg-primary/25 font-medium text-primary-foreground'
                    : 'bg-secondary text-muted-foreground'">
              {{ f.step }} · {{ f.n.toLocaleString() }}
            </span>
            <span v-if="i < data.funnel.length - 1" class="text-muted-foreground">→</span>
          </template>
        </div>

        <hr class="my-4 border-border" />

        <!-- view controls: these filter what is already on screen -->
        <div class="flex flex-wrap items-center gap-2">
          <input v-model="search" type="search" placeholder="Search gene…"
                 class="w-36 rounded-md border border-input bg-background px-2 py-1 text-sm" />
          <ActTabs :model-value="novelOnly ? 'novel' : 'all'"
                   :options="[{ value: 'all', label: 'All' }, { value: 'novel', label: 'Novel only' }]"
                   @update:model-value="(v) => (novelOnly = v === 'novel')" />
          <span class="flex items-center">
            <select v-model="tract" class="rounded-md border border-input bg-background px-2 py-1 text-sm">
              <option value="">Any tractability</option>
              <option value="sm">Small-molecule</option>
              <option value="ab">Antibody</option>
              <option value="either">Either</option>
            </select>
            <ActInfo text="Small-molecule: a drug-like pocket. Antibody: reachable from outside the cell. Either: at least one." />
          </span>
          <span class="flex items-center">
            <select v-model="klass" class="rounded-md border border-input bg-background px-2 py-1 text-sm">
              <option value="">Any target class</option>
              <option v-for="c in classes" :key="c" :value="c">{{ c }}</option>
            </select>
            <ActInfo text="Open Targets' protein family — enzyme, membrane receptor, transcription factor and so on." />
          </span>
          <label class="flex items-center gap-2 text-sm"
                 :class="liab ? 'font-medium text-destructive' : ''">
            <input v-model="liab" type="checkbox" class="size-4 accent-[var(--destructive)]" />
            Strike out liabilities
            <ActInfo text="A public annotation recording that an adverse effect has been observed and published for this protein — from clinical or experimental evidence, aggregated by Open Targets. Its limits matter: the flag is not dose-, modality- or indication-specific, it says nothing about whether an effect is manageable, and it can only exist for targets that have already been drugged or studied. So an unflagged gene is not safe — it is unstudied. Treat it as evidence of attention, not of danger." />
          </label>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ shown.length }} of {{ data?.rows.length ?? 0 }} shown
          </span>
        </div>

        <div v-if="shown.length" class="mt-3 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rank<ActInfo text="Position in this disease's list. The score behind it is uncalibrated, so the ordering is what carries meaning — not the number." /></TableHead>
                <TableHead>Gene<ActInfo text="HGNC symbol of the candidate protein." /></TableHead>
                <TableHead>Class<ActInfo text="Open Targets protein family." /></TableHead>
                <TableHead>Tract.<ActInfo text="SM = small-molecule tractable · Ab = antibody tractable · — = neither assessed." /></TableHead>
                <TableHead>Status<ActInfo text="associated = an Open Targets genetic or somatic association already exists for this disease–gene pair, at score ≥ 0.3 — this is the label the model was trained on · novel = no such association · approved / trial = drug evidence, shown as ground truth and never filterable · liability = a recorded safety flag." /></TableHead>
                <TableHead>Top drivers<ActInfo text="The features that moved this candidate most, from its SHAP attribution." /></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <!-- The row IS the control. Clicking one answers "why this gene?"
                   below and scrolls there; keyboard reaches it the same way. -->
              <TableRow v-for="r in paged" :key="r.gene_name"
                        class="cursor-pointer transition-colors hover:bg-accent/40"
                        :class="[
                          liab && r.has_safety_liability ? 'opacity-45 line-through' : '',
                          sel?.gene_index === r.gene_index ? 'bg-accent/60' : '',
                        ]"
                        tabindex="0" role="button"
                        :aria-label="`Why ${r.gene_name}?`"
                        :aria-pressed="sel?.gene_index === r.gene_index"
                        @click="selectRow(r)"
                        @keydown.enter.prevent="selectRow(r)"
                        @keydown.space.prevent="selectRow(r)">
                <TableCell class="font-mono tabular-nums text-muted-foreground">{{ r.rank_in_disease }}</TableCell>
                <TableCell class="font-mono font-medium">{{ r.gene_name }}</TableCell>
                <TableCell class="text-muted-foreground">{{ r.ot_class_l1 || '—' }}</TableCell>
                <TableCell class="font-mono text-[11px]">{{ tractLabel(r) }}</TableCell>
                <TableCell class="no-underline">
                  <span class="mr-1 inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                        :class="r.is_target ? 'bg-secondary text-muted-foreground' : 'bg-primary/25 text-primary-foreground'">
                    {{ r.is_target ? 'associated' : 'novel' }}
                  </span>
                  <span v-if="r.approved_for_disease"
                        class="mr-1 inline-block rounded bg-chart-3/20 px-1.5 py-0.5 font-mono text-[10px] uppercase">approved</span>
                  <span v-if="r.investigational_for_disease"
                        class="mr-1 inline-block rounded bg-chart-4/25 px-1.5 py-0.5 font-mono text-[10px] uppercase">trial</span>
                  <span v-if="r.has_safety_liability"
                        class="inline-block rounded bg-destructive/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-destructive">liability</span>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ r.top_shap_drivers || '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div v-if="shown.length > PAGE"
             class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ (page - 1) * PAGE + 1 }}–{{ Math.min(page * PAGE, shown.length) }}
            of {{ shown.length.toLocaleString() }}
          </span>
          <div class="flex items-center gap-1">
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === 1" @click="page = 1">« First</button>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === 1" @click="page--">‹ Prev</button>
            <span class="px-2 font-mono text-[11px] text-muted-foreground">
              page {{ page }} / {{ pageCount }}
            </span>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === pageCount" @click="page++">Next ›</button>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === pageCount" @click="page = pageCount">Last »</button>
          </div>
        </div>
        <EaEmpty v-if="!shown.length" :icon="ListFilter" title="Nothing matches"
                 description="Loosen a filter, or pick another disease." />

        <div class="mt-3 rounded-lg border border-dashed border-destructive/50 px-3.5 py-2.5 text-[13px] leading-relaxed">
          <p class="mb-1 font-mono text-[10px] uppercase tracking-wide text-destructive">Must not appear</p>
          <b>The drug badges are not filterable, and that is deliberate.</b> Approved-for-disease and
          in-trials are the ground truth the discovery result is measured against. A shortlist filtered
          by them would be circular, so they are shown and never actionable.
        </div>
      </ActCard>

      <ActCard id="why-this-gene" span="col-span-12 lg:col-span-6" :icon="Microscope"
               :title="sel ? `Why ${sel.gene_name}?` : 'Why this gene?'"
               :chips="[['live', 'live']]"
               desc="Each feature placed against this disease's own distribution, not a global one."
               :src="['dashboard_candidates']">
        <EaEmpty v-if="!sel" :icon="Microscope" title="Pick a row"
                 description="Click any candidate in the list above." />

        <p v-else-if="detailError"
           class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {{ detailError }}
        </p>

        <div v-else class="flex flex-col gap-4">
          <!-- Where this candidate sits, before any explanation of why. -->
          <div class="flex flex-col gap-1.5">
            <div class="flex flex-wrap items-baseline gap-2">
              <span class="font-mono text-[17px] font-medium">{{ sel.gene_name }}</span>
              <span class="mr-1 inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                    :class="sel.is_target ? 'bg-secondary text-muted-foreground' : 'bg-primary/25 text-primary-foreground'">
                {{ sel.is_target ? 'associated' : 'novel' }}
              </span>
              <span v-if="sel.approved_for_disease"
                    class="inline-block rounded bg-chart-3/20 px-1.5 py-0.5 font-mono text-[10px] uppercase">approved</span>
              <span v-if="sel.investigational_for_disease"
                    class="inline-block rounded bg-chart-4/25 px-1.5 py-0.5 font-mono text-[10px] uppercase">trial</span>
              <span v-if="sel.has_safety_liability"
                    class="inline-block rounded bg-destructive/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-destructive">liability</span>
            </div>
            <p class="font-mono text-[11px] text-muted-foreground">
              rank #{{ sel.rank_in_disease.toLocaleString() }}<template v-if="detail?.pool_size">
                of {{ detail.pool_size.toLocaleString() }}</template>
              <template v-if="sel.rank_percentile !== null"> · {{ sel.rank_percentile }} pct</template>
              · {{ sel.ot_class_l1 || 'class not assessed' }}
              · {{ tractLabel(sel) === '—' ? 'tractability not assessed' : tractLabel(sel) }}
              · node_index {{ sel.gene_index }}
            </p>
            <p v-if="sel.has_safety_liability && safetyEvents.length"
               class="text-[12px] leading-relaxed text-muted-foreground">
              <span class="text-destructive">Recorded liability:</span>
              {{ safetyEvents.join(' · ') }}
            </p>
          </div>

          <!-- What moved it. Two drivers, because two is what is stored. -->
          <div class="flex flex-col gap-1.5">
            <h3 class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              What moved this candidate
              <ActInfo text="The features with the largest SHAP contribution for this one prediction, with the direction of each. A positive driver pushed the score up; a negative one pushed it down." />
            </h3>
            <div v-if="drivers.length" class="flex flex-col gap-1">
              <div v-for="d in drivers" :key="d.key"
                   class="flex items-baseline justify-between gap-3 rounded-md bg-muted/40 px-2.5 py-1.5">
                <span class="text-[12.5px] leading-snug">
                  {{ d.label ?? d.key }}
                  <span v-if="d.label" class="ml-1 font-mono text-[10px] text-muted-foreground">{{ d.key }}</span>
                </span>
                <span v-if="d.value" class="flex-none font-mono text-[12px] tabular-nums"
                      :class="d.sign === '+' ? 'text-chart-3' : 'text-destructive'">
                  {{ d.sign }}{{ d.value }}
                </span>
              </div>
            </div>
            <p v-else class="text-[13px] text-muted-foreground">No attribution stored for this candidate.</p>
            <p class="text-[11.5px] leading-relaxed text-muted-foreground">
              <b class="text-foreground">The two strongest drivers only.</b> A full per-feature waterfall
              needs the scoring recipe to carry its whole SHAP matrix into
              <code class="font-mono text-[10.5px]">dashboard_candidates</code>; today only the top two
              survive the flow, so this is what exists rather than what was chosen.
            </p>
          </div>

          <!-- Every model input, ranked inside this disease's own pool. -->
          <div class="flex flex-col gap-2">
            <h3 class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
              The evidence, against this disease
              <ActInfo text="Every input to the champion model, not a selection. The bar is the candidate's rank within this disease's own pool — the raw value beside it is what the model actually read." />
            </h3>
            <p v-if="detailBusy" class="text-[13px] text-muted-foreground">Loading…</p>
            <div v-for="g in featureGroups" :key="g.kind" class="flex flex-col gap-1.5">
              <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground/70">{{ g.kind }}</span>
              <div v-for="f in g.features" :key="f.key" class="flex flex-col gap-0.5">
                <div class="flex items-baseline justify-between gap-3">
                  <span class="text-[12px] leading-snug">
                    {{ f.label }}
                    <ActInfo v-if="f.direction === 'lower'"
                             text="Fewer is stronger for this one: a candidate one hop from the disease module is as close as the feature can report. The bar is ranked accordingly." />
                  </span>
                  <span class="flex-none font-mono text-[11px] tabular-nums text-muted-foreground">
                    {{ fmtValue(f.value) }} · {{ f.percentile }} pct
                  </span>
                </div>
                <div class="h-[5px] overflow-hidden rounded-full bg-muted">
                  <i class="block h-full rounded-full bg-chart-3"
                     :style="{ width: `${f.percentile}%` }" />
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-dashed border-border px-3.5 py-2.5 text-[11.5px] leading-relaxed text-muted-foreground">
            <p><b class="text-foreground">How the percentile is computed.</b> For one gene and one
              feature it is <code class="font-mono text-[10.5px]">100 × (candidates for this disease this
              one is stronger than) ÷ (candidates with a non-null value)</code> — a rank <b>within this
              disease's own pool</b>, never a global one. The same gene can sit at the 96th percentile
              here and the 40th for another disease on an identical raw value.</p>
            <p class="mt-1.5">Stronger means a <b class="text-foreground">higher</b> value everywhere
              except hop distance, where it means a lower one. Ties never count toward the number, so a
              feature most of the pool shares reads modestly rather than at the 100th percentile.</p>
            <p v-if="detail?.missing_features?.length" class="mt-1.5">
              <b class="text-foreground">Not shown:</b>
              <code v-for="m in detail.missing_features" :key="m"
                    class="mx-1 font-mono text-[10.5px]">{{ m }}</code>
              — a model input that never reaches
              <code class="font-mono text-[10.5px]">dashboard_candidates</code>, so the bars above are
              {{ detail.features.length }} of the champion's
              {{ detail.features.length + detail.missing_features.length }} features.
            </p>
          </div>
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" :icon="Network" title="The mechanism, on the graph"
               :chips="[['live', 'live']]"
               desc="Every route from this candidate to the disease's own annotated genes — interaction, pathway, molecular function, biological process, and drug."
               :src="['Kuzu folder (ytvuniN8)', 'tool b6Rpbve']">
        <EaEmpty v-if="!sel" :icon="Network" title="Pick a row"
                 description="The queries are generated from the candidate you select." />

        <div v-else class="flex flex-col gap-3">
          <p class="text-[12.5px] leading-relaxed text-muted-foreground">
            Four of these routes are the graph form of the model's own path features; the fifth is the
            drug route, which is <b class="text-foreground">not</b> one.
          </p>

          <div class="flex flex-wrap items-center gap-2">
            <button type="button" :disabled="graphBusy"
                    class="flex items-center gap-1.5 rounded-md bg-primary px-2.5 py-1 text-xs
                           text-primary-foreground disabled:opacity-50"
                    @click="runMechanism">
              <Loader2 v-if="graphBusy" class="size-3 animate-spin" />
              <Play v-else class="size-3" />
              {{ graphBusy ? 'Querying five routes…' : graph ? 'Run again' : 'Show the mechanism' }}
            </button>
            <button v-if="graph" type="button"
                    class="flex items-center gap-1.5 rounded-md border border-input px-2.5 py-1
                           text-xs text-muted-foreground hover:bg-accent/50"
                    @click="copyCypher">
              <Check v-if="copied" class="size-3" />
              <Copy v-else class="size-3" />
              {{ copied ? 'Copied' : 'Copy query for the Explorer' }}
            </button>
            <span class="font-mono text-[10.5px] text-muted-foreground">follows the selected row</span>
          </div>

          <p v-if="graphError"
             class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {{ graphError }}
          </p>

          <template v-if="graph">
            <ActGraph v-if="graph.n_nodes" :nodes="graph.nodes" :edges="graph.edges" :height="380" />

            <!-- Which routes exist, and which do not. An absent route is a fact
                 about this candidate, not a gap in the picture — a novel gene
                 with no drug route is exactly what "novel" means. -->
            <div class="flex flex-col gap-1">
              <div v-for="r in routesFound" :key="r.key"
                   class="flex items-baseline justify-between gap-3 rounded-md bg-muted/40 px-2.5 py-1">
                <span class="text-[12.5px]">
                  via {{ r.label }}
                  <span v-if="r.feature" class="ml-1 font-mono text-[10px] text-muted-foreground">{{ r.feature }}</span>
                  <span v-else
                        class="ml-1 rounded bg-chart-4/25 px-1 py-0.5 font-mono text-[9.5px] uppercase">not a feature</span>
                </span>
                <span class="flex-none font-mono text-[11px] tabular-nums text-muted-foreground">
                  {{ r.n_edges }} edges
                </span>
              </div>
              <p v-if="routesEmpty.length" class="text-[11.5px] leading-relaxed text-muted-foreground">
                <b class="text-foreground">No route via</b>
                {{ routesEmpty.map((r) => r.label).join(', ') }} — nothing connects this candidate to
                the disease that way, which is part of the answer rather than a missing picture.
              </p>
              <p v-for="r in routesFailed" :key="r.key"
                 class="text-[11.5px] leading-relaxed text-destructive">
                The {{ r.label }} route did not run: {{ r.error }}
              </p>
            </div>

            <div class="flex flex-wrap items-baseline gap-x-4 font-mono text-[10.5px] text-muted-foreground">
              <span>
                <b class="text-primary-foreground">{{ graph.n_nodes }}</b> nodes ·
                <b class="text-primary-foreground">{{ graph.n_edges }}</b> edges
              </span>
              <span v-if="graph.truncated" class="text-destructive">
                capped — {{ graph.dropped_nodes }} further nodes not drawn
              </span>
              <!-- Per-route, because the bounds differ: the GO routes are tighter
                   than PPI and the drug route tighter still. One number here
                   would be wrong for three of the five. -->
              <span>path bound {{ routeBounds }}</span>
            </div>

            <!-- Two forms, and the difference is the point. The one-query form
                 is what a person should run in the Explorer; the five are what
                 this backend had to execute to draw the canvas above. -->
            <div class="rounded-md border border-border">
              <button type="button"
                      class="flex w-full items-center justify-between px-2.5 py-1.5 font-mono
                             text-[10.5px] text-muted-foreground hover:bg-muted/40"
                      @click="queriesOpen = !queriesOpen">
                <span>{{ queriesOpen ? '▾' : '▸' }} the Cypher — one query for the Explorer,
                  {{ graph.queries.length }} for this canvas</span>
                <span class="text-[10px]">{{ queriesOpen ? 'hide' : 'show' }}</span>
              </button>
              <div v-if="queriesOpen" class="flex flex-col gap-2 border-t border-border p-2">
                <p class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  one query · run this in the Visual Graph Explorer
                </p>
                <pre class="max-h-72 overflow-auto rounded-md bg-muted/40 p-2.5 font-mono
                            text-[10.5px] leading-relaxed">{{ graph.explorer_cypher }}</pre>
                <p class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">
                  the {{ graph.queries.length }} that drew the canvas above
                </p>
                <pre class="max-h-72 overflow-auto rounded-md bg-muted/40 p-2.5 font-mono
                            text-[10.5px] leading-relaxed">{{ allCypher }}</pre>
              </div>
            </div>
          </template>

          <div class="rounded-lg border border-dashed border-border px-3.5 py-2.5 text-[11.5px] leading-relaxed text-muted-foreground">
            <p><b class="text-foreground">The drug route is not a model feature.</b> No feature
              traverses a drug node, so nothing on that route fed the score. It <b class="text-foreground">is</b>
              one of three routes admitting a pair into the candidate pool, so it shaped the population
              that got scored — <i>not a feature</i>, never <i>not used</i>. Only `indication` and
              `drug_investigated_for` exist here; contraindication was never built.</p>
            <p class="mt-1.5"><b class="text-foreground">Why five queries here and one in the Explorer.</b>
              As a single query the <code class="font-mono text-[10.5px]">OPTIONAL MATCH</code> clauses
              <b class="text-foreground">multiply</b> rows rather than adding them, and
              <code class="font-mono text-[10.5px]">LIMIT</code> bounds the output, not the join. The
              <b class="text-foreground">Visual Graph Explorer runs it in about a second</b> — it talks to
              Kuzu directly. This card cannot: its only path is the graph agent tool, whose Kuzu runs in a
              memory-capped kernel and answers <i>“the buffer pool is full”</i> after a minute or more. So
              the canvas is drawn from the five routes run separately and merged, and the copy button hands
              you the single query for the Explorer.</p>
            <p class="mt-1.5">Traversal is <b class="text-foreground">undirected</b>; relationship variables
              must be <b class="text-foreground">bound and returned</b> or the canvas shows floating nodes;
              the engine's label for genes is <code class="font-mono text-[10.5px]">protein</code>. The two
              GO routes cap the term's own degree at 200, or a hub like <i>protein binding</i> matches
              everything and means nothing. Node indices are snapshot-specific and generated from the live
              row. Run these in the interactive explorer, never a query recipe.</p>
          </div>
        </div>
      </ActCard>
    </div>
  </div>
</template>
