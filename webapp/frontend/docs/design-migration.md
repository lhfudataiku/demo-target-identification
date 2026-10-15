# Design migration guide

Managed by bs-blueprint 0.2.0 (`npx bs-blueprint sync` rewrites it; do not edit).
`npm run check` prints doctor findings; each one links to a section here. Work through the
sections in the order below, run `npm run check` after each, and commit as you go. The two
baseline files (`eslint-suppressions.json`, `bs-blueprint.baseline.json`) shrink automatically
as drift disappears; never edit them by hand.

## Order

1. [Setup](#setup): Vite wiring, hash router, theme mode. These block `check` until done.
2. [Tokens](#tokens): remove the app's own palette so the kit theme actually applies.
3. [Icons](#icons): `lucide-vue-next` to `@dataiku/vue-icons`.
4. [Primitives](#primitives): local `src/components/ui` to the kit.
5. [Shell](#shell): local sidebar and layout to `AppLayout`.
6. [API](#api): local `apiUrl` to the bs-blueprint one.
7. [Arbitrary values](#arbitrary-values) and [custom classes](#custom-classes).
8. [Theme](#theme), then [done](#done).

Small, verifiable commits: one section, or one file group, per commit. `vue-tsc` is strict
about unused imports, so remove the old import in the same edit that adds the new one.

## Setup

```ts
// vite.config.ts
import dkuWebapp from '@dataiku/vite-plugin-dku-webapp'
export default defineConfig({
  plugins: [vue(), tailwindcss(), dkuWebapp()],
  resolve: { dedupe: ['vue', 'vue-router'] },
  optimizeDeps: {
    exclude: ['@dataiku/ea-ui-kit', 'bs-blueprint'],   // source packages: never pre-bundle
    include: ['reka-ui', '@vueuse/core', 'class-variance-authority', 'clsx', 'tailwind-merge',
              '@tanstack/vue-table', 'vee-validate', 'vue-sonner', 'embla-carousel-vue', 'vaul-vue',
              '@internationalized/date', 'vue-input-otp'],
  },
  build: { assetsInlineLimit: 32 * 1024 },   // DSS libraries are text-only: inline the kit's font files
})
```

```ts
// router: DSS owns the page URL, so routes live after the hash. Drop any `baseUrl` computed
// from window.location; the hash history does not need it.
createRouter({ history: createWebHashHistory(), routes })
```

```vue
<!-- App.vue -->
<script setup lang="ts">
import { useThemeMode } from 'bs-blueprint'
useThemeMode('light')   // applies the theme; expose isDark from the same composable in Settings
</script>
```

## Tokens

The kit theme (`src/styles/kit.css`, which imports `@dataiku/ea-ui-kit/style/rfx.css`) defines
every color, radius and font token and maps them to Tailwind utilities. An app-owned palette
(`src/styles/tokens.css`, a `:root { --primary: … }` block, a `@theme inline { --color-*: … }`
bridge) overrides it and keeps the old look alive. Remove it:

1. Delete the app's tokens file and the `@theme inline` bridge in `src/style.css`. Keep only
   `@import './styles/kit.css';`, your `@source` lines if any, and app-specific `@layer` rules.
2. Drop `@plugin '@tailwindcss/typography'` and `tw-animate-css`: the kit theme provides prose
   classes and animations.
3. Replace app-only tokens by kit tokens:

| App token or utility | Kit equivalent |
|---|---|
| `bg-raised` (cards on cards, inputs) | `bg-muted` or `bg-card` |
| `text-faint-foreground`, `fill-faint-foreground` | `text-muted-foreground/70` |
| `border-border-strong` | `border-border` (or `border-2`) |
| `bg-primary-hover`, `bg-primary-press` | `hover:bg-primary/90`, `active:bg-primary/80` |
| `text-info`, `bg-info/15` | `text-primary`, `bg-primary/10`, or `<StatusBadge status="info">` |
| `bg-glass`, `text-glass-foreground` | `bg-background/80 backdrop-blur` |
| `text-micro` (11px) | `text-2xs` (from kit-extras) |
| `text-caption` (12.5px) | `text-xs` |
| `micro-label` | `text-xs font-semibold uppercase tracking-wider text-muted-foreground` |
| `--radius: 0.625rem` | the kit's `0.5rem`; use `rounded-lg`/`rounded-md` |

The kit ships `--success` and `--warning` through `src/styles/kit-extras.css` (generated;
`text-success`, `bg-warning/10` work). Chart code reads colors with `useThemeColors()` from
bs-blueprint, never `'var(--chart-1)'` strings.

## Icons

`@dataiku/vue-icons` exports 944 components named in PascalCase, used exactly like lucide
components (`<Search class="size-4" />`, or passed as `icon` props and route meta). Three
steps per file: change the import source, rename the glyphs that differ, keep the classes.

- Many names are identical: Search, Plus, Minus, X, Trash, Copy, Filter, Eye, EyeOff, Home,
  Mail, Send, Tag, User, Clock, Calendar, Bell, Link, Info, Bookmark, File, FileText,
  FolderOpen, History, ChevronDown/Up/Left/Right, ArrowLeft/Right/Up/Down.
- Common renames (the doctor prints which of these your app uses):

| lucide | @dataiku/vue-icons |
|---|---|
| `Activity` | `Pulse` |
| `AlertTriangle` | `WarningOutline` |
| `Blocks` | `Block` |
| `Bot` | `AiAgent` |
| `Check` | `Checkmark` |
| `CheckCircle` | `CheckmarkCircleOutline` |
| `CheckCircle2` | `CheckmarkCircleFill` |
| `ChevronsUpDown` | `ArrowSort` |
| `CircleDotDashed` | `PendingCircleOutline` |
| `CircleX` | `DismissCircleOutline` |
| `ClipboardList` | `ClipboardBulletList` |
| `Clock3` | `Clock` |
| `Database` | `Dataset` |
| `Download` | `ArrowDownload` |
| `Edit` | `Edit` |
| `Edit2` | `Edit` |
| `Edit3` | `Edit` |
| `ExternalLink` | `ArrowExternalLink` |
| `Folder` | `FolderClosed` |
| `GitFork` | `CodeFork` |
| `Layers` | `Stacked` |
| `LayoutDashboard` | `Dashboard` |
| `ListChecks` | `ClipboardBulletList` |
| `Loader` | `Spinner` |
| `Loader2` | `Spinner` |
| `Lock` | `LockClosed` |
| `LogOut` | `ArrowSignOut` |
| `Maximize2` | `Fullscreen` |
| `MessageSquare` | `Comment` |
| `MoreHorizontal` | `MenuHorizontalDots` |
| `MoreVertical` | `MenuVerticalDots` |
| `Network` | `Flow` |
| `Pencil` | `Edit` |
| `Play` | `PlayFill` |
| `Puzzle` | `PuzzlePiece` |
| `Radio` | `Signal` |
| `Redo` | `ArrowRedo` |
| `RefreshCw` | `ArrowClockwise` |
| `RotateCcw` | `ArrowCounterClockwise` |
| `Settings` | `Gear` |
| `Shield` | `ShieldCheck` |
| `Sparkles` | `Stars` |
| `Star` | `StarOutline` |
| `SunMedium` | `Sun` |
| `Table2` | `Table` |
| `Trash2` | `Trash` |
| `TriangleAlert` | `WarningOutline` |
| `Undo` | `ArrowUndo` |
| `Upload` | `ArrowUpload` |
| `Wand2` | `MagicWand` |
| `Wrench` | `ToolWrench` |
| `XCircle` | `DismissCircleOutline` |
| `Zap` | `Lightning` |

- Anything else: `ls node_modules/@dataiku/vue-icons/src | grep -i <word>` and pick the closest
  glyph. Prefer the `Outline` variant for neutral UI and the `Fill` variant for status.
- Spinners: `<Spinner class="size-4 animate-spin" />`.
- When the last import is gone: `npm uninstall lucide-vue-next` (also `@lucide/vue`).

## Primitives

Delete `src/components/ui` and import the kit parts. The kit is shadcn-vue re-skinned by the
UX team, so props follow shadcn-vue conventions; browse
`solutions-store.infra.dataiku.io/storybook/@dataiku/ea-ui-kit/dev/` for the exact API.

| Local primitive | Replacement | Notes |
|---|---|---|
| `EaButton` (variant, size) | `Button` from the kit | variants `default` (was `primary`), `secondary`, `outline`, `ghost`, `destructive`, `link`; sizes `sm`, `default` (was `md`), `lg`, `icon` |
| `EaInput` | `Input` | `v-model` works the same |
| `EaSelect` (options array) | `SelectField` from bs-blueprint | same `options`, `modelValue`, `placeholder`; or the kit's `Select*` parts for custom items |
| `EaCheckbox` | `Checkbox` + `Label` | `v-model` is `modelValue: boolean` |
| `EaDialog` | `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, `DialogDescription`, `DialogFooter` | `v-model:open` |
| `EaConfirmDialog` | `AlertDialog*` parts | put the confirm handler on `AlertDialogAction` |
| `EaActionMenu` (items array) | `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem` | iterate your items in the template |
| `EaToaster` + a toast store | `Toaster` from the kit in the layout, `toast()` from `vue-sonner` | delete the store |
| `EaEmpty` (icon, title, description, slot) | `EmptyState` from bs-blueprint | same props and default slot |
| `SettingsSwitchItem` | the one from bs-blueprint | same props |
| `StatusBadge` (local) | the one from bs-blueprint | `status`: `success`, `warning`, `destructive`, `info`, `muted`; map app statuses with a small function |
| `Table`, `TableHeader`, `TableBody`, `TableRow`, `TableHead`, `TableCell` | the kit's `Table*` parts, inside a `ScrollArea` | sort state: `getNextSortState` and `sortRows` from bs-blueprint |
| `cn()`, `cva` in pages | remove | pages compose components and never restyle them |

Raw `<select>`, `<input>`, `<textarea>` with hand-written classes become the kit's
`NativeSelect`/`Select*`, `Input`, `Textarea`. Direct `reka-ui` imports in pages become the
kit part that wraps them (`Switch` instead of `SwitchRoot`/`SwitchThumb`).

## Shell

Replace the local `AppSidebar.vue`, `useAppMenu.ts`, `types/menu.ts` and `DefaultLayout.vue`
by `AppLayout` from bs-blueprint as the root route component:

```ts
{ path: '/', component: AppLayout, props: { appName, appSubtitle, appIcon, showAdministration }, children: [...] }
```

Route meta contract (`AppRouteMeta` from bs-blueprint): `title`, `icon` (a vue-icons glyph),
`menu: 'primary' | 'secondary' | 'tertiary' | 'new'`, `order`, `group` (the label a primary
route sits under; replaces hard-coded section labels), `menuLevel: 'flow'` for wizard steppers,
`hiddenInMenu`, `requiresAdmin`, `state(route)`. There is no `menuLabel`: keep titles short.
`menu: 'secondary'` routes show when `showAdministration` is true (keep your admin store, pass
the flag). The brand block takes `appName`, `appSubtitle`, `appIcon`; delete local brand markup.
Put `PageHeader` at the top of each view instead of hand-built `h-16 border-b` headers.

## API

bs-blueprint's `apiUrl()` routes through `dataiku.getWebAppBackendUrl()`, the DSS client API
that resolves the backend URL for the webapp in every embedding mode. A local version that
captures `window.location.pathname` works in the iframe case only. Replace the local
`apiUrl` export by `export { apiUrl } from 'bs-blueprint'` and keep your own `httpError`,
`apiFetch` or streaming helpers around it. Every `fetch` takes `apiUrl('/api/…')`.

## Arbitrary values

Pick the nearest scale step. Grid templates (`grid-cols-[1fr_auto]`) and `[var(--…)]` are
allowed; everything else is a scale step or a kit component prop.

| Arbitrary | Use |
|---|---|
| `w-[7px] h-[7px]` (status dot) | `size-2` |
| `text-[11px]`, `text-[13px]` | `text-2xs`, `text-sm` |
| `text-[22px]`, `text-[26px]`, `text-[40px]` | `text-xl`, `text-2xl`, `text-4xl` |
| `max-w-[520px]`, `max-w-[640px]` | `max-w-lg`, `max-w-2xl` |
| `h-[80vh]`, `max-h-[80vh]` | `h-[80vh]` is fine only inside a dialog; otherwise `h-full` in a flex column |
| `rounded-[4px]`, `rounded-[2px]` | `rounded-sm`, `rounded-xs` |
| `tracking-[0.12em]` | `tracking-widest` |
| `z-[60]` | `z-50` (the kit's floating layers already stack correctly) |
| `pl-[18px]` | `pl-4` or `pl-5` |
| `min-w-[var(--reka-select-trigger-width)]` | gone with the local select; the kit handles it |

## Custom classes

The lint knows Tailwind utilities and the kit's classes. A class of your own (`chat-markdown`,
`thinking-dot`) is reported as unknown. Two legitimate options:

- Keep it as a scoped `<style>` in the component that uses it (markdown containers, keyframes).
  Declare it once in `eslint.config.js`: `designConfig({ ignore: ['^chat-markdown$'] })`.
- Replace it by utilities when it is only a shorthand for a few of them.

Never re-introduce a global `@utility` or `@layer components` class that duplicates a token.

## Theme

`useThemeMode('light')` in `App.vue` keeps a light-only app light. When ready, expose
`const { isDark } = useThemeMode()` behind a `SettingsSwitchItem` in Settings; the kit's
`.dark` palette then applies with no per-component work, provided all colors are tokens.

## Done

- `npm run check` prints `check: ok`.
- `eslint-suppressions.json` and `bs-blueprint.baseline.json` are committed and shrinking; when
  both are empty, delete them.
- The old UI guidance in `AGENTS.md` (local primitives, lucide, tokens.css) is rewritten to
  match the managed block, and the "Don't remove" list no longer names deleted files.
