<script setup lang="ts">
  /**
   * Act 4 — the list, and the eyeball test.
   *
   * The act this demo exists for: open a disease you know, judge the top of the
   * list yourself, then narrow it on your own thresholds.
   *
   * Guardrails this view must keep (see WEBAPP design doc):
   *  - the drug badges are the ground truth the enrichment is measured against,
   *    so they render as badges and are never a filter control;
   *  - the liability flag is shown, never filtered — filtering it deletes ERBB2
   *    from its own disease's list;
   *  - every funnel count renders its rank cut-off, so a count never acquires
   *    two values;
   *  - `prediction` is not fetched and not shown.
   */
  import { onMounted, ref, watch } from 'vue'
  import { ListFilter } from 'lucide-vue-next'
  import { EaSelect, EaEmpty } from '@/components/ui'
  import { apiUrl } from '@/utils/api'

  defineOptions({ name: 'ShortlistView' })

  interface Disease {
    disease_index: number
    disease_name: string
    n_candidates: number
    n_known: number
  }
  interface Row {
    gene_name: string
    rank_in_disease: number
    score: number
    is_target: number
    top_shap_drivers: string | null
    druggability_class: string | null
    ot_class_l1: string | null
    has_safety_liability: number
    approved_for_disease: number
    investigational_for_disease: number
  }
  interface Payload {
    disease_name: string
    funnel: { step: string; n: number }[]
    rows: Row[]
    returned: number
  }

  const diseases = ref<Disease[]>([])
  const selected = ref<number | undefined>()
  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  const novelOnly = ref(false)
  const tractableOnly = ref(false)
  const excludeSecreted = ref(false)
  const maxRank = ref(200)

  async function loadDiseases() {
    try {
      const res = await fetch(apiUrl('/api/candidates/diseases'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      diseases.value = await res.json()
      // HER2+ is the spine: a clinician recognises its top ranks on sight.
      const her2 = diseases.value.find((d) => /HER2/i.test(d.disease_name))
      selected.value = (her2 ?? diseases.value[0])?.disease_index
    } catch (e) {
      error.value = `Could not load diseases: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function loadCandidates() {
    if (selected.value === undefined) return
    loading.value = true
    error.value = null
    try {
      const q = new URLSearchParams({
        disease: String(selected.value),
        novel_only: String(novelOnly.value),
        tractable_only: String(tractableOnly.value),
        exclude_secreted: String(excludeSecreted.value),
        max_rank: String(maxRank.value),
      })
      const res = await fetch(apiUrl(`/api/candidates?${q}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load candidates: ${e instanceof Error ? e.message : String(e)}`
      data.value = null
    } finally {
      loading.value = false
    }
  }

  onMounted(loadDiseases)
  watch([selected, novelOnly, tractableOnly, excludeSecreted, maxRank], loadCandidates)
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <header class="flex flex-col gap-1">
      <p class="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
        Act 4 of 4 · The list
      </p>
      <h1 class="text-2xl font-semibold tracking-tight">Does this look right to you?</h1>
      <p class="max-w-3xl text-sm text-muted-foreground">
        One disease, all the way down. Nothing is pre-filtered — narrow it on your own thresholds,
        then judge the top of the list yourself.
      </p>
    </header>

    <div class="flex flex-wrap items-end gap-4 rounded-md border border-border bg-card p-4">
      <label class="flex min-w-64 flex-col gap-1 text-sm">
        <span class="text-muted-foreground">Disease</span>
        <EaSelect
          v-model="selected"
          :options="diseases.map((d) => ({ value: d.disease_index, label: d.disease_name }))"
          placeholder="— Select a disease —"
        />
      </label>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="novelOnly" type="checkbox" class="size-4" /> Novel only
      </label>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="tractableOnly" type="checkbox" class="size-4" /> Tractable
      </label>
      <label class="flex items-center gap-2 text-sm">
        <input v-model="excludeSecreted" type="checkbox" class="size-4" /> Not secreted
      </label>
      <label class="flex flex-col gap-1 text-sm">
        <span class="text-muted-foreground">Rank ≤</span>
        <input v-model.number="maxRank" type="number" min="1" max="5000"
               class="w-24 rounded-md border border-border bg-background px-2 py-1" />
      </label>
    </div>

    <p v-if="error" class="text-sm text-destructive">{{ error }}</p>

    <div v-if="data" class="flex flex-wrap gap-2">
      <span
        v-for="(f, i) in data.funnel"
        :key="f.step"
        class="rounded-md border border-border px-3 py-1.5 font-mono text-xs"
        :class="i === data.funnel.length - 1 ? 'bg-primary/10 font-semibold' : 'bg-muted/40'"
      >
        {{ f.step }} · {{ f.n.toLocaleString() }}
      </span>
    </div>

    <div v-if="data && data.rows.length" class="overflow-x-auto rounded-md border border-border">
      <table class="w-full text-sm">
        <thead class="border-b border-border bg-muted/40 text-left">
          <tr class="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <th class="px-3 py-2">Rank</th><th class="px-3 py-2">Gene</th>
            <th class="px-3 py-2">Score</th><th class="px-3 py-2">Class</th>
            <th class="px-3 py-2">Evidence</th><th class="px-3 py-2">Drivers</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in data.rows" :key="r.gene_name" class="border-b border-border/50 last:border-0">
            <td class="px-3 py-2 font-mono tabular-nums text-muted-foreground">{{ r.rank_in_disease }}</td>
            <td class="px-3 py-2 font-mono font-medium">{{ r.gene_name }}</td>
            <td class="px-3 py-2 font-mono tabular-nums">{{ r.score?.toFixed(3) }}</td>
            <td class="px-3 py-2 text-muted-foreground">{{ r.ot_class_l1 || '—' }}</td>
            <td class="flex flex-wrap gap-1 px-3 py-2">
              <span v-if="r.is_target" class="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase">known</span>
              <span v-else class="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] uppercase">novel</span>
              <span v-if="r.approved_for_disease"
                    class="rounded bg-emerald-500/10 px-1.5 py-0.5 text-[10px] uppercase" title="Ground truth the enrichment is measured against — not a filter">approved</span>
              <span v-if="r.investigational_for_disease"
                    class="rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase" title="In trials — not a filter">in trials</span>
              <span v-if="r.has_safety_liability"
                    class="rounded bg-rose-500/10 px-1.5 py-0.5 text-[10px] uppercase"
                    title="A public liability flag. Liabilities are discovered BY drugging — the flag marks well-studied targets, and is deliberately not a filter">liability</span>
            </td>
            <td class="px-3 py-2 text-xs text-muted-foreground">{{ r.top_shap_drivers || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <EaEmpty v-else-if="!loading && !error" :icon="ListFilter" title="No candidates"
             description="Select a disease to see its ranked list." />
  </div>
</template>
