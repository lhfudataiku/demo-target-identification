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
    span?: string
  }>(), { span: 'col-span-12' })

  const emit = defineEmits<{
    selectQuery: [starter: VisualGraphExplorerStarter | null]
    open: [context: ExplorerLaunchContext]
  }>()

  const explorer = useVisualGraphExplorerStore()
  const selectedStarterId = ref<string | null>(null)
  const copied = ref(false)
  const copyFailed = ref(false)

  const preparedCypher = computed(() => {
    const selected = props.starterQueries?.find((starter) => starter.id === selectedStarterId.value)
    return selected?.cypher ?? props.cypher ?? ''
  })
  const hasQuery = computed(() => Boolean(preparedCypher.value.trim()))

  watch(() => props.cypher, () => { selectedStarterId.value = null })
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
  <ActCard :span="span" :title="title" :desc="description" :icon="Network" accent="var(--chart-2)">
    <div class="flex flex-col gap-3">
      <div v-if="starterQueries?.length" class="flex flex-wrap gap-2" aria-label="Prepared graph queries">
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
    </div>
  </ActCard>
</template>
