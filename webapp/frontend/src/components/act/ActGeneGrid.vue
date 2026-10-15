<script setup lang="ts">
  /**
   * Gene × term membership grid — v3's `geneGrid`, as a CSS grid.
   *
   * The information is the RANK, not mere membership: dot size and opacity
   * encode it (≤10 largest/opaque, ≤25 middle, else small/faint), exactly as v3
   * does, and the hover names the gene, the term and the rank.
   *
   * Genes flow down columns of 30, so a long list reads as several short
   * columns rather than one unscannable strip.
   */
  import { computed } from 'vue'
  import { seriesVar } from '@/utils/seriesColours'

  defineOptions({ name: 'ActGeneGrid' })

  const props = withDefaults(
    defineProps<{
      genes: { name: string; ranks: Record<string, number>; n_terms: number }[]
      columns: string[]
      perCol?: number
      /** A gene in at least this many terms counts as shared programme. */
      sharedAt?: number
    }>(),
    { perCol: 30, sharedAt: 3 },
  )

  const groups = computed(() => {
    const out: (typeof props.genes)[] = []
    for (let i = 0; i < props.genes.length; i += props.perCol)
      out.push(props.genes.slice(i, i + props.perCol))
    return out
  })
  const dot = (rank: number) =>
    rank <= 10 ? { size: 10, op: 0.95 } : rank <= 25 ? { size: 8, op: 0.7 } : { size: 6, op: 0.45 }
  const short = (l: string) => (l.length > 16 ? l.slice(0, 15) + '…' : l)
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex gap-6 overflow-x-auto pb-1">
      <div v-for="(g, gi) in groups" :key="gi" class="flex-none">
        <!-- rotated term headers -->
        <div class="flex" style="padding-left: 86px">
          <div v-for="c in columns" :key="'h' + gi + c" class="relative h-16 w-3.75 flex-none">
            <span class="absolute bottom-0 left-1/2 origin-bottom-left -rotate-60 whitespace-nowrap
                         font-mono grid-tick text-muted-foreground" :title="c">{{ short(c) }}</span>
          </div>
        </div>
        <div v-for="row in g" :key="row.name" class="flex items-center">
          <div class="w-21.5 flex-none truncate pr-1.5 text-right font-mono grid-gene"
               :class="row.n_terms >= sharedAt ? 'text-muted-foreground' : ''"
               :style="row.n_terms >= sharedAt ? undefined : { color: seriesVar('highlight') }"
               :title="`${row.name} — in ${row.n_terms} of ${columns.length} subtypes`">{{ row.name }}</div>
          <!-- the title lives on the CELL, not the dot: a 6px dot is not a
               hover target, which is why the tooltip never appeared. -->
          <div v-for="c in columns" :key="row.name + c"
               class="grid h-3.75 w-3.75 flex-none cursor-default place-items-center"
               :title="row.ranks[c] ? `${row.name} — ${c} · rank ${row.ranks[c]}`
                                    : `${row.name} — ${c} · not in top 50`">
            <span v-if="row.ranks[c]"
                  class="block rounded-full"
                  :style="{
                    width: dot(row.ranks[c]).size + 'px',
                    height: dot(row.ranks[c]).size + 'px',
                    background: row.n_terms >= sharedAt ? seriesVar('contrast') : seriesVar('highlight'),
                    opacity: dot(row.ranks[c]).op,
                  }" />
          </div>
        </div>
      </div>
    </div>
    <div class="flex flex-wrap gap-4 font-mono text-2xs text-muted-foreground">
      <span class="flex items-center gap-1.5">
        <span class="inline-block size-2.5 rounded-full" :style="{ background: seriesVar('contrast') }"></span>
        in {{ sharedAt }}+ terms — the common programme
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block size-2.5 rounded-full" :style="{ background: seriesVar('highlight') }"></span>
        subtype-specific
      </span>
      <span>dot size and opacity encode rank · hover for the number</span>
    </div>
  </div>
</template>

<style scoped>
/* Chart-internal label sizes, set here as the canvas charts set theirs in their
   options: 15px cells and 60°-rotated subtype headers do not fit the type
   scale's smallest step (11px). Declared in eslint.config.js. */
.grid-tick {
  font-size: 8.5px;
}
.grid-gene {
  font-size: 9px;
}
</style>
