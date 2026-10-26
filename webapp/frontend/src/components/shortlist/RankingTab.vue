<script setup lang="ts">
  /**
   * "Why this ranking?" — the stored SHAP drivers, each beside where this
   * gene's value for that input sits within this disease's own pool (scope D2:
   * only the features with a SHAP value are listed). Today the flow keeps the
   * top two; the top five arrive with the rescoring in a later phase.
   */
  import { computed, ref } from 'vue'
  import { Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Skeleton } from '@dataiku/ea-ui-kit'
  import { ArrowDown, ArrowUp, ChevronDown, ChevronRight } from '@dataiku/vue-icons'
  import { SERIES_BG, SERIES_TEXT } from '@/utils/seriesColours'
  import type { Detail, Driver } from './types'

  const props = defineProps<{ drivers: Driver[]; detail: Detail | null; busy: boolean; error: string | null }>()
  const open = ref(false)

  const rows = computed(() => props.drivers.map((d) => {
    const f = props.detail?.features.find((x) => x.key === d.key)
    return { ...d, kind: f?.kind ?? null, percentile: f?.percentile ?? null, lower: f?.direction === 'lower' }
  }))
  /** Up is the compared series, down is a negative contribution (WEBAPP_DESIGN §3.5). */
  const signClass = (sign: string) => SERIES_TEXT[sign === '-' ? 'negative' : 'contrast']
  const nInputs = computed(() => (props.detail ? props.detail.features.length + props.detail.missing_features.length : null))
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-sm leading-relaxed text-muted-foreground">
      SHAP shows how much each input moved this gene's score. The percentile shows where the gene's value for
      that input sits among all candidates for this disease. Neither measures biological certainty.
    </p>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ error }}
    </p>
    <Skeleton v-else-if="busy" class="h-24 w-full" />
    <p v-else-if="!rows.length" class="text-sm text-muted-foreground">No attribution is stored for this candidate.</p>
    <div v-else class="overflow-hidden rounded-lg border">
      <div class="grid grid-cols-12 gap-3 bg-muted/30 px-4 py-2 text-2xs font-semibold uppercase tracking-wide text-muted-foreground">
        <span class="col-span-5">Model input</span>
        <span class="col-span-3">SHAP contribution</span>
        <span class="col-span-4">Within this disease</span>
      </div>
      <div v-for="(d, i) in rows" :key="d.key" class="grid grid-cols-12 items-center gap-3 border-t px-4 py-3">
        <div class="col-span-5 flex flex-col">
          <span class="text-sm font-medium">{{ i + 1 }}. {{ d.label ?? d.key }}</span>
          <span class="font-mono text-2xs text-muted-foreground"><template v-if="d.kind">{{ d.kind }} · </template>{{ d.key }}</span>
        </div>
        <div class="col-span-3 flex items-center gap-2">
          <template v-if="d.value">
            <component :is="d.sign === '-' ? ArrowDown : ArrowUp" class="size-4"
                       :class="signClass(d.sign)" />
            <span class="font-mono text-sm tabular-nums">{{ d.sign === '-' ? '−' : '+' }}{{ d.value }}</span>
          </template>
          <span v-else class="text-xs text-muted-foreground">not parsed</span>
        </div>
        <div class="col-span-4 flex flex-col gap-1">
          <template v-if="d.percentile !== null">
            <span class="text-xs">{{ d.lower ? 'Closer than' : 'Stronger than' }} {{ d.percentile }}% of candidates</span>
            <div class="h-1.5 overflow-hidden rounded-full bg-muted">
              <div class="h-full rounded-full" :class="SERIES_BG.contrast" :style="{ width: `${d.percentile}%` }" />
            </div>
          </template>
          <span v-else-if="detail" class="text-xs text-muted-foreground">Not in dashboard_candidates</span>
        </div>
      </div>
    </div>

    <p class="text-xs leading-relaxed text-muted-foreground">
      <b class="text-foreground">Only the inputs with a stored SHAP value are listed.</b> Today the scoring
      flow keeps the {{ drivers.length === 1 ? 'strongest driver' : `${drivers.length} strongest drivers` }}<template
        v-if="nInputs"> of the champion's {{ nInputs }} inputs</template>; the others are in the glossary.
    </p>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2">
          <component :is="open ? ChevronDown : ChevronRight" class="size-4" /> How to read these measures
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent class="flex flex-col gap-2 pt-1 text-sm leading-relaxed text-muted-foreground">
        <p>A positive SHAP value pushed the score up; a negative one pushed it down. Values are on the model's
          own scale and are not probabilities.</p>
        <p>The percentile is <code class="font-mono text-xs">100 × (candidates for this disease this one is
          stronger than) ÷ (candidates with a non-null value)</code><template v-if="detail?.pool_size">, over
          this disease's {{ detail.pool_size.toLocaleString() }} candidates</template> — a rank within this
          disease's own pool, never a global one. Stronger means a higher value everywhere except hop distance,
          where fewer is stronger, so it reads “closer than”. Ties count toward neither side.</p>
        <p v-if="detail?.missing_features.length">
          <b class="text-foreground">No percentile for</b>
          <code v-for="m in detail.missing_features" :key="m" class="mx-1 font-mono text-xs">{{ m }}</code>:
          a model input that never reaches <code class="font-mono text-xs">dashboard_candidates</code>.
        </p>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
