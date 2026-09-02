import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ExplorerLaunchContext {
  title: string
  cypher?: string
  handoff?: string
  copyStatus?: ExplorerCopyStatus
}

export type ExplorerCopyStatus = 'idle' | 'copied' | 'failed'

export const useVisualGraphExplorerStore = defineStore('visualGraphExplorer', () => {
  const isOpen = ref(false)
  const title = ref('')
  const cypher = ref<string | undefined>()
  const handoff = ref<string | undefined>()
  const copyStatus = ref<ExplorerCopyStatus>('idle')

  function open(context: ExplorerLaunchContext): void {
    title.value = context.title
    cypher.value = context.cypher
    handoff.value = context.handoff
    copyStatus.value = context.copyStatus ?? 'idle'
    isOpen.value = true
  }

  function close(): void {
    isOpen.value = false
    title.value = ''
    cypher.value = undefined
    handoff.value = undefined
    copyStatus.value = 'idle'
  }

  return { isOpen, title, cypher, handoff, copyStatus, open, close }
})
