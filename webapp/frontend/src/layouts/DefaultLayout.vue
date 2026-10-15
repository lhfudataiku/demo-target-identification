<script setup lang="ts">
import { Button } from '@dataiku/ea-ui-kit'
import { Book } from '@dataiku/vue-icons'
import { AppLayout } from 'bs-blueprint'
import VisualGraphExplorerCard from '@/components/graph/VisualGraphExplorerCard.vue'
import ActGlossaryDrawer from '@/components/act/ActGlossaryDrawer.vue'
import { APP_ICON, APP_NAME } from '@/config'
import { useGlossaryStore } from '@/stores/glossary'

// Binds the app's identity to the bs-blueprint shell, which builds the sidebar
// from route meta. The glossary is not a route — it answers a question asked
// mid-card, so it overlays instead of navigating — so it sits in the shell's
// page-actions slot, top right of every page.
defineOptions({ name: 'AppDefaultLayout' })

const glossary = useGlossaryStore()

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
  <AppLayout :app-name="APP_NAME" :app-icon="APP_ICON" :show-administration="false">
    <template #page-actions>
      <Button variant="ghost" size="sm" :aria-expanded="glossary.isOpen" @click="glossary.toggle()">
        <Book class="size-4" /> Glossary
      </Button>
    </template>
  </AppLayout>

  <aside v-if="showExplorerPreview" class="fixed bottom-4 right-4 z-40 w-112 max-w-full">
    <VisualGraphExplorerCard
      title="Explorer launcher preview"
      description="Development-only harness. It prepares a query but never executes it."
      context-title="Shared card validation"
      :cypher="previewCypher"
    />
  </aside>

  <ActGlossaryDrawer />
</template>
