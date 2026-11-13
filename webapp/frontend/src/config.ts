// App identity — the display name comes from `VITE_APP_NAME` in app.env;
// the icon is a fixed brand mark. No per-app code edits needed for setup.

import { Block } from '@dataiku/vue-icons'
import type { Component } from 'vue'

/** Human-readable name shown in the sidebar header (set VITE_APP_NAME in app.env). */
export const APP_NAME: string = import.meta.env.VITE_APP_NAME ?? ''

/** Icon component shown next to the app name in the sidebar.
 *  Swap `Block` for any other @dataiku/vue-icons glyph if you want a different mark. */
export const APP_ICON: Component = Block

/** Build-time identity of the Visual Graph Explorer webapp. */
export const VISUAL_GRAPH_PROJECT_KEY: string =
  import.meta.env.VITE_VISUAL_GRAPH_PROJECT_KEY?.trim() ?? ''
export const VISUAL_GRAPH_WEBAPP_ID: string =
  import.meta.env.VITE_VISUAL_GRAPH_WEBAPP_ID?.trim() ?? ''
/** DSS navigation object ID (webapp ID plus its current slug). */
export const VISUAL_GRAPH_OBJECT_ID: string =
  import.meta.env.VITE_VISUAL_GRAPH_OBJECT_ID?.trim() ?? ''
/** Optional DSS origin for local development; production defaults to same-origin. */
export const DSS_ORIGIN: string = import.meta.env.VITE_DSS_ORIGIN?.trim() ?? ''
