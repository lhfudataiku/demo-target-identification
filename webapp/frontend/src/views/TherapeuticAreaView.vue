<script setup lang="ts">
  /**
   * Act 3 — the therapeutic area.
   *
   * "Does it hold across my area, or just on one term?" — pick a family, show
   * the same model against every term in it.
   *
   * The point of this act is the UNCERTAINTY, not the average. A term with 8
   * associated targets and one with 600 must not read the same, so every AUC renders
   * with its 95% interval, and terms flagged untrustworthy are shown but never
   * quoted as a score.
   */
  import { computed, onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import { EaSelect, EaEmpty } from '@/components/ui'
  import ActTabs from '@/components/act/ActTabs.vue'
  import ActGeneGrid from '@/components/act/ActGeneGrid.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import ActSay from '@/components/act/ActSay.vue'
  import ActIntervals from '@/components/act/ActIntervals.vue'
  import ActMatrix from '@/components/act/ActMatrix.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import { Network, GitCompare, Ruler, Users } from 'lucide-vue-next'

  defineOptions({ name: 'TherapeuticAreaView' })

  interface Family { family_id: number; family_name: string; n_terms: number; macro_auc: number; n_trustworthy: number }
  interface Term {
    disease_index: number; disease_name: string
    auc: number; lo95: number; hi95: number; trustworthy: boolean; n_pos: number
    enrichment: number | null; hop_depth: number
  }
  interface Detail { gene_grid: { name: string; ranks: Record<string, number>; n_terms: number }[]
  grid_columns: string[]
  overlap_all: { a: string; b: string; shared: number }[]
  overlap_novel: { a: string; b: string; shared: number }[]
  coverage: { with_data: number; total: number }
  family_id: number; n_terms: number; macro_auc: number; terms: Term[]; overlap: { a: string; b: string; shared: number }[] }

  const families = ref<Family[]>([])
  const selected = ref<number | undefined>()
  const ovMode = ref('all')
  const selectedStr = computed<string | undefined>({
    get: () => (selected.value === undefined ? undefined : String(selected.value)),
    set: (v) => { selected.value = v === undefined ? undefined : Number(v) },
  })
  const detail = ref<Detail | null>(null)
  const error = ref<string | null>(null)

  // AUC axis runs 0.4–1.0: below chance is not a meaningful distinction here,
  // and a 0–1 axis wastes half the width on range nothing occupies.
  const LO = 0.4
  const pos = (v: number) => Math.max(0, Math.min(100, ((v - LO) / (1 - LO)) * 100))

  const untrustworthy = computed(() => detail.value?.terms.filter((t) => !t.trustworthy).length ?? 0)
  // v3 plots ENRICHMENT for the thin terms, labelled with n, coloured by whether
  // the AUC is trustworthy. The associated-target count is the label, not the bar.
  // v3 lists terms in ontology order — by hop depth, then size within a level.
  const orderedTerms = computed(() =>
    [...(detail.value?.terms ?? [])].sort(
      (a, b) => a.hop_depth - b.hop_depth || b.n_pos - a.n_pos))

  const thin = computed(() =>
    (detail.value?.terms ?? [])
      .filter((t) => t.enrichment !== null)
      // Ranked by associated-target count, descending: the biggest terms first, so
      // the thin tail reads as a tail.
      .sort((a, b) => b.n_pos - a.n_pos)
      .map((t) => ({
        label: `${t.disease_name}  (n=${t.n_pos})`,
        count: Math.round((t.enrichment ?? 0) * 10) / 10,
        colour: t.trustworthy ? 'var(--chart-3)' : 'var(--destructive)',
      })))
  // Genes shared by every pair in the family: the common programme.
  // The tab selects which overlap the matrix shows — it was bound but unused,
  // so switching did nothing.
  const overlapPairs = computed(() =>
    (ovMode.value === 'novel' ? detail.value?.overlap_novel : detail.value?.overlap_all) ?? [])
  // Hop order, from the backend — the same order the term table uses.
  const overlapLabels = computed(() => detail.value?.grid_columns ?? [])

  // v3's common-programme grid is the four biomarker subtypes, not every term.
  const BIOMARKER = /HER2|luminal a|luminal b|triple.?neg/i
  const gridColumns = computed(() =>
    (detail.value?.grid_columns ?? []).filter((c) => BIOMARKER.test(c)))
  const gridGenes = computed(() => {
    const cols = new Set(gridColumns.value)
    return (detail.value?.gene_grid ?? [])
      .map((g) => ({
        ...g,
        ranks: Object.fromEntries(Object.entries(g.ranks).filter(([k]) => cols.has(k))),
      }))
      .filter((g) => Object.keys(g.ranks).length > 0)
      .map((g) => ({ ...g, n_terms: Object.keys(g.ranks).length }))
      .sort((a, b) => b.n_terms - a.n_terms || a.name.localeCompare(b.name))
  })

  const commonShare = computed(() => {
    const o = detail.value?.overlap ?? []
    if (!o.length) return null
    return Math.round(o.reduce((a, p) => a + p.shared, 0) / o.length)
  })

  async function loadFamilies() {
    try {
      const res = await fetch(apiUrl('/api/families'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      families.value = await res.json()
      const breast = families.value.find((f) => /breast/i.test(f.family_name))
      selected.value = (breast ?? families.value[0])?.family_id
    } catch (e) {
      error.value = `Could not load families: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function loadDetail() {
    if (selected.value === undefined) return
    try {
      const res = await fetch(apiUrl(`/api/families/${selected.value}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      detail.value = await res.json()
    } catch (e) {
      error.value = `Could not load the family: ${e instanceof Error ? e.message : String(e)}`
      detail.value = null
    }
  }

  onMounted(loadFamilies)
  watch(selected, loadDetail)
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 3 of 4 · The therapeutic area
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">
        Does it hold across my area, or just on one term?
      </h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Most groups own one therapeutic area, so a single cherry-picked disease proves nothing. Pick
        a family and see the same model against every term in it — with the uncertainty each term
        actually has.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <ActCard span="col-span-12" :icon="Network" title="Choose a family" :chips="[['live', 'live']]"
               desc="Families are drawn from a curated medical ontology, not by an algorithm — and that choice lowered the score we report."
               :src="['family_panel']">
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-80 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Disease family</span>
            <EaSelect v-model="selectedStr" placeholder="— Select a family —"
                      :options="families.map((f) => ({ value: String(f.family_id),
                                 label: `${f.family_name} — ${f.n_terms} terms` }))" />
          </label>
          <div v-if="detail" class="flex gap-8">
            <ActStat label="Terms" :value="detail.n_terms" />
            <ActStat label="Macro AUC" :value="detail.macro_auc.toFixed(4)" />
          </div>
        </div>
        <div v-if="detail" class="mt-4 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Term</TableHead><TableHead>Known targets</TableHead>
                <TableHead>AUC</TableHead><TableHead>95% interval</TableHead><TableHead>Enrichment</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="t in orderedTerms" :key="t.disease_index">
                <TableCell>
                  <span v-if="t.hop_depth > 0" class="font-mono text-muted-foreground"
                        :style="{ paddingLeft: (t.hop_depth - 1) * 14 + 'px' }">└ </span>{{ t.disease_name }}
                </TableCell>
                <TableCell class="font-mono tabular-nums text-muted-foreground">{{ t.n_pos }}</TableCell>
                <TableCell class="font-mono tabular-nums"
                           :class="t.trustworthy ? '' : 'text-muted-foreground line-through'">
                  {{ t.auc.toFixed(4) }}
                </TableCell>
                <TableCell class="font-mono text-[11.5px] tabular-nums text-muted-foreground">
                  {{ t.lo95.toFixed(3) }}–{{ t.hi95.toFixed(3) }}
                </TableCell>
                <TableCell class="font-mono tabular-nums">{{ t.enrichment ?? '—' }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p class="mt-3 text-[13px] leading-relaxed text-muted-foreground">
          Train and test are split by <b class="text-foreground">family</b>, not at random. Random
          splitting puts “diabetes” and “type 2 diabetes” on opposite sides — the same programme
          wearing two labels — and inflates the score. This is also the concrete place a customer's
          own judgment already enters the pipeline.
        </p>
      </ActCard>

      <ActCard span="col-span-12" title="AUC, with the uncertainty it actually has"
               :chips="[['live', 'live']]"
               :desc="detail ? `${detail.n_terms} terms. ${untrustworthy} have intervals too wide to read as a score — shown, never quoted.` : undefined"
               :src="['family_panel']">
        <ActIntervals v-if="detail"
                      :rows="orderedTerms.map((t) => ({ label: t.disease_name, value: t.auc,
                             lo: t.lo95, hi: t.hi95, n: t.n_pos, muted: !t.trustworthy }))" />
        <div v-if="detail && detail.terms.some((t) => t.hi95 > 1)"
             class="mt-3 rounded-lg border-l-2 border-destructive bg-destructive/10 px-3.5 py-2.5 text-[13px] leading-relaxed">
          <b>Some intervals run above 1.0 — higher than an AUC can reach.</b>
          With only a handful of associated targets the estimate is not wrong, it is
          <i>unpinned</i>. That single fact retires the metric for thin diseases better than any
          threshold argument, which is why the card beside this one changes the measure.
        </div>
        <EaEmpty v-else :icon="Network" title="No family selected"
                 description="Pick a disease family to see every term in it." />
      </ActCard>

      <ActCard span="col-span-12" :icon="Ruler" accent="var(--chart-4)"
               title="For the thin diseases, change the metric" :chips="[['live', 'live']]"
               desc="Enrichment at the head — observed hits over what chance would give. Red marks a term whose AUC is not trustworthy."
               :src="['family_panel']">
        <ActBar v-if="thin.length" :rows="thin" :row-height="22" />
        <p v-else class="py-4 text-center text-[13px] text-muted-foreground">
          Every term in this family has enough associated targets to score.
        </p>
        <ActSay class="mt-3">
          For these, quote <b>hits in the top 20</b> or the rank of the best associated target — a count
          you can verify by eye — not an AUC whose interval spans half the range.
        </ActSay>
      </ActCard>

      

      <ActCard span="col-span-12 lg:col-span-7" :icon="GitCompare" accent="var(--chart-3)" title="How much do the subtypes overlap?"
               :chips="[['live', 'live']]"
               desc="Shared genes in each pair's top 50."
               :src="['pairwise_overlap']">
        <ActTabs v-model="ovMode" class="mb-3"
                 :options="[{ value: 'all', label: 'All top-50 genes' },
                            { value: 'novel', label: 'Novel only' }]" />
        <p v-if="detail && detail.coverage.with_data < detail.coverage.total"
           class="mb-3 text-[12.5px] text-muted-foreground">
          Showing the <b>{{ detail.coverage.with_data }}</b> of {{ detail.coverage.total }} terms that
          carry ranked candidates — the rest are not scored into a top-50 list, so they cannot appear.
        </p>
        <ActMatrix v-if="overlapPairs.length" :labels="overlapLabels" :pairs="overlapPairs" />
        <EaEmpty v-else :icon="GitCompare" title="No overlap computed"
                 description="Pairwise top-50 overlap has not been computed for this family." />
      </ActCard>

      

      <ActCard span="col-span-12 lg:col-span-6" :icon="Users" accent="var(--chart-2)"
               title="The common programme, and what is subtype-specific"
               :desc="commonShare !== null ? `Pairs in this family share ${commonShare} of their top 50 on average.` : undefined">
        <ActGeneGrid v-if="gridGenes.length" :genes="gridGenes.slice(0, 120)"
                     :columns="gridColumns" :shared-at="Math.min(3, gridColumns.length)" />
        <p v-else class="py-4 text-center text-[13px] text-muted-foreground">
          No top-50 membership computed for this family.
        </p>
        <ActSay class="mt-3">
          Both halves are useful and they answer different questions. A high overlap is not a
          failure — it is a statement about the public data, and it tells you where
          <b>not</b> to expect subtype resolution.
        </ActSay>
      </ActCard>

      </div>
  </div>
</template>
