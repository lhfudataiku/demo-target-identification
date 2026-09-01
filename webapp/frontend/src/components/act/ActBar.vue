<script setup lang="ts">
  /**
   * Horizontal bar chart on ECharts (already a dependency via vue-echarts).
   *
   * Replaces the hand-rolled CSS-width bars: this gets tooltips, proper value
   * axes and consistent typography for free, and matches the charting the
   * template already uses elsewhere.
   */
  import { computed } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { BarChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActBar' })

  const props = withDefaults(
    defineProps<{
      /** `colour` on a row wins, so a card can colour by GROUP as v3 does. */
      rows: { label: string; count: number; colour?: string; note?: string }[]
      color?: string
      /** Cycle the chart palette across bars, as the mockup does, instead of
          painting every bar one colour. */
      multicolour?: boolean
      /** px per bar; the chart grows with the data rather than scrolling. */
      rowHeight?: number
    }>(),
    { color: 'var(--chart-2)', multicolour: false, rowHeight: 22 },
  )

  const PALETTE = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5']

  const height = computed(() => Math.max(120, props.rows.length * props.rowHeight + 28))

  // ECharts renders to canvas and cannot resolve CSS custom properties, so the
  // token is read off the document at build time.
  const resolve = (c: string) => {
    const m = /^var\((--[\w-]+)\)$/.exec(c)
    if (!m) return c
    return getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || '#3EDAB2'
  }
  const resolved = computed(() => resolve(props.color))

  const option = computed((): EChartsOption => ({
    grid: { left: 4, right: 56, top: 4, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (p: { dataIndex: number }) => {
        const r = props.rows[p.dataIndex]
        return r ? `<b>${r.label}</b><br/>${r.count.toLocaleString()}`
                   + (r.note ? `<br/>${r.note}` : '') : ''
      },
    },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      inverse: true,
      data: props.rows.map((r) => r.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        fontFamily: 'DM Mono, monospace', fontSize: 11, color: 'var(--muted-foreground)',
        width: 190, overflow: 'truncate',   // long disease names must not eat the plot
      },
    },
    series: [{
      type: 'bar',
      data: props.rows.map((r) => (r.colour
        ? { value: r.count, itemStyle: { color: resolve(r.colour) } }
        : r.count)),
      itemStyle: { borderRadius: [0, 3, 3, 0] },
      colorBy: props.multicolour ? 'data' : 'series',
      color: props.multicolour
        ? PALETTE.map((v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim())
        : resolved.value,
      barMaxWidth: 14,
      label: {
        show: true, position: 'right',
        formatter: (p: { value: number }) => Number(p.value).toLocaleString(),
        fontFamily: 'DM Mono, monospace', fontSize: 11,
      },
    }],
  }))
</script>

<template>
  <VChart :option="option" :style="{ height: height + 'px', width: '100%' }" autoresize />
</template>
