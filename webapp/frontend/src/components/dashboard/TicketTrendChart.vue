<script setup lang="ts">
  import { computed, nextTick, onMounted, ref } from 'vue'
  import VChart from 'vue-echarts'
  import { use } from 'echarts/core'
  import { BarChart, LineChart } from 'echarts/charts'
  import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
  import { CanvasRenderer } from 'echarts/renderers'
  import type { EChartsOption } from 'echarts'
  import type { TicketTrendPoint } from '@/data/mock/medical-info-tickets'

  use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

  const props = defineProps<{ data: TicketTrendPoint[] }>()

  const ready = ref(false)
  onMounted(() => nextTick(() => (ready.value = true)))

  const chartOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    color: ['hsl(166 38% 66%)', 'hsl(25 58% 73%)', 'hsl(220 50% 73%)'],
    legend: {
      data: ['Answered by MI', 'Rerouted', 'SLA %'],
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      icon: 'roundRect',
      textStyle: { fontSize: 12, color: 'var(--muted-foreground)' },
    },
    grid: { left: 42, right: 42, top: 16, bottom: 42 },
    xAxis: {
      type: 'category',
      data: props.data.map((point) => point.date),
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'var(--border)' } },
      axisLabel: {
        color: 'var(--muted-foreground)',
        fontSize: 10,
        formatter: (value: string) => {
          const date = new Date(value)
          return `${date.toLocaleString('en-US', { month: 'short' })} ${date.getDate()}`
        },
      },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Tickets',
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { lineStyle: { type: 'dashed', color: 'var(--border)' } },
        axisLabel: { color: 'var(--muted-foreground)', fontSize: 10 },
      },
      {
        type: 'value',
        name: 'SLA %',
        min: 70,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: {
          color: 'var(--muted-foreground)',
          fontSize: 10,
          formatter: (value: number) => `${value}%`,
        },
      },
    ],
    series: [
      {
        name: 'Answered by MI',
        type: 'bar',
        data: props.data.map((point) => point.answeredByMedicalInfo),
        barWidth: 16,
        itemStyle: {
          color: 'hsl(166 38% 66%)',
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: 'Rerouted',
        type: 'bar',
        data: props.data.map((point) => point.routedToOtherTeams),
        barWidth: 16,
        itemStyle: {
          color: 'hsl(25 58% 73%)',
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: 'SLA %',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        data: props.data.map((point) => point.slaPct),
        lineStyle: { width: 3, color: 'hsl(220 50% 73%)' },
        itemStyle: { color: 'hsl(220 50% 73%)' },
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
