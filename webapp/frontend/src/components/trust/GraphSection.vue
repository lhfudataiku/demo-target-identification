<script setup lang="ts">
  /**
   * Section 1 — what the model can see (Act 1, formerly seven cards).
   *
   * Up front: the graph's totals, provenance on every interaction, and what
   * "known target" means. Under "Show the detail": node types, node sources and
   * relations. "Explore the graph yourself" moved to the shortlist's Explorer card.
   */
  import { computed, ref } from 'vue'
  import { Button, Collapsible, CollapsibleContent, CollapsibleTrigger } from '@dataiku/ea-ui-kit'
  import { ChevronDown, ChevronRight } from '@dataiku/vue-icons'
  import ActTerm from '@/components/act/ActTerm.vue'
  import BarList from './BarList.vue'
  import type { EvidencePayload } from './types'

  const props = defineProps<{ graph: EvidencePayload }>()
  const open = ref(false)
  const fmt = (n: number) => n.toLocaleString()
  const pct = (a: number, b: number) => `${((100 * a) / b).toFixed(1)}%`

  // MONDO_grouped is the graph's own grouping of MONDO terms, not a separate
  // source, so the headline counts six public sources where the table lists seven.
  const publicSources = computed(() => props.graph.node_sources.filter((s) => !s.label.endsWith('_grouped')))
  const tiles = computed(() => [
    [fmt(props.graph.totals.nodes), 'nodes'],
    [fmt(props.graph.totals.edges), 'edges'],
    [String(props.graph.totals.relations), 'relation types'],
    [String(publicSources.value.length), 'public sources'],
  ])

  const ppiTotal = computed(() => props.graph.ppi_provenance.reduce((s, r) => s + r.count, 0))
  const corroborated = computed(() =>
    props.graph.ppi_provenance.filter((r) => r.label.includes('+')).reduce((s, r) => s + r.count, 0))
  const SOURCE_NAME: Record<string, string> = { huri: 'HuRI', string: 'STRING', menche: 'Menche' }
  const ppiBars = computed(() => props.graph.ppi_provenance.map((r) => ({
    label: r.label.split('+').map((s) => SOURCE_NAME[s] ?? s).join(' + '),
    count: r.count,
    note: r.label.includes('+') ? 'Asserted by more than one interactome' : 'One interactome only',
  })))

  const labelBars = computed(() => props.graph.label_evidence.map((r) => ({
    label: r.label.includes('+') ? 'both' : r.label.replace(/_/g, ' '), count: r.count,
  })))
  const labelled = computed(() => props.graph.label_evidence.reduce((s, r) => s + r.count, 0))
  const diseaseProtein = computed(() => props.graph.relations.find((r) => r.label === 'disease_protein')?.count ?? 0)
</script>

<template>
  <div class="flex flex-col gap-5">
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div v-for="[n, l] in tiles" :key="l" class="rounded-lg border bg-card p-3">
        <p class="font-mono text-xl font-semibold tabular-nums">{{ n }}</p>
        <p class="text-xs text-muted-foreground">{{ l }}</p>
      </div>
    </div>

    <div class="grid gap-5 md:grid-cols-2">
      <section class="flex flex-col gap-2">
        <p class="text-sm font-semibold">Every interaction records its source</p>
        <p class="text-xs text-muted-foreground">
          Of {{ fmt(ppiTotal) }} protein interactions, <b class="text-foreground">{{ fmt(corroborated) }}
          ({{ pct(corroborated, ppiTotal) }})</b> are asserted by more than one independent
          <ActTerm t="interactome">interactome</ActTerm>, and the graph records which.
        </p>
        <BarList :items="ppiBars" unit="interactions" />
      </section>
      <section class="flex flex-col gap-2">
        <p class="text-sm font-semibold">What “known target” means</p>
        <p class="text-xs text-muted-foreground">
          The label the model learns from: a gene–disease <ActTerm t="association">association</ActTerm>
          backed by genetic association or somatic mutation evidence. {{ fmt(diseaseProtein - labelled) }} of
          {{ fmt(diseaseProtein) }} disease–gene edges carry no evidence type and are not counted here.
        </p>
        <BarList :items="labelBars" unit="annotated edges" />
      </section>
    </div>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2">
          <component :is="open ? ChevronDown : ChevronRight" class="size-4" /> Show the detail
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent class="grid gap-5 pt-2 md:grid-cols-2">
        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">What's in the graph</p>
          <BarList :items="graph.node_types" unit="nodes" />
          <p class="mt-3 text-sm font-semibold">Where the data came from</p>
          <BarList :items="graph.node_sources" unit="nodes" />
        </section>
        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">How things connect</p>
          <BarList :items="graph.relations" unit="edges" />
          <p class="mt-2 text-xs text-muted-foreground">
            Counts are accepted against the frozen <ActTerm t="primekg" /> reference rather than trusted from
            the build. Faithful assembly is a lineage property, not a claim about the model's quality.
          </p>
        </section>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
