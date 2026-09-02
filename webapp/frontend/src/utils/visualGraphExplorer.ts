import {
  DSS_ORIGIN,
  VISUAL_GRAPH_PROJECT_KEY,
  VISUAL_GRAPH_WEBAPP_ID,
} from '@/config'

export interface VisualGraphExplorerConfig {
  projectKey: string
  webappId: string
  origin?: string
}

function currentOrigin(): string {
  // A local Vite origin cannot host a DSS Visual Webapp. Require the explicit
  // VITE_DSS_ORIGIN override in development; deployed builds stay same-origin.
  if (import.meta.env.DEV || typeof window === 'undefined') return ''
  return window.location.origin
}

function cleanOrigin(origin: string): string {
  return origin.trim().replace(/\/+$/, '')
}

/** Construct the DSS Visual Graph webapp URL without interpolating raw IDs. */
export function visualGraphExplorerUrl(
  config: VisualGraphExplorerConfig = {
    projectKey: VISUAL_GRAPH_PROJECT_KEY,
    webappId: VISUAL_GRAPH_WEBAPP_ID,
    origin: DSS_ORIGIN,
  },
): string | null {
  const projectKey = config.projectKey.trim()
  const webappId = config.webappId.trim()
  const origin = cleanOrigin(config.origin ?? '') || currentOrigin()
  if (!projectKey || !webappId || !origin) return null

  return `${origin}/projects/${encodeURIComponent(projectKey)}/webapps/${encodeURIComponent(webappId)}/view`
}

export function isVisualGraphExplorerConfigured(): boolean {
  return visualGraphExplorerUrl() !== null
}

/** Open only a constructed URL and report whether the browser created a tab. */
export function openVisualGraphExplorer(url: string): boolean {
  if (typeof window === 'undefined') return false
  const opened = window.open(url, '_blank')
  if (!opened) return false
  opened.opener = null
  return true
}

/** Clipboard access is best-effort in DSS iframes; never report an unconfirmed copy. */
export async function copyVisualGraphCypher(cypher: string): Promise<boolean> {
  if (typeof navigator === 'undefined' || !navigator.clipboard?.writeText) return false
  try {
    await navigator.clipboard.writeText(cypher)
    return true
  } catch {
    return false
  }
}
