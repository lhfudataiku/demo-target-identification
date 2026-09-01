<script setup lang="ts">
  /**
   * Proportion band — the top half of v3's `poolFlow`: what share of a
   * population passes a gate. One stacked horizontal bar with the eligible
   * portion highlighted and the excluded remainder muted.
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { BarChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActBand' })

  const props = defineProps<{
    inLabel: string; inValue: number
    outLabel: string; outValue: number
  }>()

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))
  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 700,
    grid: { left: 0, right: 0, top: 4, bottom: 4, containLabel: false },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps: { seriesName: string; value: number }[]) =>
        ps.map((p) => `${p.seriesName}: <b>${p.value.toLocaleString()}</b>`).join('<br/>'),
    },
    xAxis: { type: 'value', show: false, max: props.inValue + props.outValue },
    yAxis: { type: 'category', show: false, data: [''] },
    series: [
      { name: props.inLabel, type: 'bar', stack: 'g', barWidth: 26, data: [props.inValue],
        itemStyle: { color: token('--chart-2', '#3EDAB2'), borderRadius: [3, 0, 0, 3] } },
      { name: props.outLabel, type: 'bar', stack: 'g', data: [props.outValue],
        itemStyle: { color: token('--muted', '#EEEDEA'), borderRadius: [0, 3, 3, 0] } },
    ],
  }))
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="h-[34px] w-full">
      <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
    </div>
    <div class="flex justify-between font-mono text-[10.5px]">
      <span class="text-primary-foreground">
        <b>{{ inValue.toLocaleString() }}</b> {{ inLabel }}
      </span>
      <span class="text-muted-foreground">
        <b>{{ outValue.toLocaleString() }}</b> {{ outLabel }}
      </span>
    </div>
  </div>
</template>
