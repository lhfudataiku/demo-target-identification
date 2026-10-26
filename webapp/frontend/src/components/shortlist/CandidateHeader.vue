<script setup lang="ts">
  /**
   * The selected candidate: where it sits, and the flags it carries, before any
   * explanation of why. HGNC identity joins this header in a later phase.
   */
  import { computed } from 'vue'
  import { StatusBadge } from 'bs-blueprint'
  import { tractLabel, type Detail, type Row } from './types'

  const props = defineProps<{ row: Row; detail: Detail | null; diseaseName: string }>()

  /* Open Targets packs several observed effects into one pipe-delimited cell
     ("cardiotoxicity|heart disease|..."). Shown as a list, not as the raw cell. */
  const safetyEvents = computed(() =>
    (props.detail?.safety_events ?? '').split('|').map((s) => s.trim()).filter(Boolean))
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      Selected candidate · rank {{ row.rank_in_disease.toLocaleString() }}<template v-if="detail?.pool_size">
        of {{ detail.pool_size.toLocaleString() }}</template> for {{ diseaseName }}
    </p>
    <h2 class="font-mono text-3xl font-semibold tracking-tight">{{ row.gene_name }}</h2>
    <div class="flex flex-wrap gap-1.5">
      <StatusBadge :status="row.is_target ? 'muted' : 'info'">
        {{ row.is_target ? 'Recorded association' : 'Novel' }}
      </StatusBadge>
      <StatusBadge v-if="row.approved_for_disease" status="success">Approved for this disease</StatusBadge>
      <StatusBadge v-if="row.investigational_for_disease" status="warning">In trials for this disease</StatusBadge>
      <StatusBadge v-if="row.has_safety_liability" status="destructive">Liability recorded</StatusBadge>
      <StatusBadge status="muted">{{ row.ot_class_l1 || 'Class not assessed' }}</StatusBadge>
      <StatusBadge status="muted">{{ tractLabel(row) }}</StatusBadge>
    </div>
    <p v-if="row.has_safety_liability && safetyEvents.length" class="text-xs leading-relaxed text-muted-foreground">
      <span class="text-destructive">Recorded liability:</span> {{ safetyEvents.join(' · ') }}
    </p>
    <p class="font-mono text-2xs text-muted-foreground">
      <template v-if="row.rank_percentile !== null">top {{ row.rank_percentile }}% of the pool · </template>graph node_index
      {{ row.gene_index }}
    </p>
  </div>
</template>
