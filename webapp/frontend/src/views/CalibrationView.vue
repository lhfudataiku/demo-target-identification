<script setup lang="ts">
  /**
   * Act 2 — calibration. Rebuilt against DASHBOARD_MOCKUP_V3's card set.
   * Governed claims consumed: TI-MOD-001 TI-VAL-001 TI-VAL-002 TI-VAL-003.
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
   *
   * COPY REVIEW 2026-09-03. This act carried eleven distinct statistical
   * quantities and defined none of them. Three changes, all structural:
   *
   *  - THE ELIGIBILITY CARD IS NOW TWO CARDS. It held four ideas at one visual
   *    weight -- the gate, the pair multiplication, route de-duplication, and
   *    the split -- so a reader could not tell which was the point.
   *  - THREE AUCs (per-disease, macro, pooled) appear in this act and were
   *    never distinguished. They now have one shared definition each in
   *    utils/glossary.ts and a #method block that puts them side by side.
   *  - TWO HARDCODED LITERALS ARE GONE. `1.9%` in a subtitle and `0.9776` in a
   *    note were typed into the template while their neighbours read live from
   *    `data.champion`, so a retrain made the card contradict itself on screen
   *    -- in the act whose whole argument is that the numbers are honest. The
   *    accuracy figure is now derived as the all-negative baseline (1 - base
   *    rate), which is the claim the sentence was actually making.
   */
  import { computed, onMounted, ref } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActHistogram from '@/components/act/ActHistogram.vue'
  import ActBand from '@/components/act/ActBand.vue'
  import ActSankey from '@/components/act/ActSankey.vue'
  import ActBeeswarm from '@/components/act/ActBeeswarm.vue'
  import ActTabs from '@/components/act/ActTabs.vue'
  import ActTerm from '@/components/act/ActTerm.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Split, Gauge, Crosshair, ListTree, Target, Filter } from 'lucide-vue-next'

  defineOptions({ name: 'CalibrationView' })

  interface Payload {
    champion: { precision: number; recall: number; f1: number; auprc: number
                auc_pooled: number; lift: number; base_rate: number; source: string }
    eligibility: { total: number; eligible: number; excluded: number; pct_excluded: number; gate: string }
    routes: { label: string; count: number; source: string }[]
    route_admissions: number; duplicates_removed: number; pairs_per_disease: number
    union_rows: number; pos_rate: number; n_families: number
    glossary: { feature: string; kind: string; label: string; what: string }[]
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
  /** The stat tile said "Units", which means nothing to a reader and changes
      meaning with the tab. It now says what the tab selected. */
  const scopeNoun = computed(() => (aucScope.value === 'disease' ? 'Diseases' : 'Families'))

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
  /** Pooled minus macro, in points. The note claimed "roughly seven points"
      from a literal; it is derivable, so it is derived. */
  const pooledExcess = computed(() => {
    const c = data.value?.champion
    if (!c || !scopeValues.value.length) return null
    return ((c.auc_pooled - scopeMacro.value) * 100).toFixed(1)
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
  /** What a model that answers "no" to everything scores. Derived from the base
      rate, which is exactly the argument the note is making. */
  const trivialAccuracy = computed(() => {
    const c = data.value?.champion
    return c ? (100 * (1 - c.base_rate)).toFixed(1) : null
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
  /** Provenance's share of top-driver appearances, AND how many features earn
      it. Both numbers, because the share alone invites the wrong claim: at 38%
      provenance is not the largest KIND (path is, collectively), so the finding
      is the disproportion -- 2 features of 14 taking 38% of the slots -- not
      dominance. Stating the count keeps the subtitle from overclaiming. */
  const provenance = computed(() => {
    const rows = data.value?.drivers ?? []
    const total = rows.reduce((a, d) => a + d.count, 0)
    if (!total) return null
    const prov = rows.filter((d) => data.value!.drivers_kind[d.label] === 'provenance')
    return {
      pct: Math.round((100 * prov.reduce((a, d) => a + d.count, 0)) / total),
      n: prov.length,
      total: rows.length,
    }
  })
  /** The single most frequent top driver, named the way a reader can check.
      `drivers[].label` is the raw column (`ppi_evidence_depth`); the payload's
      glossary carries the standalone wording for exactly this position, from
      backend/feature_glossary.py. Falls back to the column name rather than
      rendering nothing. */
  const topDriver = computed(() => {
    const rows = [...(data.value?.drivers ?? [])].sort((a, b) => b.count - a.count)
    const top = rows[0]
    if (!top) return null
    const g = data.value?.glossary.find((f) => f.feature === top.label)
    return { ...top, name: g?.label ?? top.label }
  })

  /* The Sankey's route labels arrived as feature codes -- "GGD · gene-gene",
     "GPGD · via pathway", "GCD · via drug". Those are column names, and this is
     the first plot a client sees in act 2. Renamed for display only; the
     mapping is one-way and the payload is untouched. */
  const ROUTE_NAMES: [RegExp, string][] = [
    [/GPGD/i, 'via a shared pathway'],
    [/GCD/i, 'via a shared drug'],
    [/GGD/i, 'via an interacting gene'],
  ]
  const routeLabel = (raw: string) =>
    ROUTE_NAMES.find(([re]) => re.test(raw))?.[1] ?? raw
  const routes = computed(() =>
    (data.value?.routes ?? []).map((r) => ({ ...r, name: routeLabel(r.label) })))

  /** Median and the middle half. NOT min-max: the minimum is 0.0x -- a disease
      with no known target in its top 50 -- and "the spread runs 0.0x to 59.2x"
      reads as a broken card rather than as the point. The quartiles are also
      what the documented claim quotes. */
  const personaSpread = computed(() => {
    const v = [...(data.value?.personas ?? [])].map((p) => p.value).sort((a, b) => a - b)
    if (!v.length) return null
    const at = (q: number) => v[Math.min(v.length - 1, Math.floor(q * v.length))]
    // Even counts average the two middle values, so this agrees with the
    // documented median rather than sitting 0.1 above it.
    const mid = v.length % 2 ? v[(v.length - 1) / 2]
                             : (v[v.length / 2 - 1] + v[v.length / 2]) / 2
    return {
      median: mid.toFixed(1),
      q1: at(0.25).toFixed(0),
      q3: at(0.75).toFixed(0),
      max: v[v.length - 1].toFixed(0),
    }
  })

  const KINDS: [string, string][] = [
    ['path', 'feature-path'],
    ['proximity', 'feature-proximity'],
    ['topology', 'feature-topology'],
    ['provenance', 'feature-provenance'],
  ]

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
        targets land near the top. The distribution leads and the summary follows. Every metric on
        this page carries its definition — hover any underlined term.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <!-- ── The gate. Its own card: it is a claim about who is EXCLUDED, and
           it was previously the top third of a card about something else. ── -->
      <ActCard span="col-span-12 lg:col-span-5" :icon="Filter" accent="var(--chart-4)"
               title="Which diseases qualify" :chips="[['live', 'live']]"
               :src="['disease_eligibility']">
        <template #desc>
          <template v-if="data">
            {{ data.eligibility.excluded.toLocaleString() }} of
            {{ data.eligibility.total.toLocaleString() }} diseases never enter — they carry too few
            curated <ActTerm t="association">associations</ActTerm> to learn from or be tested on.
          </template>
          <template v-else>The test a disease must pass before any of its genes are scored.</template>
        </template>

        <template v-if="data">
          <p class="mb-1.5 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            Disease nodes · <ActTerm t="eligibility-gate">gate</ActTerm> {{ data.eligibility.gate }}
          </p>
          <ActBand :in-label="'eligible'" :in-value="data.eligibility.eligible"
                   :out-label="'excluded — too few curated associations'" :out-value="data.eligibility.excluded" />
        </template>

        <template #note>
          <b>The model has nothing to say about those<template v-if="data">
          {{ data.eligibility.pct_excluded }}% of all disease nodes</template>.</b>
          Not “it scores them badly”: it never sees them. If a client's disease of interest is in
          that group, the honest answer is that this pipeline does not cover it yet.
        </template>
        <template #presenter>
          This is the number to volunteer, not to be asked for.
        </template>
      </ActCard>

      <!-- ── The pool. -->
      <ActCard span="col-span-12 lg:col-span-7" :icon="Split" accent="var(--chart-3)"
               title="How the candidate pool is built" :chips="[['live', 'live']]"
               :src="['enriched_dwpc_GGD', 'enriched_dwpc_GPGD', 'enriched_dwpc_GCD']">
        <template #desc>
          Three graph routes admit
          <ActTerm t="gene-disease-pair">gene–disease pairs</ActTerm>; overlaps are de-duplicated into
          one <ActTerm t="candidate-pool">pool</ActTerm><template v-if="data"> of
          {{ data.union_rows.toLocaleString() }}</template>, then split for training and testing.
        </template>

        <template v-if="data">
          <ActSankey
            :nodes="[...routes.map((r) => ({ name: r.name })),
                     { name: 'candidate pool', color: '--chart-2' },
                     { name: 'duplicate admissions', color: '--muted' },
                     ...data.splits.map((sp) => ({ name: sp.split }))]"
            :links="[
              ...routes.map((r) => ({ source: r.name, target: 'candidate pool', value: r.count })),
              { source: 'candidate pool', target: 'duplicate admissions', value: data.duplicates_removed },
              ...data.splits.map((sp) => ({ source: 'candidate pool', target: sp.split, value: sp.rows }))]"
            :height="320" />

          <div class="mt-2 flex gap-8">
            <ActStat label="Pool" :value="data.union_rows.toLocaleString()" sub="gene–disease pairs" />
            <ActStat :label="'Positive rate'" :value="data.pos_rate + '%'"
                     sub="already-known targets — what precision must beat" />
          </div>
        </template>

        <template #note>
          <b>A pair is a gene considered for one disease, not a gene.</b> The same gene can sit at the
          head of one disease's list and nowhere on another's, which is why nothing in this act is a
          statement about a gene on its own.
        </template>
        <template #method>
          <p v-if="data"><b class="text-foreground">Why the routes sum to more than the pool.</b> They
            are not disjoint — one pair can be admitted by two routes at once, so the three add to
            {{ data.route_admissions.toLocaleString() }} admissions but only
            {{ data.union_rows.toLocaleString() }} distinct pairs survive. The
            {{ data.duplicates_removed.toLocaleString() }} difference is not a loss: it is the same
            pair counted twice. The pool is exactly what the three splits partition, which is why the
            split widths add back to it.</p>
          <p v-if="data" class="mt-1.5"><b class="text-foreground">Where the pool size comes from.</b>
            {{ data.eligibility.eligible.toLocaleString() }} eligible diseases ×
            ~{{ data.pairs_per_disease.toLocaleString() }} genes the graph links to each ≈
            {{ data.union_rows.toLocaleString() }} pairs. The excluded diseases contribute nothing.</p>
          <p class="mt-1.5"><b class="text-foreground">The three routes</b> are internally
            <code class="font-mono text-[10.5px]">GGD</code> (gene–gene–disease),
            <code class="font-mono text-[10.5px]">GPGD</code> (via pathway) and
            <code class="font-mono text-[10.5px]">GCD</code> (via drug/compound). The drug route
            admits pairs into the pool but no model feature traverses a drug node.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" :icon="Target" accent="var(--chart-1)"
               title="Precision vs. chance" :chips="[['live', 'live']]"
               :src="['split_audit_2']">
        <template #desc>
          <template v-if="data">
            The model is right {{ (100 * data.champion.precision).toFixed(1) }}% of the time where
            <ActTerm t="base-rate">chance alone</ActTerm> would be
            {{ (100 * data.champion.base_rate).toFixed(2) }}% — about {{ precisionLift }}× better.
          </template>
          <template v-else>What the model achieves, against the base rate it has to beat.</template>
        </template>

        <template v-if="data">
          <p class="mb-1 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            <ActTerm t="precision">Precision</ActTerm> · %
          </p>
          <ActBar :rows="precisionRows" :row-height="26" />
          <p class="mb-1 mt-4 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">
            <ActTerm t="auprc">Average precision</ActTerm> · area under PR
          </p>
          <ActBar :rows="auprcRows" :row-height="26" />
          <p class="mt-3 font-mono text-[10px] text-muted-foreground">
            <ActTerm t="champion-model">champion m7-f14</ActTerm> · metrics {{ data.champion.source }}
          </p>
        </template>

        <template #note>
          <b>Accuracy is the number to distrust here.</b> At this
          <ActTerm t="class-imbalance">class balance</ActTerm> a model that answers “no” to everything
          is <template v-if="trivialAccuracy">{{ trivialAccuracy }}%</template><template v-else>about
          98%</template> accurate and finds nothing at all.
        </template>
        <template #method>
          <p><b class="text-foreground">Precision</b> — of the candidates the model calls positive, the
            share that really are known targets. Measured at the threshold that maximises F1, with
            <b class="text-foreground">recall</b><template v-if="data">
            {{ (100 * data.champion.recall).toFixed(1) }}%</template> — the share of all known targets
            it found.</p>
          <p class="mt-1.5"><b class="text-foreground">Average precision</b> is the area under the
            precision–recall curve: precision averaged over every possible cut-off, so it does not
            depend on choosing one. A random ranker scores the base rate, which is what the second bar
            draws.</p>
          <p class="mt-1.5"><b class="text-foreground">Base rate</b> is the share of the validation
            split that is already a known target. Every number on this card is stated against it,
            because a metric that is not is not comparable to anything.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" :icon="Gauge" title="AUC, disease by disease"
               :chips="[['live', 'live']]" method-label="Three AUCs, and why they differ"
               :src="['validation_auc_by_disease', 'family_auc_by_family']">
        <template #desc>
          Each held-out disease gets its own <ActTerm t="auc-per-disease">AUC</ActTerm> — the result is
          a distribution, not a single number<template v-if="data">; median
          {{ scopeMedian.toFixed(3) }}</template>.
        </template>

        <div v-if="data" class="mb-3 flex flex-wrap items-center justify-between gap-3">
          <ActTabs v-model="aucScope" :options="[
            { value: 'disease', label: `By disease · ${data.n_diseases}` },
            { value: 'family', label: `By family · ${data.n_families}` }]" />
          <div class="flex gap-6">
            <ActStat label="Macro AUC" :value="scopeMacro.toFixed(4)" sub="never pooled" />
            <ActStat label="Median" :value="scopeMedian.toFixed(4)" />
            <ActStat :label="scopeNoun" :value="scopeValues.length" />
          </div>
        </div>
        <ActHistogram v-if="data" :bins="aucHist" x-label="AUC" />

        <template #note>
          <b>Reconstruction, not prediction.</b> This measures how faithfully the model rebuilds known
          biology that was hidden from it. It is not evidence that it predicts biology nobody has
          found yet — that claim would need prospective validation.
        </template>
        <template #method>
          <p><b class="text-foreground">Per-disease AUC</b> — for one disease, the chance that a known
            target scores higher than a randomly picked non-target for that same disease. 0.5 is a coin
            flip. One number per disease; this histogram bins them.</p>
          <p class="mt-1.5"><b class="text-foreground">Macro AUC</b> — the plain average of those
            per-disease numbers. Every disease counts once, whether it has eight known targets or six
            hundred. <b class="text-foreground">This is the number we report.</b></p>
          <p class="mt-1.5"><b class="text-foreground">Pooled AUC</b> — one AUC over every pair at
            once, ignoring which disease each belongs to. It reads
            <template v-if="data">{{ data.champion.auc_pooled.toFixed(4) }}</template>
            here<template v-if="pooledExcess">, about {{ pooledExcess }} points higher</template>,
            because a few large diseases carry all the small ones. We compute it and never quote it.</p>
          <p class="mt-1.5"><b class="text-foreground">Held out</b> means the model never saw these
            rows while training. The <i>By family</i> tab groups them the way the split does — see
            Act 3 for why the split is by family rather than at random.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" :icon="Gauge" accent="var(--chart-4)"
               title="Enrichment, disease by disease" :chips="[['live', 'live']]"
               :src="['persona_enrichment']">
        <template #desc>
          <template v-if="personaSpread">
            The head of the list is a median {{ personaSpread.median }}× denser in real targets than
            chance — but the middle half alone runs {{ personaSpread.q1 }}× to
            {{ personaSpread.q3 }}×, and some diseases barely enrich at all.
          </template>
          <template v-else>How much better than chance the top of each disease's list is.</template>
        </template>

        <ActBeeswarm v-if="data" :points="data.personas"
                     :min="0" :max="Math.ceil(Math.max(...data.personas.map((p) => p.value)) / 10) * 10"
                     unit="rank enrichment" />
        <p class="mt-2 font-mono text-[10.5px] text-muted-foreground">
          box = <ActTerm t="iqr">interquartile range</ActTerm> · line =
          <ActTerm t="median" /> · one dot per disease
        </p>

        <template #note>
          <b>A single number hides this.</b> Some diseases enrich twenty-fold and some barely at all —
          which is which is more useful to you than the average.
        </template>
        <template #method>
          <p><b class="text-foreground">How enrichment is computed.</b> Take a disease's
            <ActTerm t="top-50">top 50</ActTerm> ranked genes and count how many are already-known
            targets, as a share of 50. Divide by the share of known targets in that disease's whole
            candidate pool.</p>
          <p class="mt-1.5">20× means the top of the list is twenty times as dense in real targets as
            the pool it was drawn from. Unlike AUC it stays readable for a disease with only a handful
            of known targets, which is why Act 3 switches to it for the thin terms.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" :icon="Crosshair" accent="var(--chart-2)"
               title="What drives the score" :chips="[['live', 'live']]"
               :src="['shap_driver_frequency']">
        <template #desc>
          <template v-if="provenance">Just {{ provenance.n }} of the {{ provenance.total }} features
            are <ActTerm t="feature-provenance">provenance</ActTerm> — how many independent sources
            back an interaction — and they take {{ provenance.pct }}% of all top-driver slots.
          </template>
          <template v-else>How often each feature is among the two that moved a candidate most.</template>
        </template>

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

        <template #note>
          <b>The strongest single driver is how well-evidenced an interaction is<template
            v-if="topDriver"> — {{ topDriver.name }}</template></b>, not anything about what the
          protein does. Read that as a finding about this feature set rather than about biology: it is
          the honest answer when someone asks what the model has learned.
        </template>
        <template #method>
          <p><b class="text-foreground">What SHAP is.</b> SHAP splits one prediction into a
            contribution per input: how much each feature pushed this specific gene's score up or
            down. It explains one decision, not the model in general.</p>
          <p class="mt-1.5">This chart counts how often each feature lands in a candidate's top two
            contributors, across every scored candidate — so it is a frequency, not an average
            effect size. A feature that moves a few predictions enormously and the rest not at all
            will read low here.</p>
          <p class="mt-1.5"><b class="text-foreground">Provenance is not the largest kind, and the
            card does not say it is.</b> Collectively the four path features take a larger share than
            the two provenance ones. The claim is the disproportion: two features earning a share that
            fourteen split evenly would give to roughly two.</p>
        </template>
      </ActCard>

      <ActCard span="col-span-12" :icon="ListTree" accent="var(--chart-5)"
               title="The model's inputs" :chips="[['live', 'live']]">
        <template #desc>
          Fourteen <ActTerm t="feature">features</ActTerm>, all of them graph structure — no sequence,
          no expression, no biology of the protein itself.
        </template>

        <div class="mb-3 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[10.5px] text-muted-foreground">
          <span v-for="[label, key] in KINDS" :key="key">
            <ActTerm :t="key" plain>{{ label }}</ActTerm>
          </span>
        </div>

        <Table v-if="data">
          <TableHeader>
            <TableRow>
              <TableHead>Feature</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>What it measures</TableHead>
            </TableRow>
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

        <template #note>
          <b>The model cannot see what a protein does.</b> Everything it reads is a property of how the
          gene sits in the network — which is why a strong score is a hypothesis worth testing, not a
          mechanism.
        </template>
        <template #method>
          <p>The <code class="font-mono text-[10.5px]">dwpc_*</code> features are
            <ActTerm t="dwpc">degree-weighted path counts</ActTerm>: routes reaching the disease are
            counted, with routes through very well-connected nodes counted for less, so a popular hub
            gene cannot score highly on connectivity alone.</p>
          <p class="mt-1.5"><b class="text-foreground">This card has no src footer, deliberately.</b>
            It is not a dataset number: it is the champion's declared input list, whose authority is
            <code class="font-mono text-[10.5px]">.index/features.tsv</code>. The wording comes from
            <code class="font-mono text-[10.5px]">backend/feature_glossary.py</code>, the one copy —
            Act 4's candidate drawer renders the same strings, so the two acts cannot describe the
            same model differently.</p>
        </template>
      </ActCard>
    </div>
  </div>
</template>
