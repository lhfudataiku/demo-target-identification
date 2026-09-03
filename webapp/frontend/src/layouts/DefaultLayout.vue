<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import VisualGraphExplorerCard from '@/components/graph/VisualGraphExplorerCard.vue'
import VisualGraphExplorerDialog from '@/components/graph/VisualGraphExplorerDialog.vue'
import ActGlossaryDrawer from '@/components/act/ActGlossaryDrawer.vue'

defineOptions({ name: 'AppDefaultLayout' })

// A local-only harness keeps Wave 1 testable without wiring either act before
// its migration gate. Open `?explorerPreview=1` while running Vite to use it.
const showExplorerPreview = import.meta.env.DEV
  && new URLSearchParams(window.location.search).get('explorerPreview') === '1'
const previewCypher = `// Wave 1 launcher test — opening the shell does not execute this query.
MATCH (n)
RETURN n
ORDER BY n.node_index
LIMIT 1`
</script>

<template>
  <div class="h-screen bg-background text-foreground flex">
    <AppSidebar />
    <div class="flex-1 flex flex-col overflow-auto">
      <main class="flex-1 overflow-auto">
        <router-view />
      </main>
    </div>

    <aside v-if="showExplorerPreview" class="fixed bottom-4 right-4 z-40 w-[min(28rem,calc(100vw-2rem))]">
      <VisualGraphExplorerCard
        title="Explorer launcher preview"
        description="Development-only Wave 1 harness. It prepares a query but never executes it."
        context-title="Shared shell validation"
        :cypher="previewCypher"
      />
    </aside>

    <VisualGraphExplorerDialog />
    <ActGlossaryDrawer />
  </div>
</template>
