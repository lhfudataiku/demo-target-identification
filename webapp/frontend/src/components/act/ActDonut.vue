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
  import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'
  import { categoricalColors, resolveColour } from '@/utils/seriesColours'

  use([PieChart, LegendComponent, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActDonut' })

  const props = withDefaults(
    defineProps<{ rows: { label: string; count: number }[]; height?: number }>(),
    { height: 240 },
  )

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const colors = computed(() => categoricalColors())

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'item',
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const entry = Array.isArray(params) ? params[0] : params
        if (!entry) return ''
        const value = typeof entry.value === 'number' ? entry.value.toLocaleString() : String(entry.value ?? '')
        const percent = typeof entry.percent === 'number' ? entry.percent.toFixed(1) : ''
        return `${entry.name}<br/><b>${value}</b> (${percent}%)`
      },
    },
    legend: {
      type: 'scroll', orient: 'vertical', top: 'center', right: 0,
      itemWidth: 10, itemHeight: 10, icon: 'roundRect',
      textStyle: { fontSize: 11, color: resolveColour('var(--foreground)') },
    },
    series: [{
      type: 'pie',
      radius: ['56%', '82%'],
      center: ['34%', '50%'],
      label: { show: false },
      labelLine: { show: false },
      itemStyle: {
        borderRadius: 6,
        borderColor: resolveColour('var(--card)'),
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
