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
   *
   * COPY REVIEW 2026-09-03. This act's specific failure was vocabulary
   * inherited without introduction: "top 50" appeared nine times and was
   * defined zero times; "trustworthy" is a numeric threshold used as an English
   * adjective; and "enrichment" carried a SECOND, differently-worded gloss from
   * act 2's -- exactly the drift backend/feature_glossary.py exists to stop.
   * Every such term is now an <ActTerm> reading utils/glossary.ts, so the two
   * acts cannot describe one metric two ways again.
   */
  import { computed, onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import { EaSelect, EaEmpty } from '@/components/ui'
  import ActTabs from '@/components/act/ActTabs.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import ActTerm from '@/components/act/ActTerm.vue'
  import ActInfo from '@/components/act/ActInfo.vue'
  import ActIntervals from '@/components/act/ActIntervals.vue'
  import ActMatrix from '@/components/act/ActMatrix.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActGeneGrid from '@/components/act/ActGeneGrid.vue'
  import { Network, GitCompare, Ruler, Users, Grid3x3 } from 'lucide-vue-next'

  defineOptions({ name: 'TherapeuticAreaView' })

  interface Family { family_id: number; family_name: string; n_terms: number
    macro_auc: number | null; n_trustworthy: number; n_leaves: number }
  interface Programme {
    leaves: string[]; common: string[]; n_common: number
    specific: Record<string, string[]>
    excludes_non_leaves: boolean
  }
  interface GapRow { depth_gap: number; pairs: number; mean: number }
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
  family_id: number; n_terms: number; macro_auc: number | null; terms: Term[]
  overlap: { a: string; b: string; shared: number }[]
  programme: Programme
  gap_profile: GapRow[]
  mean_overlap: number | null
  n_near_duplicates: number }

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
  // The grid caps at GRID_MAX genes. `gene_grid` arrives sorted by n_terms
  // descending, so the cap keeps the most widely shared genes -- exactly what this
  // card is about -- but the count is rendered so the truncation is never silent.
  const GRID_MAX = 120
  const gridGenes = computed(() => (detail.value?.gene_grid ?? []).slice(0, GRID_MAX))
  const gridTotal = computed(() => detail.value?.gene_grid?.length ?? 0)

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
      <ActCard span="col-span-12" :icon="Network" title="The family panel" :chips="[['live', 'live']]"
               method-label="Why families, and why we split by them"
               :src="['family_panel']">
        <template #desc>
          Every term in the family scored by the same model — with the uncertainty each term
          actually has.
        </template>
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-80 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Disease family</span>
            <EaSelect v-model="selectedStr" placeholder="— Select a family —"
                      :options="families.map((f) => ({ value: String(f.family_id),
                                 label: `${f.family_name} — ${f.n_terms} terms` }))" />
          </label>
          <div v-if="detail" class="flex gap-8">
            <ActStat label="Terms" :value="detail.n_terms"
                     info="Disease terms in this family, from the curated ontology. Indented terms in the table sit under the one above them." />
            <ActStat t="auc-macro" label="Macro AUC" :value="(detail.macro_auc ?? 0).toFixed(4)" />
          </div>
        </div>
        <div v-if="detail" class="mt-4 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Term<ActInfo text="One disease term from the curated ontology. Indented terms sit under the one above them." /></TableHead>
                <TableHead>Known targets<ActInfo text="How many genes already carry a curated association with this term. It is the sample size behind every other number in the row." /></TableHead>
                <TableHead>AUC<ActInfo text="The chance a known target for this term outranks a randomly picked non-target for it. 0.5 is a coin flip. Struck through where the term has too few known targets to quote it." /></TableHead>
                <TableHead>95% interval<ActInfo text="The range the true AUC is likely to sit in, given how much data there was. A wide interval does not mean the estimate is wrong — it means it is unpinned." /></TableHead>
                <TableHead>Enrichment<ActInfo text="How many of the top 50 are already-known targets, as a share of 50, divided by the share of known targets in this term's whole candidate pool. 20x means the head of the list is twenty times as dense in real targets as the pool it came from." /></TableHead>
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
        <template #note>
          <b>Train and test are split by family, not at random.</b> Random splitting puts “diabetes”
          and “type 2 diabetes” on opposite sides — the same programme wearing two labels — and
          inflates the score.
        </template>
        <template #method>
          <p><b class="text-foreground">Families come from a curated medical
            <ActTerm t="ontology" />, not from an algorithm.</b> Clustering the diseases ourselves
            would have produced tidier groups and a higher number; using somebody else's published
            hierarchy lowered the score we report, and it is the concrete place a customer's own
            judgment already enters the pipeline.</p>
          <p class="mt-1.5">Splitting by family is the guard against
            <ActTerm t="leakage" />: any two terms that are really the same programme land on the same
            side of the split, so the model cannot score well by having memorised one of them. Act 2's
            <i>By family</i> tab is this same grouping.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12" title="AUC with confidence intervals"
               :chips="[['live', 'live']]" method-label="Why an interval can exceed 1.0"
               :src="['family_panel']">
        <template #desc>
          <template v-if="detail">
            {{ untrustworthy }} of {{ detail.n_terms }} terms have too few known targets to pin a
            score down — shown, never quoted.
          </template>
          <template v-else>Every term's AUC, with the range it could actually be in.</template>
        </template>

        <ActIntervals v-if="detail"
                      :rows="orderedTerms.map((t) => ({ label: t.disease_name, value: t.auc,
                             lo: t.lo95, hi: t.hi95, n: t.n_pos, muted: !t.trustworthy }))" />
        <EaEmpty v-else :icon="Network" title="No family selected"
                 description="Pick a disease family to see every term in it." />

        <template #note>
          <b>A struck-through score is shown, never quoted.</b> Greying it out would hide how much of
          a family we cannot measure; deleting it would be worse. The card beside this one changes the
          measure for exactly these terms.
        </template>
        <template #method>
          <p><b class="text-foreground">Some intervals run above 1.0 — higher than an AUC can
            reach.</b> With only a handful of known targets the estimate is not wrong, it is
            <i>unpinned</i>. That single fact retires the metric for thin diseases better than any
            threshold argument.</p>
          <p class="mt-1.5"><b class="text-foreground">What “trustworthy” means here</b> is a
            threshold, not a judgement: at least 30 known targets <i>and</i> an upper confidence bound
            at or below 1.0. Measured 95% interval widths fall from 0.24 below 30 positives to 0.15 at
            30–49 and 0.05 at 100+, so 30 is where the break actually is.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12" :icon="Ruler" accent="var(--chart-4)"
               title="When AUC stops working" :chips="[['live', 'live']]"
               method-label="How enrichment is computed"
               :src="['family_panel']">
        <template #desc>
          For terms with only a handful of known targets, quote
          <ActTerm t="enrichment">enrichment</ActTerm> or
          <ActTerm t="hits-at-k">hits in the top 20</ActTerm> — a count you can check by eye.
        </template>

        <ActBar v-if="thin.length" :rows="thin" :row-height="22" />
        <p v-else class="py-4 text-center text-[13px] text-muted-foreground">
          Every term in this family has enough associated targets to score.
        </p>
        <div v-if="thin.length" class="mt-2 flex gap-4 font-mono text-[10.5px] text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-3)"></span>
            AUC is trustworthy for this term
          </span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--destructive)"></span>
            AUC is not — read the enrichment instead
          </span>
        </div>

        <template #note>
          <b>The bars are enrichment; the colour is about AUC.</b> A red bar can still be a good
          enrichment — it means only that the term's AUC is the number you should not quote.
        </template>
        <template #method>
          <p>Take a term's <ActTerm t="top-50">top 50</ActTerm> ranked genes and count how many are
            already-known targets, as a share of 50. Divide by the share of known targets in that
            term's whole candidate pool. 20× means the head of the list is twenty times as dense in
            real targets as the pool it was drawn from.</p>
          <p class="mt-1.5">Unlike AUC it stays readable with very few known targets, because it is a
            ratio of counts rather than an estimate with a standard error. This is the same definition
            Act 2 uses — one wording, cited twice.</p>
        </template>
      </ActCard>

      

      <ActCard span="col-span-12 lg:col-span-7" :icon="GitCompare" accent="var(--chart-3)"
               title="Subtype overlap" :chips="[['live', 'live']]"
               method-label="What the top 50 is"
               :src="['family_panel_overlap']">
        <template #desc>
          How many of each pair's <ActTerm t="top-50">top 50</ActTerm> genes are the
          same<template v-if="commonShare !== null"> — {{ commonShare }} on average</template>.
        </template>
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
        <p v-if="overlapPairs.length" class="mt-2 font-mono text-[10.5px] text-muted-foreground">
          each cell = shared genes out of 50 · higher is more similar
        </p>

        <template #note>
          <b>Subtypes of one disease largely converge on one programme.</b> That is the expected
          result, and the interesting cases are the pairs that do <i>not</i> — a clinician treats
          those as different diseases, and so should the list.
        </template>
        <template #method>
          <p><b class="text-foreground">Top 50.</b> Every gene the graph connects to a term is scored
            and ranked; the top 50 is the head of that list — the shortlist a team would actually look
            at. Nothing about 50 is special: it is a demo cut-off, and Act 4 lets you set your own.</p>
          <p class="mt-1.5"><b class="text-foreground">Novel only</b> drops the genes that already
            carry a curated association with the term, leaving what the model surfaced rather than
            reproduced. Novel means we have not recorded a link — not that no link is known to
            science.</p>
        </template>
      </ActCard>

      

      <ActCard span="col-span-12 lg:col-span-6" :icon="Users" accent="var(--chart-2)"
               title="Shared vs. subtype-specific"
               method-label="Why only the curated leaf terms">
        <template #desc>
          <template v-if="commonShare !== null">
            Pairs share {{ commonShare }} of their top 50 — the family runs on a common core, with a
            small distinct edge each.
          </template>
          <template v-else>The genes every subtype reaches, and the genes only one does.</template>
        </template>
        <template v-if="detail?.programme?.leaves?.length">
          <!-- The shared core first: it is the answer the title promises. -->
          <div class="flex flex-col gap-1.5">
            <p class="font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
              shared by all {{ detail.programme.leaves.length }} subtypes ·
              {{ detail.programme.n_common }} of 50
            </p>
            <div class="flex flex-wrap gap-1">
              <span v-for="g in detail.programme.common" :key="g"
                    class="rounded border border-border bg-muted/40 px-1.5 py-0.5
                           font-mono text-[11px] text-muted-foreground">{{ g }}</span>
            </div>
          </div>

          <div class="mt-4 flex flex-col gap-2.5">
            <p class="font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
              in exactly one subtype's top 50
            </p>
            <div v-for="lf in detail.programme.leaves" :key="lf" class="flex flex-col gap-1">
              <span class="text-[12.5px] font-medium">
                {{ lf }}
                <span class="font-mono text-[10.5px] text-muted-foreground">
                  {{ (detail.programme.specific[lf] ?? []).length }} own
                </span>
              </span>
              <div class="flex flex-wrap gap-1">
                <span v-for="g in (detail.programme.specific[lf] ?? []).slice(0, 14)" :key="g"
                      class="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5
                             font-mono text-[11px] text-primary-foreground">{{ g }}</span>
                <span v-if="(detail.programme.specific[lf] ?? []).length > 14"
                      class="px-1 font-mono text-[10.5px] text-muted-foreground">
                  +{{ (detail.programme.specific[lf] ?? []).length - 14 }} more
                </span>
              </div>
            </div>
          </div>

        </template>
        <p v-else class="py-4 text-center text-[13px] text-muted-foreground">
          No leaf subtypes configured for this family.
        </p>

        <template #note>
          <b>A gene in exactly one subtype's top 50 is the interesting column.</b> It is where the
          model is claiming this subtype needs something the others do not — the claim a clinician
          can falsify fastest.
        </template>
        <template #method>
          <p><b class="text-foreground">The curated <ActTerm t="leaf-term">leaf</ActTerm> set
            only.</b> The other terms appear in the two cards above, where a broad term's top 50 being
            largely a blend of the narrower ones is the point. They are held out here because that set
            contains umbrella terms, whose “specific” genes would be an artefact of aggregation.</p>
          <p class="mt-1.5">Leaf is a curation call, not a depth rule — a term left out here is not
            necessarily anyone's parent.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12" :icon="Grid3x3" accent="var(--chart-3)"
               title="Gene coverage across the family"
               :chips="[['live', 'live']]" method-label="How to read the grid"
               :src="['family_panel_top50']">
        <template #desc>
          A row of filled cells is a gene the whole family runs on; a single cell is one subtype's
          own.
        </template>
        <ActGeneGrid v-if="gridGenes.length" :genes="gridGenes" :columns="overlapLabels"
                     :shared-at="Math.min(3, overlapLabels.length)" />
        <p v-else class="py-4 text-center text-[13px] text-muted-foreground">
          No top-50 membership computed for this family.
        </p>
        <p v-if="gridTotal > gridGenes.length"
           class="mt-2 font-mono text-[10.5px] text-muted-foreground">
          showing the {{ gridGenes.length }} most widely shared of {{ gridTotal }} genes
        </p>

        <template #note>
          The card above says <b>which</b> genes are shared; this one says <b>where</b>.
        </template>
        <template #method>
          <p v-if="gridTotal">{{ gridTotal }} genes across {{ overlapLabels.length }} terms. A filled
            cell means the gene is in that term's <ActTerm t="top-50">top 50</ActTerm>; dot size and
            opacity encode the rank, so a large solid dot is near the head of that term's list.</p>
          <p class="mt-1.5">Columns run in ontology order — the broad terms sit left of the narrow
            ones — so a block of cells filling in from the left is a gene inherited from the parent
            term rather than one the subtype found on its own.</p>
        </template>
      </ActCard>

      </div>
  </div>
</template>
