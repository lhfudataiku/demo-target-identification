<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import { Check, Copy, ExternalLink, Network } from 'lucide-vue-next'
  import ActCard from '@/components/act/ActCard.vue'
  import { EaButton } from '@/components/ui'
  import type { ExplorerLaunchContext } from '@/stores/visualGraphExplorer'
  import { useVisualGraphExplorerStore } from '@/stores/visualGraphExplorer'
  import { copyVisualGraphCypher } from '@/utils/visualGraphExplorer'

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
    handoff?: ExplorerLaunchContext['handoff']
    starterQueries?: VisualGraphExplorerStarter[]
    chips?: [string, string][]
    src?: string[]
    span?: string
    methodLabel?: string
  }>(), { span: 'col-span-12' })

  const emit = defineEmits<{
    selectQuery: [starter: VisualGraphExplorerStarter | null]
    open: [context: ExplorerLaunchContext]
  }>()

  const explorer = useVisualGraphExplorerStore()
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

  async function openExplorer() {
    // Clipboard access begins within this click handler so browsers retain the user gesture.
    const copyStatus = !hasQuery.value
      ? 'idle'
      : (await copyVisualGraphCypher(preparedCypher.value)) ? 'copied' : 'failed'
    const context: ExplorerLaunchContext = {
      title: props.contextTitle ?? props.title,
      cypher: preparedCypher.value,
      handoff: props.handoff,
      copyStatus,
    }
    explorer.open(context)
    emit('open', context)
  }

  async function copyOnly() {
    if (!hasQuery.value) return
    copied.value = await copyVisualGraphCypher(preparedCypher.value)
    copyFailed.value = !copied.value
  }
</script>

<template>
  <ActCard :span="span" :title="title" :desc="description" :icon="Network" :chips="chips" :src="src"
           accent="var(--chart-2)" :method-label="methodLabel ?? 'How this is computed'">
    <div class="flex flex-col gap-3">
      <div v-if="starterQueries?.length" role="group" aria-label="Available graph queries"
           class="flex flex-wrap gap-2">
        <button v-for="starter in starterQueries" :key="starter.id" type="button"
                :aria-pressed="selectedStarterId === starter.id" :title="starter.description"
                class="rounded-md border px-2.5 py-1 text-left text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
                :class="selectedStarterId === starter.id
                  ? 'border-primary bg-primary/15 text-primary-foreground'
                  : 'border-border bg-muted/30 text-muted-foreground hover:bg-muted/60'"
                @click="selectStarter(starter)">
          {{ starter.label }}
        </button>
      </div>

      <p v-if="contextTitle" class="font-mono text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
        Context: {{ contextTitle }}
      </p>

      <div v-if="hasQuery" class="rounded-md border border-border bg-muted/25">
        <div class="border-b border-border px-2.5 py-1.5">
          <p class="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">
            Selected query<span v-if="selectedStarter"> · {{ selectedStarter.label }}</span>
          </p>
          <p v-if="selectedStarter?.description" class="mt-0.5 text-[11.5px] leading-relaxed text-muted-foreground">
            {{ selectedStarter.description }}
          </p>
        </div>
        <pre tabindex="0" aria-label="Selected Cypher query, selectable for manual copy"
             class="max-h-44 overflow-auto p-2.5 font-mono text-[10.5px] leading-relaxed text-foreground outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring/40">{{ preparedCypher }}</pre>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <EaButton size="sm" @click="openExplorer">
          <ExternalLink class="size-3.5" /> Open full Explorer
        </EaButton>
        <EaButton v-if="hasQuery" variant="outline" size="sm" @click="copyOnly">
          <Check v-if="copied" class="size-3.5" />
          <Copy v-else class="size-3.5" />
          {{ copied ? 'Copied' : 'Copy query' }}
        </EaButton>
        <span v-if="copyFailed" role="status" class="text-xs text-destructive">
          Copy was not available. The full Explorer shows the selectable query.
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
