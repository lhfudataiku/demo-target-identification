<script setup lang="ts">
  /**
   * Interval plot — v3's `intervals`, on ECharts `custom`.
   *
   * An earlier pass drew this as static SVG to get v3's details right and lost
   * interactivity doing it. `renderItem` carries all of them and keeps hover,
   * tooltips and resize:
   *   - axis 0.6-1.06, not 0-1
   *   - a dashed ceiling at AUC = 1.0
   *   - whisker caps, or an ARROW where the interval runs past the ceiling
   *   - n= printed in the right gutter, with the overflowing hi value
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { CustomChart } from 'echarts/charts'
  import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([CustomChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActIntervals' })

  const props = defineProps<{
    rows: { label: string; value: number; lo: number; hi: number; n?: number; muted?: boolean }[]
  }>()

  const LO = 0.6, HI = 1.06, RH = 24
  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))
  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f
  const height = computed(() => Math.max(150, props.rows.length * RH + 46))

  const chartOption = computed((): EChartsOption => {
    const ok = token('--chart-3', '#7092F2')
    const bad = token('--destructive', '#B3261E')
    const dim = token('--muted-foreground', '#777')
    return {
      animationDuration: 600,
      grid: { left: 128, right: 84, top: 8, bottom: 28, containLabel: false },
      tooltip: {
        trigger: 'item',
        formatter: (p: { dataIndex: number }) => {
          const r = props.rows[p.dataIndex]
          if (!r) return ''
          return `<b>${r.label}</b><br/>AUC <b>${r.value.toFixed(3)}</b>` +
                 `<br/>95% interval ${r.lo.toFixed(3)} – ${r.hi.toFixed(3)}` +
                 `<br/>associated targets: ${r.n ?? 0}` +
                 (r.muted ? '<br/><i>interval too wide to quote as a score</i>' : '')
        },
      },
      xAxis: {
        type: 'value', min: LO, max: HI,
        splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
        axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 9.5, color: 'var(--muted-foreground)' },
      },
      yAxis: {
        type: 'category', inverse: true, data: props.rows.map((r) => r.label),
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: {
          fontSize: 11, width: 120, overflow: 'truncate',
          color: (_v: string, i: number) => (props.rows[i]?.muted ? bad : dim),
        },
      },
      series: [{
        type: 'custom',
        renderItem: (params, api) => {
          // NOT api.value(7): with `encode` set, only the encoded dimensions are
          // addressable by index and the rest read back as 0 — which is where
          // the n=0 in the gutter came from. dataIndex is exact.
          const row = props.rows[params.dataIndex]
          const cat = api.value(0) as number
          const muted = !!row.muted
          const colour = muted ? bad : ok
          const v = api.coord([api.value(1), cat])
          const lo = api.coord([api.value(2), cat])
          const rawHi = row.hi
          const over = rawHi > 1.0
          const hi = api.coord([Math.min(rawHi, HI), cat])
          const n = row.n ?? 0
          const width = api.getWidth()
          const children: unknown[] = [
            { type: 'line', shape: { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1] },
              style: { stroke: colour, lineWidth: 1.5 } },
            { type: 'line', shape: { x1: lo[0], y1: lo[1] - 4, x2: lo[0], y2: lo[1] + 4 },
              style: { stroke: colour, lineWidth: 1.5 } },
            over
              // past the ceiling: an arrow, not a cap — the value is unpinned
              ? { type: 'polygon', shape: { points: [[hi[0], hi[1] - 5], [hi[0] + 7, hi[1]], [hi[0], hi[1] + 5]] },
                  style: { fill: colour } }
              : { type: 'line', shape: { x1: hi[0], y1: hi[1] - 4, x2: hi[0], y2: hi[1] + 4 },
                  style: { stroke: colour, lineWidth: 1.5 } },
            { type: 'circle', shape: { cx: v[0], cy: v[1], r: 3.4 }, style: { fill: colour } },
            { type: 'text', style: {
                x: width - 6, y: v[1] - 6, textAlign: 'right',
                text: `n=${n}` + (over ? `  hi ${rawHi.toFixed(3)}` : ''),
                fill: muted ? bad : dim, font: '9.5px "DM Mono", monospace' } },
          ]
          return { type: 'group', children }
        },
        encode: { x: [1, 2, 3], y: 0 },
        data: props.rows.map((r, i) =>
          [i, r.value, r.lo, r.hi, r.muted ? 1 : 0, 0, r.label, r.n ?? 0]),
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: bad, type: 'dashed', width: 1 },
          label: {
            formatter: 'AUC = 1.0, the ceiling', position: 'insideEndBottom',
            fontFamily: 'DM Mono, monospace', fontSize: 9, color: bad,
          },
          data: [{ xAxis: 1.0 }],
        },
      }],
    }
  })
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
