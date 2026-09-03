/**
 * The glossary drawer's open/close state.
 *
 * WHY A DRAWER AND NOT A ROUTE. A client asking "what was AUC again?" is three
 * cards into act 2 and mid-sentence. A `/glossary` route would have been fewer
 * files and would have followed the sidebar convention, but it answers the
 * question by taking them off the card they were reading. The drawer overlays.
 *
 * Mirrors stores/visualGraphExplorer.ts, which is the app's existing pattern for
 * a globally-reachable overlay: a store here, one component mounted once in
 * DefaultLayout, and any number of triggers.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useGlossaryStore = defineStore('glossary', () => {
  const isOpen = ref(false)
  /** A term to scroll to and highlight on open. Cleared on close so reopening
      from the sidebar does not silently re-highlight the last term. */
  const focusKey = ref<string | null>(null)

  function open(key?: string): void {
    focusKey.value = key ?? null
    isOpen.value = true
  }

  function close(): void {
    isOpen.value = false
    focusKey.value = null
  }

  function toggle(): void {
    if (isOpen.value) close()
    else open()
  }

  return { isOpen, focusKey, open, close, toggle }
})
