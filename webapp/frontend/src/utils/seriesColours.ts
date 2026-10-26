// The one place a chart series gets its colour.
//
// Colours carry meaning across the app — the model's own result is always the
// same hue, the exception to look at is always another — so a view names the
// MEANING and this table picks the kit token. The table is documented in
// docs/demo/WEBAPP_DESIGN.md §3.5; change it there first.
//
// Served as utility classes, never as inline styles: the design lint cannot see
// a colour set through a bound `:style`, and a class it can check. Every class
// is written out in full so Tailwind generates it.
import type { ThemeColorName } from 'bs-blueprint'

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

/** Text colour for a series. */
export const SERIES_TEXT: Record<Series, string> = {
  measured: 'text-chart-2',
  contrast: 'text-chart-3',
  highlight: 'text-chart-1',
  approved: 'text-success',
  trial: 'text-warning',
  baseline: 'text-muted-foreground',
  negative: 'text-destructive',
}

/** Fill for a series: bars, dots, swatches. */
export const SERIES_BG: Record<Series, string> = {
  measured: 'bg-chart-2',
  contrast: 'bg-chart-3',
  highlight: 'bg-chart-1',
  approved: 'bg-success',
  trial: 'bg-warning',
  baseline: 'bg-muted-foreground',
  negative: 'bg-destructive',
}
