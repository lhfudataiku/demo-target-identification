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
  import type {
    DefaultLabelFormatterCallbackParams,
    EChartsOption,
    TooltipComponentFormatterCallbackParams,
  } from 'echarts'
  import { categoricalColors, resolveColour, seriesVar } from '@/utils/seriesColours'

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
    { color: seriesVar('measured'), multicolour: false, rowHeight: 22 },
  )

  const height = computed(() => Math.max(120, props.rows.length * props.rowHeight + 28))

  // ECharts renders to canvas and cannot resolve CSS custom properties (nor the
  // kit's space-separated hsl()), so every colour is resolved to rgb() first.
  const resolved = computed(() => resolveColour(props.color))

  const option = computed((): EChartsOption => ({
    grid: { left: 4, right: 56, top: 4, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'item',
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const entry = Array.isArray(params) ? params[0] : params
        const r = entry && props.rows[entry.dataIndex]
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
        fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 11, color: resolveColour('var(--muted-foreground)'),
        width: 190, overflow: 'truncate',   // long disease names must not eat the plot
      },
    },
    series: [{
      type: 'bar',
      data: props.rows.map((r) => (r.colour
        ? { value: r.count, itemStyle: { color: resolveColour(r.colour) } }
        : r.count)),
      itemStyle: { borderRadius: [0, 3, 3, 0] },
      colorBy: props.multicolour ? 'data' : 'series',
      color: props.multicolour
        ? categoricalColors()
        : resolved.value,
      barMaxWidth: 14,
      label: {
        show: true, position: 'right',
        formatter: (params: DefaultLabelFormatterCallbackParams) =>
          typeof params.value === 'number' ? params.value.toLocaleString() : String(params.value ?? ''),
        fontFamily: 'ui-monospace, SFMono-Regular, monospace', fontSize: 11,
      },
    }],
  }))
</script>

<template>
  <VChart :option="option" :style="{ height: height + 'px', width: '100%' }" autoresize />
</template>
