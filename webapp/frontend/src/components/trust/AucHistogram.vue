<script setup lang="ts">
  /**
   * Per-disease AUC across the validation set, 20 bins, with the selected
   * disease marked as a position in the spread rather than a headline.
   */
  import { computed } from 'vue'
  import { Tooltip, TooltipContent, TooltipTrigger } from '@dataiku/ea-ui-kit'
  import type { Bin } from './types'

  const props = defineProps<{ bins: Bin[]; marker: number | null; markerLabel: string }>()

  const max = computed(() => Math.max(...props.bins.map((b) => b.n), 1))
  const markerBin = computed(() =>
    props.marker === null ? -1 : props.bins.findIndex((b) => props.marker! >= b.lo && props.marker! < b.hi))
  const TICKS = [0, 0.25, 0.5, 0.75, 1]
</script>

<template>
  <div class="flex flex-col gap-1">
    <div class="relative h-44">
      <!-- chance line -->
      <div class="absolute inset-y-0 left-1/2 border-l border-border" />
      <span class="absolute left-1/2 top-0 ml-1 text-2xs text-muted-foreground">chance</span>
      <div class="absolute inset-0 flex items-end gap-0.5">
        <Tooltip v-for="(b, i) in bins" :key="b.lo">
          <TooltipTrigger as-child>
            <div class="flex h-full flex-1 items-end justify-center hover:bg-muted/50">
              <div class="w-full max-w-6 rounded-t-sm"
                   :class="i === markerBin ? 'bg-primary' : 'bg-primary/35'"
                   :style="{ height: b.n ? `${Math.max(2, (100 * b.n) / max)}%` : '0' }" />
            </div>
          </TooltipTrigger>
          <TooltipContent>
            AUC {{ b.lo.toFixed(2) }}–{{ b.hi.toFixed(2) }}: {{ b.n }} disease{{ b.n === 1 ? '' : 's' }}
            <template v-if="i === markerBin"> · includes {{ markerLabel }}</template>
          </TooltipContent>
        </Tooltip>
      </div>
      <!-- the selected disease -->
      <div v-if="marker !== null" class="pointer-events-none absolute inset-y-0 border-l-2 border-foreground"
           :style="{ left: `${marker * 100}%` }">
        <span class="absolute -top-1 right-1 whitespace-nowrap rounded-sm bg-card px-1 text-2xs font-medium">
          {{ markerLabel }} · {{ marker.toFixed(4) }}
        </span>
      </div>
    </div>
    <div class="relative h-4 border-t border-border">
      <span v-for="t in TICKS" :key="t" class="absolute -translate-x-1/2 font-mono text-2xs text-muted-foreground"
            :style="{ left: `${t * 100}%` }">{{ t.toFixed(2) }}</span>
    </div>
    <p class="text-center text-2xs text-muted-foreground">AUC within each disease · one bar = 0.05</p>
  </div>
</template>
