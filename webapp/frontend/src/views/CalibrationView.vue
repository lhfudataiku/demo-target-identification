<script setup lang="ts">
  /**
   * Act 2 — calibration.
   *
   * "How faithfully does it reconstruct?" Read the AUC as reconstruction
   * fidelity, not predictive power.
   *
   * Three cards that must appear together, because each is dishonest alone:
   * the distribution (usefulness is not uniform), the hub-bias meter (we
   * under-score under-studied true targets), and orthogonality (a high
   * association AUC does not buy therapeutic relevance).
   *
   * Guardrail: macro AUC only. Pooled reads 0.8932 and overstates by ~7 points;
   * it must never appear beside the macro figure.
   */
  import { computed, onMounted, ref } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'
  import ActStat from '@/components/act/ActStat.vue'
  import ActSay from '@/components/act/ActSay.vue'
  import ActBar from '@/components/act/ActBar.vue'
  import ActScatter from '@/components/act/ActScatter.vue'
  import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
  import { Gauge, Network, Scale } from 'lucide-vue-next'

  defineOptions({ name: 'CalibrationView' })

  interface Payload {
    n_diseases: number; macro_auc: number; median_auc: number; below_chance: number
    histogram: { lo: number; hi: number; n: number }[]
    hub_bias: { quintile: number; median_degree: number; mean_proba: number; pct_predicted_positive: number; n_genes: number }[]
    rho_degree_proba: number; threshold: number
    orthogonality: { n: number; pearson_r: number; r2: number; points: { assoc: number; drug: number }[]; drug_macro_auc: number }
  }

  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)

  const histRows = computed(() =>
    (data.value?.histogram ?? [])
      .filter((b) => b.n > 0)
      .map((b) => ({ label: `${b.lo.toFixed(2)}–${b.hi.toFixed(2)}`, count: b.n })))

  const swing = computed(() => {
    const h = data.value?.hub_bias
    if (!h?.length) return null
    const lo = h[0].pct_predicted_positive, hi = h[h.length - 1].pct_predicted_positive
    return lo ? (hi / lo).toFixed(1) : null
  })

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
        Across every held-out disease, how reliably do the already-validated targets land near the
        top. Read this as reconstruction fidelity, not predictive power — and read the distribution
        before the summary, because usefulness is not uniform.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <ActCard span="col-span-12 lg:col-span-7" :icon="Gauge" title="The distribution, not the summary"
               :chips="[['live', 'live']]"
               desc="One number answers a question nobody asked. Which diseases reconstruct well is more useful than the average."
               :src="['validation_auc_by_disease']">
        <div v-if="data" class="mb-3 flex gap-8">
          <ActStat label="Diseases" :value="data.n_diseases" />
          <ActStat label="Macro AUC" :value="data.macro_auc.toFixed(4)" sub="never pooled" />
          <ActStat label="Median" :value="data.median_auc.toFixed(4)" />
          <ActStat label="Below chance" :value="data.below_chance" sub="AUC < 0.5" />
        </div>
        <ActBar v-if="data" :rows="histRows" color="var(--chart-2)" :row-height="16" />
        <ActSay class="mt-3">
          <b>Macro, never pooled.</b> Pooling reads <b>0.8932</b> and overstates by roughly seven
          points, because it lets large diseases carry small ones. The macro figure is the one that
          goes in front of anybody.
        </ActSay>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" :icon="Network" accent="var(--chart-4)"
               title="Where it still under-scores" :chips="[['live', 'live']]"
               desc="Biology held constant — known targets only — split into fifths by network connectivity."
               :src="['hub_bias_meter']">
        <Table v-if="data">
          <TableHeader>
            <TableRow>
              <TableHead>Connectivity</TableHead>
              <TableHead>Median degree</TableHead>
              <TableHead>Mean score</TableHead>
              <TableHead>Predicted +</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow v-for="q in data.hub_bias" :key="q.quintile">
              <TableCell class="font-mono">Q{{ q.quintile }}</TableCell>
              <TableCell class="font-mono tabular-nums text-muted-foreground">{{ q.median_degree }}</TableCell>
              <TableCell class="font-mono tabular-nums">{{ q.mean_proba.toFixed(2) }}</TableCell>
              <TableCell class="font-mono tabular-nums">{{ q.pct_predicted_positive.toFixed(1) }}%</TableCell>
            </TableRow>
          </TableBody>
        </Table>
        <ActSay v-if="data && swing" class="mt-3">
          A <b>{{ swing }}×</b> detection swing on network position alone, with biology held
          constant. Both things are true: the ranking is not explained by popularity, and
          <b>the model still under-scores under-studied true targets.</b> We have not fixed that.
        </ActSay>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" :icon="Scale" accent="var(--chart-3)"
               title="A high AUC does not buy therapeutic relevance" :chips="[['live', 'live']]"
               desc="Each point is one disease: how well it reconstructs association labels, against how well it ranks real drug targets."
               :src="['orthogonality_scatter']">
        <ActScatter v-if="data" :points="data.orthogonality.points"
                    x-label="association AUC" y-label="drug-target AUC" />
        <div v-if="data" class="mt-3 flex gap-8">
          <ActStat label="Pearson r" :value="data.orthogonality.pearson_r.toFixed(4)" />
          <ActStat label="R²" :value="data.orthogonality.r2.toFixed(4)" />
          <ActStat label="Diseases" :value="data.orthogonality.n" />
        </div>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" title="Why the drug benchmark is never a score">
        <p class="text-[13px] leading-relaxed text-muted-foreground">
          The two axes are uncorrelated. A disease the model ranks well on association tells you
          nothing about whether it ranks drug targets well.
        </p>
        <ActSay class="mt-3">
          On that benchmark a popularity lookup — <i>“how many diseases is this gene already a
          target for”</i> — beats the trained model. <b>A benchmark a lookup table wins is measuring
          the lookup.</b> We report it as a warning flag and never optimise against it.
        </ActSay>
      </ActCard>
    </div>
  </div>
</template>
