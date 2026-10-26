<script setup lang="ts">
  /**
   * The ranked list.
   *
   * Two kinds of control, kept visibly apart: POPULATION controls change which
   * candidates are in the list at all (they refetch, and the funnel moves); VIEW
   * controls only narrow what is drawn. Guardrails enforced here, not merely
   * documented:
   *  - drug badges and the liability flag RENDER but are never filter controls
   *    (the badges are the ground truth the enrichment is measured against;
   *    filtering the liability flag deletes ERBB2 from its own disease's list);
   *  - every count renders its rank cut-off, so a count cannot acquire two values;
   *  - "no link in snapshot" is never written as "no drug".
   */
  import { computed, ref, watch } from 'vue'
  import { storeToRefs } from 'pinia'
  import {
    Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Checkbox, Collapsible,
    CollapsibleContent, CollapsibleTrigger, Input, NativeSelect, NativeSelectOption, Pagination,
    PaginationContent, PaginationEllipsis, PaginationItem, PaginationNext, PaginationPrevious, Separator,
    Skeleton, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  } from '@dataiku/ea-ui-kit'
  import { ChevronDown, ChevronRight, ListNumbered, Search } from '@dataiku/vue-icons'
  import { EmptyState, SelectField, StatusBadge } from 'bs-blueprint'
  import ActInfo from '@/components/act/ActInfo.vue'
  import ActTerm from '@/components/act/ActTerm.vue'
  import { useSelectionStore } from '@/stores/selection'
  import { tractLabel, type Payload, type Row } from './types'

  const props = defineProps<{ data: Payload | null; loading: boolean; selectedGene: number | null }>()
  const emit = defineEmits<{ (e: 'select', row: Row): void }>()

  // Population: these refetch, because they change what is in the list.
  const novelOnly = defineModel<boolean>('novelOnly', { required: true })
  const tractableOnly = defineModel<boolean>('tractableOnly', { required: true })
  const excludeSecreted = defineModel<boolean>('excludeSecreted', { required: true })
  const maxRank = defineModel<number>('maxRank', { required: true })
  // The kit's Input emits strings. Keep the last valid rank while the box is
  // empty or mid-edit, rather than querying with max_rank=''.
  function setMaxRank(v: string | number) {
    const n = Number(v)
    if (v !== '' && Number.isFinite(n) && n >= 1) maxRank.value = n
  }

  // The disease is shared with "Why trust the list" (stores/selection.ts).
  const selection = useSelectionStore()
  const { diseases, diseaseIndex } = storeToRefs(selection)
  const diseaseStr = computed<string | undefined>({
    get: () => (diseaseIndex.value === undefined ? undefined : String(diseaseIndex.value)),
    set: (v) => { diseaseIndex.value = v === undefined ? undefined : Number(v) },
  })
  const diseaseName = computed(() => diseases.value.find((d) => d.disease_index === diseaseIndex.value)?.disease_name)

  // View: filters the rows already loaded, without a refetch. The funnel still
  // describes the population, so nothing here can hide how big the list is.
  const search = ref('')
  const tract = ref('')          // '' | sm | ab | either
  const klass = ref('')
  const strike = ref(false)      // strike out, never remove

  const rows = computed(() => props.data?.rows ?? [])
  const classes = computed(() => [...new Set(rows.value.map((r) => r.ot_class_l1).filter(Boolean))].sort() as string[])
  const shown = computed(() => rows.value.filter((r) => {
    if (search.value && !r.gene_name.toLowerCase().includes(search.value.toLowerCase())) return false
    if (tract.value === 'sm' && !r.ot_sm_tractable) return false
    if (tract.value === 'ab' && !r.ot_ab_tractable) return false
    if (tract.value === 'either' && !(r.ot_sm_tractable || r.ot_ab_tractable)) return false
    if (klass.value && r.ot_class_l1 !== klass.value) return false
    return true
  }))

  // 15 rows is what a person can scan; the funnel still reports the true totals.
  const PAGE = 15
  const page = ref(1)
  const paged = computed(() => shown.value.slice((page.value - 1) * PAGE, page.value * PAGE))
  // Any change to the filters or the disease puts you back on page 1: staying on
  // page 7 of a list that now has two pages reads as an empty table.
  watch([search, tract, klass, diseaseIndex, novelOnly, tractableOnly, excludeSecreted, maxRank],
        () => { page.value = 1 })

  const methodOpen = ref(false)
  const rowClass = (r: Row) => [
    props.selectedGene === r.gene_index ? 'bg-accent' : 'hover:bg-accent/50',
    strike.value && r.has_safety_liability ? 'line-through opacity-50' : '',
  ]
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>Ranked candidates</CardTitle>
      <CardDescription>
        <template v-if="data && diseaseName">
          {{ rows.length.toLocaleString() }} candidates at rank ≤ {{ maxRank }} for {{ diseaseName }},
          strongest evidence first. Nothing is pre-filtered; select a row to review its evidence below.
        </template>
        <template v-else>
          Every gene the graph connects to the disease, ordered by the champion model's score within this
          disease. Nothing is pre-filtered.
        </template>
      </CardDescription>
    </CardHeader>
    <CardContent class="flex flex-col gap-4">
      <!-- Population -->
      <div class="flex flex-col gap-2">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Population<ActInfo text="These controls change which candidates are in the list at all, so the funnel below them changes too." />
          <span class="font-normal normal-case tracking-normal">· changes which genes are listed</span>
        </p>
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-72 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Disease<ActInfo :text="`One of the ${diseases.length} diseases scored into a ranked candidate list. Shared with Why trust the list.`" />
            </span>
            <SelectField v-model="diseaseStr" placeholder="— Select a disease —"
                         :options="diseases.map((d) => ({ value: String(d.disease_index),
                                    label: `${d.disease_name} (${d.n_candidates.toLocaleString()})` }))" />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <Checkbox v-model="novelOnly" /> Novel only
            <ActInfo text="Drops genes already annotated as targets for this disease, so what remains is what the model surfaced rather than reproduced." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <Checkbox v-model="tractableOnly" /> Tractable
            <ActInfo text="Open Targets judges the protein reachable by a small molecule or an antibody." />
          </label>
          <label class="flex items-center gap-2 text-sm">
            <Checkbox v-model="excludeSecreted" /> Not secreted
            <ActInfo text="Excludes proteins released between cells. Harder to drug than ones sitting on a membrane." />
          </label>
          <label class="flex flex-col gap-1 text-sm">
            <span class="text-muted-foreground">
              Rank ≤<ActInfo text="How far down the ranked list to go. Every count below carries this cut-off, so a number can never mean two things." />
            </span>
            <Input :model-value="maxRank" type="number" min="1" max="5000" class="w-24"
                   @update:model-value="setMaxRank" />
          </label>
        </div>
        <div v-if="data" class="flex flex-wrap items-center gap-1.5 font-mono text-xs">
          <template v-for="(f, i) in data.funnel" :key="f.step">
            <span class="rounded-md px-2 py-1"
                  :class="i === data.funnel.length - 1 ? 'bg-primary/10 font-medium text-primary' : 'bg-muted text-muted-foreground'">
              {{ f.step }} · {{ f.n.toLocaleString() }}
            </span>
            <span v-if="i < data.funnel.length - 1" class="text-muted-foreground">→</span>
          </template>
        </div>
      </div>

      <Separator />

      <!-- View -->
      <div class="flex flex-col gap-2">
        <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          View<ActInfo text="These controls only narrow what is drawn on screen. The funnel above still reports the true population, so nothing here can hide how big the list really is." />
          <span class="font-normal normal-case tracking-normal">· filters what is on screen</span>
        </p>
        <div class="flex flex-wrap items-center gap-2">
          <div class="relative">
            <Search class="pointer-events-none absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
            <Input v-model="search" placeholder="Gene symbol" class="w-44 pl-8" />
          </div>
          <span class="flex items-center">
            <NativeSelect v-model="tract">
              <NativeSelectOption value="">Any tractability</NativeSelectOption>
              <NativeSelectOption value="sm">Small molecule</NativeSelectOption>
              <NativeSelectOption value="ab">Antibody</NativeSelectOption>
              <NativeSelectOption value="either">Either</NativeSelectOption>
            </NativeSelect>
            <ActInfo text="Small molecule: a drug-like pocket. Antibody: reachable from outside the cell. Either: at least one." />
          </span>
          <span class="flex items-center">
            <NativeSelect v-model="klass">
              <NativeSelectOption value="">Any target class</NativeSelectOption>
              <NativeSelectOption v-for="c in classes" :key="c" :value="c">{{ c }}</NativeSelectOption>
            </NativeSelect>
            <ActInfo text="Open Targets' protein family — enzyme, membrane receptor, transcription factor and so on." />
          </span>
          <label class="flex items-center gap-2 text-sm">
            <Checkbox v-model="strike" /> Strike out liabilities
            <ActInfo text="A public annotation recording that an adverse effect has been observed and published for this protein — from clinical or experimental evidence, aggregated by Open Targets. Its limits matter: the flag is not dose-, modality- or indication-specific, it says nothing about whether an effect is manageable, and it can only exist for targets that have already been drugged or studied. So an unflagged gene is not safe — it is unstudied. Treat it as evidence of attention, not of danger." />
          </label>
          <span class="ml-auto font-mono text-2xs text-muted-foreground">
            {{ shown.length.toLocaleString() }} of {{ rows.length.toLocaleString() }} shown · rank ≤ {{ maxRank }}
          </span>
        </div>
      </div>

      <Skeleton v-if="loading && !data" class="h-64 w-full" />
      <div v-else-if="shown.length" class="overflow-hidden rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow class="bg-muted/30">
              <TableHead class="w-16">Rank<ActInfo text="Position in this disease's list. The score behind it is uncalibrated, so the ordering is what carries meaning — not the number." /></TableHead>
              <TableHead>Gene<ActInfo text="HGNC symbol of the candidate protein." /></TableHead>
              <TableHead>Class<ActInfo text="Open Targets protein family." /></TableHead>
              <TableHead>Tractability</TableHead>
              <TableHead>Association<ActInfo text="Recorded association = an Open Targets genetic or somatic association already exists for this disease–gene pair, at score ≥ 0.3 — this is the label the model was trained on. Novel = no such association." /></TableHead>
              <TableHead>Drug evidence<ActInfo text="Approved and in trials are drug evidence for this exact disease node, shown as ground truth and never filterable. No link in snapshot is not the same as no drug." /></TableHead>
              <TableHead>Safety<ActInfo text="A recorded safety flag. An unflagged gene is unstudied, not safe." /></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <!-- The row IS the control: selecting it opens its evidence below. -->
            <TableRow v-for="r in paged" :key="r.gene_index" :class="rowClass(r)" class="cursor-pointer"
                      tabindex="0" role="button" :aria-pressed="selectedGene === r.gene_index"
                      :aria-label="`Review ${r.gene_name}`"
                      @click="emit('select', r)" @keydown.enter.prevent="emit('select', r)"
                      @keydown.space.prevent="emit('select', r)">
              <TableCell class="font-mono tabular-nums text-muted-foreground">{{ r.rank_in_disease }}</TableCell>
              <TableCell class="font-mono font-medium text-primary">{{ r.gene_name }}</TableCell>
              <TableCell class="text-muted-foreground">{{ r.ot_class_l1 || 'Not assessed' }}</TableCell>
              <TableCell class="text-muted-foreground">{{ tractLabel(r) }}</TableCell>
              <TableCell>
                <StatusBadge :status="r.is_target ? 'muted' : 'info'">
                  {{ r.is_target ? 'Recorded association' : 'Novel' }}
                </StatusBadge>
              </TableCell>
              <TableCell>
                <div class="flex flex-wrap gap-1">
                  <StatusBadge v-if="r.approved_for_disease" status="success">Approved</StatusBadge>
                  <StatusBadge v-if="r.investigational_for_disease" status="warning">In trials</StatusBadge>
                  <span v-if="!r.approved_for_disease && !r.investigational_for_disease"
                        class="text-xs text-muted-foreground">No link in snapshot</span>
                </div>
              </TableCell>
              <TableCell>
                <StatusBadge v-if="r.has_safety_liability" status="destructive">Liability</StatusBadge>
                <span v-else class="text-xs text-muted-foreground">None recorded</span>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>
      <EmptyState v-else-if="data" :icon="ListNumbered" title="Nothing matches"
                  description="Loosen a filter, or pick another disease." />

      <div v-if="shown.length > PAGE" class="flex flex-wrap items-center justify-between gap-3">
        <span class="font-mono text-2xs text-muted-foreground">
          {{ (page - 1) * PAGE + 1 }}–{{ Math.min(page * PAGE, shown.length) }} of
          {{ shown.length.toLocaleString() }} · rank ≤ {{ maxRank }}
        </span>
        <Pagination v-slot="{ page: current }" v-model:page="page" :items-per-page="PAGE" :total="shown.length"
                    :sibling-count="1" class="mx-0 w-auto">
          <PaginationContent v-slot="{ items }">
            <PaginationPrevious />
            <template v-for="(item, i) in items" :key="i">
              <PaginationItem v-if="item.type === 'page'" :value="item.value" :is-active="item.value === current">
                {{ item.value }}
              </PaginationItem>
              <PaginationEllipsis v-else :index="i" />
            </template>
            <PaginationNext />
          </PaginationContent>
        </Pagination>
      </div>

      <p class="text-xs leading-relaxed text-muted-foreground">
        <b class="text-foreground">Approved, in trials and liability are shown but cannot be filtered on.</b>
        The drug badges are the ground truth the discovery result is measured against, and filtering on the
        liability flag would remove ERBB2 from its own disease's list. “No link in snapshot” is not “no drug”:
        links are recorded on the exact disease node.
      </p>

      <Collapsible v-model:open="methodOpen">
        <CollapsibleTrigger as-child>
          <Button variant="ghost" size="sm" class="-ml-2">
            <component :is="methodOpen ? ChevronDown : ChevronRight" class="size-4" /> How genes are ranked
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent class="flex flex-col gap-1.5 pt-1 text-xs leading-relaxed text-muted-foreground">
          <p>Every gene the graph connects to this disease enters the
            <ActTerm t="candidate-pool">candidate pool</ActTerm>. The
            <ActTerm t="champion-model">champion model</ActTerm> scores each
            <ActTerm t="gene-disease-pair">gene–disease pair</ActTerm> from graph-structure features (listed in
            the glossary), and the genes are sorted by that score <b class="text-foreground">within this
            disease</b>.</p>
          <p>The score is <ActTerm t="uncalibrated">uncalibrated</ActTerm> — it orders candidates correctly but
            is not a probability, so 0.8 does not mean an 80% chance of being a real target.
            <b class="text-foreground">The order carries the meaning, not the number</b>, and a rank of 9 here is
            not comparable to a rank of 9 for another disease, because the pools differ in both size and
            density.</p>
          <p><b class="text-foreground">Nothing is pre-filtered.</b> Every count above renders the rank cut-off
            it was measured at, so a number can never acquire two values.</p>
        </CollapsibleContent>
      </Collapsible>
    </CardContent>
  </Card>
</template>
