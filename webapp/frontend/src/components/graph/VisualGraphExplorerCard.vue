<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { ArrowExternalLink, Checkmark, Copy, Flow } from '@dataiku/vue-icons'
  import ActCard from '@/components/act/ActCard.vue'
  import { Button, ToggleGroup, ToggleGroupItem } from '@dataiku/ea-ui-kit'
  import { copyVisualGraphCypher, visualGraphExplorerUrl } from '@/utils/visualGraphExplorer'

  defineOptions({ name: 'VisualGraphExplorerCard' })

  export interface VisualGraphExplorerStarter {
    id: string
    label: string
    cypher: string
    description?: string
  }

  const props = withDefaults(defineProps<{
    title: string
    description?: string
    contextTitle?: string
    cypher?: string
    /** Act-specific note shown under the shared run-it-yourself steps. */
    handoff?: string
    starterQueries?: VisualGraphExplorerStarter[]
    chips?: [string, string][]
    src?: string[]
    span?: string
    methodLabel?: string
  }>(), { span: 'col-span-12' })

  const emit = defineEmits<{
    selectQuery: [starter: VisualGraphExplorerStarter | null]
  }>()

  // Built once from build-time config; null when this environment has no Explorer to link to.
  const explorerUrl = visualGraphExplorerUrl()
  const selectedStarterId = ref<string | null>(null)
  const copied = ref(false)
  const copyFailed = ref(false)

  const selectedStarter = computed(() =>
    props.starterQueries?.find((starter) => starter.id === selectedStarterId.value) ?? null)
  const preparedCypher = computed(() => {
    return selectedStarter.value?.cypher ?? props.cypher ?? ''
  })
  const hasQuery = computed(() => Boolean(preparedCypher.value.trim()))

  watch(
    () => props.starterQueries?.map((starter) => starter.id).join('\u0000') ?? '',
    () => {
      const starters = props.starterQueries ?? []
      if (!starters.some((starter) => starter.id === selectedStarterId.value)) {
        selectedStarterId.value = starters[0]?.id ?? null
      }
    },
    { immediate: true },
  )
  watch(preparedCypher, () => {
    copied.value = false
    copyFailed.value = false
  })

  function selectStarter(starter: VisualGraphExplorerStarter) {
    selectedStarterId.value = starter.id
    emit('selectQuery', starter)
  }

  // The ToggleGroup emits the chosen id, or an empty value when the active chip
  // is clicked again; a query is always selected, so that click is ignored.
  function pickStarter(id: unknown) {
    const starter = props.starterQueries?.find((s) => s.id === id)
    if (starter) selectStarter(starter)
  }

  async function copyOnly() {
    if (!hasQuery.value) return
    copied.value = await copyVisualGraphCypher(preparedCypher.value)
    copyFailed.value = !copied.value
  }
</script>

<template>
  <ActCard :span="span" :title="title" :desc="description" :icon="Flow" :chips="chips" :src="src"
           :method-label="methodLabel ?? 'How this is computed'">
    <div class="flex flex-col gap-3">
      <ToggleGroup v-if="starterQueries?.length" type="single" variant="outline" size="sm"
                   :spacing="2" aria-label="Available graph queries" class="flex-wrap"
                   :model-value="selectedStarterId" @update:model-value="pickStarter">
        <ToggleGroupItem v-for="starter in starterQueries" :key="starter.id" :value="starter.id"
                         :title="starter.description" class="px-2.5 text-xs">
          {{ starter.label }}
        </ToggleGroupItem>
      </ToggleGroup>

      <p v-if="contextTitle" class="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
        Context: {{ contextTitle }}
      </p>

      <div v-if="hasQuery" class="rounded-md border border-border bg-muted/25">
        <div class="border-b border-border px-2.5 py-1.5">
          <p class="font-mono text-2xs uppercase tracking-wider text-muted-foreground">
            Selected query<span v-if="selectedStarter"> · {{ selectedStarter.label }}</span>
          </p>
          <p v-if="selectedStarter?.description" class="mt-0.5 text-2xs leading-relaxed text-muted-foreground">
            {{ selectedStarter.description }}
          </p>
        </div>
        <pre tabindex="0" aria-label="Selected Cypher query, selectable for manual copy"
             class="max-h-44 overflow-auto p-2.5 font-mono text-2xs leading-relaxed text-foreground outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/40">{{ preparedCypher }}</pre>
      </div>

      <div v-if="hasQuery" class="text-2xs leading-relaxed text-muted-foreground">
        <p class="font-mono text-2xs uppercase tracking-wider">Run it in the Explorer</p>
        <ol class="mt-1 list-decimal space-y-0.5 pl-4">
          <li>Copy the query above with <b class="text-foreground">Copy query</b>.</li>
          <li>Open the Explorer with <b class="text-foreground">Open full Explorer</b>. It opens in a new tab.</li>
          <li>In the Explorer, create a new query, paste it and run it.</li>
        </ol>
        <p v-if="handoff" class="mt-1.5">{{ handoff }}</p>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <Button v-if="hasQuery" variant="outline" size="sm" @click="copyOnly">
          <Checkmark v-if="copied" class="size-3.5" />
          <Copy v-else class="size-3.5" />
          {{ copied ? 'Copied' : 'Copy query' }}
        </Button>
        <Button v-if="explorerUrl" as="a" size="sm" :href="explorerUrl" target="_blank" rel="noopener noreferrer">
          <ArrowExternalLink class="size-3.5" /> Open full Explorer
          <span class="sr-only">(opens in a new tab)</span>
        </Button>
        <Button v-else size="sm" disabled>
          <ArrowExternalLink class="size-3.5" /> Open full Explorer
        </Button>
        <span v-if="copyFailed" role="status" class="text-xs text-destructive">
          Copy was not available. Select the query above and copy it manually.
        </span>
        <span v-if="!explorerUrl" role="status" class="text-xs text-muted-foreground">
          The Explorer link is not configured for this environment.
        </span>
      </div>

      <slot />
    </div>

    <!-- The card's footer slots belong to the caller, not to this wrapper:
         act 1 and act 4 embed the same Explorer with different methodology. -->
    <template v-if="$slots.note" #note><slot name="note" /></template>
    <template v-if="$slots.method" #method><slot name="method" /></template>
    <template v-if="$slots.presenter" #presenter><slot name="presenter" /></template>
  </ActCard>
</template>
