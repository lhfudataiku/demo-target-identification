<script setup lang="ts">
  /**
   * "Why trust the list" — Acts 1–3 on one page (DEC-DEMO-005).
   *
   * Three questions, each answered for the disease open on the shortlist: what
   * the model can see (act 1), how faithfully it reconstructs known biology
   * (act 2), whether it holds across the disease family (act 3). Every analysis
   * the three act pages carried is still here, under "Show the detail".
   *
   * The disease is the shared one (stores/selection.ts). Deep links from the
   * shortlist (`?section=graph|reconstruction|family`) scroll to a section.
   * Each section loads and fails on its own, so a slow family panel never
   * blanks the graph totals.
   */
  import { computed, nextTick, onMounted, ref, watch } from 'vue'
  import { useRoute } from 'vue-router'
  import { storeToRefs } from 'pinia'
  import { Alert, AlertDescription, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Skeleton } from '@dataiku/ea-ui-kit'
  import { ArrowLeft } from '@dataiku/vue-icons'
  import { PageHeader, SelectField } from 'bs-blueprint'
  import GraphSection from '@/components/trust/GraphSection.vue'
  import ReconstructionSection from '@/components/trust/ReconstructionSection.vue'
  import FamilySection from '@/components/trust/FamilySection.vue'
  import type {
    CalibrationPayload, EvidencePayload, FamilyPanel, FamilySummary, TrustDisease,
  } from '@/components/trust/types'
  import { useSelectionStore } from '@/stores/selection'
  import { apiUrl } from '@/utils/api'

  defineOptions({ name: 'TrustView' })

  const selection = useSelectionStore()
  const { diseases, diseaseIndex } = storeToRefs(selection)
  // SelectField models strings; disease_index is numeric.
  const diseaseStr = computed<string | undefined>({
    get: () => (diseaseIndex.value === undefined ? undefined : String(diseaseIndex.value)),
    set: (v) => { diseaseIndex.value = v === undefined ? undefined : Number(v) },
  })

  const SECTIONS = [
    { id: 'graph', act: 1, title: 'What the model can see', desc: 'The knowledge graph it learns from, and what counts as a known target.' },
    { id: 'reconstruction', act: 2, title: 'How faithfully it reconstructs known biology', desc: 'Held-out diseases: does the list put already-known targets near the top?' },
    { id: 'family', act: 3, title: 'Does it hold across the disease family', desc: 'The same model on every term in the family, with its uncertainty.' },
  ] as const

  /** One section's payload: data, or the reason it is missing. */
  interface Load<T> { data: T | null; error: string | null }
  const evidence = ref<Load<EvidencePayload>>({ data: null, error: null })
  const calibration = ref<Load<CalibrationPayload>>({ data: null, error: null })
  const families = ref<Load<FamilySummary[]>>({ data: null, error: null })
  const panel = ref<Load<FamilyPanel>>({ data: null, error: null })
  const panelLoading = ref(false)

  async function getJson<T>(path: string, into: { value: Load<T> }) {
    try {
      const res = await fetch(apiUrl(path))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      into.value = { data: (await res.json()) as T, error: null }
    } catch (e) {
      into.value = { data: null, error: `Could not load ${path}: ${e instanceof Error ? e.message : String(e)}` }
    }
  }

  const current = computed<TrustDisease | null>(() => {
    const d = diseases.value.find((x) => x.disease_index === diseaseIndex.value)
    if (!d) return null
    return {
      disease_index: d.disease_index,
      disease_name: d.disease_name,
      auc: calibration.value.data?.diseases.find((x) => x.disease_index === d.disease_index) ?? null,
      family: families.value.data?.find((f) => f.disease_indexes.includes(d.disease_index)) ?? null,
    }
  })

  // Panels are fetched once per family and kept: switching between two
  // diseases of one family must not refetch it.
  const panels = new Map<number, FamilyPanel>()
  async function loadPanel(familyId: number | undefined) {
    if (familyId === undefined) { panel.value = { data: null, error: null }; return }
    const hit = panels.get(familyId)
    if (hit) { panel.value = { data: hit, error: null }; return }
    panelLoading.value = true
    await getJson<FamilyPanel>(`/api/families/${familyId}`, panel)
    if (panel.value.data) panels.set(familyId, panel.value.data)
    panelLoading.value = false
  }
  watch(() => current.value?.family?.family_id, loadPanel)

  // Scroll the content pane itself: scrollIntoView would also scroll the shell's
  // fixed-height ancestors and push the sidebar off screen.
  const route = useRoute()
  const pane = ref<HTMLElement | null>(null)
  function reveal(id: unknown) {
    nextTick(() => {
      const el = typeof id === 'string' ? document.getElementById(`section-${id}`) : null
      if (!el || !pane.value) return
      pane.value.scrollTop += el.getBoundingClientRect().top - pane.value.getBoundingClientRect().top - 16
    })
  }
  watch(() => route.query.section, reveal)

  onMounted(async () => {
    await Promise.all([
      selection.ensureDiseases(),
      getJson<EvidencePayload>('/api/evidence', evidence),
      getJson<CalibrationPayload>('/api/calibration', calibration),
      getJson<FamilySummary[]>('/api/families', families),
    ])
    // Reveal once the sections have their height, or the offset lands short.
    reveal(route.query.section)
  })
</script>

<template>
  <div class="flex h-full flex-col">
    <PageHeader title="Why trust the list">
      <template #actions>
        <Button variant="outline" size="sm" as-child>
          <router-link :to="{ name: 'shortlist' }"><ArrowLeft class="size-4" /> Back to the shortlist</router-link>
        </Button>
      </template>
    </PageHeader>

    <div ref="pane" class="min-h-0 flex-1 overflow-auto">
      <div class="mx-auto flex w-full max-w-5xl flex-col gap-6 p-8">
        <header class="flex flex-col gap-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-primary">Supporting evidence</p>
          <h2 class="text-3xl font-semibold tracking-tight">Three questions behind every ranking.</h2>
          <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
            Each section answers one question for the disease open on the shortlist. The full analysis stays
            one click away under <i>Show the detail</i>.
          </p>
          <label class="flex max-w-md flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Disease, shared with the shortlist</span>
            <SelectField v-model="diseaseStr"
                         :options="diseases.map((d) => ({ value: String(d.disease_index), label: d.disease_name }))" />
          </label>
          <nav class="flex flex-wrap gap-2">
            <Button v-for="s in SECTIONS" :key="s.id" variant="ghost" size="sm" as-child>
              <router-link :to="{ name: 'trust', query: { section: s.id } }">{{ s.act }} · {{ s.title }}</router-link>
            </Button>
          </nav>
        </header>

        <Alert v-if="selection.error" variant="destructive">
          <AlertDescription>{{ selection.error }}</AlertDescription>
        </Alert>

        <Card v-for="s in SECTIONS" :id="`section-${s.id}`" :key="s.id">
          <CardHeader>
            <CardTitle class="flex items-center gap-2">
              <span class="flex size-6 items-center justify-center rounded-full bg-primary text-xs text-primary-foreground">{{ s.act }}</span>
              {{ s.title }}
            </CardTitle>
            <CardDescription>{{ s.desc }}</CardDescription>
          </CardHeader>
          <CardContent>
            <template v-if="s.id === 'graph'">
              <GraphSection v-if="evidence.data" :graph="evidence.data" />
              <Alert v-else-if="evidence.error" variant="destructive"><AlertDescription>{{ evidence.error }}</AlertDescription></Alert>
              <Skeleton v-else class="h-40 w-full" />
            </template>
            <template v-else-if="s.id === 'reconstruction'">
              <ReconstructionSection v-if="calibration.data && current" :cal="calibration.data" :disease="current" />
              <Alert v-else-if="calibration.error" variant="destructive"><AlertDescription>{{ calibration.error }}</AlertDescription></Alert>
              <Skeleton v-else class="h-40 w-full" />
            </template>
            <template v-else>
              <Alert v-if="families.error || panel.error" variant="destructive">
                <AlertDescription>{{ families.error ?? panel.error }}</AlertDescription>
              </Alert>
              <Skeleton v-else-if="!families.data || !current || panelLoading" class="h-40 w-full" />
              <FamilySection v-else :disease="current" :panel="current.family ? panel.data : null"
                             :families="families.data" />
            </template>
          </CardContent>
        </Card>

        <p class="text-xs text-muted-foreground">
          Not shown anywhere on this page: pooled AUC, the ablation ladder, any hyperparameter, and any
          headline number without the spread beside it.
        </p>
      </div>
    </div>
  </div>
</template>
