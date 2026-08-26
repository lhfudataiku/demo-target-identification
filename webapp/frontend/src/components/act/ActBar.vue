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
      rows: { label: string; count: number }[]
      color?: string
      /** px per bar; the chart grows with the data rather than scrolling. */
      rowHeight?: number
    }>(),
    { color: 'var(--chart-2)', rowHeight: 22 },
  )

  const height = computed(() => Math.max(120, props.rows.length * props.rowHeight + 28))

  // ECharts renders to canvas and cannot resolve CSS custom properties, so the
  // token is read off the document at build time.
  const resolved = computed(() => {
    const m = /^var\((--[\w-]+)\)$/.exec(props.color)
    if (!m) return props.color
    return getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || '#3EDAB2'
  })

  const option = computed((): EChartsOption => ({
    grid: { left: 4, right: 56, top: 4, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'item',
      valueFormatter: (v) => Number(v).toLocaleString(),
    },
    xAxis: { type: 'value', show: false },
    yAxis: {
      type: 'category',
      inverse: true,
      data: props.rows.map((r) => r.label),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 11, color: 'var(--muted-foreground)' },
    },
    series: [{
      type: 'bar',
      data: props.rows.map((r) => r.count),
      itemStyle: { color: resolved.value, borderRadius: [0, 3, 3, 0] },
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
