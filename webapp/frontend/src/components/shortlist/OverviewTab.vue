<script setup lang="ts">
  /**
   * A fixed brief built from the candidate's flags and its top SHAP drivers. No LLM
   * writes this tab. Each box answers one question, points at the tab that holds
   * the detail, and — for the model and the association — at the section of
   * "Why trust the list" that says how we know (scope §4.1).
   */
  import { computed } from 'vue'
  import { Button } from '@dataiku/ea-ui-kit'
  import { ArrowRight } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import type { Detail, Driver, Row } from './types'

  const props = defineProps<{ row: Row; detail: Detail | null; drivers: Driver[]; diseaseName: string }>()
  const emit = defineEmits<{ (e: 'go', tab: string): void }>()

  const top = computed(() => props.drivers[0])
  const hasDrug = computed(() => Boolean(props.row.approved_for_disease || props.row.investigational_for_disease))
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      <section class="flex flex-col gap-2 rounded-lg border bg-card p-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Why the model ranked it</p>
        <p class="text-sm">
          Rank <b>{{ row.rank_in_disease.toLocaleString() }}</b><template v-if="detail?.pool_size">
            of {{ detail.pool_size.toLocaleString() }}</template>.
          <template v-if="top">The strongest driver is <b>{{ top.label ?? top.key }}</b>.</template>
          <template v-else>No attribution is stored for this candidate.</template>
        </p>
        <Button variant="link" size="sm" class="h-auto self-start whitespace-normal px-0 text-left" @click="emit('go', 'ranking')">
          See what moved it <ArrowRight class="size-4" />
        </Button>
        <Button variant="link" size="sm" class="h-auto self-start whitespace-normal px-0 text-left" as-child>
          <router-link :to="{ name: 'trust', query: { section: 'reconstruction' } }">
            How do we know? How reliable the ranking is for this disease <ArrowRight class="size-4" />
          </router-link>
        </Button>
      </section>

      <section class="flex flex-col gap-2 rounded-lg border bg-card p-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Graph association</p>
        <p class="text-sm">
          <template v-if="row.is_target">
            An Open Targets association with this disease is recorded at score ≥ 0.3. That association is the
            label the model was trained on, so this is a <b>reconstruction</b>, not a discovery.
          </template>
          <template v-else>
            No association with this disease is recorded. The model surfaced this gene; nothing in the
            snapshot had already linked it.
          </template>
        </p>
        <Button variant="link" size="sm" class="h-auto self-start whitespace-normal px-0 text-left" as-child>
          <router-link :to="{ name: 'trust', query: { section: 'graph' } }">
            How do we know? What counts as a known target <ArrowRight class="size-4" />
          </router-link>
        </Button>
      </section>

      <section class="flex flex-col gap-2 rounded-lg border bg-card p-4">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Drug evidence for this disease</p>
        <div v-if="hasDrug" class="flex flex-wrap gap-1.5">
          <StatusBadge v-if="row.approved_for_disease" status="success">Approved</StatusBadge>
          <StatusBadge v-if="row.investigational_for_disease" status="warning">In trials</StatusBadge>
        </div>
        <p class="text-sm" :class="hasDrug ? 'text-muted-foreground' : ''">
          <template v-if="hasDrug">
            A drug acting on this protein is recorded as approved or investigated for {{ diseaseName }}.
          </template>
          <template v-else>
            No drug record links this gene to {{ diseaseName }} in the snapshot. That is not the same as no drug.
          </template>
        </p>
        <Button variant="link" size="sm" class="h-auto self-start whitespace-normal px-0 text-left" @click="emit('go', 'lineage')">
          Where the badges come from <ArrowRight class="size-4" />
        </Button>
      </section>
    </div>

    <section class="rounded-lg border border-info bg-card p-4">
      <p class="text-sm font-semibold">What these sources cannot tell you</p>
      <p class="mt-1 text-sm leading-relaxed text-muted-foreground">
        A recorded association, a drug acting on the protein and a drug approved for the disease are three
        separate facts. Together they still do not show that changing this protein's activity benefits
        patients with this disease. Each tab keeps its source attached so the gap stays visible.
      </p>
      <p v-if="row.has_safety_liability" class="mt-2 text-sm text-muted-foreground">
        <b class="text-foreground">Liability recorded.</b> An adverse effect has been published for this
        protein. The flag is not specific to dose, modality or indication.
      </p>
    </section>
  </div>
</template>
