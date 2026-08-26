<script setup lang="ts">
  /** Heat matrix — v3's `matrix`: pairwise top-50 overlap between subtypes. */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { HeatmapChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent, VisualMapComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([HeatmapChart, GridComponent, TooltipComponent, VisualMapComponent, CanvasRenderer])
  defineOptions({ name: 'ActMatrix' })

  const props = withDefaults(
    defineProps<{
      labels: string[]
      /** [x, y, value] triples; the diagonal is omitted by the caller. */
      cells: [number, number, number][]
      max?: number
      unitLabel?: string
    }>(),
    { max: 50, unitLabel: 'of 50' },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const short = computed(() => props.labels.map((l) => (l.length > 22 ? l.slice(0, 21) + '…' : l)))
  const height = computed(() => Math.max(220, props.labels.length * 26 + 130))

  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 700,
    tooltip: {
      position: 'top',
      formatter: (p: { value: [number, number, number] }) =>
        `${props.labels[p.value[1]]}<br/>vs ${props.labels[p.value[0]]}<br/>` +
        `<b>${p.value[2]}</b> ${props.unitLabel}`,
    },
    grid: { left: 4, right: 12, top: 88, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category', data: short.value, position: 'top',
      axisLine: { show: false }, axisTick: { show: false }, splitArea: { show: true },
      axisLabel: {
        rotate: 42, fontFamily: 'DM Mono, monospace', fontSize: 10,
        color: 'var(--muted-foreground)',
      },
    },
    yAxis: {
      type: 'category', data: short.value, inverse: true,
      axisLine: { show: false }, axisTick: { show: false }, splitArea: { show: true },
      axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 10, color: 'var(--muted-foreground)' },
    },
    visualMap: {
      min: 0, max: props.max, calculable: false, orient: 'horizontal',
      left: 'center', bottom: 0, itemWidth: 10, itemHeight: 90, show: false,
      inRange: { color: [token('--card', '#fff'), token('--chart-2', '#3EDAB2')] },
    },
    series: [{
      type: 'heatmap',
      data: props.cells,
      label: {
        show: true, formatter: (p: { value: [number, number, number] }) => String(p.value[2]),
        fontFamily: 'DM Mono, monospace', fontSize: 10,
      },
      itemStyle: { borderColor: 'var(--card)', borderWidth: 2 },
    }],
  }))
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
