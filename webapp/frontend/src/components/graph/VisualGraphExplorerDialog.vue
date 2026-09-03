<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
  import { Check, Copy, ExternalLink, Loader2, RefreshCw, X } from 'lucide-vue-next'
  import { EaButton } from '@/components/ui'
  import { useVisualGraphExplorerStore } from '@/stores/visualGraphExplorer'
  import {
    copyVisualGraphCypher,
    isVisualGraphExplorerConfigured,
    openVisualGraphExplorer,
    visualGraphExplorerUrl,
  } from '@/utils/visualGraphExplorer'

  defineOptions({ name: 'VisualGraphExplorerDialog' })

  const explorer = useVisualGraphExplorerStore()
  const dialog = ref<HTMLElement | null>(null)
  const iframeLoaded = ref(false)
  const iframeError = ref(false)
  const iframeKey = ref(0)
  const copyState = ref<'idle' | 'copied' | 'failed'>('idle')
  const newTabFailed = ref(false)
  const opener = ref<HTMLElement | null>(null)
  const previousBodyOverflow = ref('')

  const configured = computed(() => isVisualGraphExplorerConfigured())
  const explorerUrl = computed(() => visualGraphExplorerUrl())
  const query = computed(() => explorer.cypher?.trim() ?? '')
  const title = computed(() => explorer.title?.trim() || 'Visual Graph Explorer')
  const labelledBy = 'visual-graph-explorer-dialog-title'

  function resetFrame() {
    iframeLoaded.value = false
    iframeError.value = false
    iframeKey.value += 1
  }

  function close() {
    explorer.close()
  }

  function retry() {
    resetFrame()
  }

  async function copyQuery() {
    if (!query.value) return
    copyState.value = (await copyVisualGraphCypher(query.value)) ? 'copied' : 'failed'
  }

  function openInNewTab() {
    newTabFailed.value = explorerUrl.value
      ? !openVisualGraphExplorer(explorerUrl.value)
      : true
  }

  function focusableElements() {
    return [...(dialog.value?.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), iframe, [tabindex]:not([tabindex="-1"])',
    ) ?? [])].filter((element) => !element.hasAttribute('disabled') && element.offsetParent !== null)
  }

  function onKeydown(event: KeyboardEvent) {
    if (!explorer.isOpen) return
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
      return
    }
    if (event.key !== 'Tab') return

    const elements = focusableElements()
    if (!elements.length) {
      event.preventDefault()
      dialog.value?.focus()
      return
    }

    const first = elements[0]
    const last = elements[elements.length - 1]
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  watch(
    () => explorer.isOpen,
    async (open, wasOpen) => {
      if (open) {
        opener.value = document.activeElement instanceof HTMLElement ? document.activeElement : null
        copyState.value = explorer.copyStatus
        newTabFailed.value = false
        previousBodyOverflow.value = document.body.style.overflow
        document.body.style.overflow = 'hidden'
        resetFrame()
        await nextTick()
        dialog.value?.focus()
      } else if (wasOpen) {
        await nextTick()
        document.body.style.overflow = previousBodyOverflow.value
        opener.value?.focus()
        opener.value = null
      }
    },
  )

  watch(query, () => { copyState.value = 'idle' })

  onMounted(() => document.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKeydown)
    document.body.style.overflow = previousBodyOverflow.value
    opener.value?.focus()
  })
</script>

<template>
  <Teleport to="body">
    <div v-if="explorer.isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-3">
      <div class="absolute inset-0 bg-foreground/40" aria-hidden="true" />

      <section ref="dialog" tabindex="-1" role="dialog" aria-modal="true" :aria-labelledby="labelledBy"
               class="relative z-10 flex h-full w-full flex-col overflow-hidden rounded-xl border border-border bg-popover text-popover-foreground shadow-2xl outline-none">
        <header class="flex flex-wrap items-start justify-between gap-3 border-b border-border px-4 py-3 sm:px-5">
          <div class="min-w-0">
            <p class="font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">Full-screen tool</p>
            <h2 :id="labelledBy" class="truncate font-serif text-lg font-semibold">{{ title }}</h2>
          </div>
          <EaButton variant="ghost" size="icon" aria-label="Close Visual Graph Explorer" @click="close">
            <X class="size-4" />
          </EaButton>
        </header>

        <div class="grid min-h-0 flex-1 grid-rows-[minmax(0,1fr)_auto] bg-muted/30">
          <div class="relative min-h-0">
            <div v-if="!configured" class="flex h-full items-center justify-center p-6 text-center">
              <div class="max-w-md rounded-lg border border-destructive/35 bg-destructive/10 p-4 text-sm text-destructive">
                The Visual Graph Explorer has not been configured for this environment. Use “Open in new tab” after its URL is configured.
              </div>
            </div>

            <template v-else>
              <iframe v-if="!iframeError" :key="iframeKey" :src="explorerUrl ?? undefined" :title="`${title} workspace`"
                      class="h-full w-full border-0 bg-background" @load="iframeLoaded = true" @error="iframeError = true" />
              <div v-if="!iframeLoaded && !iframeError" class="absolute inset-0 grid place-items-center bg-background/80" aria-live="polite">
                <div class="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 class="size-4 animate-spin" /> Loading the Explorer…
                </div>
              </div>
              <div v-if="iframeError" class="flex h-full items-center justify-center p-6 text-center">
                <div class="max-w-md rounded-lg border border-destructive/35 bg-destructive/10 p-4 text-sm text-destructive">
                  <p>The Explorer could not be displayed here.</p>
                  <EaButton class="mt-3" variant="outline" size="sm" @click="retry">
                    <RefreshCw class="size-3.5" /> Retry
                  </EaButton>
                </div>
              </div>
            </template>
          </div>

          <footer class="border-t border-border bg-popover px-4 py-3 sm:px-5">
            <div class="flex flex-wrap items-center gap-2">
              <EaButton :disabled="!query" variant="secondary" size="sm" @click="copyQuery">
                <Check v-if="copyState === 'copied'" class="size-3.5" />
                <Copy v-else class="size-3.5" />
                {{ copyState === 'copied' ? 'Query copied' : 'Copy query' }}
              </EaButton>
              <EaButton :disabled="!explorerUrl" variant="outline" size="sm" @click="openInNewTab">
                <ExternalLink class="size-3.5" /> Open in new tab
              </EaButton>
              <EaButton variant="ghost" size="sm" @click="close">Close</EaButton>
              <span v-if="copyState === 'failed'" role="status" class="text-xs text-destructive">
                Copy was not available. Select the query below and copy it manually.
              </span>
              <span v-else-if="copyState === 'copied'" role="status" class="text-xs text-muted-foreground">
                Query copied. In the Explorer, open the graph, create a new query, paste and run.
              </span>
              <span v-if="newTabFailed" role="status" class="text-xs text-destructive">
                The browser blocked the new tab. Allow pop-ups or open the configured Explorer URL directly.
              </span>
            </div>

            <p v-if="explorer.handoff" class="mt-2 text-xs leading-relaxed text-muted-foreground">
              {{ explorer.handoff }}
            </p>
            <p class="mt-2 text-xs leading-relaxed text-muted-foreground">
              If DSS shows a sign-in or access-denied page, use “Open in new tab” to sign in or request access to the Explorer project.
            </p>

            <div v-if="query" class="mt-3">
              <p class="mb-1 font-mono text-[10px] uppercase tracking-[0.08em] text-muted-foreground">Prepared Cypher</p>
              <pre tabindex="0" aria-label="Prepared Cypher query, selectable for manual copy"
                   class="max-h-28 overflow-auto rounded-md border border-border bg-muted/45 p-2.5 font-mono text-[11px] leading-relaxed text-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring/40">{{ query }}</pre>
            </div>
          </footer>
        </div>
      </section>
    </div>
  </Teleport>
</template>
