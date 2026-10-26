/**
 * The one disease both pages describe (DEC-DEMO-005).
 *
 * WHY. The shortlist and "Why trust the list" answer questions about the same
 * disease: the list ranks its genes, the evidence page places its AUC in the
 * spread and opens its family. Two local selections would let the two pages
 * show different diseases side by side, so both read and write this store.
 *
 * The disease list is the shortlist's own (`/api/candidates/diseases`), fetched
 * once for both pages. Not persisted: a fresh load opens on the spine disease.
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiUrl } from '@/utils/api'

export interface Disease {
  disease_index: number
  disease_name: string
  n_candidates: number
  n_known: number
}

export const useSelectionStore = defineStore('selection', () => {
  const diseases = ref<Disease[]>([])
  const diseaseIndex = ref<number | undefined>(undefined)
  const error = ref<string | null>(null)
  let pending: Promise<void> | null = null

  async function fetchDiseases() {
    try {
      const res = await fetch(apiUrl('/api/candidates/diseases'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      diseases.value = await res.json()
      error.value = null
      // The spine disease: a clinician recognises its top ranks on sight.
      // Falls back to the largest pool if no name carries "HER2".
      diseaseIndex.value ??= (diseases.value.find((d) => /HER2/i.test(d.disease_name))
        ?? diseases.value[0])?.disease_index
    } catch (e) {
      error.value = `Could not load diseases: ${e instanceof Error ? e.message : String(e)}`
      pending = null
    }
  }

  /** Load the list once; later callers share the same request. */
  function ensureDiseases(): Promise<void> {
    pending ??= fetchDiseases()
    return pending
  }

  return { diseases, diseaseIndex, error, ensureDiseases }
})
