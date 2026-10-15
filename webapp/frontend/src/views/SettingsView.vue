<script setup lang="ts">
  /**
   * SettingsView — app settings persisted to DSS project variables.
   *
   * Currently: LLM picker (which model the app uses for AI-assisted features).
   * Add more settings sections below as your app grows.
   *
   * Settings are stored under the key `<prefix>_app_settings` in the project's
   * "standard" variables, so they survive webapp restarts.
   */
  import { onMounted, computed, ref } from 'vue'
  import { Spinner } from '@dataiku/vue-icons'
  import { SelectField, SettingsSwitchItem } from 'bs-blueprint'
  import { useSettingsStore } from '@/stores/settings'
  import { usePresenterStore } from '@/stores/presenter'

  defineOptions({ name: 'SettingsView' })

  const store = useSettingsStore()
  // Per-browser, not a project variable: it is a property of who is standing in
  // front of the screen, and it must not need a backend round trip thirty
  // seconds before a demo. See stores/presenter.ts.
  const presenter = usePresenterStore()
  const savingLlm = ref(false)
  const llmError = ref<string | null>(null)

  onMounted(async () => {
    await store.ensureLoaded()
  })

  const llmOptions = computed(() =>
    store.llms.map((l) => ({ value: l.id, label: l.label }))
  )

  async function onLlmChange(value: string | undefined) {
    savingLlm.value = true
    llmError.value = null
    try {
      await store.updateSettings({ llm_id: value ?? null })
    } catch (e) {
      llmError.value = e instanceof Error ? e.message : String(e)
    } finally {
      savingLlm.value = false
    }
  }
</script>

<template>
  <div class="h-full flex flex-col">
    <header class="shrink-0 h-16 border-b px-8 flex flex-col justify-center">
      <h1 class="text-xl font-semibold tracking-tight">Settings</h1>
      <p class="text-sm text-muted-foreground mt-0.5">Application configuration — persisted to DSS project variables.</p>
    </header>
    <div class="flex-1 overflow-auto">
    <div class="max-w-3xl mx-auto p-8 space-y-8">

      <!-- LLM selection -->
      <section class="border rounded-lg bg-white">
        <div class="px-5 py-4 border-b">
          <h2 class="text-base font-semibold">Language model</h2>
          <p class="text-xs text-muted-foreground mt-1">
            The LLM used for AI-assisted features across the app.
            Populated from LLMs configured in your DSS project.
          </p>
        </div>
        <div class="px-5 py-4 space-y-2">
          <label class="text-xs font-medium text-muted-foreground">LLM</label>
          <div class="flex items-center gap-2">
            <SelectField
              class="flex-1 min-w-0"
              placeholder="— Select an LLM —"
              :model-value="store.settings.llm_id ?? undefined"
              :options="llmOptions"
              :disabled="store.isLoading || savingLlm"
              @update:model-value="onLlmChange"
            />
            <Spinner
              v-if="store.isLoading || savingLlm"
              class="w-4 h-4 animate-spin text-muted-foreground shrink-0"
            />
          </div>
          <p v-if="store.error" class="text-xs text-destructive">
            Could not load LLMs: {{ store.error }}
          </p>
          <p v-if="llmError" class="text-xs text-destructive">
            Save failed: {{ llmError }}
          </p>
          <p v-if="!store.isLoading && llmOptions.length === 0 && !store.error"
             class="text-xs text-muted-foreground">
            No LLMs found. Add a model in your DSS project's LLM settings.
          </p>
        </div>
      </section>

      <!-- ── Presenting: who the deck is being shown to ──────────────────── -->
      <section class="border rounded-lg bg-white">
        <div class="px-5 py-4 border-b">
          <h2 class="text-base font-semibold">Presenting</h2>
          <p class="text-xs text-muted-foreground mt-1">
            Stored in this browser only — not in the DSS project, so it never changes what a
            colleague sees.
          </p>
        </div>
        <div class="px-5 py-4">
          <SettingsSwitchItem
            id="presenter-notes"
            v-model="presenter.showNotes"
            label="Presenter notes"
            description="Show the lines written for whoever is demoing — the caveat to volunteer, the number not to quote. Turn this off before sharing your screen with a client."
          />
        </div>
      </section>

      <!-- ── Add more settings sections here ─────────────────────────────── -->
      <!-- Pattern:
           1. Add a key to ALLOWED_KEYS in backend/services/settings.py
           2. Add it to AppSettings interface in frontend/src/stores/settings.ts
           3. Add a section below similar to the LLM section above
      -->

    </div>
    </div>
  </div>
</template>
