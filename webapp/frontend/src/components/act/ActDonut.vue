<script setup lang="ts">
  /**
   * Donut — follows the template's RoutingMixDonut conventions (ready/nextTick
   * guard, radius/center, roundRect legend, borderRadius 6) with brand tokens
   * instead of its hard-coded hsl() palette.
   *
   * v3 draws this card with `hbars`; the donut is a deliberate change, because
   * the point of "what the association evidence is" is the SHARE of each
   * evidence type, not the magnitude.
   */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { PieChart } from 'echarts/charts'
  import { LegendComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'

  use([PieChart, LegendComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActDonut' })

  const props = withDefaults(
    defineProps<{ rows: { label: string; count: number }[]; height?: number }>(),
    { height: 240 },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const PALETTE = ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5']
  const colors = computed(() =>
    PALETTE.map((v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim()))

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'item',
      formatter: (p: { name: string; value: number; percent: number }) =>
        `${p.name}<br/><b>${p.value.toLocaleString()}</b> (${p.percent.toFixed(1)}%)`,
    },
    legend: {
      type: 'scroll', orient: 'vertical', top: 'center', right: 0,
      itemWidth: 10, itemHeight: 10, icon: 'roundRect',
      textStyle: { fontSize: 11, color: 'var(--foreground)' },
    },
    series: [{
      type: 'pie',
      radius: ['56%', '82%'],
      center: ['34%', '50%'],
      label: { show: false },
      labelLine: { show: false },
      itemStyle: {
        borderRadius: 6,
        borderColor: 'color-mix(in oklab, white 85%, var(--card) 15%)',
        borderWidth: 1,
      },
      data: props.rows.map((r, i) => ({
        name: r.label, value: r.count,
        itemStyle: { color: colors.value[i % colors.value.length] },
      })),
    }],
  }))
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
