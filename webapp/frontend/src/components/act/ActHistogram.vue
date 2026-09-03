<script setup lang="ts">
  /**
   * Vertical histogram — v3's `histogram`: binned counts on a value axis.
   * Distinct from ActBar (horizontal, categorical): a histogram's x axis is
   * continuous, so the bins touch and the axis reads as a scale.
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { BarChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'

  use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActHistogram' })

  const props = withDefaults(
    defineProps<{ bins: { lo: number; hi: number; n: number }[]; xLabel?: string; height?: number }>(),
    { xLabel: '', height: 210 },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))
  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 700,
    grid: { left: 34, right: 10, top: 10, bottom: 30 },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const entry = Array.isArray(params) ? params[0] : params
        const bin = entry && props.bins[entry.dataIndex]
        if (!entry || !bin) return ''
        const value = typeof entry.value === 'number' ? entry.value : ''
        return `${bin.lo.toFixed(2)} – ${bin.hi.toFixed(2)}<br/><b>${value}</b>`
      },
    },
    xAxis: {
      type: 'category',
      data: props.bins.map((b) => b.lo.toFixed(2)),
      name: props.xLabel, nameLocation: 'middle', nameGap: 20,
      nameTextStyle: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
      axisTick: { alignWithLabel: true },
      axisLabel: {
        fontFamily: 'DM Mono, monospace', fontSize: 9, color: 'var(--muted-foreground)',
        interval: (i: number) => i % 4 === 0,
      },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
      axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 9, color: 'var(--muted-foreground)' },
    },
    series: [{
      type: 'bar',
      data: props.bins.map((b) => b.n),
      barCategoryGap: '2%',            // bins touch: this is a distribution, not categories
      itemStyle: { color: token('--chart-2', '#3EDAB2'), borderRadius: [2, 2, 0, 0] },
    }],
  }))
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
