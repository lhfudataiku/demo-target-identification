<script setup lang="ts">
  /**
   * "Trials" and "Literature" — what the searches retrieved for this pair, then the records one LLM
   * selection pass picked, each with a role and a quote the backend found in the passage (scope
   * D3–D5). The records render as soon as the search returns; the selection fills in after. Either
   * request failing shows here only: the other tabs do not depend on them.
   */
  import { computed, ref } from 'vue'
  import { Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Skeleton } from '@dataiku/ea-ui-kit'
  import { ArrowExternalLink, ChevronDown, ChevronRight, Update } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import { ROLE_LABEL, SUBTYPE_LABEL, type Corpus, type Selection, type SourcesDoc } from './types'

  const props = defineProps<{
    corpus: Corpus
    doc: SourcesDoc | null; docError: string | null
    selection: Selection | null; selectionError: string | null
    busy: boolean
  }>()
  const emit = defineEmits<{ refresh: [] }>()
  const openRest = ref(false)

  const noun = computed(() => (props.corpus === 'trials' ? 'trials' : 'papers'))
  const source = computed(() => (props.corpus === 'trials' ? 'ClinicalTrials.gov' : 'PubMed open-access subset'))
  const result = computed(() => props.doc?.search[props.corpus] ?? null)
  const byId = computed(() => new Map((result.value?.records ?? []).map((r) => [r.id, r])))
  const picks = computed(() => (props.selection?.[props.corpus] ?? [])
    .map((p) => ({ ...p, rec: byId.value.get(p.id) }))
    .filter((p) => p.rec))
  const rest = computed(() => {
    const picked = new Set(picks.value.map((p) => p.id))
    return (result.value?.records ?? []).filter((r) => !picked.has(r.id))
  })
  const droppedHere = computed(() => (props.selection?.dropped ?? []).filter((d) => d.corpus === props.corpus))
  const when = (iso: string | undefined) => (iso ? iso.replace('T', ' ').slice(0, 16) + ' UTC' : '')
  const roleStatus = (role: string) =>
    role === 'conflicting_finding' ? 'destructive' : role === 'contextual_mention' ? 'muted' : 'info'
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <p class="max-w-prose text-sm leading-relaxed text-muted-foreground">
        {{ noun === 'trials' ? 'Trials' : 'Papers' }} from the {{ source }} that name
        {{ doc?.context.symbol ?? 'the gene' }}, searched for this pair only. Counts are what the search
        retrieved, never all that exist; a trial's phase or status says nothing about whether it worked.
      </p>
      <Button variant="outline" size="sm" :disabled="busy" @click="emit('refresh')">
        <Update class="size-4" /> Refresh
      </Button>
    </div>

    <p v-if="docError" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {{ docError }}
    </p>
    <Skeleton v-else-if="!doc" class="h-32 w-full" />
    <p v-else-if="result?.error" class="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      The {{ source }} search failed: {{ result.error }}
    </p>
    <template v-else-if="result">
      <p class="font-mono text-2xs text-muted-foreground">
        {{ result.retrieved }} retrieved · {{ result.records.length }} name the gene
        <template v-if="result.dropped.reference_only"> · {{ result.dropped.reference_only }} only in a reference list</template>
        · searched {{ when(doc.search.retrieved_at) }}<template v-if="doc.cached"> (cached)</template>
      </p>

      <!-- The selection -->
      <p v-if="selectionError || selection?.errors?.[corpus]" class="text-sm text-muted-foreground">
        The selection pass failed ({{ selectionError ?? selection?.errors?.[corpus] }}); the retrieved {{ noun }}
        are listed below unlabelled.
      </p>
      <Skeleton v-else-if="!selection && result.records.length" class="h-24 w-full" />
      <p v-else-if="selection && !picks.length" class="text-sm text-muted-foreground">
        No retrieved {{ noun.slice(0, -1) }} was picked as relevant to {{ doc.context.symbol }} in this disease.
      </p>
      <ol v-else-if="picks.length" class="flex flex-col gap-3">
        <li v-for="p in picks" :key="p.id" class="flex flex-col gap-1.5 rounded-lg border px-4 py-3">
          <div class="flex flex-wrap items-baseline justify-between gap-2">
            <a :href="p.rec!.url ?? undefined" target="_blank" rel="noopener"
               class="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline">
              {{ p.rec!.title ?? p.id }} <ArrowExternalLink class="size-3" />
            </a>
            <span class="font-mono text-2xs text-muted-foreground">{{ p.id }}</span>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <StatusBadge :status="roleStatus(p.role)">{{ ROLE_LABEL[p.role] ?? p.role }}</StatusBadge>
            <StatusBadge status="muted">{{ SUBTYPE_LABEL[p.subtype_match] }}</StatusBadge>
            <StatusBadge v-if="p.rec!.status" status="muted">{{ p.rec!.status.toLowerCase().replaceAll('_', ' ') }}</StatusBadge>
            <StatusBadge v-if="p.rec!.phases" status="muted">{{ p.rec!.phases }}</StatusBadge>
          </div>
          <p class="text-sm">{{ p.reason }}</p>
          <blockquote class="border-l-2 pl-3 text-xs italic leading-relaxed text-muted-foreground">“{{ p.quote }}”</blockquote>
        </li>
      </ol>
      <p v-if="selection && !selection.note" class="font-mono text-2xs text-muted-foreground">
        Picked and labelled by {{ selection.model.split(':').pop() }} · {{ when(selection.selected_at) }} · every quote
        is found in its passage<template v-if="droppedHere.length"> · {{ droppedHere.length }}
          {{ droppedHere.length === 1 ? 'label' : 'labels' }} dropped for failing that check</template>
      </p>

      <!-- Everything else retrieved -->
      <Collapsible v-if="rest.length" v-model:open="openRest">
        <CollapsibleTrigger as-child>
          <Button variant="ghost" size="sm" class="-ml-2">
            <component :is="openRest ? ChevronDown : ChevronRight" class="size-4" />
            {{ picks.length ? 'Other' : 'All' }} retrieved {{ noun }} ({{ rest.length }})
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <ul class="flex flex-col gap-1 pt-1">
            <li v-for="r in rest" :key="r.id" class="flex flex-wrap items-baseline gap-x-2 text-sm">
              <a :href="r.url ?? undefined" target="_blank" rel="noopener" class="text-primary hover:underline">{{ r.title ?? r.id }}</a>
              <span class="font-mono text-2xs text-muted-foreground">{{ r.id }}</span>
            </li>
          </ul>
        </CollapsibleContent>
      </Collapsible>
      <p v-if="!result.records.length" class="text-sm text-muted-foreground">
        None of the retrieved {{ noun }} names {{ doc.context.symbol }} outside a reference list.
      </p>
      <p class="font-mono text-2xs text-muted-foreground">queries: {{ doc.search.queries.join(' · ') }}</p>
    </template>
  </div>
</template>
