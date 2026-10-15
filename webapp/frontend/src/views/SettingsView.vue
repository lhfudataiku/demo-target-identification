<script setup lang="ts">
  /**
   * SettingsView — per-browser display settings.
   *
   * Currently: presenter notes. Nothing here is stored in the DSS project, so a
   * setting never changes what a colleague sees.
   */
  import { PageHeader, SettingsSwitchItem } from 'bs-blueprint'
  import { usePresenterStore } from '@/stores/presenter'

  defineOptions({ name: 'SettingsView' })

  // Per-browser, not a project variable: it is a property of who is standing in
  // front of the screen, and it must not need a backend round trip thirty
  // seconds before a demo. See stores/presenter.ts.
  const presenter = usePresenterStore()
</script>

<template>
  <div class="flex h-full flex-col">
    <PageHeader title="Settings" description="Display settings — stored in this browser only." />
    <div class="min-h-0 flex-1 overflow-auto">
      <div class="mx-auto max-w-3xl space-y-8 p-8">
        <!-- ── Presenting: who the deck is being shown to ──────────────────── -->
        <section class="rounded-lg border bg-card">
          <div class="border-b px-5 py-4">
            <h2 class="text-base font-semibold">Presenting</h2>
            <p class="mt-1 text-xs text-muted-foreground">
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
      </div>
    </div>
  </div>
</template>
