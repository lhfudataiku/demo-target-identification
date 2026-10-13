<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import VisualGraphExplorerCard from '@/components/graph/VisualGraphExplorerCard.vue'
import ActGlossaryDrawer from '@/components/act/ActGlossaryDrawer.vue'

defineOptions({ name: 'AppDefaultLayout' })

// A local-only harness renders the shared Explorer card without needing either act's data.
// Open `?explorerPreview=1` while running Vite to use it.
const showExplorerPreview = import.meta.env.DEV
  && new URLSearchParams(window.location.search).get('explorerPreview') === '1'
const previewCypher = `// Launcher preview — this app never executes this query.
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
        description="Development-only harness. It prepares a query but never executes it."
        context-title="Shared card validation"
        :cypher="previewCypher"
      />
    </aside>

    <ActGlossaryDrawer />
  </div>
</template>
