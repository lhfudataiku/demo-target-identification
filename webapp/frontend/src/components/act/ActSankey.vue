<script setup lang="ts">
  /** Sankey — v3's `poolFlow`: how candidate pairs enter the pool by route. */
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { SankeyChart } from 'echarts/charts'
  import { TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption, TooltipComponentFormatterCallbackParams } from 'echarts'

  use([SankeyChart, TooltipComponent, CanvasRenderer])
  defineOptions({ name: 'ActSankey' })

  const props = withDefaults(
    defineProps<{
      nodes: { name: string; color?: string }[]
      links: { source: string; target: string; value: number }[]
      height?: number
    }>(),
    { height: 300 },
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
      trigger: 'item', triggerOn: 'mousemove',
      formatter: (params: TooltipComponentFormatterCallbackParams) => {
        const entry = Array.isArray(params) ? params[0] : params
        if (!entry) return ''
        const value = typeof entry.value === 'number' ? entry.value.toLocaleString() : String(entry.value ?? '')
        return entry.dataType === 'edge'
          ? `${entry.name}<br/><b>${value}</b> pairs`
          : entry.name
      },
    },
    series: [{
      type: 'sankey',
      left: 4, right: 96, top: 8, bottom: 8,
      nodeWidth: 14, nodeGap: 10,
      emphasis: { focus: 'adjacency' },
      // An explicit `color` lets a view carry a meaning across plots -- the
      // pool card paints "survives the gate" and "dropped" the same in the band
      // above and the flow below. Falls back to the palette cycle.
      data: props.nodes.map((n, i) => ({
        name: n.name,
        itemStyle: {
          color: n.color
            ? getComputedStyle(document.documentElement).getPropertyValue(n.color).trim() || n.color
            : colors.value[i % colors.value.length],
          borderWidth: 0,
        },
      })),
      links: props.links,
      lineStyle: { color: 'gradient', opacity: 0.34, curveness: 0.5 },
      label: { fontFamily: 'DM Mono, monospace', fontSize: 10, color: 'var(--foreground)' },
    }],
  }))
</script>

<template>
  <div class="w-full" :style="{ height: height + 'px' }">
    <VChart v-if="ready" :option="chartOption" :autoresize="true" class="h-full w-full" />
  </div>
</template>
