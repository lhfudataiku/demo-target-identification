<script setup lang="ts">
  /**
   * Node-link graph — the renderer for Act 1's "Explore the graph".
   *
   * Draws the `customData.graph` payload the visual-graph agent tool returns.
   * vis-network does the drawing; this file is the glue, and it deliberately
   * reproduces the plugin's own wrapper so a subgraph looks the same here as it
   * does in an Agent Hub answer:
   *
   *  - the forceAtlas2Based physics block, verbatim;
   *  - `withUniqueRenderedEdgeIds` -- the payload can repeat an edge id, and
   *    vis silently drops duplicates, so repeats get a suffix;
   *  - `withCurvedParallelEdges` -- PPI is DOUBLE-STORED in this graph (which
   *    is why the degree recipes divide by 2), so parallel edges are the norm,
   *    not the exception. Without curving they stack into one line and a
   *    six-protein neighbourhood looks like three.
   *
   * Colour keys on `group_name`, NOT on the payload's own `nodes_view`.
   * `nodes_view` is keyed by `group_id` -- an opaque per-build hash like
   * "cPkSWg" -- so a graph rebuild would resilently recolour the legend.
   * `group_name` ("protein", "disease") is stable and semantic.
   */
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  // The STANDALONE build, deliberately. The lighter "peer" build needs six peer
  // packages and injects no CSS -- with `component-emitter` absent and no
  // stylesheet, it produced a silent blank canvas. Standalone is self-contained
  // and ships its own styles, so both failure modes go away together.
  import { DataSet, Network } from 'vis-network/standalone'

  defineOptions({ name: 'ActGraph' })

  export interface GraphNode { id: string; label: string; group_name: string }
  export interface GraphEdge { id: string; src: string; dst: string; group_name: string }

  const props = withDefaults(
    defineProps<{
      nodes: GraphNode[]
      edges: GraphEdge[]
      height?: number
    }>(),
    { height: 420 },
  )

  /* group_name -> design token. The tokens live in styles/tokens.css so both
     themes are defined in one place; this map only says which token a node type
     wears. Canvas cannot use Tailwind classes, so the values are resolved at
     draw time via token(), exactly as ActBand and ActSankey do. */
  const GROUP_TOKEN: Record<string, string> = {
    protein: '--graph-protein',
    disease: '--graph-disease',
    drug: '--graph-drug',
    pathway: '--graph-pathway',
    phenotype: '--graph-phenotype',
    'effect/phenotype': '--graph-phenotype',
    biological_process: '--graph-bioprocess',
    molecular_function: '--graph-molfunc',
    cellular_component: '--graph-cellcomp',
  }

  const el = ref<HTMLDivElement | null>(null)
  let network: Network | null = null

  const CURVE_STEP = 0.2
  const RENDERED = '__rendered_'

  /** A repeated edge id is dropped by vis; suffix the repeats so all survive. */
  function withUniqueRenderedEdgeIds<T extends { id: string }>(edges: T[]): T[] {
    const total = new Map<string, number>()
    const seen = new Map<string, number>()
    for (const e of edges) total.set(e.id, (total.get(e.id) ?? 0) + 1)
    return edges.map((e) => {
      if ((total.get(e.id) ?? 0) < 2) return e
      const n = (seen.get(e.id) ?? 0) + 1
      seen.set(e.id, n)
      return { ...e, id: `${e.id}${RENDERED}${n}` }
    })
  }

  /** Fan parallel edges apart so a double-stored PPI pair reads as two edges. */
  function withCurvedParallelEdges<T extends { from: string; to: string }>(edges: T[]) {
    const byPair = new Map<string, T[]>()
    for (const e of edges) {
      const k = `${e.from}->${e.to}`
      const bucket = byPair.get(k)
      if (bucket) bucket.push(e)
      else byPair.set(k, [e])
    }
    return edges.map((e) => {
      const same = byPair.get(`${e.from}->${e.to}`) ?? []
      const reverse = byPair.get(`${e.to}->${e.from}`) ?? []
      if (same.length < 2 && reverse.length === 0) return e
      const i = same.indexOf(e)
      return {
        ...e,
        smooth: { enabled: true, type: 'curvedCW', roundness: 0.1 + (i * CURVE_STEP) / same.length },
      }
    })
  }

  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f

  function options() {
    const fg = token('--foreground', '#1A1A1A')
    return {
      autoResize: false,                       // we drive resize ourselves
      interaction: { hover: true, hoverConnectedEdges: true, tooltipDelay: 120 },
      nodes: {
        shape: 'dot', size: 13, borderWidth: 1.5,
        color: { border: token('--border', '#DAD9D3') },
        font: { color: fg, size: 12, face: 'Roboto, sans-serif' },
      },
      edges: {
        width: 1, color: { color: token('--chart-5', '#A8BCDD'), highlight: token('--chart-3', '#7092F2') },
        font: { size: 9, face: 'DM Mono, monospace', color: fg, strokeWidth: 3,
                strokeColor: token('--card', '#FEFEF9'), align: 'middle' },
        smooth: { enabled: false },
      },
      layout: { randomSeed: 10, improvedLayout: true, clusterThreshold: 200,
                hierarchical: { enabled: false } },
      physics: {
        enabled: true, solver: 'forceAtlas2Based',
        forceAtlas2Based: { theta: 0.5, gravitationalConstant: -100, centralGravity: 0.01,
                            springConstant: 0.08, springLength: 100, damping: 0.3, avoidOverlap: 0 },
        stabilization: { enabled: false },
      },
    }
  }

  /** The token a node type wears, resolved to a real colour for canvas. */
  const groupColor = (group: string) =>
    token(GROUP_TOKEN[group] ?? '--graph-other', '#C4C4BD')

  const legend = computed(() => {
    const seen = new Map<string, number>()
    for (const n of props.nodes) seen.set(n.group_name, (seen.get(n.group_name) ?? 0) + 1)
    return [...seen.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([group, n]) => ({ group, n, color: groupColor(group) }))
  })

  function draw() {
    if (!el.value) return
    network?.destroy()
    network = null
    if (!props.nodes.length) return

    const nodes = new DataSet(
      props.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        title: `${n.label}\n${n.group_name}`,
        color: { background: groupColor(n.group_name),
                 border: token('--border', '#DAD9D3') },
      })) as any[],
    )
    const raw = props.edges.map((e) => ({
      id: e.id, from: e.src, to: e.dst, title: e.group_name,
    }))
    const edges = new DataSet(withCurvedParallelEdges(withUniqueRenderedEdgeIds(raw)) as any[])

    network = new Network(el.value, { nodes, edges }, options() as any)
    resize()
  }

  function resize() {
    if (!network || !el.value) return
    const { clientWidth: w, clientHeight: h } = el.value
    if (w <= 0 || h <= 0) return
    network.setSize(`${w}px`, `${h}px`)
    network.redraw()
  }

  onMounted(() => {
    draw()
    window.addEventListener('resize', resize)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('resize', resize)
    network?.destroy()
    network = null
  })
  watch(() => [props.nodes, props.edges], draw, { deep: true })
</script>

<template>
  <div class="flex flex-col gap-2">
    <div ref="el" :style="{ height: height + 'px' }"
         class="w-full rounded-md border border-border bg-card" />

    <div v-if="legend.length" class="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10.5px]">
      <span v-for="l in legend" :key="l.group" class="flex items-center gap-1.5 text-muted-foreground">
        <span class="inline-block size-2.5 rounded-full border border-border"
              :style="{ background: l.color }" />
        {{ l.group }} <b class="text-primary-foreground">{{ l.n }}</b>
      </span>
    </div>
  </div>
</template>
