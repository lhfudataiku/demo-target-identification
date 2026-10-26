<script setup lang="ts">
  /**
   * One series of horizontal bars: label, bar, value at the tip. Thin marks
   * (12px), a rounded data-end, square at the baseline, hover tooltip per bar.
   */
  import { computed } from 'vue'
  import { Tooltip, TooltipContent, TooltipTrigger } from '@dataiku/ea-ui-kit'

  const props = defineProps<{
    items: { label: string; count: number; note?: string }[]
    total?: number
    unit: string
  }>()

  const max = computed(() => Math.max(...props.items.map((i) => i.count), 1))
  const sum = computed(() => props.total ?? props.items.reduce((s, i) => s + i.count, 0))
  const pct = (n: number) => `${((100 * n) / sum.value).toFixed(1)}%`
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <Tooltip v-for="i in items" :key="i.label">
      <TooltipTrigger as-child>
        <div class="grid grid-cols-12 items-center gap-3 rounded-md px-1 py-0.5 hover:bg-muted/50">
          <span class="col-span-4 text-xs leading-tight">{{ i.label }}</span>
          <div class="col-span-6">
            <div class="h-3 rounded-r-sm bg-primary" :style="{ width: `${Math.max(1, (100 * i.count) / max)}%` }" />
          </div>
          <span class="col-span-2 text-right font-mono text-2xs tabular-nums text-muted-foreground">
            {{ i.count.toLocaleString() }}
          </span>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p class="font-medium">{{ i.label }}</p>
        <p>{{ i.count.toLocaleString() }} {{ unit }} · {{ pct(i.count) }} of {{ sum.toLocaleString() }}</p>
        <p v-if="i.note" class="opacity-80">{{ i.note }}</p>
      </TooltipContent>
    </Tooltip>
  </div>
</template>
