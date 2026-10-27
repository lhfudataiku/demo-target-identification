/// <reference types="vite/client" />

// Declares `import.meta.env`, the VITE_* env vars, and module types
// for `*.vue`, `*.css`, and other assets. Previously provided transitively by
// the truenorth package; now owned locally.

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface ImportMetaEnv {
  readonly VITE_DSS_ORIGIN?: string
  readonly VITE_VISUAL_GRAPH_PROJECT_KEY?: string
  readonly VITE_VISUAL_GRAPH_WEBAPP_ID?: string
  readonly VITE_VISUAL_GRAPH_OBJECT_ID?: string
  readonly VITE_AGENT_HUB_PROJECT_KEY?: string
  readonly VITE_AGENT_HUB_OBJECT_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
