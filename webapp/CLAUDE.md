<!-- GENERATED FILE: edit the canonical harness source, then run python3 tools/sync_harness.py --write. -->

# Webapp overlay

This is a Vue 3 + FastAPI Dataiku DSS webapp. Keep a change narrow: one view, route, and, when
needed, one backend route/service. Do not read the complete `webapp/README.md` before classifying
the task.

## Route by task

- First setup or configuration: read `README.md` **Quick start** and `.env.example`. The six identity
  values in `app.env` must come from the user or read-only discovery; do not guess them. Show derived
  values and ask for confirmation before writing them.
- UI change: follow the bs-blueprint block below and the relevant component; the recipes for migrating
  older code are in `frontend/docs/` (managed by bs-blueprint). The app is mid-migration
  (`docs/demo/BLUEPRINT_ALIGNMENT_PLAN.md`): fix baselined drift in a file you touch, never add new.
- Frontend route or API call: inspect `frontend/src/router/` and use `apiUrl()`; a bare `/api/...`
  fetch does not reach the backend inside DSS.
- Backend/DSS data access: inspect `backend/dss_client.py` and the closest route/service. Use
  `get_project()` / `get_dataiku()` rather than environment branches or ad-hoc clients.
- Deployment or embedding: read `DEPLOYMENT.md` and the README's **DSS integration** and
  **non-obvious bits** sections. Deployment is a live DSS mutation and requires explicit user intent.

## Load-bearing rules

- Keep the DSS build contract: Vite `base: './'`, single-bundle output, Vue dedupe, and the
  `dkuWebapp()`, `optimizeDeps` and `assetsInlineLimit` wiring in `vite.config.ts`.
- Deploys are paused until the plan's Phase 2: `deploy.sh` refuses a plugin build. Do not remove that
  guard outside Phase 2.
- Use `dku` only for read-only discovery during development. Do not mutate a DSS project merely to
  develop or inspect this app.
- DSS libraries are text-only: icons are `@dataiku/vue-icons` components, never binary assets.

## Finish proportionately

For frontend work, `npm run check` from `frontend/` must print `check: ok`. Start local development or deploy only
when the requested work calls for it; run `make deploy` only with explicit user authorization.

<!-- bs-blueprint:begin -->
## UI and design system (managed by bs-blueprint 0.2.0)

Do not edit between the bs-blueprint markers: `npx bs-blueprint sync` rewrites this block.
**These rules override any older UI guidance elsewhere in this file** (local `Ea*` primitives,
`lucide-vue-next`, a local `tokens.css`, shadcn registries): the app is migrating to the team's
design system and older instructions describe the state before that.

### Where things come from
- **Components:** `@dataiku/ea-ui-kit` (`Button`, `Input`, `Select*`, `Dialog*`, `Table*`,
  `DropdownMenu*`, `Toaster`, and the rest). Never copy a component into the app.
- **Icons:** `@dataiku/vue-icons`, the DSS icon set. No other icon library.
- **Shell and helpers:** `bs-blueprint` (`AppLayout`, `PageHeader`, `EmptyState`, `StatusBadge`,
  `SelectField`, `SettingsSwitchItem`, `useThemeMode`, `useThemeColors`, `apiUrl`, sort helpers).
- **Theme:** `frontend/src/styles/kit.css` imports the kit theme. `frontend/DESIGN.md` is the design
  system as agents read it: tokens, layout, components, do's and don'ts.

### Rules
- Only token-backed utilities (`bg-card`, `text-muted-foreground`, `border-border`). No Tailwind
  palette classes, no `bg-white`/`text-white`, no hex or rgb anywhere, no inline style colors.
- No arbitrary values (`text-[13px]`, `w-[160px]`): use the nearest scale step. Grid templates
  and `[var(--…)]` are the two exceptions.
- Every API call goes through `apiUrl()` from `bs-blueprint`; bare `fetch('/api/…')` breaks in DSS.
- Navigation is built from route meta `{ title, icon, menu, order, group }` by `AppLayout`;
  never hand-build menus. Creation flows are `menu: 'new'` routes. The router uses
  `createWebHashHistory()`.
- Chart libraries read colors through `useThemeColors()`.

### When `npm run check` fails
Run it from `frontend/` (doctor, design lint, typecheck). Each doctor finding names the files, the
fix, and a section of `frontend/docs/design-migration.md` with the recipe. Work in the order the
doctor prints. Pre-existing drift is baselined in `frontend/eslint-suppressions.json` and
`frontend/bs-blueprint.baseline.json`: it does not block, it shrinks on its own when you fix a
file, and it must never be edited by hand or grown (`npx bs-blueprint baseline` is a deliberate
human decision). Fixing baselined drift in a file you touch is always welcome. Your own CSS
classes go in `eslint.config.js` (`designConfig({ ignore: ['^brand$'] })`) or a scoped `<style>`.

### Before declaring frontend work done
`cd frontend/. && npm run check` must print `check: ok`.
<!-- bs-blueprint:end -->
