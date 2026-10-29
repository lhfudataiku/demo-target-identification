<script setup lang="ts">
  /**
   * "Drugs & graph" — the drugs behind the badges, where they come from, and
   * the five Visual Graph Explorer queries for the pair. The per-drug records
   * (`/api/candidates/drugs`, scope D7) are this tab's own request: if it fails,
   * the tab says so and the badges and Explorer still work.
   *
   * The Explorer queries are generated locally from the live pair. Nothing runs
   * when a row is selected: the user picks one query, copies it, and runs it in
   * the Explorer. A later query replaces the current Explorer result; the app
   * never joins or accumulates graph responses.
   */
  import { computed, ref, watch } from 'vue'
  import {
    Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Skeleton,
    Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
  } from '@dataiku/ea-ui-kit'
  import { ChevronDown, ChevronRight, DataLineage } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import ActTerm from '@/components/act/ActTerm.vue'
  import VisualGraphExplorerCard from '@/components/graph/VisualGraphExplorerCard.vue'
  import { buildA4ExplorerQueries } from '@/utils/a4ExplorerQueries'
  import { apiUrl } from '@/utils/api'
  import { stageLabel, type DrugRecord, type Row } from './types'

  const props = defineProps<{ row: Row; diseaseIndex: number; diseaseName: string }>()
  const open = ref(false)

  const hasDrug = computed(() => Boolean(props.row.approved_for_disease || props.row.investigational_for_disease))

  const records = ref<DrugRecord[] | null>(null)
  const recordsError = ref<string | null>(null)

  async function loadRecords(disease: number, gene: number) {
    records.value = null; recordsError.value = null
    const current = () => props.diseaseIndex === disease && props.row.gene_index === gene
    try {
      const res = await fetch(apiUrl(`/api/candidates/drugs?disease=${disease}&gene=${gene}`))
      const body = await res.json().catch(() => null)
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`)
      // A slower earlier request must not overwrite a later selection.
      if (current()) records.value = body.records
    } catch (e) {
      if (current()) recordsError.value = e instanceof Error ? e.message : String(e)
    }
  }
  watch(() => [props.diseaseIndex, props.row.gene_index] as const,
    ([d, g]) => loadRecords(d, g), { immediate: true })

  const releases = computed(() => [...new Set((records.value ?? []).map((r) => r.source_release))])

  const LINEAGE = [
    ['Open Targets Platform 26.06', 'ChEMBL drug layer: mechanisms of action and clinical indications'],
    ['extract_drug_ot', 'DEMO_KG_LS · keeps the highest clinical stage per drug and disease'],
    ['harmonize_drug_disease', 'approval or pre-approval → indication; every other stage, including an unrecorded one, → investigated for'],
    ['drug_disease_edges · drug_protein_edges', 'the stage and the drug’s action on the protein survive here'],
    ['compute_drug_evidence_pairs', 'DEMO_TARGET_IDENTIFICATION · keeps two yes/no flags per gene–disease pair'],
    ['approved / in-trials badges', 'the two flags, as this list shows them'],
    ['drug_evidence_records', 'the same edges kept one row per drug, with stage and action: the table above'],
  ]

  const explorerQueries = computed(() =>
    buildA4ExplorerQueries(props.diseaseIndex, props.row.gene_index)
      .map(({ id, label, description, classification, feature, cap, cypher }) => ({
        id,
        label,
        cypher,
        description: classification === 'feature'
          ? `${description} Model feature ${feature}; cap ${cap}.`
          : `${description} Context only; cap ${cap}.`,
      })))
</script>

<template>
  <div class="flex flex-col gap-5">
    <section class="flex flex-col gap-2">
      <p class="text-sm font-semibold">Drug evidence behind the badges</p>
      <div v-if="hasDrug" class="flex flex-wrap gap-1.5">
        <StatusBadge v-if="row.approved_for_disease" status="success">Approved for this disease</StatusBadge>
        <StatusBadge v-if="row.investigational_for_disease" status="warning">In trials for this disease</StatusBadge>
      </div>
      <p class="text-xs leading-relaxed text-muted-foreground">
        A badge counts a drug that acts on {{ row.gene_name }} <b class="text-foreground">and</b> is approved or
        investigated for exactly {{ diseaseName }}. <i>In trials</i> covers every stage short of approval,
        including programmes whose stage is not recorded and ones that stopped.
        <template v-if="!hasDrug">
          No such drug is recorded in the snapshot. That is not the same as no drug: a drug approved for a
          broader disease node does not count here.
        </template>
      </p>
      <Skeleton v-if="hasDrug && !records && !recordsError" class="h-20 w-full" />
      <p v-else-if="recordsError" class="text-xs text-muted-foreground">
        Drug records unavailable: {{ recordsError }}
      </p>
      <template v-else-if="records?.length">
        <div class="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow class="bg-muted/30">
                <TableHead>Drug</TableHead>
                <TableHead>Highest stage for this disease</TableHead>
                <TableHead>Action on {{ row.gene_name }}</TableHead>
                <TableHead>DrugBank</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow v-for="d in records" :key="d.drug_id">
                <TableCell class="font-medium">{{ d.drug_name ?? d.drug_id }}</TableCell>
                <TableCell>
                  <StatusBadge :status="d.relation === 'indication' ? 'success' : 'warning'">
                    {{ stageLabel(d.max_stage) }}
                  </StatusBadge>
                </TableCell>
                <TableCell class="text-xs">{{ d.action_type.length ? d.action_type.join(' · ').toLowerCase() : '—' }}</TableCell>
                <TableCell class="font-mono text-xs">{{ d.drug_id }}</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <p class="font-mono text-2xs text-muted-foreground">
          {{ releases.join(' · ') }} · {{ records.length }} {{ records.length === 1 ? 'drug' : 'drugs' }} linked to
          this exact disease node
        </p>
      </template>
    </section>

    <Collapsible v-model:open="open">
      <CollapsibleTrigger as-child>
        <Button variant="ghost" size="sm" class="-ml-2">
          <component :is="open ? ChevronDown : ChevronRight" class="size-4" />
          <DataLineage class="size-4" /> Where the badges come from
        </Button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <ol class="mt-2 flex flex-col border-l pl-4">
          <li v-for="[name, what] in LINEAGE" :key="name" class="relative pb-3 last:pb-0">
            <span class="absolute -left-5 top-1.5 size-2 rounded-full bg-muted-foreground" />
            <p class="font-mono text-xs font-medium">{{ name }}</p>
            <p class="text-xs text-muted-foreground">{{ what }}</p>
          </li>
        </ol>
      </CollapsibleContent>
    </Collapsible>

    <VisualGraphExplorerCard
      title="See the evidence on the graph"
      :description="`Five ready-made queries showing the routes behind ${row.gene_name}'s score.`"
      :context-title="`${row.gene_name} → ${diseaseName}`"
      :starter-queries="explorerQueries"
      handoff="Running another default query replaces the current result."
      :chips="[['live', 'live']]" :src="['Kuzu folder (ytvuniN8)']"
      method-label="Query details">
      <template #note>
        <b>Four of the five queries are graph forms of model features</b> — protein interaction, shared
        pathway, shared molecular function, shared biological process. The fifth is the drug route: it helped
        admit this pair into the candidate pool, but <b>no feature traverses a drug node</b>, so nothing on it
        fed the score.
      </template>
      <template #method>
        <p><b class="text-foreground">Each query is independent.</b> Selecting a row only prepares Cypher; it
          does not query the graph. Run one query at a time in the Explorer — publishing captures only the
          currently displayed result.</p>
        <p class="mt-1.5">Traversal is <b class="text-foreground">undirected</b>, relationship variables are
          bound and returned, and the engine's gene label is <code class="font-mono text-2xs">protein</code>.
          The two GO queries exclude terms with <ActTerm t="node">node</ActTerm> degree above 200, which is what
          stops a generic term such as “protein binding” from returning the whole graph. Node indices are
          snapshot-specific and generated from the selected row.</p>
      </template>
    </VisualGraphExplorerCard>
  </div>
</template>
