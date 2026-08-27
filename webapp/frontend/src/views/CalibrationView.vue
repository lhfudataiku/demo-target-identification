<script setup lang="ts">
  /**
   * Act 2 — calibration. Rebuilt against DASHBOARD_MOCKUP_V3's card set.
   *
   * Corrections from the parity review:
   *  - "Where the candidates come from" is TWO plots: a disease-eligibility
   *    band above a three-route sankey. Not the train/test split.
   *  - "How well the ranking holds" is a histogram with a by-disease/by-family
   *    tab, not a horizontal bar of my own binning.
   *  - "Usefulness is not uniform" plots ENRICHMENT per persona, not AUC.
   *  - Driver bars are coloured in two GROUPS (provenance vs the rest), with a
   *    legend — not a colour cycle.
   *  - Hub-bias, orthogonality and the drug-benchmark card belong to the Acts
   *    5-6 talk track and are not in the app.
   *  - Disclaimer cards live in the narrative, not here.
   */
  import { computed, onMounted, ref } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import ActSay from '@/components/act/ActSay.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActHistogram from '@/components/act/ActHistogram.vue'
  import ActBand from '@/components/act/ActBand.vue'
  import ActSankey from '@/components/act/ActSankey.vue'
  import ActBeeswarm from '@/components/act/ActBeeswarm.vue'
  import ActTabs from '@/components/act/ActTabs.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Split, Gauge, Crosshair, ListTree, Target } from 'lucide-vue-next'

  defineOptions({ name: 'CalibrationView' })

  interface Payload {
    champion: { precision: number; recall: number; f1: number; auprc: number
                auc_pooled: number; lift: number; base_rate: number; source: string }
    eligibility: { total: number; eligible: number; excluded: number; pct_excluded: number; gate: string }
    routes: { label: string; count: number; source: string }[]
    route_admissions: number; duplicates_removed: number; pairs_per_disease: number
    union_rows: number; pos_rate: number; n_families: number
    glossary: { feature: string; kind: string; what: string }[]
    drivers: { label: string; count: number }[]
    drivers_kind: Record<string, string>
    auc_values: number[]; family_auc_values: number[]
    personas: { label: string; value: number; current: boolean }[]
    n_diseases: number; macro_auc: number; median_auc: number
    splits: { split: string; rows: number; positives: number; pos_rate_pct: number }[]
  }

  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)
  const aucScope = ref('disease')

  const HIST_BINS = 20
  // The values behind whichever tab is selected. Macro and median are derived
  // from THIS array, so they change with the tab -- they described the disease
  // scope regardless of the tab before, which made the switch look broken.
  const scopeValues = computed(() =>
    !data.value ? [] : aucScope.value === 'disease' ? data.value.auc_values : data.value.family_auc_values)

  const aucHist = computed(() => {
    const out = Array.from({ length: HIST_BINS }, (_, i) => ({
      lo: i / HIST_BINS, hi: (i + 1) / HIST_BINS, n: 0,
    }))
    for (const v of scopeValues.value)
      out[Math.min(HIST_BINS - 1, Math.max(0, Math.floor(v * HIST_BINS)))].n++
    return out
  })
  const scopeMacro = computed(() => {
    const v = scopeValues.value
    return v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0
  })
  const scopeMedian = computed(() => {
    const v = [...scopeValues.value].sort((a, b) => a - b)
    return v.length ? v[Math.floor(v.length / 2)] : 0
  })
  // v3 colours drivers in two groups, with a legend — provenance against the rest.
  // Two scalars at one operating point, not a curve: what the model achieves
  // against what chance gives. Bars, as v3 draws it — a line would imply a
  // threshold sweep this card is not making a claim about.
  const precisionRows = computed(() => {
    const c = data.value?.champion
    if (!c) return []
    return [
      { label: 'model precision', count: +(100 * c.precision).toFixed(1), colour: 'var(--chart-2)',
        note: `at the F1-optimised threshold · recall ${(100 * c.recall).toFixed(1)}%` },
      { label: 'base rate (chance)', count: +(100 * c.base_rate).toFixed(2), colour: 'var(--muted-foreground)',
        note: 'the validation split’s positive rate' },
    ]
  })
  const precisionLift = computed(() => {
    const c = data.value?.champion
    return c && c.base_rate ? (c.precision / c.base_rate).toFixed(0) : null
  })
  const auprcRows = computed(() => {
    const c = data.value?.champion
    if (!c) return []
    return [
      { label: 'average precision', count: +c.auprc.toFixed(3), colour: 'var(--chart-2)',
        note: 'area under the precision–recall curve' },
      { label: 'baseline', count: +c.base_rate.toFixed(3), colour: 'var(--muted-foreground)',
        note: 'what a random ranker scores' },
    ]
  })

  const driverRows = computed(() =>
    (data.value?.drivers ?? []).map((d) => ({
      label: d.label, count: d.count,
      colour: data.value!.drivers_kind[d.label] === 'provenance' ? 'var(--chart-2)' : 'var(--chart-3)',
    })))

  onMounted(async () => {
    try {
      const res = await fetch(apiUrl('/api/calibration'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load calibration: ${e instanceof Error ? e.message : String(e)}`
    }
  })
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 2 of 4 · Calibration
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">How faithfully does it reconstruct?</h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Where the candidates come from, how they were split, and how reliably the already-validated
        targets land near the top. The distribution leads and the summary follows.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <!-- Two plots in one card, as v3's poolFlow draws it. -->
      <ActCard span="col-span-12" :icon="Split" accent="var(--chart-3)"
               title="Where the candidates come from" :chips="[['live', 'live']]"
               desc="A disease has to clear a gate before any of its genes become candidates — then three graph routes admit the pairs."
               :src="['disease_eligibility', 'enriched_dwpc_GGD', 'enriched_dwpc_GPGD', 'enriched_dwpc_GCD']">
        <template v-if="data">
          <p class="mb-1.5 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            Disease nodes · gate {{ data.eligibility.gate }}
          </p>
          <ActBand :in-label="'eligible'" :in-value="data.eligibility.eligible"
                   :out-label="'excluded — too few curated associations'" :out-value="data.eligibility.excluded" />

          <!-- The bridge. The band ends in DISEASES and the flow begins in PAIRS;
               without the multiplication written down, the two halves read as
               unrelated plots that happen to share a card. -->
          <div class="mt-4 flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-md border border-dashed
                      border-border bg-muted/30 px-3 py-2 font-mono text-[11px]">
            <span class="text-primary-foreground">
              <b>{{ data.eligibility.eligible.toLocaleString() }}</b> eligible diseases
            </span>
            <span class="text-muted-foreground">×</span>
            <span class="text-primary-foreground">
              <b>~{{ data.pairs_per_disease.toLocaleString() }}</b> genes the graph links to each
            </span>
            <span class="text-muted-foreground">=</span>
            <span class="text-primary-foreground">
              <b>{{ data.union_rows.toLocaleString() }}</b> gene–disease pairs
            </span>
            <span class="ml-auto text-muted-foreground">
              the {{ data.eligibility.excluded.toLocaleString() }} excluded diseases contribute nothing
            </span>
          </div>

          <p class="mb-1.5 mt-3 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            How those pairs are admitted, de-duplicated and split
          </p>
          <!-- `duplicate admissions` is drawn, not just described: without it the
               pool node takes 8.8M in and emits 6.75M, and 23% of the width
               disappears at the node with nothing on screen to account for it.
               Colours are deliberate, not a cycle -- --chart-2 is what survives
               and --muted is what is dropped, in BOTH plots. -->
          <ActSankey
            :nodes="[...data.routes.map((r) => ({ name: r.label })),
                     { name: 'candidate pool', color: '--chart-2' },
                     { name: 'duplicate admissions', color: '--muted' },
                     ...data.splits.map((sp) => ({ name: sp.split }))]"
            :links="[
              ...data.routes.map((r) => ({ source: r.label, target: 'candidate pool', value: r.count })),
              { source: 'candidate pool', target: 'duplicate admissions', value: data.duplicates_removed },
              ...data.splits.map((sp) => ({ source: 'candidate pool', target: sp.split, value: sp.rows }))]"
            :height="320" />

          <div class="mt-2 flex gap-8">
            <ActStat label="Pool" :value="data.union_rows.toLocaleString()" sub="gene–disease pairs" />
            <ActStat label="Positive rate" :value="data.pos_rate + '%'" sub="what precision must beat" />
          </div>

          <ActSay class="mt-3">
            <b>Why the routes sum to more than the pool.</b> They are not disjoint — one pair can be
            admitted by two routes at once, so the three add to
            {{ data.route_admissions.toLocaleString() }} admissions but only
            <b>{{ data.union_rows.toLocaleString() }}</b> distinct pairs survive.
            The {{ data.duplicates_removed.toLocaleString() }} difference is not a loss: it is the same
            pair counted twice. The pool is exactly what the three splits partition, which is why the
            split widths below add back to it.
          </ActSay>
          <ActSay class="mt-2">
            <b>{{ data.eligibility.excluded.toLocaleString() }} of
            {{ data.eligibility.total.toLocaleString() }} diseases — {{ data.eligibility.pct_excluded }}% —
            never enter at all</b>, because they carry too few curated gene associations. The model has
            nothing to learn from and nothing to be tested on for those. This is the number to volunteer,
            not to be asked for.
          </ActSay>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" :icon="Target" accent="var(--chart-1)"
               title="Precision, against the base rate it has to beat" :chips="[['live', 'live']]"
               desc="Accuracy is meaningless at a 1.9% positive rate — a model predicting “no” for everything scores 98%. Precision against the base rate is the honest comparison."
               :src="['split_audit_2']">
        <template v-if="data">
          <p class="mb-1 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            Precision · %
          </p>
          <ActBar :rows="precisionRows" :row-height="26" />
          <p class="mb-1 mt-4 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            Average precision · area under PR
          </p>
          <ActBar :rows="auprcRows" :row-height="26" />
          <ActSay class="mt-3">
            Precision is <b>{{ (100 * data.champion.precision).toFixed(1) }}%</b> against a base rate of
            <b>{{ (100 * data.champion.base_rate).toFixed(2) }}%</b> — about
            <b>{{ precisionLift }}×</b> chance. The number to distrust is the
            <b>{{ (100 * 0.9776).toFixed(1) }}%</b> accuracy: at this class balance it says nothing.
          </ActSay>
          <p class="mt-2 font-mono text-[10px] text-muted-foreground">
            champion m7-f14 · metrics {{ data.champion.source }}
          </p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" :icon="Gauge" title="How well the ranking holds"
               :chips="[['live', 'live']]"
               desc="Every held-out unit, binned. Read it as reconstruction fidelity, not predictive power."
               :src="['validation_auc_by_disease', 'family_auc_by_family']">
        <div v-if="data" class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <ActTabs v-model="aucScope" :options="[
            { value: 'disease', label: `By disease · ${data.n_diseases}` },
            { value: 'family', label: `By family · ${data.n_families}` }]" />
          <div class="flex gap-6">
            <ActStat label="Macro AUC" :value="scopeMacro.toFixed(4)" sub="never pooled" />
            <ActStat label="Median" :value="scopeMedian.toFixed(4)" />
            <ActStat label="Units" :value="scopeValues.length" />
          </div>
        </div>
        <ActHistogram v-if="data" :bins="aucHist" x-label="AUC" />
        <ActSay class="mt-3">
          <b>Macro, never pooled.</b> Pooling reads 0.8932 and overstates by roughly seven points,
          because it lets large diseases carry small ones.
        </ActSay>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" :icon="Gauge" accent="var(--chart-4)"
               title="Usefulness is not uniform — every disease, not just a summary"
               :chips="[['live', 'live']]"
               desc="Rank enrichment per disease. The box is the interquartile range; the line is the median."
               :src="['persona_enrichment']">
        <ActBeeswarm v-if="data" :points="data.personas"
                     :min="0" :max="Math.ceil(Math.max(...data.personas.map((p) => p.value)) / 10) * 10"
                     unit="rank enrichment" />
        <ActSay class="mt-3">
          A single number hides this. Some diseases enrich twenty-fold and some barely at all —
          <b>which is which is more useful to you than the average.</b>
        </ActSay>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" :icon="Crosshair" accent="var(--chart-2)"
               title="What the model actually keys on" :chips="[['live', 'live']]"
               desc="How often each feature is a top SHAP driver across every scored candidate."
               :src="['shap_driver_frequency']">
        <ActBar v-if="data" :rows="driverRows" :row-height="17" />
        <div class="mt-2 flex gap-4 font-mono text-[10.5px] text-muted-foreground">
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-2)"></span>
            edge-provenance features
          </span>
          <span class="flex items-center gap-1.5">
            <span class="inline-block size-2.5 rounded-sm" style="background:var(--chart-3)"></span>
            path, proximity and topology
          </span>
        </div>
      </ActCard>

      <ActCard span="col-span-12" :icon="ListTree" accent="var(--chart-5)"
               title="What the 14 features actually are" :chips="[['live', 'live']]"
               desc="Network topology, not biology. Provenance features are highlighted — they are what the model leans on most.">
        <Table v-if="data">
          <TableHeader>
            <TableRow><TableHead>Feature</TableHead><TableHead>Kind</TableHead><TableHead>What it measures</TableHead></TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="f in data.glossary" :key="f.feature">
              <TableCell class="font-mono text-[11.5px] font-medium whitespace-nowrap">{{ f.feature }}</TableCell>
              <TableCell>
                <span class="rounded px-1.5 py-0.5 font-mono text-[10px] uppercase"
                      :class="f.kind === 'provenance' ? 'bg-primary/25 text-primary-foreground' : 'bg-secondary text-muted-foreground'">
                  {{ f.kind }}
                </span>
              </TableCell>
              <TableCell class="text-[12px] text-muted-foreground">{{ f.what }}</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </ActCard>

      

      

      
    </div>
  </div>
</template>
