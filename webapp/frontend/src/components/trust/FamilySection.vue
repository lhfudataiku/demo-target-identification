<script setup lang="ts">
  /**
   * Section 3 — does it hold across the disease family (Act 3, formerly six cards).
   *
   * Up front: every term with its 95% interval and the thin-label warning, and
   * the subtype separation check. Under "Show the detail": shared vs.
   * subtype-specific, subtype overlap and gene coverage, in the form of the live
   * Act 3 plots (DEC-DEMO-005; scope D12). A disease with no panel says so.
   */
  import { computed, ref } from 'vue'
  import { Button, Collapsible, CollapsibleContent, CollapsibleTrigger } from '@dataiku/ea-ui-kit'
  import { ChevronDown, ChevronRight, Flow } from '@dataiku/vue-icons'
  import { EmptyState } from 'bs-blueprint'
  import ActGeneGrid from '@/components/act/ActGeneGrid.vue'
  import ActMatrix from '@/components/act/ActMatrix.vue'
  import ActTabs from '@/components/act/ActTabs.vue'
  import ActTerm from '@/components/act/ActTerm.vue'
  import FamilyIntervals from './FamilyIntervals.vue'
  import type { FamilyPanel, FamilySummary, TrustDisease } from './types'

  const props = defineProps<{
    disease: TrustDisease
    /** Null when the disease has no panel. */
    panel: FamilyPanel | null
    /** Every family that has a panel, to name them when this disease has none. */
    families: FamilySummary[]
  }>()
  const open = ref(false)

  const panelNames = computed(() => {
    const names = props.families.map((f) => f.family)
    return names.length > 1 ? `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}` : names.join('')
  })
  const scored = computed(() => props.panel?.terms.filter((t) => t.scored) ?? [])
  const thin = computed(() => props.panel?.terms.filter((t) => t.auc !== null && !t.trustworthy) ?? [])
  const leaves = computed(() => props.panel?.programme.leaves ?? [])
  const isLeaf = computed(() => leaves.value.includes(props.disease.disease_name))

  /** The selected term against each subtype leaf: how many of its NOVEL top-50 genes they share. */
  const separation = computed(() => {
    const p = props.panel
    if (!p) return []
    const me = props.disease.disease_name
    return leaves.value.filter((l) => l !== me).map((l) => {
      const o = p.overlap.find((x) => (x.a === me && x.b === l) || (x.b === me && x.a === l))
      return { other: l, novel: o?.shared_novel ?? null }
    }).sort((a, b) => (a.novel ?? Infinity) - (b.novel ?? Infinity))
  })
  const leafPairs = computed(() =>
    props.panel?.overlap.filter((o) => leaves.value.includes(o.a) && leaves.value.includes(o.b)) ?? [])

  const ovMode = ref('all')
  const overlapPairs = computed(() =>
    (ovMode.value === 'novel' ? props.panel?.overlap_novel : props.panel?.overlap_all) ?? [])
  // The grid caps at GRID_MAX genes, as the live Act 3 card did. `gene_grid`
  // arrives sorted by n_terms, so the cap keeps the most widely shared.
  const GRID_MAX = 120
  const SPECIFIC_MAX = 14
  const gridGenes = computed(() => (props.panel?.gene_grid ?? []).slice(0, GRID_MAX))
  const commonShare = computed(() => {
    const o = props.panel?.overlap ?? []
    return o.length ? Math.round(o.reduce((a, p) => a + p.shared, 0) / o.length) : null
  })
  const short = (s: string) => s.replace(' breast carcinoma', '').replace(' adenocarcinoma', ' adeno.')
</script>

<template>
  <EmptyState v-if="!panel" :icon="Flow" :title="`No family panel for ${disease.disease_name}`"
              :description="`Panels exist for the ${panelNames} families, where subtypes can be compared. This disease is checked by its own AUC in section 2.`" />

  <div v-else class="flex flex-col gap-5">
    <p class="text-sm leading-relaxed">
      Same model, every term in the <b>{{ panel.family }}</b> family: {{ scored.length }} of
      {{ panel.terms.length }} terms are scored<template v-if="panel.macro_auc !== null">, with a
      <ActTerm t="auc-macro">macro AUC</ActTerm> of <b class="font-mono">{{ panel.macro_auc.toFixed(4) }}</b>
      over the <ActTerm t="trustworthy">trustworthy</ActTerm> ones</template>.
      <template v-if="thin.length">
        {{ thin.length === 1 ? 'One term has' : `${thin.length} terms have` }} too few known targets for its AUC
        to be quoted, marked below.
      </template>
    </p>

    <div class="grid gap-5 md:grid-cols-5">
      <div class="md:col-span-3">
        <FamilyIntervals :terms="panel.terms" :selected="disease.disease_index" />
      </div>
      <section class="flex flex-col gap-2 md:col-span-2">
        <p class="text-sm font-semibold">Do the <ActTerm t="subtype">subtypes</ActTerm> separate?</p>
        <p class="text-xs text-muted-foreground">
          <ActTerm t="novel">Novel</ActTerm> genes in the <ActTerm t="top-50">top 50</ActTerm> that
          {{ isLeaf ? disease.disease_name : 'each subtype' }} shares with
          {{ isLeaf ? 'each other subtype' : 'the others' }}. Few shared means the lists differ.
        </p>
        <div v-if="isLeaf" class="flex flex-col gap-1.5">
          <div v-for="s in separation" :key="s.other" class="flex items-center justify-between gap-3 rounded-md bg-muted/30 px-3 py-2">
            <span class="text-xs">{{ s.other }}</span>
            <span class="font-mono text-sm tabular-nums"><b>{{ s.novel ?? '—' }}</b><span class="text-2xs text-muted-foreground"> of 50</span></span>
          </div>
        </div>
        <div v-else class="flex flex-col gap-1.5">
          <div v-for="o in leafPairs" :key="o.a + o.b" class="flex items-center justify-between gap-3 rounded-md bg-muted/30 px-3 py-2">
            <span class="text-xs">{{ short(o.a) }} · {{ short(o.b) }}</span>
            <span class="font-mono text-sm tabular-nums"><b>{{ o.shared_novel }}</b><span class="text-2xs text-muted-foreground"> of 50</span></span>
          </div>
        </div>
        <p class="text-xs text-muted-foreground">
          This shows the lists are coherent and distinct. It is not validation of any one list.
        </p>
      </section>
    </div>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2">
          <component :is="open ? ChevronDown : ChevronRight" class="size-4" /> Show the detail
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent class="flex flex-col gap-6 pt-2">
        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">Shared vs. subtype-specific</p>
          <p v-if="commonShare !== null" class="text-xs text-muted-foreground">
            Pairs share {{ commonShare }} of their top 50 on average: the family runs on a common
            <ActTerm t="programme">programme</ActTerm>, with a small distinct edge each.
          </p>
          <div class="flex flex-col gap-1.5">
            <p class="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
              shared by all {{ leaves.length }} subtypes · {{ panel.programme.n_common }} of 50
            </p>
            <div class="flex flex-wrap gap-1">
              <span v-for="g in panel.programme.common" :key="g"
                    class="rounded border border-border bg-muted/40 px-1.5 py-0.5
                           font-mono text-2xs text-muted-foreground">{{ g }}</span>
            </div>
          </div>
          <div class="mt-2 flex flex-col gap-2.5">
            <p class="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
              in exactly one subtype's top 50
            </p>
            <div v-for="lf in leaves" :key="lf" class="flex flex-col gap-1">
              <span class="text-xs font-medium">
                {{ lf }}
                <span class="font-mono text-2xs text-muted-foreground">
                  {{ (panel.programme.specific[lf] ?? []).length }} own
                </span>
              </span>
              <div class="flex flex-wrap gap-1">
                <span v-for="g in (panel.programme.specific[lf] ?? []).slice(0, SPECIFIC_MAX)" :key="g"
                      class="rounded border border-primary/40 bg-primary/10 px-1.5 py-0.5
                             font-mono text-2xs text-primary">{{ g }}</span>
                <span v-if="(panel.programme.specific[lf] ?? []).length > SPECIFIC_MAX"
                      class="px-1 font-mono text-2xs text-muted-foreground">
                  +{{ (panel.programme.specific[lf] ?? []).length - SPECIFIC_MAX }} more
                </span>
              </div>
            </div>
          </div>
        </section>

        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">Subtype overlap</p>
          <p class="text-xs text-muted-foreground">How many of each pair's top 50 genes are the same.</p>
          <ActTabs v-model="ovMode" class="mb-1"
                   :options="[{ value: 'all', label: 'All top-50 genes' }, { value: 'novel', label: 'Novel only' }]" />
          <ActMatrix v-if="overlapPairs.length" :labels="panel.grid_columns" :pairs="overlapPairs" />
          <p class="font-mono text-2xs text-muted-foreground">each cell = shared genes out of 50 · higher is more similar</p>
        </section>

        <section class="flex flex-col gap-2">
          <p class="text-sm font-semibold">Gene coverage across the family</p>
          <p class="text-xs text-muted-foreground">
            A row of filled cells is a gene the whole family runs on; a single cell is one subtype's own.
          </p>
          <ActGeneGrid v-if="gridGenes.length" :genes="gridGenes" :columns="panel.grid_columns"
                       :shared-at="Math.min(3, panel.grid_columns.length)" />
          <p v-if="panel.gene_grid.length > gridGenes.length" class="font-mono text-2xs text-muted-foreground">
            showing the {{ gridGenes.length }} most widely shared of {{ panel.gene_grid.length }} genes
          </p>
        </section>
      </CollapsibleContent>
    </Collapsible>
  </div>
</template>
