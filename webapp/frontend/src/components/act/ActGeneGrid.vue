<script setup lang="ts">
  /**
   * Gene membership grid — v3's `geneGrid`.
   *
   * A plain CSS grid, deliberately: it is a table of labelled cells, not a
   * chart. ECharts would add a canvas, lose text selection and gain nothing.
   */
  defineOptions({ name: 'ActGeneGrid' })

  withDefaults(
    defineProps<{
      /** `groups` marks which column-set a gene belongs to; drives the tint. */
      genes: { name: string; group: string }[]
      legend?: { group: string; label: string; colour: string }[]
    }>(),
    { legend: () => [] },
  )
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="grid gap-1"
         style="grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); max-height: 340px; overflow-y: auto">
      <span v-for="g in genes" :key="g.name"
            class="truncate rounded px-1.5 py-1 text-center font-mono text-[11px]"
            :style="{
              background: `color-mix(in oklab, ${legend.find((l) => l.group === g.group)?.colour ?? 'var(--muted)'} 22%, var(--card))`,
              color: 'var(--foreground)',
            }"
            :title="g.name">{{ g.name }}</span>
    </div>
    <div v-if="legend.length" class="flex flex-wrap gap-4 font-mono text-[10.5px] text-muted-foreground">
      <span v-for="l in legend" :key="l.group" class="flex items-center gap-1.5">
        <span class="inline-block size-2.5 rounded-sm" :style="{ background: l.colour }"></span>{{ l.label }}
      </span>
    </div>
  </div>
</template>
