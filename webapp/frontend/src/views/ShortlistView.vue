<script setup lang="ts">
  /**
   * Act 4 — the list, and the eyeball test. The home page (DEC-DEMO-005).
   *
   * Open a disease you know, judge the top of the list, narrow it on your own
   * thresholds, then ask what supports one gene. One selection drives the
   * header and every tab below the list, so they can never describe different
   * genes. The disease is shared with "Why trust the list", and the *How do we
   * know?* links lead there.
   *
   * Guardrails held here and in the parts:
   *  - `prediction` is never fetched or shown, and no AUC appears on this page;
   *  - drug and liability badges render but are never filters (CandidateTable);
   *  - every count carries its rank cut-off;
   *  - the app ranks and explains; no copy recommends what to pursue.
   *
   * Trials and literature (Phase 6), per-drug records (Phase 4), HGNC identity
   * (Phase 3) and the evidence assistant (Phase 7) join these tabs later.
   */
  import { computed, nextTick, onMounted, ref, watch } from 'vue'
  import { storeToRefs } from 'pinia'
  import { Button, Card, CardContent, Tabs, TabsContent, TabsList, TabsTrigger } from '@dataiku/ea-ui-kit'
  import { Microscope, News, Pulse } from '@dataiku/vue-icons'
  import { EmptyState, PageHeader } from 'bs-blueprint'
  import CandidateHeader from '@/components/shortlist/CandidateHeader.vue'
  import CandidateTable from '@/components/shortlist/CandidateTable.vue'
  import LineageTab from '@/components/shortlist/LineageTab.vue'
  import OverviewTab from '@/components/shortlist/OverviewTab.vue'
  import RankingTab from '@/components/shortlist/RankingTab.vue'
  import { TRUST_LINKS, parseDrivers, type Detail, type Payload, type Row } from '@/components/shortlist/types'
  import { useSelectionStore } from '@/stores/selection'
  import { apiUrl } from '@/utils/api'

  defineOptions({ name: 'ShortlistView' })

  const selection = useSelectionStore()
  const { diseases, diseaseIndex } = storeToRefs(selection)
  const diseaseName = computed(() =>
    diseases.value.find((d) => d.disease_index === diseaseIndex.value)?.disease_name ?? '')

  /* ── The list ────────────────────────────────────────────────────────────── */
  const data = ref<Payload | null>(null)
  const error = ref<string | null>(null)
  const loading = ref(false)
  const novelOnly = ref(false)
  const tractableOnly = ref(false)
  const excludeSecreted = ref(false)
  const maxRank = ref(200)

  async function loadCandidates() {
    if (diseaseIndex.value === undefined) return
    loading.value = true; error.value = null
    try {
      const q = new URLSearchParams({
        disease: String(diseaseIndex.value), novel_only: String(novelOnly.value),
        tractable_only: String(tractableOnly.value), exclude_secreted: String(excludeSecreted.value),
        max_rank: String(maxRank.value),
      })
      const res = await fetch(apiUrl(`/api/candidates?${q}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      data.value = await res.json()
    } catch (e) {
      error.value = `Could not load candidates: ${e instanceof Error ? e.message : String(e)}`
      data.value = null
    } finally { loading.value = false }
  }

  onMounted(async () => {
    await selection.ensureDiseases()
    if (selection.error) error.value = selection.error
  })
  // Immediate: returning from the evidence page, the shared disease is already set.
  watch([diseaseIndex, novelOnly, tractableOnly, excludeSecreted, maxRank], loadCandidates, { immediate: true })

  /* ── The selected candidate ──────────────────────────────────────────────── */
  const sel = ref<Row | null>(null)
  const detail = ref<Detail | null>(null)
  const detailBusy = ref(false)
  const detailError = ref<string | null>(null)
  const tab = ref('overview')

  // Only the DISEASE invalidates a selection. The population filters do not:
  // percentiles are computed against the disease's whole pool, not the filtered one.
  watch(diseaseIndex, () => { sel.value = null; detail.value = null; detailError.value = null })

  async function select(r: Row) {
    if (diseaseIndex.value === undefined) return
    sel.value = r
    tab.value = 'overview'
    detail.value = null
    detailError.value = null
    detailBusy.value = true
    reveal()
    const forGene = r.gene_index
    try {
      const q = new URLSearchParams({ disease: String(diseaseIndex.value), gene: String(r.gene_index) })
      const res = await fetch(apiUrl(`/api/candidates/gene?${q}`))
      if (!res.ok) {
        const d = await res.json().catch(() => null)
        throw new Error(d?.detail ?? `HTTP ${res.status}`)
      }
      const payload: Detail = await res.json()
      // A slower earlier request must not overwrite a later selection.
      if (sel.value?.gene_index !== forGene) return
      detail.value = payload
    } catch (e) {
      if (sel.value?.gene_index !== forGene) return
      detailError.value = e instanceof Error ? e.message : String(e)
    } finally {
      if (sel.value?.gene_index === forGene) detailBusy.value = false
    }
  }

  // Scroll the content pane itself: scrollIntoView also scrolls the shell's
  // fixed-height ancestors and pushes the sidebar off screen.
  const pane = ref<HTMLElement | null>(null)
  function reveal() {
    nextTick(() => {
      const card = document.getElementById('candidate')
      if (!card || !pane.value) return
      pane.value.scrollTop += card.getBoundingClientRect().top - pane.value.getBoundingClientRect().top - 16
    })
  }

  // Driver wording comes from the list payload's own labels, which come from
  // backend/feature_glossary.py, so the list and the tabs name features alike.
  const drivers = computed(() =>
    parseDrivers(sel.value?.top_shap_drivers, (k) => data.value?.feature_labels[k] ?? null))
</script>

<template>
  <div class="flex h-full flex-col">
    <PageHeader title="The shortlist" />

    <div ref="pane" class="min-h-0 flex-1 overflow-auto">
      <div class="mx-auto flex w-full max-w-6xl flex-col gap-6 p-8">
        <header class="flex flex-col gap-1.5">
          <p class="text-xs font-semibold uppercase tracking-wide text-primary">Candidate review</p>
          <h2 class="text-3xl font-semibold tracking-tight">Does this look right to you?</h2>
          <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Open a disease you know and judge the top of the list yourself; the scientist is the instrument.
            Nothing is pre-filtered: narrow it on your own thresholds, then ask what supports each gene. The
            model's reasons and the drug evidence stay in separate tabs, each with its source attached.
          </p>
          <nav class="flex flex-wrap items-center gap-1 text-sm">
            <span class="mr-1 text-muted-foreground">How do we know?</span>
            <Button v-for="l in TRUST_LINKS" :key="l.section" variant="ghost" size="sm" as-child>
              <router-link :to="{ name: 'trust', query: { section: l.section } }">{{ l.label }}</router-link>
            </Button>
          </nav>
        </header>

        <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {{ error }}
        </p>

        <CandidateTable v-model:novel-only="novelOnly" v-model:tractable-only="tractableOnly"
                        v-model:exclude-secreted="excludeSecreted" v-model:max-rank="maxRank"
                        :data="data" :loading="loading" :selected-gene="sel?.gene_index ?? null"
                        @select="select" />

        <Card id="candidate">
          <CardContent class="flex flex-col gap-6">
            <EmptyState v-if="!sel || diseaseIndex === undefined" :icon="Microscope" title="Pick a row"
                        description="Select any candidate in the list above to review its evidence here." />
            <template v-else>
              <CandidateHeader :row="sel" :detail="detail" :disease-name="diseaseName" />
              <Tabs v-model="tab">
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="ranking">Why this ranking?</TabsTrigger>
                  <TabsTrigger value="trials">Trials</TabsTrigger>
                  <TabsTrigger value="literature">Literature</TabsTrigger>
                  <TabsTrigger value="lineage">Drugs & graph</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" class="pt-4">
                  <OverviewTab :row="sel" :detail="detail" :drivers="drivers" :disease-name="diseaseName"
                               @go="(t) => (tab = t)" />
                </TabsContent>
                <TabsContent value="ranking" class="pt-4">
                  <RankingTab :drivers="drivers" :detail="detail" :busy="detailBusy" :error="detailError" />
                </TabsContent>
                <TabsContent value="trials" class="pt-4">
                  <EmptyState :icon="Pulse" title="Clinical trials are not retrieved yet"
                              :description="`Trials that mention ${sel.gene_name} will be listed here with their source and the passage that names the gene.`" />
                </TabsContent>
                <TabsContent value="literature" class="pt-4">
                  <EmptyState :icon="News" title="Literature is not retrieved yet"
                              :description="`Papers that mention ${sel.gene_name} will be listed here with their source and the passage that names the gene.`" />
                </TabsContent>
                <TabsContent value="lineage" class="pt-4">
                  <LineageTab :row="sel" :disease-index="diseaseIndex" :disease-name="diseaseName" />
                </TabsContent>
              </Tabs>
            </template>
          </CardContent>
        </Card>

        <p class="text-xs text-muted-foreground">
          Not shown anywhere on this page: any AUC, the model's prediction column, and any filter on drug or
          liability badges. The app ranks and explains; it does not recommend what to pursue.
        </p>
      </div>
    </div>
  </div>
</template>
