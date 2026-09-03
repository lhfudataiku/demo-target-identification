/**
 * Presenter mode — whether the deck shows the lines meant for the presenter.
 *
 * WHY. `ActSay` was carrying two different kinds of statement at identical
 * visual weight: things the audience should read ("some diseases enrich
 * twenty-fold and some barely at all") and things only the Dataiku presenter
 * should ("this is the number to volunteer, not to be asked for", "say six
 * sources, not seven" -- the latter in the destructive red a client reads as a
 * data problem). One app, two audiences, one switch.
 *
 * Per-browser in localStorage, mirroring stores/admin.ts. Deliberately NOT a
 * DSS project variable: this is a property of who is standing in front of the
 * screen, not of the project, and it must not require a backend round trip
 * thirty seconds before a demo.
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

const STORAGE_KEY = 'targetid.presenter'

function loadFromStorage(): boolean | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return Boolean((JSON.parse(raw) as { showNotes?: boolean }).showNotes)
  } catch {
    return null
  }
}

export const usePresenterStore = defineStore('presenter', () => {
  // Default ON: the person running this locally is almost always the presenter
  // rehearsing. Switch it off before sharing the screen with a client.
  const showNotes = ref<boolean>(loadFromStorage() ?? true)

  watch(showNotes, (v) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify({ showNotes: v }))
    } catch {
      /* localStorage unavailable (e.g. blocked third-party storage) */
    }
  })

  return { showNotes }
})
