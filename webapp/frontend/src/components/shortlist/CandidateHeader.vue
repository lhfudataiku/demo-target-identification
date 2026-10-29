<script setup lang="ts">
  /**
   * The selected candidate: where it sits, the flags it carries, and who it is
   * — its HGNC identity, preloaded from one dated HGNC file and joined to the
   * graph by NCBI Gene ID (`/api/candidates/identity`, scope D16). The request
   * belongs to this header alone: if it fails, the header says so and every tab
   * below still works.
   */
  import { computed, ref, watch } from 'vue'
  import { Button, Collapsible, CollapsibleContent, CollapsibleTrigger, Skeleton } from '@dataiku/ea-ui-kit'
  import { ArrowExternalLink, ChevronDown, ChevronRight } from '@dataiku/vue-icons'
  import { StatusBadge } from 'bs-blueprint'
  import { apiUrl } from '@/utils/api'
  import { tractLabel, type Detail, type Identity, type Row } from './types'

  const props = defineProps<{ row: Row; detail: Detail | null; diseaseName: string }>()

  /* Open Targets packs several observed effects into one pipe-delimited cell
     ("cardiotoxicity|heart disease|..."). Shown as a list, not as the raw cell. */
  const safetyEvents = computed(() =>
    (props.detail?.safety_events ?? '').split('|').map((s) => s.trim()).filter(Boolean))

  const identity = ref<Identity | null>(null)
  const identityError = ref<string | null>(null)
  const identityBusy = ref(false)
  const open = ref(false)

  async function loadIdentity(gene: number) {
    identity.value = null; identityError.value = null; identityBusy.value = true; open.value = false
    try {
      const res = await fetch(apiUrl(`/api/candidates/identity?gene=${gene}`))
      const body = await res.json().catch(() => null)
      if (!res.ok) throw new Error(body?.detail ?? `HTTP ${res.status}`)
      // A slower earlier request must not overwrite a later selection.
      if (props.row.gene_index === gene) identity.value = body
    } catch (e) {
      if (props.row.gene_index === gene) identityError.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (props.row.gene_index === gene) identityBusy.value = false
    }
  }
  watch(() => props.row.gene_index, loadIdentity, { immediate: true })

  const list = (v: string[] | null | undefined) => (v?.length ? v.join(' · ') : '—')
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
      Selected candidate · rank {{ row.rank_in_disease.toLocaleString() }}<template v-if="detail?.pool_size">
        of {{ detail.pool_size.toLocaleString() }}</template> for {{ diseaseName }}
    </p>
    <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h2 class="font-mono text-3xl font-semibold tracking-tight">{{ row.gene_name }}</h2>
      <span v-if="identity?.found" class="text-base text-muted-foreground">{{ identity.name }}</span>
      <Skeleton v-else-if="identityBusy" class="h-5 w-64" />
    </div>
    <div class="flex flex-wrap gap-1.5">
      <StatusBadge :status="row.is_target ? 'muted' : 'info'">
        {{ row.is_target ? 'Recorded association' : 'Novel' }}
      </StatusBadge>
      <StatusBadge v-if="row.approved_for_disease" status="success">Approved for this disease</StatusBadge>
      <StatusBadge v-if="row.investigational_for_disease" status="warning">In trials for this disease</StatusBadge>
      <StatusBadge v-if="row.has_safety_liability" status="destructive">Liability recorded</StatusBadge>
      <StatusBadge status="muted">{{ row.ot_class_l1 || 'Class not assessed' }}</StatusBadge>
      <StatusBadge status="muted">{{ tractLabel(row) }}</StatusBadge>
    </div>
    <p v-if="row.has_safety_liability && safetyEvents.length" class="text-xs leading-relaxed text-muted-foreground">
      <span class="text-destructive">Recorded liability:</span> {{ safetyEvents.join(' · ') }}
    </p>

    <!-- Identity, from HGNC -->
    <template v-if="identity?.found">
      <p v-if="identity.symbol && identity.symbol !== row.gene_name" class="text-sm text-warning">
        HGNC's current symbol is <b class="font-mono">{{ identity.symbol }}</b>; the graph names it
        {{ row.gene_name }}.
      </p>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
        <div><dt class="text-2xs uppercase tracking-wide text-muted-foreground">HGNC</dt><dd class="font-mono text-xs">{{ identity.hgnc_id }}</dd></div>
        <div><dt class="text-2xs uppercase tracking-wide text-muted-foreground">Location</dt><dd class="font-mono text-xs">{{ identity.location ?? '—' }}</dd></div>
        <div><dt class="text-2xs uppercase tracking-wide text-muted-foreground">NCBI Gene</dt><dd class="font-mono text-xs">{{ identity.ncbi_gene_id }}</dd></div>
        <div>
          <dt class="text-2xs uppercase tracking-wide text-muted-foreground">Ensembl</dt>
          <dd>
            <a v-if="identity.ensembl_gene_id" :href="`https://www.ensembl.org/id/${identity.ensembl_gene_id}`"
               target="_blank" rel="noopener"
               class="inline-flex items-center gap-1 font-mono text-xs text-primary hover:underline">
              {{ identity.ensembl_gene_id }} <ArrowExternalLink class="size-3" />
            </a>
            <span v-else class="font-mono text-xs">—</span>
          </dd>
        </div>
      </dl>
      <p v-if="identity.alias_symbol?.length" class="text-sm">
        <span class="mr-1.5 text-muted-foreground">Also known as</span>
        <span class="font-mono text-xs">{{ identity.alias_symbol.join(' · ') }}</span>
      </p>
      <Collapsible v-model:open="open">
        <CollapsibleTrigger as-child>
          <Button variant="ghost" size="sm" class="-ml-2">
            <component :is="open ? ChevronDown : ChevronRight" class="size-4" /> Gene groups and previous names
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent class="flex flex-col gap-1 pt-1 text-sm">
          <p><span class="text-muted-foreground">Gene groups:</span> {{ list(identity.gene_group) }}</p>
          <p><span class="text-muted-foreground">Previous symbols:</span> {{ list(identity.prev_symbol) }}</p>
          <p><span class="text-muted-foreground">UniProt:</span> <span class="font-mono text-xs">{{ list(identity.uniprot_ids) }}</span></p>
          <p><span class="text-muted-foreground">Locus type:</span> {{ identity.locus_type ?? '—' }}</p>
        </CollapsibleContent>
      </Collapsible>
      <p class="font-mono text-2xs text-muted-foreground">
        {{ identity.source }} · {{ identity.source_file }} · matched by NCBI Gene ID
        {{ identity.ncbi_gene_id }}<template v-if="identity.date_modified">
          · record modified {{ identity.date_modified.slice(0, 10) }}</template>
      </p>
    </template>
    <p v-else-if="identity" class="text-xs text-muted-foreground">
      The HGNC file this app loads has no record for NCBI Gene ID {{ identity.ncbi_gene_id }}.
    </p>
    <p v-else-if="identityError" class="text-xs text-muted-foreground">
      Gene identity unavailable: {{ identityError }}
    </p>

    <p class="font-mono text-2xs text-muted-foreground">
      <template v-if="row.rank_percentile !== null">top {{ row.rank_percentile }}% of the pool · </template>graph
      node_index {{ row.gene_index }}
    </p>
  </div>
</template>
