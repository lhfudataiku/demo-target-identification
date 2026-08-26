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
      <ActCard span="col-span-12" :icon="FileCheck2" accent="var(--chart-1)" title="The contract"
               desc="Stated before the list appears, because it is what makes the rest arguable.">
        <ul class="flex flex-col gap-1.5 text-[13px] leading-relaxed text-muted-foreground">
          <li><b class="text-foreground">Nothing is pre-filtered.</b> Every candidate the model scored is here; you cut it.</li>
          <li><b class="text-foreground">Every row carries its evidence</b> — the drivers that moved it, and the class it belongs to.</li>
          <li><b class="text-foreground">The drug badges are ground truth, not a filter.</b> They are what the enrichment is measured against; filtering on them would make the claim circular.</li>
          <li><b class="text-foreground">This is a reconstruction test.</b> We are not claiming discovery — we are asking whether the top of a list you know reads correctly.</li>
        </ul>
      </ActCard>

      <!-- Your thresholds, not ours. -->
      <ActCard span="col-span-12 lg:col-span-7" title="Your thresholds, not ours"
               :chips="[['live', 'live']]"
               desc="Set the cut-offs a programme would actually apply. The funnel shows what each one costs."
               :src="['dashboard_candidates']">
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-64 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Disease</span>
            <EaSelect v-model="selectedStr" placeholder="— Select a disease —"
                      :options="diseases.map((d) => ({ value: String(d.disease_index),
                                 label: `${d.disease_name} (${d.n_candidates.toLocaleString()})` }))" />
          </label>
          <label class="flex items-center gap-2 text-sm"><input v-model="novelOnly" type="checkbox" class="size-4 accent-primary" /> Novel only</label>
          <label class="flex items-center gap-2 text-sm"><input v-model="tractableOnly" type="checkbox" class="size-4 accent-primary" /> Tractable</label>
          <label class="flex items-center gap-2 text-sm"><input v-model="excludeSecreted" type="checkbox" class="size-4 accent-primary" /> Not secreted</label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Rank ≤</span>
            <input v-model.number="maxRank" type="number" min="1" max="5000"
                   class="w-24 rounded-md border border-input bg-background px-2 py-1.5" />
          </label>
        </div>

        <div v-if="data" class="mt-4 flex flex-wrap items-center gap-1.5">
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
      </ActCard>

      <!-- What a safety filter would cost. -->
      <ActCard span="col-span-12 lg:col-span-5" :icon="ShieldAlert" accent="var(--chart-4)" title="What a safety filter would cost you"
               :chips="[['live', 'live']]"
               desc="The most obviously-right filter in drug discovery, and the measurement went the other way.">
        <p class="text-[13px] leading-relaxed text-muted-foreground">
          Liability-flagged genes are <b class="text-foreground">4.62×</b> enriched among real drug
          targets. Liabilities are discovered <i>by</i> drugging something, so the flag marks the
          best-studied targets rather than the dangerous ones.
        </p>
        <ActSay v-if="data" class="mt-3">
          In this list, <b class="font-mono">{{ liabilityInTop15 }}</b> of the top 15 carry a
          liability flag. Filtering them out removes them from their own disease's shortlist —
          which is why the flag is shown and never filtered.
        </ActSay>
      </ActCard>

      <!-- The ranked list. -->
      <ActCard span="col-span-12" :title="`The ranked list${current ? ' — ' + current.disease_name : ''}`"
               :chips="[['live', 'live']]"
               :desc="data ? `Showing ${data.returned} of ${data.funnel[data.funnel.length - 1].n.toLocaleString()} after your filters.` : undefined"
               :src="['dashboard_candidates']">
        <div v-if="data && data.rows.length" class="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Rank</TableHead><TableHead>Gene</TableHead>
                <TableHead>Score</TableHead><TableHead>Class</TableHead>
                <TableHead>Evidence</TableHead><TableHead>Top drivers</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="r in data.rows" :key="r.gene_name">
                <TableCell class="font-mono tabular-nums text-muted-foreground">{{ r.rank_in_disease }}</TableCell>
                <TableCell class="font-mono font-medium">{{ r.gene_name }}</TableCell>
                <TableCell class="font-mono tabular-nums">{{ r.score?.toFixed(3) }}</TableCell>
                <TableCell class="text-muted-foreground">{{ r.ot_class_l1 || '—' }}</TableCell>
                <TableCell>
                  <span class="mr-1 inline-block rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                        :class="r.is_target ? 'bg-secondary text-muted-foreground' : 'bg-primary/25 text-primary-foreground'">
                    {{ r.is_target ? 'known' : 'novel' }}
                  </span>
                  <span v-if="r.approved_for_disease"
                        title="Ground truth the enrichment is measured against — deliberately not a filter"
                        class="mr-1 inline-block rounded bg-chart-3/20 px-1.5 py-0.5 font-mono text-[10px] uppercase">approved</span>
                  <span v-if="r.investigational_for_disease"
                        title="In trials — deliberately not a filter"
                        class="mr-1 inline-block rounded bg-chart-4/25 px-1.5 py-0.5 font-mono text-[10px] uppercase">in trials</span>
                  <span v-if="r.has_safety_liability"
                        title="A public liability flag. Liabilities are discovered BY drugging, so the flag marks well-studied targets — shown, never filtered."
                        class="inline-block rounded bg-destructive/15 px-1.5 py-0.5 font-mono text-[10px] uppercase text-destructive">liability</span>
                </TableCell>
                <TableCell class="text-xs text-muted-foreground">{{ r.top_shap_drivers || '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p v-else-if="loading" class="py-6 text-center text-sm text-muted-foreground">Loading…</p>
        <EaEmpty v-else :icon="ListFilter" title="No list yet"
                 description="Select a disease to see its ranked candidates." />
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="Why this gene?" :chips="[['mock', 'not built']]"
               desc="The SHAP attribution drawer — which evidence moved this candidate.">
        <p class="py-6 text-center text-[13px] text-muted-foreground">
          Not built yet. The drivers column above is the raw form of what this will render.
        </p>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-6" title="The mechanism, on the graph"
               :chips="[['port', 'existing webapp']]"
               desc="The Visual Graph Explorer embed — top-ranked genes and their interaction edges to known disease genes.">
        <p class="py-6 text-center text-[13px] text-muted-foreground">
          Not built yet. Ports from the existing graph webapp.
        </p>
      </ActCard>
    </div>
  </div>
</template>
