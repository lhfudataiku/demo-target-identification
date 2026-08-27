<script setup lang="ts">
  /**
   * Pairwise overlap matrix — a plain CSS grid, dynamically tinted.
   *
   * The ECharts heatmap was unreadable at this size: rotated category labels
   * collided and the value labels fought the cells. v3 draws it as SVG cells
   * with `fill-opacity = 0.08 + t * 0.9` and the value printed inside; a CSS
   * grid does the same with real text, selectable labels and native tooltips.
   */
  import { computed } from 'vue'

  defineOptions({ name: 'ActMatrix' })

  const props = withDefaults(
    defineProps<{
      labels: string[]
      pairs: { a: string; b: string; shared: number }[]
      unit?: number
    }>(),
    { unit: 50 },
  )

  const lookup = computed(() => {
    const m = new Map<string, number>()
    for (const p of props.pairs) {
      m.set(`${p.a}|${p.b}`, p.shared)
      m.set(`${p.b}|${p.a}`, p.shared)
    }
    return m
  })
  const max = computed(() => Math.max(1, ...props.pairs.map((p) => p.shared)))
  const short = (l: string) => (l.length > 26 ? l.slice(0, 25) + '…' : l)
</script>

<template>
  <div class="overflow-x-auto">
    <div class="inline-block min-w-full">
      <!-- header row: rotated labels, given real height so they cannot collide -->
      <div class="flex" :style="{ paddingLeft: '190px' }">
        <div v-for="l in labels" :key="'h' + l"
             class="relative h-[104px] w-[30px] flex-none">
          <span class="absolute bottom-1 left-1/2 origin-bottom-left -rotate-[52deg] whitespace-nowrap
                       font-mono text-[9.5px] text-muted-foreground"
                :title="l">{{ short(l) }}</span>
        </div>
      </div>

      <div v-for="a in labels" :key="a" class="flex items-center">
        <div class="w-[190px] flex-none truncate pr-2 text-right text-[11px]" :title="a">{{ a }}</div>
        <div v-for="b in labels" :key="a + '|' + b" class="w-[30px] flex-none p-[1px]">
          <div v-if="a === b" class="grid h-[26px] place-items-center rounded-sm bg-muted"></div>
          <div v-else
               class="grid h-[26px] place-items-center rounded-sm font-mono text-[9.5px]"
               :style="{
                 background: `color-mix(in oklab, var(--chart-3) ${(8 + ((lookup.get(a + '|' + b) ?? 0) / max) * 90).toFixed(0)}%, var(--card))`,
                 color: ((lookup.get(a + '|' + b) ?? 0) / max) > 0.55
                   ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
               }"
               :title="`${a} × ${b}: ${lookup.get(a + '|' + b) ?? 0} of ${unit}`">
            {{ lookup.get(a + '|' + b) ?? 0 }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
