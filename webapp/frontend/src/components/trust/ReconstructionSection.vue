<script setup lang="ts">
  /**
   * Section 2 — how faithfully it reconstructs known biology (Act 2, formerly
   * seven cards).
   *
   * Governed claims consumed: TI-DATA-001 TI-MOD-001 TI-VAL-001 TI-VAL-002 TI-VAL-003 TI-VAL-004 TI-VAL-005.
   *
   * Up front: the leakage audit in one line, the AUC distribution with the
   * selected disease marked, its rank and enrichment, the macro AUC as the
   * summary, and that reconstruction is not therapeutic value. Under "Show the
   * detail": the split table, which diseases qualify, how the candidate pool is
   * built, precision against chance, family-level AUC and the hub bias.
   * "What drives the score" and "The model's inputs" moved to the shortlist.
   */
  import { computed, ref } from 'vue'
  import {
    Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Table, TableBody, TableCell, TableHead,
    TableHeader, TableRow,
  } from '@dataiku/ea-ui-kit'
  import { CheckmarkCircleOutline, ChevronDown, ChevronRight, InfoCircleOutline } from '@dataiku/vue-icons'
  import ActTerm from '@/components/act/ActTerm.vue'
  import AucHistogram from './AucHistogram.vue'
  import BarList from './BarList.vue'
  import type { CalibrationPayload, TrustDisease } from './types'

  const props = defineProps<{ cal: CalibrationPayload; disease: TrustDisease }>()
  const open = ref(false)
  const fmt = (n: number) => n.toLocaleString()

  const leakFree = computed(() => Object.values(props.cal.leakage).every((v) => v === 0))
  const auc = computed(() => props.disease.auc)
  /** Share of scored diseases this one ranks above. */
  const beats = computed(() => auc.value === null ? null
    : Math.round((100 * (props.cal.n_diseases - auc.value.auc_rank)) / props.cal.n_diseases))
  const e = computed(() => props.cal.enrichment)
</script>

<template>
  <div class="flex flex-col gap-5">
    <p class="flex items-center gap-2 text-xs text-muted-foreground">
      <CheckmarkCircleOutline v-if="leakFree" class="size-4 text-success" />
      <span v-if="leakFree"><b class="text-foreground">No disease is shared between training, validation and test.</b>
        Every number below is measured on <ActTerm t="held-out">held-out</ActTerm> diseases the model never saw.</span>
      <span v-else><b class="text-foreground">The leakage audit is not clean:</b> see the split table in the detail.</span>
    </p>

    <div class="grid gap-5 md:grid-cols-5">
      <div class="flex flex-col gap-3 md:col-span-2">
        <template v-if="auc">
          <p class="text-sm leading-relaxed">
            <b>{{ disease.disease_name }}</b> recovers its known targets at
            <b class="font-mono"><ActTerm t="auc-per-disease">AUC</ActTerm> {{ auc.auc.toFixed(4) }}</b>: rank
            {{ auc.auc_rank }} of {{ cal.n_diseases }} diseases, higher than {{ beats }}% of them.
          </p>
          <p v-if="auc.enrichment !== null" class="text-sm leading-relaxed text-muted-foreground">
            Its <ActTerm t="top-50">top 50</ActTerm> genes are <b class="text-foreground">{{ auc.enrichment }}×</b>
            as dense in known targets as its whole candidate pool
            (<ActTerm t="enrichment">enrichment</ActTerm>).
          </p>
        </template>
        <p v-else class="text-sm text-muted-foreground">
          {{ disease.disease_name }} is not in the validation set, so it has no AUC of its own.
        </p>
        <p class="text-xs leading-relaxed text-muted-foreground">
          Across all {{ cal.n_diseases }} diseases the median AUC is {{ cal.median_auc?.toFixed(4) }}; the
          <ActTerm t="auc-macro">macro average</ActTerm>, {{ cal.macro_auc.toFixed(4) }}, summarises the spread.
          Enrichment has a median of {{ e.median }}× (middle half {{ e.q1 }}–{{ e.q3 }}×, highest {{ e.max }}×).
        </p>
      </div>
      <div class="md:col-span-3">
        <AucHistogram :bins="cal.histogram" :marker="auc?.auc ?? null" :marker-label="disease.disease_name" />
      </div>
    </div>

    <p class="flex gap-2 rounded-lg border bg-muted/30 p-3 text-xs leading-relaxed text-muted-foreground">
      <InfoCircleOutline class="mt-0.5 size-4 shrink-0" />
      <span>
        <b class="text-foreground"><ActTerm t="reconstruction-not-prediction">This measures reconstruction, not
        therapeutic value.</ActTerm></b> Across {{ cal.orthogonality.n }} diseases, a disease's association AUC and
        its drug-target AUC are unrelated
        (r = {{ cal.orthogonality.pearson_r >= 0 ? '+' : '' }}{{ cal.orthogonality.pearson_r.toFixed(3) }}).
        The model also scores well-connected genes higher; see the detail.
      </span>
    </p>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2">
          <component :is="open ? ChevronDown : ChevronRight" class="size-4" /> Show the detail
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent class="flex flex-col gap-6 pt-2">
        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">The split, and the <ActTerm t="leakage">leakage</ActTerm> audit</p>
          <div class="overflow-hidden rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow class="bg-muted/30">
                  <TableHead>Split</TableHead><TableHead class="text-right">Pairs</TableHead>
                  <TableHead class="text-right">Known pairs</TableHead><TableHead class="text-right">Diseases</TableHead>
                  <TableHead class="text-right">Disease families</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow v-for="s in cal.splits" :key="s.split">
                  <TableCell class="capitalize">{{ s.split }}</TableCell>
                  <TableCell class="text-right font-mono text-xs">{{ fmt(s.rows) }}</TableCell>
                  <TableCell class="text-right font-mono text-xs">{{ fmt(s.positives) }} · {{ s.pos_rate_pct }}%</TableCell>
                  <TableCell class="text-right font-mono text-xs">{{ fmt(s.n_diseases) }}</TableCell>
                  <TableCell class="text-right font-mono text-xs">{{ fmt(s.n_anchor_families) }}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
          <p class="text-xs text-muted-foreground">
            Shared or straddling disease groups between splits:
            <span class="font-mono">{{ Object.values(cal.leakage).join(' · ') }}</span>.
          </p>
        </section>

        <div class="grid gap-6 md:grid-cols-2">
          <section class="flex flex-col gap-2">
            <p class="text-sm font-semibold">Which diseases qualify</p>
            <p class="text-xs text-muted-foreground">
              {{ fmt(cal.eligibility.eligible) }} of {{ fmt(cal.eligibility.total) }} diseases pass the
              <ActTerm t="eligibility-gate">eligibility gate</ActTerm>
              (<span class="font-mono">{{ cal.eligibility.gate }}</span>); the rest cannot be scored meaningfully.
            </p>
            <p class="mt-2 text-sm font-semibold">How the <ActTerm t="candidate-pool">candidate pool</ActTerm> is built</p>
            <p class="text-xs text-muted-foreground">
              A pair enters the pool if any of {{ cal.routes.length }} graph routes connects the gene to the disease.
              {{ fmt(cal.route_admissions) }} admissions, {{ fmt(cal.duplicates_removed) }} duplicates
              removed, {{ fmt(cal.union_rows) }} pairs at a {{ cal.pos_rate }}% positive rate.
            </p>
            <BarList :items="cal.routes" unit="pairs admitted" />
          </section>
          <section class="flex flex-col gap-2">
            <p class="text-sm font-semibold">Precision against chance</p>
            <p class="text-xs text-muted-foreground">
              At the model's threshold, {{ (100 * cal.champion.precision).toFixed(1) }}% of predicted pairs are
              known targets, against a <ActTerm t="base-rate">base rate</ActTerm> of
              {{ (100 * cal.champion.base_rate).toFixed(2) }}%.
            </p>
            <p class="mt-2 text-sm font-semibold">Disease families</p>
            <p v-if="cal.family_macro_auc !== null" class="text-xs text-muted-foreground">
              Macro AUC over {{ fmt(cal.n_families) }} families that have known targets:
              <span class="font-mono">{{ cal.family_macro_auc.toFixed(4) }}</span>.
            </p>
            <p class="mt-2 text-sm font-semibold">Well-connected genes score higher</p>
            <div class="overflow-hidden rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow class="bg-muted/30">
                    <TableHead>Degree quintile</TableHead><TableHead class="text-right">Median partners</TableHead>
                    <TableHead class="text-right">Mean score, known targets</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  <TableRow v-for="h in cal.hub_bias" :key="h.quintile">
                    <TableCell>{{ h.quintile }}</TableCell>
                    <TableCell class="text-right font-mono text-xs">{{ h.median_degree }}</TableCell>
                    <TableCell class="text-right font-mono text-xs">{{ h.mean_proba.toFixed(4) }}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </div>
          </section>
        </div>
        <p class="text-xs text-muted-foreground">
          What drives each gene's score and what the {{ cal.n_features }} inputs measure are in the shortlist's
          detail and the glossary, so they are not repeated here.
        </p>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
