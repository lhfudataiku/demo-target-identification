// The one place a chart series gets its colour.
//
// Colours carry meaning across acts — the model's own result is always the same
// hue, the exception to look at is always another — so a view names the MEANING
// and this table picks the kit token. The table is the one approved in
// docs/demo/BLUEPRINT_ALIGNMENT_PLAN.md (Phase 3); change it there first.
import { themeColor, type ThemeColorName } from 'bs-blueprint'

export const SERIES = {
  /** The model or pipeline result: precision, AUPRC, corroborated evidence, the pool. */
  measured: 'chart-2',
  /** The series compared against `measured`: other drivers, relations, shared terms. */
  contrast: 'chart-3',
  /** The exception worth a look: single-source evidence, genes distinct to one term. */
  highlight: 'chart-1',
  /** Status badges on the ranked list. */
  approved: 'success',
  trial: 'warning',
  /** Base rate, chance, grouped or duplicate rows. */
  baseline: 'muted-foreground',
  /** Failed trust checks and negative contributions. */
  negative: 'destructive',
} as const satisfies Record<string, ThemeColorName>

export type Series = keyof typeof SERIES

/** Categories with no fixed meaning (Sankey routes, donut slices), in kit order. */
const CATEGORICAL: ThemeColorName[] = ['chart-1', 'chart-2', 'chart-3', 'chart-4', 'chart-5']

/** CSS value for templates, inline styles and color-mix(): the browser resolves it. */
export const seriesVar = (s: Series): string => `var(--${SERIES[s]})`

/** Resolved rgb() for canvas renderers (ECharts cannot read CSS variables, nor the
 *  kit's space-separated hsl() values). Read at render time so it follows the theme. */
export const seriesColor = (s: Series): string => themeColor(SERIES[s])

/** Resolved rgb() palette for categorical charts. */
export const categoricalColors = (): string[] => CATEGORICAL.map(themeColor)

/** Resolve any CSS colour (including `var(--token)`) to rgb() for a canvas renderer. */
export function resolveColour(css: string): string {
  const probe = document.createElement('span')
  probe.style.color = css
  document.body.appendChild(probe)
  const value = getComputedStyle(probe).color
  probe.remove()
  return value
}
