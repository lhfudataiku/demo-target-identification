<script setup lang="ts">
  /**
   * Beeswarm — v3's `beeswarm`: every disease as a point, so the DISTRIBUTION
   * leads and the summary follows. Scatter with deterministic vertical jitter;
   * the quartile box is drawn as a markArea so the spread reads at a glance.
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { ScatterChart } from 'echarts/charts'
  import { GridComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([ScatterChart, GridComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActBeeswarm' })

  const props = withDefaults(
    defineProps<{ points: { label: string; value: number }[]; min?: number; max?: number
                  unit?: string; height?: number }>(),
    { min: 0, max: 1, unit: 'AUC', height: 200 },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))
  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f

  const stats = computed(() => {
    const v = props.points.map((p) => p.value).sort((a, b) => a - b)
    const q = (p: number) => v[Math.min(v.length - 1, Math.floor(p * v.length))]
    return { q1: q(0.25), med: q(0.5), q3: q(0.75) }
  })

  const chartOption = computed((): EChartsOption => {
    const accent = token('--chart-2', '#3EDAB2')
    // Deterministic jitter: a hash of the index, so the swarm is stable across
    // renders rather than reshuffling on every repaint.
    const pts = props.points.map((p, i) =>
      [p.value, ((Math.sin(i * 12.9898) * 43758.5453) % 1 + 1) % 1, p.label])
    return {
      animationDuration: 700,
      grid: { left: 8, right: 8, top: 10, bottom: 28, containLabel: true },
      tooltip: {
        trigger: 'item',
        // The label travels as the third element so the hover names the disease.
        formatter: (p: { value: [number, number, string] }) =>
          `<b>${p.value[2]}</b><br/>${props.unit} ${p.value[0].toFixed(2)}`,
      },
      xAxis: {
        type: 'value', min: props.min, max: props.max, name: props.unit,
        nameLocation: 'middle', nameGap: 20,
        nameTextStyle: { fontFamily: 'DM Mono, monospace', fontSize: 10 },
        splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
        axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 10, color: 'var(--muted-foreground)' },
      },
      yAxis: { type: 'value', min: -0.15, max: 1.15, show: false },
      series: [{
        type: 'scatter', symbolSize: 5, data: pts,
        itemStyle: { color: accent, opacity: 0.5 },
        markArea: {
          silent: true,
          itemStyle: { color: accent, opacity: 0.09 },
          data: [[{ xAxis: stats.value.q1 }, { xAxis: stats.value.q3 }]],
        },
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { color: accent, width: 2 },
          label: {
            formatter: `median ${stats.value.med.toFixed(3)}`,
            fontFamily: 'DM Mono, monospace', fontSize: 10, position: 'insideEndTop',
          },
          data: [{ xAxis: stats.value.med }],
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
