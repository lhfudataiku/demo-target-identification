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
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Database, GitBranch, Layers, FileText } from 'lucide-vue-next'

  defineOptions({ name: 'EvidenceView' })

  interface Bar { label: string; count: number }
  interface Payload {
    node_types: Bar[]; relations: Bar[]; node_sources: Bar[]
    ppi_provenance: Bar[]; label_evidence: Bar[]
    totals: Record<string, number>
  }

  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)

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
