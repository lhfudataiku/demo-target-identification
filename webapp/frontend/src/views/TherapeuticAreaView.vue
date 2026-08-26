<script setup lang="ts">
  /**
   * Act 3 — the therapeutic area.
   *
   * "Does it hold across my area, or just on one term?" — pick a family, show
   * the same model against every term in it.
   *
   * The point of this act is the UNCERTAINTY, not the average. A term with 8
   * known targets and one with 600 must not read the same, so every AUC renders
   * with its 95% interval, and terms flagged untrustworthy are shown but never
   * quoted as a score.
   */
  import { computed, onMounted, ref, watch } from 'vue'
  import { apiUrl } from '@/utils/api'
  import ActCard from '@/components/act/ActCard.vue'

  defineOptions({ name: 'TherapeuticAreaView' })

  interface Family { family_id: number; family_name: string; n_terms: number; macro_auc: number; n_trustworthy: number }
  interface Term {
    disease_index: number; disease_name: string
    auc: number; lo95: number; hi95: number; trustworthy: boolean; n_pos: number
  }
  interface Detail { family_id: number; n_terms: number; macro_auc: number; terms: Term[]; overlap: { a: string; b: string; shared: number }[] }

  const families = ref<Family[]>([])
  const selected = ref<number | undefined>()
  const detail = ref<Detail | null>(null)
  const error = ref<string | null>(null)

  // AUC axis runs 0.4–1.0: below chance is not a meaningful distinction here,
  // and a 0–1 axis wastes half the width on range nothing occupies.
  const LO = 0.4
  const pos = (v: number) => Math.max(0, Math.min(100, ((v - LO) / (1 - LO)) * 100))

  const untrustworthy = computed(() => detail.value?.terms.filter((t) => !t.trustworthy).length ?? 0)

  async function loadFamilies() {
    try {
      const res = await fetch(apiUrl('/api/families'))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      families.value = await res.json()
      const breast = families.value.find((f) => /breast/i.test(f.family_name))
      selected.value = (breast ?? families.value[0])?.family_id
    } catch (e) {
      error.value = `Could not load families: ${e instanceof Error ? e.message : String(e)}`
    }
  }

  async function loadDetail() {
    if (selected.value === undefined) return
    try {
      const res = await fetch(apiUrl(`/api/families/${selected.value}`))
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      detail.value = await res.json()
    } catch (e) {
      error.value = `Could not load the family: ${e instanceof Error ? e.message : String(e)}`
      detail.value = null
    }
  }

  onMounted(loadFamilies)
  watch(selected, loadDetail)
</script>

<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex flex-col gap-1.5 border-b border-border pb-5">
      <p class="font-mono text-[11px] uppercase tracking-[0.08em] text-muted-foreground">
        Act 3 of 4 · The therapeutic area
      </p>
      <h1 class="font-serif text-3xl font-semibold tracking-tight">
        Does it hold across my area, or just on one term?
      </h1>
      <p class="max-w-3xl text-sm leading-relaxed text-muted-foreground">
        Most groups own one therapeutic area, so a single cherry-picked disease proves nothing. Pick
        a family and see the same model against every term in it — with the uncertainty each term
        actually has.
      </p>
    </header>

    <p v-if="error" class="rounded-md border border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive">
      {{ error }}
    </p>

    <div class="grid grid-cols-12 gap-4">
      <ActCard span="col-span-12" title="Choose a family" :chips="[['live', 'live']]"
               desc="Families are drawn from a curated medical ontology, not by an algorithm — and that choice lowered the score we report."
               :src="['family_panel']">
        <div class="flex flex-wrap items-end gap-4">
          <label class="flex min-w-72 flex-col gap-1 text-sm">
            <span class="text-muted-foreground">Disease family</span>
            <select v-model="selected" class="rounded-md border border-input bg-background px-2 py-1.5 text-sm">
              <option v-for="f in families" :key="f.family_id" :value="f.family_id">
                {{ f.family_name }} — {{ f.n_terms }} terms
              </option>
            </select>
          </label>
          <div v-if="detail" class="flex gap-6">
            <div class="flex flex-col">
              <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">Terms</span>
              <span class="font-mono text-xl tabular-nums">{{ detail.n_terms }}</span>
            </div>
            <div class="flex flex-col">
              <span class="font-mono text-[10px] uppercase tracking-wide text-muted-foreground">Macro AUC</span>
              <span class="font-mono text-xl tabular-nums">{{ detail.macro_auc.toFixed(4) }}</span>
            </div>
          </div>
        </div>
        <p class="mt-3 text-[13px] leading-relaxed text-muted-foreground">
          Train and test are split by <b class="text-foreground">family</b>, not at random. Random
          splitting puts “diabetes” and “type 2 diabetes” on opposite sides — the same programme
          wearing two labels — and inflates the score. This is also the concrete place a customer's
          own judgment already enters the pipeline.
        </p>
      </ActCard>

      <ActCard span="col-span-12" title="AUC, with the uncertainty it actually has"
               :chips="[['live', 'live']]"
               :desc="detail ? `${detail.n_terms} terms. ${untrustworthy} have intervals too wide to read as a score — shown, never quoted.` : undefined"
               :src="['family_panel']">
        <div v-if="detail" class="flex flex-col gap-2">
          <div v-for="t in detail.terms" :key="t.disease_index" class="flex items-center gap-3">
            <span class="w-56 flex-none truncate text-[12px]" :title="t.disease_name">{{ t.disease_name }}</span>
            <span class="w-14 flex-none text-right font-mono text-[11px] tabular-nums text-muted-foreground">
              n={{ t.n_pos }}
            </span>
            <span class="relative h-4 flex-1 rounded-sm bg-secondary">
              <!-- the 95% interval, then the point estimate on top of it -->
              <span class="absolute top-1/2 h-1 -translate-y-1/2 rounded-full"
                    :class="t.trustworthy ? 'bg-primary/40' : 'bg-muted-foreground/25'"
                    :style="{ left: pos(t.lo95) + '%', width: Math.max(0.5, pos(t.hi95) - pos(t.lo95)) + '%' }" />
              <span class="absolute top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full"
                    :class="t.trustworthy ? 'bg-primary' : 'bg-muted-foreground/60'"
                    :style="{ left: pos(t.auc) + '%' }" />
            </span>
            <span class="w-14 flex-none text-right font-mono text-[11px] tabular-nums"
                  :class="t.trustworthy ? '' : 'text-muted-foreground line-through'">
              {{ t.auc.toFixed(3) }}
            </span>
          </div>
          <div class="mt-1 flex justify-between font-mono text-[10px] text-muted-foreground">
            <span>{{ LO.toFixed(1) }}</span><span>0.7</span><span>1.0</span>
          </div>
        </div>
        <p v-else class="py-6 text-center text-sm text-muted-foreground">Select a family.</p>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-7" title="How much do the subtypes overlap?"
               :chips="[['live', 'live']]"
               desc="Shared genes in each pair's top 50. This is where the method's limit lives, and showing it here is what makes act 4 believable."
               :src="['pairwise_overlap']">
        <div v-if="detail && detail.overlap.length" class="flex flex-col gap-1.5">
          <div v-for="p in detail.overlap" :key="p.a + '|' + p.b" class="flex items-center gap-3">
            <span class="w-40 flex-none truncate text-[12px]" :title="p.a">{{ p.a }}</span>
            <span class="flex-none text-muted-foreground">vs</span>
            <span class="w-40 flex-none truncate text-[12px]" :title="p.b">{{ p.b }}</span>
            <span class="h-3 flex-1 overflow-hidden rounded-sm bg-secondary">
              <span class="block h-full rounded-sm bg-primary" :style="{ width: (100 * p.shared / 50) + '%' }" />
            </span>
            <span class="w-14 flex-none text-right font-mono text-[11px] tabular-nums text-muted-foreground">
              {{ p.shared }}/50
            </span>
          </div>
        </div>
        <p v-else class="py-6 text-center text-[13px] text-muted-foreground">
          No pairwise overlap computed for this family.
        </p>
      </ActCard>

      <ActCard span="col-span-12 lg:col-span-5" title="What this tells you before you build on it">
        <p class="text-[13px] leading-relaxed text-muted-foreground">
          Two subtypes sharing most of their top 50 means the public data barely distinguishes them —
          the model will not resolve them either, and no amount of tuning changes that. Two subtypes
          sharing few means the lists are genuinely different programmes.
        </p>
        <p class="mt-3 text-[13px] leading-relaxed text-muted-foreground">
          <b class="text-foreground">We can tell you which of your subtypes this resolves</b> before
          you commit to it. That is a scoping answer, not a performance claim.
        </p>
      </ActCard>
    </div>
  </div>
</template>
