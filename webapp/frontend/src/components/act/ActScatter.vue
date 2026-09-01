<script setup lang="ts">
  /** Scatter on ECharts, for the orthogonality plot. */
  import { computed } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { ScatterChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([ScatterChart, GridComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActScatter' })

  const props = defineProps<{
    points: { assoc: number; drug: number }[]
    xLabel: string
    yLabel: string
  }>()

  const token = (name: string, fallback: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback

  const option = computed((): EChartsOption => ({
    grid: { left: 46, right: 14, top: 12, bottom: 36 },
    tooltip: {
      trigger: 'item',
      formatter: (p: { value: number[] }) =>
        `assoc ${p.value[0].toFixed(3)}<br/>drug ${p.value[1].toFixed(3)}`,
    },
    xAxis: {
      type: 'value', min: 0, max: 1, name: props.xLabel, nameLocation: 'middle', nameGap: 22,
      nameTextStyle: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
      splitLine: { lineStyle: { opacity: 0.25 } },
      axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
    },
    yAxis: {
      type: 'value', min: 0, max: 1, name: props.yLabel, nameLocation: 'middle', nameGap: 32,
      nameTextStyle: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
      splitLine: { lineStyle: { opacity: 0.25 } },
      axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
    },
    series: [{
      type: 'scatter',
      symbolSize: 5,
      data: props.points.map((p) => [p.assoc, p.drug]),
      itemStyle: { color: token('--chart-3', '#7092F2'), opacity: 0.55 },
    }],
  }))
</script>

<template>
  <VChart :option="option" style="height: 300px; width: 100%" autoresize />
</template>
