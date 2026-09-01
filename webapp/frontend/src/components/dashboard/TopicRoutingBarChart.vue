<script setup lang="ts">
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { BarChart } from 'echarts/charts'
  import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'
  import type { TopicVolume } from '@/data/mock/medical-info-tickets'

  use([BarChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

  const props = defineProps<{ data: TopicVolume[] }>()

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const sorted = computed(() =>
    [...props.data].sort(
      (left, right) => left.medicalInfo + left.routedElsewhere - (right.medicalInfo + right.routedElsewhere),
    ),
  )

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    color: ['hsl(166 38% 66%)', 'hsl(25 58% 73%)'],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      data: ['Medical Information', 'Route elsewhere'],
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      icon: 'roundRect',
      textStyle: { fontSize: 12, color: 'var(--muted-foreground)' },
    },
    grid: { left: 0, right: 16, top: 8, bottom: 38, containLabel: true },
    xAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
      axisLabel: { color: 'var(--muted-foreground)', fontSize: 10 },
    },
    yAxis: {
      type: 'category',
      data: sorted.value.map((item) => item.topic),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: 'var(--foreground)', fontSize: 11 },
    },
    series: [
      {
        name: 'Medical Information',
        type: 'bar',
        stack: 'routing',
        barWidth: 18,
        data: sorted.value.map((item) => item.medicalInfo),
        itemStyle: { color: 'hsl(166 38% 66%)' },
      },
      {
        name: 'Route elsewhere',
        type: 'bar',
        stack: 'routing',
        barWidth: 18,
        data: sorted.value.map((item) => item.routedElsewhere),
        itemStyle: {
          color: 'hsl(25 58% 73%)',
          borderRadius: [0, 4, 4, 0],
        },
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
