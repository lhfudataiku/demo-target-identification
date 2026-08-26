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
  import ActSay from '@/components/act/ActSay.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { ShieldCheck, Database, GitBranch, Layers, FileText } from 'lucide-vue-next'

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
      <ActCard span="col-span-12" :icon="ShieldCheck" accent="var(--chart-1)"
               title="What this demo claims — and what it does not"
               desc="Say this before anything else. Every row is a place a competitor would overclaim.">
        <ActSay class="mb-3">
          <b>The claim.</b> From public knowledge alone, this reconstructs the targets a disease's
          field has already validated. The test is your own eyeball test on a disease you know — not
          a benchmark we chose. <b>If it reconstructs what is established, the machinery is sound</b>,
          and the interesting conversation is pointing it at data where the answer is not already
          known. That is your data, not ours.
        </ActSay>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>We are not claiming</TableHead>
              <TableHead>What is true instead</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="[claim, truth] in NOT_CLAIMING" :key="claim">
              <TableCell class="align-top font-medium whitespace-nowrap">{{ claim }}</TableCell>
              <TableCell class="align-top text-muted-foreground">{{ truth }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </ActCard>

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

      <ActCard v-for="[key, title, desc, src] in [
                 ['node_types', 'What kinds of thing the graph knows about', 'Eight node types.', 'graph_node_type_counts'],
                 ['relations', 'Every relation, and its count', 'Eighteen relations. The seven largest match GRAPH_BUILDING.md §7.1 exactly.', 'graph_relation_counts'],
                 ['node_sources', 'Where the nodes came from', 'Six external vocabularies, and one grouping we derived ourselves.', 'graph_node_source_counts'],
                 ['ppi_provenance', 'Every PPI edge knows its source', 'Which interaction databases asserted each edge — this is the lineage claim, made concrete.', 'graph_ppi_provenance'],
                 ['label_evidence', 'What “known target” actually means', 'The evidence types behind the association label. Not all of it is equally strong, and act 5 returns to that.', 'graph_label_evidence'],
               ] as [keyof Payload, string, string, string]"
               :key="key" span="col-span-12 lg:col-span-6" :title="title" :desc="desc"
               :chips="[['live', 'live']]" :src="[src]">
        <ActBar v-if="data" :rows="(data[key] as Bar[])" />
        <p v-else class="py-4 text-center text-sm text-muted-foreground">Loading…</p>
      </ActCard>

      <ActCard span="col-span-12" :icon="FileText" accent="var(--chart-5)"
               title="What this act must not do"
               desc="Provenance is not accuracy.">
        <p class="text-[13px] leading-relaxed text-muted-foreground">
          The graph being faithfully reproduced says nothing about whether the ranking is useful —
          that is act 2's job. Nothing on this screen is a quality claim, and it should not be
          presented as one. What it establishes is that the substrate is credible and traceable,
          which is the precondition for the interrogation that follows.
        </p>
      </ActCard>
    </div>
  </div>
</template>
