<script setup lang="ts">
  /**
   * Interval plot — v3's `intervals`: a point estimate on its 95% interval,
   * one row per term. Drawn with ECharts `custom` because no built-in series
   * renders "line with a dot on it" per category.
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { CustomChart } from 'echarts/charts'
  import { GridComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([CustomChart, GridComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActIntervals' })

  const props = withDefaults(
    defineProps<{
      rows: { label: string; value: number; lo: number; hi: number; muted?: boolean; note?: string }[]
      /** Axis floor. Below chance is not a meaningful distinction for AUC. */
      min?: number
      max?: number
    }>(),
    { min: 0.4, max: 1 },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const token = (n: string, f: string) =>
    getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f
  // v3's `intervals`: rh 24, label gutter 118, value gutter 78.
  const height = computed(() => Math.max(150, props.rows.length * 24 + 40))

  const chartOption = computed((): EChartsOption => {
    const accent = token('--chart-2', '#3EDAB2')
    const muted = token('--muted-foreground', '#777')
    return {
      animationDuration: 700,
      grid: { left: 118, right: 78, top: 6, bottom: 26, containLabel: false },
      tooltip: {
        trigger: 'item',
        formatter: (p: { value: (string | number)[] }) =>
          `${p.value[0]}<br/><b>${Number(p.value[1]).toFixed(3)}</b> ` +
          `[${Number(p.value[2]).toFixed(3)}–${Number(p.value[3]).toFixed(3)}]`,
      },
      xAxis: {
        type: 'value', min: props.min, max: props.max,
        splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
        axisLabel: { fontFamily: 'DM Mono, monospace', fontSize: 10, color: 'var(--muted-foreground)' },
      },
      yAxis: {
        type: 'category', data: props.rows.map((r) => r.label), inverse: true,
        axisLine: { show: false }, axisTick: { show: false },
        axisLabel: {
          fontSize: 11, color: 'var(--foreground)', width: 112, overflow: 'truncate',
        },
      },
      series: [{
        type: 'custom',
        renderItem: (params, api) => {
          const cat = api.value(0) as number
          const v = api.coord([api.value(1), cat])
          const lo = api.coord([api.value(2), cat])
          const hi = api.coord([api.value(3), cat])
          const isMuted = api.value(4) === 1
          const colour = isMuted ? muted : accent
          return {
            type: 'group',
            children: [
              { type: 'line', shape: { x1: lo[0], y1: lo[1], x2: hi[0], y2: hi[1] },
                style: { stroke: colour, lineWidth: 3, opacity: isMuted ? 0.35 : 0.45 } },
              { type: 'circle', shape: { cx: v[0], cy: v[1], r: 4 },
                style: { fill: colour, opacity: isMuted ? 0.5 : 1 } },
              // The value sits in the right gutter, as v3 prints it.
              { type: 'text', style: {
                  x: api.getWidth() - 72, y: v[1] - 6,
                  text: (api.value(1) as number).toFixed(3),
                  fill: isMuted ? muted : 'var(--foreground)',
                  font: '11px "DM Mono", monospace' } },
            ],
          }
        },
        encode: { x: [1, 2, 3], y: 0 },
        data: props.rows.map((r, i) => [i, r.value, r.lo, r.hi, r.muted ? 1 : 0, r.label]),
      }],
    }
  })
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
