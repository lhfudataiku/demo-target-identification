<script setup lang="ts">
  /**
   * Act 4 — the list, and the eyeball test.
   *
   * The act this demo exists for: open a disease you know, judge the top of the
   * list yourself, then narrow it on your own thresholds.
   *
   * Card structure follows DASHBOARD_MOCKUP_V3.html; styling is the Dataiku
   * design system rather than the mockup's standalone one.
   *
   * Guardrails enforced here, not merely documented:
   *  - drug badges and the liability flag RENDER but are never filter controls
   *    (the badges are the ground truth the enrichment is measured against;
   *    filtering the liability flag deletes ERBB2 from its own disease's list);
   *  - `prediction` is never fetched or shown;
   *  - every funnel count renders its rank cut-off, so a count cannot acquire
   *    two values;
   *  - no discovery-enrichment figure appears on a summary tile.
   */
  import { computed, onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActSay from '@/components/act/ActSay.vue'
  import { EaSelect, EaEmpty } from '@/components/ui'
  import ActStat from '@/components/act/ActStat.vue'
  import ActTabs from '@/components/act/ActTabs.vue'
  import ActInfo from '@/components/act/ActInfo.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { ListFilter, ShieldAlert, FileCheck2 } from 'lucide-vue-next'

  defineOptions({ name: 'ShortlistView' })

  interface Disease { disease_index: number; disease_name: string; n_candidates: number; n_known: number }
  interface Row {
    gene_name: string; rank_in_disease: number; score: number; is_target: number
    top_shap_drivers: string | null; druggability_class: string | null; ot_class_l1: string | null
    has_safety_liability: number; approved_for_disease: number; investigational_for_disease: number
  }
  interface Payload { disease_name: string; funnel: { step: string; n: number }[]; rows: Row[]; returned: number }

  const diseases = ref<Disease[]>([])
  const selected = ref<number | undefined>()
  // EaSelect models strings; disease_index is numeric.
  const selectedStr = computed<string | undefined>({
    get: () => (selected.value === undefined ? undefined : String(selected.value)),
    set: (v) => { selected.value = v === undefined ? undefined : Number(v) },
  })
  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)

  const novelOnly = ref(false)
  const tractableOnly = ref(false)
  const excludeSecreted = ref(false)
  const maxRank = ref(200)

  // The table's own controls, as v3 has them. These filter the rows already
  // loaded rather than refetching: the funnel above describes the population,
  // this describes what is on screen.
  const search = ref('')
  const tract = ref('')          // '' | sm | ab | either
  const klass = ref('')
  const liab = ref(false)        // strike out, never remove — see the safety card

  // Paging. 20 rows is what a person can actually scan; the funnel above still
  // reports the true totals, so paging never hides how big the list is.
  const PAGE = 20
  const page = ref(1)

  const classes = computed(() =>
    [...new Set((data.value?.rows ?? []).map((r) => r.ot_class_l1).filter(Boolean))].sort() as string[])

  const shown = computed(() => (data.value?.rows ?? []).filter((r) => {
    if (search.value && !r.gene_name.toLowerCase().includes(search.value.toLowerCase())) return false
    if (tract.value === 'sm' && !r.ot_sm_tractable) return false
    if (tract.value === 'ab' && !r.ot_ab_tractable) return false
    if (tract.value === 'either' && !(r.ot_sm_tractable || r.ot_ab_tractable)) return false
    if (klass.value && r.ot_class_l1 !== klass.value) return false
    return true
  }))
  const pageCount = computed(() => Math.max(1, Math.ceil(shown.value.length / PAGE)))
  const paged = computed(() =>
    shown.value.slice((page.value - 1) * PAGE, page.value * PAGE))
  // Any change to the filters or the disease puts you back on page 1 — staying
  // on page 7 of a list that now has two pages reads as an empty table.
  watch([search, tract, klass, selected, novelOnly, tractableOnly, excludeSecreted, maxRank],
        () => { page.value = 1 })

  const tractLabel = (r: Row) =>
    [r.ot_sm_tractable ? 'SM' : '', r.ot_ab_tractable ? 'Ab' : ''].filter(Boolean).join(' + ') || '—'

  // What the liability control would cost, on this disease's own list.
  const struckOnScreen = computed(() => shown.value.filter((r) => r.has_safety_liability).length)
  const top15 = computed(() => (data.value?.rows ?? []).filter((r) => r.rank_in_disease <= 15))
  const struckTop15 = computed(() => top15.value.filter((r) => r.has_safety_liability).length)
  const struckNamed = computed(() =>
    top15.value.filter((r) => r.has_safety_liability)
      .sort((a, b) => a.rank_in_disease - b.rank_in_disease)[0])

  const current = computed(() => diseases.value.find((d) => d.disease_index === selected.value))
  const liabilityInTop15 = computed(
    () => data.value?.rows.filter((r) => r.rank_in_disease <= 15 && r.has_safety_liability).length ?? 0,
  )

  async function loadDiseases() {
    try {
      const res = await fetch(apiUrl('/api/candidates/diseases'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      diseases.value = await res.json()
      // The spine disease: a clinician recognises its top ranks on sight.
      // Falls back to the largest pool if the name does not carry "HER2".
      selected.value = (diseases.value.find((d) => /HER2/i.test(d.disease_name))
        ?? diseases.value[0])?.disease_index
    } catch (e) {
      error.value = `Could not load diseases: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function loadCandidates() {
    if (selected.value === undefined) return
    loading.value = true; error.value = null
    try {
      const q = new URLSearchParams({
        disease: String(selected.value), novel_only: String(novelOnly.value),
        tractable_only: String(tractableOnly.value), exclude_secreted: String(excludeSecreted.value),
        max_rank: String(maxRank.value),
      })
      const res = await fetch(apiUrl(`/api/candidates?${q}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load candidates: ${e instanceof Error ? e.message : String(e)}`
      data.value = null
    } finally { loading.value = false }
  }

  onMounted(loadDiseases)
  watch([selected, novelOnly, tractableOnly, excludeSecreted, maxRank], loadCandidates)
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 4 of 4 · The list
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">Does this look right to you?</h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        One disease, all the way down — and the act this demo exists for. Open a disease you know and
        judge the top of the list yourself; the scientist is the instrument. Then take the controls:
        nothing is pre-filtered, and you narrow it on your own thresholds.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <!-- The contract, stated before the list appears. -->
      <!-- Your thresholds, not ours. -->
      <!-- The ranked list. -->
      <ActCard span="col-span-12" :icon="ListFilter"
               :title="`The ranked list${current ? ' — ' + current.disease_name : ''}`"
               :chips="[['live', 'live']]"
               desc="Every control for this act lives here. Nothing is pre-cut — you set the cut-offs, and the funnel shows what each one costs."
               :src="['dashboard_candidates']">
        <!-- population controls: these refetch, because they change what is scored -->
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-64 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Disease
              <ActInfo text="One of the 13 diseases scored into a ranked candidate list." />
            </span>
            <EaSelect v-model="selectedStr" placeholder="— Select a disease —"
                      :options="diseases.map((d) => ({ value: String(d.disease_index),
                                 label: `${d.disease_name} (${d.n_candidates.toLocaleString()})` }))" />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="novelOnly" type="checkbox" class="size-4 accent-primary" /> Novel only
            <ActInfo text="Drops genes already annotated as targets for this disease, so what remains is what the model surfaced rather than reproduced." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="tractableOnly" type="checkbox" class="size-4 accent-primary" /> Tractable
            <ActInfo text="Open Targets judges the protein reachable by a small molecule or an antibody." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <input v-model="excludeSecreted" type="checkbox" class="size-4 accent-primary" /> Not secreted
            <ActInfo text="Excludes proteins released between cells. Harder to drug than ones sitting on a membrane." />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Rank ≤
              <ActInfo text="How far down the ranked list to go. Every count below carries this cut-off, so a number can never mean two things." />
            </span>
            <input v-model.number="maxRank" type="number" min="1" max="5000"
                   class="w-24 rounded-md border border-input bg-background px-2 py-1.5" />
          </label>
        </div>

        <div v-if="data" class="mt-3 flex flex-wrap items-center gap-1.5">
          <template v-for="(f, i) in data.funnel" :key="f.step">
            <span class="rounded-md px-2.5 py-1 font-mono text-xs"
                  :class="i === data.funnel.length - 1
                    ? 'bg-primary/25 font-medium text-primary-foreground'
                    : 'bg-secondary text-muted-foreground'">
              {{ f.step }} · {{ f.n.toLocaleString() }}
            </span>
            <span v-if="i < data.funnel.length - 1" class="text-muted-foreground">→</span>
          </template>
        </div>

        <hr class="my-4 border-border" />

        <!-- view controls: these filter what is already on screen -->
        <div class="flex flex-wrap items-center gap-2">
          <input v-model="search" type="search" placeholder="Search gene…"
                 class="w-36 rounded-md border border-input bg-background px-2 py-1 text-sm" />
          <ActTabs :model-value="novelOnly ? 'novel' : 'all'"
                   :options="[{ value: 'all', label: 'All' }, { value: 'novel', label: 'Novel only' }]"
                   @update:model-value="(v) => (novelOnly = v === 'novel')" />
          <span class="flex items-center">
            <select v-model="tract" class="rounded-md border border-input bg-background px-2 py-1 text-sm">
              <option value="">Any tractability</option>
              <option value="sm">Small-molecule</option>
              <option value="ab">Antibody</option>
              <option value="either">Either</option>
            </select>
            <ActInfo text="Small-molecule: a drug-like pocket. Antibody: reachable from outside the cell. Either: at least one." />
          </span>
          <span class="flex items-center">
            <select v-model="klass" class="rounded-md border border-input bg-background px-2 py-1 text-sm">
              <option value="">Any target class</option>
              <option v-for="c in classes" :key="c" :value="c">{{ c }}</option>
            </select>
            <ActInfo text="Open Targets' protein family — enzyme, membrane receptor, transcription factor and so on." />
          </span>
          <label class="flex items-center gap-2 text-sm"
                 :class="liab ? 'font-medium text-destructive' : ''">
            <input v-model="liab" type="checkbox" class="size-4 accent-[var(--destructive)]" />
            Strike out liabilities
            <ActInfo text="A public annotation recording that an adverse effect has been observed and published for this protein — from clinical or experimental evidence, aggregated by Open Targets. Its limits matter: the flag is not dose-, modality- or indication-specific, it says nothing about whether an effect is manageable, and it can only exist for targets that have already been drugged or studied. So an unflagged gene is not safe — it is unstudied. Treat it as evidence of attention, not of danger." />
          </label>
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ shown.length }} of {{ data?.rows.length ?? 0 }} shown
          </span>
        </div>

        <div v-if="shown.length" class="mt-3 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rank<ActInfo text="Position in this disease's list. The score behind it is uncalibrated, so the ordering is what carries meaning — not the number." /></TableHead>
                <TableHead>Gene<ActInfo text="HGNC symbol of the candidate protein." /></TableHead>
                <TableHead>Class<ActInfo text="Open Targets protein family." /></TableHead>
                <TableHead>Tract.<ActInfo text="SM = small-molecule tractable · Ab = antibody tractable · — = neither assessed." /></TableHead>
                <TableHead>Status<ActInfo text="associated = an Open Targets genetic or somatic association already exists for this disease–gene pair, at score ≥ 0.3 — this is the label the model was trained on · novel = no such association · approved / trial = drug evidence, shown as ground truth and never filterable · liability = a recorded safety flag." /></TableHead>
                <TableHead>Top drivers<ActInfo text="The features that moved this candidate most, from its SHAP attribution." /></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="r in paged" :key="r.gene_name"
                        :class="liab && r.has_safety_liability ? 'opacity-45 line-through' : ''">
                <TableCell class="font-mono tabular-nums text-muted-foreground">{{ r.rank_in_disease }}</TableCell>
                <TableCell class="font-mono font-medium">{{ r.gene_name }}</TableCell>
                <TableCell class="text-muted-foreground">{{ r.ot_class_l1 || '—' }}</TableCell>
                <TableCell class="font-mono text-[11px]">{{ tractLabel(r) }}</TableCell>
                <TableCell class="no-underline">
                  <span class="mr-1 inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                        :class="r.is_target ? 'bg-secondary text-muted-foreground' : 'bg-primary/25 text-primary-foreground'">
                    {{ r.is_target ? 'associated' : 'novel' }}
                  </span>
                  <span v-if="r.approved_for_disease"
                        class="mr-1 inline-block rounded bg-chart-3/20 px-1.5 py-0.5 font-mono text-[10px] uppercase">approved</span>
                  <span v-if="r.investigational_for_disease"
                        class="mr-1 inline-block rounded bg-chart-4/25 px-1.5 py-0.5 font-mono text-[10px] uppercase">trial</span>
                  <span v-if="r.has_safety_liability"
                        class="inline-block rounded bg-destructive/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-destructive">liability</span>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ r.top_shap_drivers || '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div v-if="shown.length > PAGE"
             class="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
          <span class="font-mono text-[11px] text-muted-foreground">
            {{ (page - 1) * PAGE + 1 }}–{{ Math.min(page * PAGE, shown.length) }}
            of {{ shown.length.toLocaleString() }}
          </span>
          <div class="flex items-center gap-1">
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === 1" @click="page = 1">« First</button>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === 1" @click="page--">‹ Prev</button>
            <span class="px-2 font-mono text-[11px] text-muted-foreground">
              page {{ page }} / {{ pageCount }}
            </span>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === pageCount" @click="page++">Next ›</button>
            <button type="button" class="rounded-md border border-input px-2 py-1 text-[12px]
                    disabled:opacity-40 hover:enabled:bg-accent/50"
                    :disabled="page === pageCount" @click="page = pageCount">Last »</button>
          </div>
        </div>
        <EaEmpty v-if="!shown.length" :icon="ListFilter" title="Nothing matches"
                 description="Loosen a filter, or pick another disease." />

        <div class="mt-3 rounded-lg border border-dashed border-destructive/50 px-3.5 py-2.5 text-[13px] leading-relaxed">
          <p class="mb-1 font-mono text-[10px] uppercase tracking-wide text-destructive">Must not appear</p>
          <b>The drug badges are not filterable, and that is deliberate.</b> Approved-for-disease and
          in-trials are the ground truth the discovery result is measured against. A shortlist filtered
          by them would be circular, so they are shown and never actionable.
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="Why this gene?" :chips="[['mock', 'not built']]"
               desc="The SHAP attribution drawer — which evidence moved this candidate.">
        <p class="py-6 text-center text-[13px] text-muted-foreground">
          Not built yet. The drivers column above is the raw form of what this will render.
        </p>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="The mechanism, on the graph"
               :chips="[['port', 'existing webapp']]"
               desc="The Visual Graph Explorer embed — top-ranked genes and their interaction edges to associated disease genes.">
        <p class="py-6 text-center text-[13px] text-muted-foreground">
          Not built yet. Ports from the existing graph webapp.
        </p>
      </ActCard>
    </div>
  </div>
</template>
