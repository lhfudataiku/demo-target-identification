# bs-blueprint alignment plan

> **Lifecycle:** Decision · **Audience:** webapp implementers and technical reviewers · **Authority:**
> the agreed scope, migration sequence, acceptance criteria and decisions for realigning the
> Target Prioritizer webapp with the team's current `bs-blueprint` framework · **Update when:** a
> decision in §8 is taken, the scope changes, or a phase is accepted · **Generated dependencies:** none
> · **Excludes:** current deployed webapp behavior, which remains governed by
> [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md), [`../../webapp/README.md`](../../webapp/README.md) and
> [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) until each phase is implemented and verified.

**Status: IN PROGRESS — Phases 0–3 committed and deployed 2026-10-15; Phase 4 implemented locally, not yet committed or deployed.** All four decisions in §8 were
taken on the recommendations, and the direction is recorded as
[`DEC-DEMO-003`](../decisions/DECISION_REGISTER.md). Phases 5–8 have not started. The deploy pause that Phase 1 introduced ended with Phase 2. The measurements in §3 come from a trial run on a throwaway copy of `webapp/`. Starting
a phase, commit, push, DSS deployment and any live DSS change remain separate actions, each requiring
its own approval.

## 1. Summary

The webapp was seeded from `bs-blueprint` with `make copy` ([`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §3.1).
At that time the template carried its own primitives (`EaButton`, `EaSelect`, …), its own palette
(`styles/tokens.css`) and `lucide-vue-next` icons. The framework has since moved on. It now sits on the
engineering team's `@dataiku/ea-ui-kit`, `@dataiku/vue-icons` and a DSS Vite plugin, and it ships a
CLI (`adopt`, `check`, `sync`) that enforces the design rules. Our copy kept the old state, which is
why the app no longer looks like the team's other webapps.

The proposal is to adopt the framework through its own tooling, so that every deviation is listed,
recorded as a baseline and removed one phase at a time. Each phase must leave `npm run check` green.

Framework: <https://github.com/dataiku/bs-blueprint>. The `adopt` guide and the design-migration recipes
live in that repository's `docs/` folder. After adoption, the recipes are also copied into
`webapp/frontend/docs/`.

## 2. Goals and non-goals

**Goals**

- The app renders with the kit theme, kit primitives, DSS icons and the framework's app shell.
- `npm run check` (doctor + design lint + typecheck) passes, and both baseline files end empty.
- The DSS build and deploy follow the framework's model, so future framework updates arrive through
  `npx bs-blueprint sync` rather than by hand.
- Agent instructions and project documents describe the new state, with no contradictions left.

**Non-goals**

- No change to any act's content, claims, copy contract, backend routes or data contracts
  ([`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §3.3, §3.7, §6).
- No change to the Visual Graph Explorer handoff
  ([`../../archive/VISUAL_GRAPH_EXPLORER_INTEGRATION_SCOPE.md`](../../archive/VISUAL_GRAPH_EXPLORER_INTEGRATION_SCOPE.md), now implemented and current in [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §3.1.1).
- No dark mode. `useThemeMode('light')` keeps the app light; a theme switch is a later, separate change.
- No new features, and no DSS flow changes.

## 3. Baseline measured on a trial run (2026-10-14)

`adopt` was run on a copy of `webapp/` outside the repository, using framework commit `37e3823`
(package version `0.2.0`), which installed kit `0.0.8`.

- **Install:** clean. One blocking finding, the Vite wiring. Once that was added, `npm run check`
  printed `check: ok` and `npm run build` succeeded. The build output was `dist/dss-main.js` plus
  `assets/index.js` (1.26 MB) and `assets/index.css` (0.70 MB, which includes the inlined kit fonts).
- **Recorded drift** (the baseline, which does not block):

| Drift | Size | Framework recipe |
|---|---|---|
| App-owned palette: `styles/tokens.css` and the `@theme inline` bridge in `style.css` | 2 files | Tokens |
| `lucide-vue-next` imports | 27 files, 73 distinct icons: 17 same name, 25 known renames, 31 to choose by hand | Icons |
| Local primitives in `src/components/ui` | 15 files | Primitives |
| Local shell and helpers: `AppSidebar.vue`, `useAppMenu.ts`, `types/menu.ts`, `utils/api.ts`, `utils/sorting.ts` | 5 files | Shell, API |
| Router uses `createWebHistory`; `App.vue` has no `useThemeMode` | 2 files | Setup |
| Libraries the framework replaces: `lucide-vue-next`, `tw-animate-css` | 2 packages | Primitives |
| Design lint, across 37 files | 184 restricted classes, 49 restricted imports, 7 unknown classes | Arbitrary values, custom classes |

12 of the 27 Lucide files belong to the template's optional blocks (wizard, charts, tickets, flow,
documents, chat). All of those blocks are disabled in `webapp/app.env`.

## 4. What changes beyond styling

### 4.1 The visual identity changes

The app is deliberately themed to the Dataiku **brand** palette ([`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md),
"Design system"): mint `#3EDAB2` primary, a dark-green sidebar, off-white background, and Spectral /
Roboto / DM Mono fonts. The kit carries the DSS **product** theme: indigo `#3445cb` primary, white
background, and Source Sans Pro. Removing `tokens.css` (Phase 3) therefore changes the look of every
act, not just its details. This is the point of the alignment; D1 (§8) accepts the product theme
throughout, with no brand-palette override.

### 4.2 The chart colours change meaning

The views and `components/act/*` charts read `var(--chart-1..5)`. The kit defines those slots
differently:

| Slot | Ours today | Kit (light) |
|---|---|---|
| `--chart-1` | dark green `#06312E` | orange `hsl(22 84% 60%)` |
| `--chart-2` | mint `#3EDAB2` | teal `hsl(172 46% 48%)` |
| `--chart-3` | blue `#7092F2` | navy `hsl(221 47% 31%)` |
| `--chart-4` | orange `#EDAB4F` | lime `hsl(72 77% 75%)` |
| `--chart-5` | blue-grey `#A8BCDD` | yellow `hsl(56 77% 69%)` |

Some series carry meaning through their colour. For example, Act 2 colours provenance drivers
`--chart-2` and other drivers `--chart-3`. The kit's slots 4 and 5 are pale on white. Each chart needs
a deliberate slot choice and a visual check. D2 (§8) keeps the meanings fixed: Phase 3 starts by
writing one table that maps each meaning-bearing series (for example "provenance driver", "model",
"baseline") to a kit slot, and every chart reads its colour from that table. The framework's rule is
that charts read colours through `useThemeColors()`, not through `'var(--chart-n)'` strings.

### 4.3 The deployment model changes

Today DSS loads `dss_webapp/html.html` and `js.js`, and those files open the FastAPI backend in a
full-page iframe. The framework's Vite plugin drops the iframe. The webapp's `html` and `js` parameters
become the built `dist/index.html` and `dist/dss-main.js`, which load the bundle from the backend's
`/assets` route through `dataiku.getWebAppBackendUrl()`. The consequences:

- `dss_webapp/deploy.sh` and `backend/app.py` take the framework starter's versions of the two
  relevant parts. As a side benefit, the starter's deploy uses `dku library sync --delete`, which
  removes retired library files that we currently delete by hand
  ([`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) §4).
- The router moves to `createWebHashHistory()`. Act URLs change from `/shortlist` to `#/shortlist`,
  so any saved link breaks.
- `utils/api.ts` re-exports `apiUrl` from the framework, and `utils/embeddedBase.ts` is deleted.
- Only a real DSS deploy can verify this phase. It is the one step with live risk.

### 4.4 Agent instructions would lose the framework's rules

`adopt` writes a managed rules block into `webapp/AGENTS.md` and a Claude Code hook into
`webapp/.claude/settings.json`. `webapp/AGENTS.md` and `webapp/CLAUDE.md` are generated from
[`../../harness/WEBAPP_OVERLAY.md`](../../harness/WEBAPP_OVERLAY.md) by `tools/sync_harness.py`, so the
next harness sync would silently delete the block. The overlay also still says "use local `Ea*`
primitives" and "use Lucide components". Phase 1 must:

- teach `sync_harness.py` to carry the `bs-blueprint:begin`/`end` block into both generated files; and
- rewrite those overlay lines in the same change, so that the two sets of instructions never disagree.

### 4.5 Version pinning and tooling

- The framework has no release tags. `adopt` writes the unpinned `github:dataiku/bs-blueprint`, so pin
  the adopted commit until a tag exists. Phase 1 pinned `8d7741c`, three commits after the trial's
  `37e3823`; those three commits change only the framework's example app, not the package.
- The lint toolchain supports Node `^20.19`, `^22.13` or `>=24`. Node 23 works but warns, so use the
  current LTS.
- New tracked `.json` and `.js` files mean regenerating the code index (`tools/build_recipe_index.py`).
- CI does not install the frontend today. Adding `npm run check` to CI would need a GitHub Packages
  `read:packages` secret. That is optional and out of scope here.

## 5. Phases

### Execution governance

- One phase, or one file group within a phase, per commit. Run `npm run check`, `npm run typecheck`
  and a local `make dev` review of all four acts before each commit is proposed.
- No commit or push without approval of a change summary. No DSS deploy without explicit approval
  naming the target project.
- Rollback for every phase is reverting its commits. Phase 2 also needs a redeploy of the previous
  build.

### Phase 0 — prune the disabled template blocks *(D3)*

Delete the wizard, charts, tickets, flow, documents and chatbot blocks: their views, components,
stores, mock data, backend routes and `ENABLE_*` flags. **Accept:** the four acts, Settings and Admin
behave as before, and the typecheck passes. This removes 12 of the 27 Lucide files before migration starts.

> **Implemented and committed 2026-10-15.** Beyond the six blocks, the phase also removed
> two pieces of unrouted template scaffolding (the Agents registry and the Example dataset preview,
> with their always-on `/api/agents` and `/api/example` routes), the chatbot's tool-permission section
> in Settings, and the packages only the blocks used (`@vue-flow/core`, `marked`, `sse-starlette`,
> `python-multipart`, `langchain-core`, `pymupdf`). The documents that this phase made wrong were
> corrected in the same change, ahead of Phase 8: the webapp README, the harness webapp overlay, and
> [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §3.4 and §8. Verified locally: typecheck and build pass, the
> backend registers only the act, settings and system routes, every act renders live data, and an old
> block URL falls through to Act 1. Two leftovers are deliberately out of scope: the Settings LLM
> picker, which no feature uses any more, and the Admin page, whose toggle now controls an empty
> section. Phase 6 (shell) decides both.

### Phase 1 — adopt

Run `adopt` from `webapp/frontend/`, pin the commit, add the Vite wiring (`dkuWebapp()`,
`optimizeDeps`, `build.assetsInlineLimit`), carry the agents block through the harness (§4.4), and
commit `eslint-suppressions.json` and `bs-blueprint.baseline.json`. **Accept:** `check: ok`, the
harness check in `tools/check_indexes.sh` passes, and the app looks unchanged, because `tokens.css`
still overrides the kit.

> **Implemented and committed 2026-10-15.** `npm run check` prints `check: ok` (0
> blocking, 7 baselined); the typecheck and build pass. What differed from the plan:
>
> - **Deploys are paused until Phase 2.** `dkuWebapp()` runs on every build and always reduces
>   `dist/index.html` to body markup, which the current iframe deploy cannot serve: it would publish a
>   blank app. `deploy.sh` therefore refuses any build carrying `dist/dss-main.js`, with a message
>   naming Phase 2. Phase 2 removes the guard when it replaces the deploy.
> - **The rules block reaches Claude Code too.** `adopt` writes the block into `webapp/AGENTS.md`
>   only. `tools/sync_harness.py` now reads it back from there and appends it to both generated webapp
>   entry files, so a harness sync keeps it and Claude Code (which reads `CLAUDE.md`) sees it. The
>   overlay's `Ea*`, Lucide and `tokens.css` guidance is rewritten to agree with the block.
> - **The hook is installed twice.** The doctor requires it in `webapp/.claude/settings.json`, but
>   Claude Code loads project settings only from the session root, so the repository's root
>   `.claude/settings.json` carries the same hook, pointed at `webapp/frontend`. Worth raising upstream.
> - **Managed documents.** `webapp/frontend/DESIGN.md` and `webapp/frontend/docs/design-migration.md`
>   are registered in `tools/index_manifest.json` as excluded from claims. `tools/check_links.py`
>   skips only their mention check: they name files in the framework's repository and design-token
>   references that look like Markdown file names, and `npx bs-blueprint sync` would overwrite any local correction.
> - The new UI rules point agents at the framework's `apiUrl()`, which resolves backend URLs only in
>   the Phase 2 deploy model; with deploys paused, nothing using it can reach DSS before then.

### Phase 2 — deployment model *(D4; the only live step)*

Apply §4.3, then deploy in two steps (D4): first to a separate test webapp, then, once that is
accepted, to the live `DEMO_TARGET_IDENTIFICATION` webapp. The test deploy must not share anything
with the live app:

- **A distinct `LIB_NS` and `APP_PREFIX`.** `deploy.sh` uploads to `python/<LIB_NS>/` in the project
  library, and the live webapp imports from there. Reusing the live namespace would replace the live
  app's code during the "test".
- **No write-back into the committed `app.env`.** When `deploy.sh` creates a webapp it writes the new
  id over `WEBAPP_ID` in `app.env`. Run the test deploy from an uncommitted override (a local `.env`,
  or the script's environment variables), and check that `app.env` is unchanged afterwards.

**Accept:** the test webapp loads every act inside DSS, every API call resolves, a hard refresh on each
act works, and the checks in [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) §4 and §4.1 pass
against the test namespace. The live deploy then repeats those checks, and the test webapp and its
library folder are removed afterwards, with approval.

> **Deployed live and committed 2026-10-15.** `deploy.sh` now follows the framework's
> starter: it mirrors `backend/` and `frontend/dist/` with `dku library sync --delete` and sets the
> webapp's html and js from the build. A new `WRITE_BACK_WEBAPP_ID=0` switch keeps a throwaway
> deploy from rewriting `app.env`. The router uses hash history, `apiUrl` comes from the framework,
> and `embeddedBase.ts`, `html.html` and `js.js` are deleted. The backend already served `/assets`
> and needed no change.
>
> - **Test deploy:** webapp `t75Qsqw` in library folder `target_prioritizer_bp_test`; the shared code
>   env needed no change and `app.env` stayed byte-identical. Accepted by the user in the browser.
> - **Live deploy:** `OlmPX9a`, run by the user (the agent's permission rules blocked it). The
>   mirror deleted the 14 library files Phase 0 had retired, exactly as a dry run predicted.
>   Definition, logs and library verified from DSS.
> - **Test webapp removed 2026-10-15** by the user: the webapp in the DSS UI (`dku` has no webapp
>   delete), and its library folder with `dku library delete --recursive` (19 files). The project's
>   webapps are back to the live Target Prioritizer and the Graph Explorer.
> - The webapp README and `webapp/DEPLOYMENT.md` were corrected in the same change, ahead of
>   Phase 8, because they described the retired iframe model.

### Phase 3 — tokens *(D1, D2)*

Delete `styles/tokens.css` and the `@theme inline` bridge. Map app-only tokens to kit tokens. Write the
series-to-slot table (§4.2), review it, then move charts to `useThemeColors()` through that table. **Accept:** before/after screenshots of
every act are reviewed, and no chart series changes meaning without that being noted.

**Series-to-slot table — approved 2026-10-15.** Every meaning-bearing colour is read from
`frontend/src/utils/seriesColours.ts`, which holds exactly this table:

| Meaning | Where it appears | Before | Kit token |
|---|---|---|---|
| Measured: the model or pipeline result | precision, AUPRC, corroborated interactions, candidate pool, node types, AUC histogram, personas, eligible band | mint `--chart-2` | `chart-2` (teal) |
| Contrast: the series compared against it | other drivers, relations, shared terms, trustworthy intervals, overlap matrix, positive SHAP, score bar | blue `--chart-3` | `chart-3` (navy) |
| Highlight: the exception to look at | single-source interactions, genes distinct to one term | dark green `--chart-1` | `chart-1` (orange) |
| Approved drug | Act 4 badge | blue tint | `success` |
| Trial drug | Act 4 badge | orange tint | `warning` |
| Baseline or chance | base rate, grouped sources, duplicate admissions | `--muted-foreground` | `muted-foreground` |
| Untrustworthy or negative | failed-trust interval, negative SHAP | `--destructive` | `destructive` |
| Categories with no fixed meaning | Sankey routes and splits, label-evidence donut | `--chart-1…5` | `chart-1…5` |

Two further decisions, taken with it: card accent stripes, which were decorative, all use the kit
`primary`; and act headlines drop the Spectral serif for the kit's sans (the Google Fonts link goes,
and code and number text uses the system monospace). Canvas charts resolve every colour through the
framework's `themeColor()`, because ECharts cannot parse the kit's space-separated `hsl()` values.

> **Implemented, committed and deployed 2026-10-15.** `styles/tokens.css` and the `@theme inline`
> bridge are deleted, the Google Fonts link is gone, and every chart reads the table above; the
> doctor's app-palette finding closed on its own. Verified locally on all four acts against the
> table. What surfaced on the way:
>
> - **White text on faint tints.** The old palette's `primary-foreground` was dark green (text on a
>   light mint); the kit's is white. Eight places put it on a `bg-primary/NN` tint and became
>   unreadable; they now use `text-primary`, the kit's chip pattern.
> - **The interim sidebar.** The local sidebar painted the app name with `text-sidebar-primary`
>   (near-white in the kit) and hovered with `bg-sidebar-accent` (solid indigo) without switching
>   the text. It now follows the framework shell's pairings until Phase 6 replaces it.
> - **Axis labels never had their colour.** Canvas charts were given `'var(--border)'` and
>   `'var(--muted-foreground)'`, which ECharts cannot resolve, and named the DM Mono font; both now
>   resolve properly.
> - The Explorer card's accent and all eleven act-card accents now default to the kit primary.
> - DEPLOYMENT.md "Design system", the webapp README and [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §3.5
>   were corrected in the same change, ahead of Phase 8.

### Phase 4 — icons

Switch the remaining Lucide imports to `@dataiku/vue-icons`, using the framework's rename table, and
choose the hand-picked glyphs, recording each choice in the commit message. Uninstall `lucide-vue-next`.
**Accept:** the doctor no longer reports icon drift.

> **Implemented 2026-10-15, awaiting commit approval.** Twelve files moved to `@dataiku/vue-icons`:
> 10 glyphs kept their name, 9 took the framework's renames (for example `Database` → `Dataset`,
> `Network` → `Flow`, `Loader2` → `Spinner`), and the 14 with no counterpart took these picks,
> agreed with the user:
>
> | Lucide | Where | DSS icon |
> |---|---|---|
> | `BookOpen` | Glossary | `Book` |
> | `Gauge` | Act 2 sidebar item, "AUC, disease by disease" | `Odometer` |
> | `ListFilter` | Act 4 sidebar item, "The ranked list" | `ListNumbered` |
> | `Split` | "How the candidate pool is built" | `ArrowSplit` |
> | `Crosshair` | "What drives the score" | `ChartHorizontalBar` |
> | `ListTree` | "The model's inputs" | `ListBulleted` |
> | `GitBranch` | "How things connect" | `MergeBranch` |
> | `GitCompare` | "Subtype overlap" | `JoinInner` |
> | `Grid3x3` | "Gene coverage across the family" | `ChartHeatmap` |
> | `Ruler` | "When AUC stops working" | `WarningOutline` |
> | `Users` | "Shared vs. subtype-specific" | `UserGroup` |
> | `Presentation` | presenter-note line on every card | `Comment` |
> | `MoveLeft` | sidebar back link | `ArrowLeft` |
> | `LucideIcon` (type) | `ActCard`'s icon prop | Vue's `Component` |
>
> `lucide-vue-next` is uninstalled, and so is the direct `tw-animate-css` dependency, which the kit
> already declares and imports itself; both doctor findings (icons, forbidden dependencies) closed.
> Verified locally: every sidebar item and act card renders its icon, and the console is clean.

### Phase 5 — primitives

Replace `EaButton`, `EaSelect`, `EaEmpty`, `SettingsSwitchItem`, and the `table/` and `scroll-area/`
sets with kit parts or framework composites, then delete `src/components/ui`. **Accept:** the
Shortlist table keeps sorting, search and filters, and `ui-dir` drift is gone.

### Phase 6 — shell

`AppLayout` becomes the root route component, with `PageHeader` at the top of each act. Delete
`AppSidebar.vue`, `DefaultLayout.vue`, `useAppMenu.ts` and `types/menu.ts`. Use sorting from the
framework. **Accept:** the sidebar is still built from route `meta`, and the act order is unchanged.

### Phase 7 — lint cleanup

Work through the remaining restricted and unknown classes until `eslint-suppressions.json` and
`bs-blueprint.baseline.json` are empty, then delete them. Classes the app keeps on purpose (such as
Vue Flow's) are declared in `eslint.config.js`. **Accept:** `check: ok` with no baseline files.

### Phase 8 — documentation

Apply §6, regenerate the indexes and run `./tools/check_indexes.sh`. **Accept:** no document describes
the old stack as current.

## 6. Documentation impact

| Document | Sections | Change |
|---|---|---|
| [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) | header "What the demo surface is"; §3.1; §3.5; §3.6; §8 | Stack and seeding (adopted framework, not `make copy`); conventions (kit primitives, DSS icons, `useThemeColors()`, `npm run check`); build/deploy; drop the references to the template's optional blocks once Phase 0 lands |
| [`../../webapp/README.md`](../../webapp/README.md) | title and intro; frontend, DSS integration and non-obvious-bits sections; "Optional building blocks"; "Single-bundle Vite output" | It still presents itself as the generic starter; rewrite it as this app's README on the framework, and remove the optional blocks |
| [`../../webapp/DEPLOYMENT.md`](../../webapp/DEPLOYMENT.md) | header (iframe); "Where things live on DSS"; §4 verification; "Design system"; library pruning | New deploy model, kit theme replacing the brand palette, and `sync --delete` replacing manual pruning |
| [`../../harness/WEBAPP_OVERLAY.md`](../../harness/WEBAPP_OVERLAY.md) | "Route by task", "Load-bearing rules" | Remove `Ea*`, Lucide and `tokens.css` guidance; point at `npm run check`; regenerate the copies with `tools/sync_harness.py --write` |
| [`../README.md`](../README.md) | Planning | Move this plan to its approved, implemented or retired state |

[`../decisions/DECISION_REGISTER.md`](../decisions/DECISION_REGISTER.md): `DEC-DEMO-003` records the
direction (adopt the framework and its product theme). When Phase 8 lands, update its evidence to point
at the rewritten [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) sections.

## 7. Risks

| Risk | Mitigation |
|---|---|
| The deployed app fails to load after Phase 2 | Test deploy first (D4); keep the previous build ready to redeploy |
| A chart silently changes meaning in Phase 3 | Every series' slot is chosen deliberately (D2) and reviewed against screenshots |
| A kit primitive lacks a behaviour we rely on (such as Shortlist table sorting or select widths) | Use the framework composites (`SelectField`, sort helpers); note any gap in the framework's upstream list rather than copying a primitive |
| The framework changes underneath us | Pinned commit; update only with `npx bs-blueprint sync` plus `npm run check` |
| Bundle size grows with the inlined fonts | Measured in §3; acceptable for an internal demo, and checked again after Phase 7 |

## 8. Decisions

All four were taken on 2026-10-14, each on the recommended option.

| ID | Decision | Options considered | Taken | Why |
|---|---|---|---|---|
| D1 | Visual identity | (a) the kit's product theme throughout; (b) keep the brand palette as a deliberate override | **(a)** | An override is exactly the drift the framework flags, and it would keep the app looking different from the team's other webapps |
| D2 | Chart colours | (a) the kit's slots as they fall; (b) fixed meanings mapped to chosen kit slots | **(b)** | Several acts encode meaning in colour |
| D3 | Template optional blocks | (a) delete them in Phase 0; (b) keep them disabled | **(a)** | [`WEBAPP_DESIGN.md`](WEBAPP_DESIGN.md) §8 already enables none, and they hold 12 of the 27 icon files |
| D4 | Phase 2 deploy target | (a) the live `DEMO_TARGET_IDENTIFICATION` webapp; (b) a separate test webapp | **(b), then (a)** | Phase 2 is the only step that can break the deployed demo; the test deploy is isolated as Phase 2 describes |
