<script setup lang="ts">
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { PieChart } from 'echarts/charts'
  import { LegendComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'
  import type { RoutingSlice } from '@/data/mock/medical-info-tickets'

  use([PieChart, LegendComponent, TooltipComponent, CanvasRenderer])

  const props = defineProps<{ data: RoutingSlice[] }>()

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const colors = [
    'hsl(166 38% 66%)',
    'hsl(220 50% 73%)',
    'hsl(338 56% 78%)',
    'hsl(45 62% 74%)',
    'hsl(220 18% 76%)',
  ]

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}% of today\'s tickets',
    },
    legend: {
      orient: 'vertical',
      top: 'center',
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      icon: 'roundRect',
      textStyle: { fontSize: 12, color: 'var(--foreground)' },
    },
    series: [
      {
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
        data: props.data.map((slice, index) => ({
          name: slice.label,
          value: slice.value,
          itemStyle: { color: colors[index % colors.length] },
        })),
      },
    ],
  }))
</script>

<template>
  <div class="h-full w-full">
    <VChart
      v-if="ready"
      :option="chartOption"
      :autoresize="true"
      class="h-full w-full"
    />
  </div>
</template>
