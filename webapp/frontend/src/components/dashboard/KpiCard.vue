<script setup lang="ts">
  import { computed, nextTick, onMounted, ref } from 'vue';
  import VChart from 'vue-echarts';
  import { use } from 'echarts/core';
  import { LineChart } from 'echarts/charts';
  import { GridComponent } from 'echarts/components';
  import { CanvasRenderer } from 'echarts/renderers';
  import type { EChartsOption } from 'echarts';
  import { ArrowUpRight, ArrowDownRight, Minus, type LucideIcon } from 'lucide-vue-next';
  import type { KpiValue } from '@/types/dashboard';

  use([LineChart, GridComponent, CanvasRenderer]);

  const props = defineProps<{
    kpi: KpiValue;
    icon?: LucideIcon;
    accent?: string;
  }>();

  const ready = ref(false);
  onMounted(() => {
    nextTick(() => {
      ready.value = true;
    });
  });

  const accentColor = computed(() => props.accent ?? 'hsl(233.92 50% 35%)');
  const cardStyle = computed(() => ({
    borderColor: `color-mix(in oklab, ${accentColor.value} 18%, white)`,
    background: `linear-gradient(180deg, color-mix(in oklab, ${accentColor.value} 12%, white) 0%, var(--card) 34%)`,
  }));
  const iconStyle = computed(() => ({
    backgroundColor: `color-mix(in oklab, ${accentColor.value} 16%, white)`,
    color: accentColor.value,
  }));
  const valueStyle = computed(() => ({
    color: `color-mix(in oklab, ${accentColor.value} 58%, black)`,
  }));

  // A delta is "positive" when its direction aligns with what is desirable.
  // For open-items we want the number to go down, so "down" is positive there.
  const isPositive = computed(() => {
    if (props.kpi.deltaDirection === 'flat') return null;
    const upGood = props.kpi.upIsGood;
    return (props.kpi.deltaDirection === 'up') === upGood;
  });

  const deltaClass = computed(() => {
    if (isPositive.value === null) return 'bg-muted text-muted-foreground';
    return isPositive.value
      ? 'border border-emerald-200/70 bg-emerald-50/80 text-emerald-700'
      : 'border border-rose-200/70 bg-rose-50/80 text-rose-700';
  });

  const DeltaIcon = computed(() => {
    if (props.kpi.deltaDirection === 'flat') return Minus;
    return props.kpi.deltaDirection === 'up' ? ArrowUpRight : ArrowDownRight;
  });

  const sparkOption = computed((): EChartsOption => ({
    animationDuration: 900,
    animationEasing: 'cubicOut',
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: 'category', show: false, boundaryGap: false },
    yAxis: { type: 'value', show: false, scale: true },
    series: [
      {
        type: 'line',
        data: props.kpi.sparkline,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: accentColor.value },
        itemStyle: { color: accentColor.value },
        areaStyle: { opacity: 0.15 },
      },
    ],
  }));
</script>

<template>
  <div class="rounded-xl border p-5 flex flex-col gap-3 shadow-sm" :style="cardStyle">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <component
            :is="icon"
            v-if="icon"
            class="w-8 h-8 rounded-lg p-1.5 shrink-0"
            :style="iconStyle"
          />
          <p class="text-xs font-medium text-muted-foreground uppercase tracking-wide truncate">
            {{ kpi.label }}
          </p>
        </div>
        <p class="text-3xl font-semibold mt-2 leading-none" :style="valueStyle">{{ kpi.value }}</p>
      </div>
      <span
        class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[11px] font-medium shrink-0"
        :class="deltaClass"
      >
        <component :is="DeltaIcon" class="w-3 h-3" />
        {{ kpi.deltaLabel }}
      </span>
    </div>

    <div class="h-10 -mx-1">
      <VChart
        v-if="ready"
        :option="sparkOption"
        :autoresize="true"
        class="h-full w-full"
      />
    </div>

    <p v-if="kpi.caption" class="text-xs text-muted-foreground leading-snug">
      {{ kpi.caption }}
    </p>
  </div>
</template>
