<script setup lang="ts">
  /**
   * Every term in the family: AUC with its 95% interval, known-target count,
   * and a warning row where the label is too thin for AUC to mean anything.
   * "Too thin" is the backend's `trustworthy` flag (the flow's positive-count
   * floor), never a threshold restated here.
   */
  import { computed } from 'vue'
  import { Tooltip, TooltipContent, TooltipTrigger } from '@dataiku/ea-ui-kit'
  import { WarningOutline } from '@dataiku/vue-icons'
  import type { Term } from './types'

  const props = defineProps<{ terms: Term[]; selected: number }>()

  const LO = 0.5
  const x = (v: number) => `${(100 * (v - LO)) / (1 - LO)}%`
  const rows = computed(() => [...props.terms].filter((t) => t.auc !== null).sort((a, b) => (b.auc ?? 0) - (a.auc ?? 0)))
  const TICKS = [0.5, 0.6, 0.7, 0.8, 0.9, 1]
</script>

<template>
  <div class="flex flex-col">
    <div class="grid grid-cols-12 gap-3 px-2 pb-1 text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
      <span class="col-span-4">Disease term</span>
      <span class="col-span-6">AUC with 95% interval</span>
      <span class="col-span-2 text-right">Known targets</span>
    </div>
    <Tooltip v-for="t in rows" :key="t.disease_index">
      <TooltipTrigger as-child>
        <div class="grid grid-cols-12 items-center gap-3 rounded-md px-2 py-1"
             :class="t.disease_index === selected ? 'bg-accent' : 'hover:bg-muted/50'">
          <span class="col-span-4 flex items-center gap-1.5 text-xs leading-tight"
                :class="t.disease_index === selected ? 'font-semibold' : ''">
            <WarningOutline v-if="!t.trustworthy" class="size-3.5 shrink-0 text-warning" />
            {{ t.disease_name }}
          </span>
          <div class="relative col-span-6 h-4">
            <div class="absolute inset-y-0 left-0 right-0 my-auto h-px bg-border" />
            <div v-if="t.lo95 !== null && t.hi95 !== null" class="absolute top-1/2 h-0.5 -translate-y-1/2 rounded-full bg-primary/50"
                 :style="{ left: x(Math.max(LO, t.lo95)), width: `calc(${x(Math.min(1, t.hi95))} - ${x(Math.max(LO, t.lo95))})` }" />
            <div class="absolute top-1/2 size-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary ring-2 ring-card"
                 :style="{ left: x(t.auc ?? LO) }" />
          </div>
          <span class="col-span-2 text-right font-mono text-2xs tabular-nums"
                :class="t.trustworthy ? 'text-muted-foreground' : 'text-warning'">{{ t.n_pos }}</span>
        </div>
      </TooltipTrigger>
      <TooltipContent>
        <p class="font-medium">{{ t.disease_name }}</p>
        <p>AUC {{ t.auc?.toFixed(4) }}<template v-if="t.lo95 !== null"> · 95% interval {{ t.lo95.toFixed(3) }}–{{ t.hi95?.toFixed(3) }}</template></p>
        <p>{{ t.n_pos }} known targets<template v-if="t.enrichment !== null"> · enrichment {{ t.enrichment }}×</template></p>
        <p v-if="!t.trustworthy">Too few known targets for AUC to be quoted.</p>
      </TooltipContent>
    </Tooltip>
    <div class="grid grid-cols-12 gap-3 px-2 pt-1">
      <div class="relative col-span-6 col-start-5 h-4 border-t border-border">
        <span v-for="t in TICKS" :key="t" class="absolute -translate-x-1/2 font-mono text-2xs text-muted-foreground"
              :style="{ left: x(t) }">{{ t.toFixed(1) }}</span>
      </div>
    </div>
  </div>
</template>
