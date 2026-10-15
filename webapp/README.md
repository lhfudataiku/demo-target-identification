# Blueprint — Dataiku DSS Webapp Starter

> **Lifecycle:** Canonical · **Audience:** contributors configuring or extending the webapp ·
> **Authority:** architecture, setup, feature-block and local-development reference · **Update when:**
> those contracts or supported workflows change · **Generated dependencies:** current frontend,
> backend and configuration structure · **Excludes:** project analytical claims and deployment history.

A copy-to-start template for building on-brand webapps on Dataiku DSS.
If you know Python and data but have never shipped a web frontend, this gets you there:
the plumbing — local dev, DSS deployment, sidebar, settings, data access — is already wired up.
You fill in your domain logic.

**Stack:** Vue 3 (frontend) · FastAPI (backend) · Tailwind + the team's design system (`@dataiku/ea-ui-kit` and `bs-blueprint`) · `uv` / `npm` (package managers).

---

## Quick start

### Prerequisites

| Tool | What it is | Install |
|------|-----------|---------|
| [`uv`](https://docs.astral.sh/uv/) | Python package manager (replaces `pip`/`venv`) | `curl -Lsf https://astral.sh/uv/install.sh \| sh` |
| [`Node.js`](https://nodejs.org/) | JavaScript runtime; ships with `npm`, the frontend package manager | [nodejs.org](https://nodejs.org/) or `brew install node` |
| `dku` CLI | Dataiku command-line tool for deploying | Install globally so it's on your PATH, then authenticate with `dku auth` |
| `~/.dataiku/config.json` | Your local DSS credentials | |

### Get started

Clone the repo, set the app identity in `app.env`, start the app:

```bash
git clone git@github.com:dataiku/bs-blueprint.git my-app
cd my-app
# edit app.env: LIB_NS, APP_PREFIX, VITE_APP_NAME, ENV_NAME, DKU_INSTANCE, PROJECT_KEY
make dev                          # → open http://localhost:5173
```

`app.env` is the single source of truth for the app's identity and DSS target — that's
the whole setup, no code edits. `make dev` installs deps on first run and **blocks
(exits non-zero) until those six values are set**, listing any that are missing. The
frontend hot-reloads on save; the backend reloads on Python file saves. Every act reads
live DSS datasets, so export DSS credentials first (see `DEPLOYMENT.md`).

> **Setting up with an AI coding agent?** Don't let it guess the identity/target values.
> The agent should discover the real options and ask you to confirm: derive `LIB_NS` /
> `APP_PREFIX` / `VITE_APP_NAME` from an app name you give it, list your DSS instances
> (`dku auth list`) for `DKU_INSTANCE`, and run `dku project list` to pick
> `PROJECT_KEY`. It writes them to `app.env` only after you confirm, then runs `make dev`.
> (See `AGENTS.md` for the exact agent instructions.)

```bash
make stop     # kill both servers
make status   # see which ports are running
make logs     # tail the log files in .run/logs/
make deps     # force-reinstall both Python and Node deps
```

### Deploy to DSS

Two one-time steps, then one command:

**One-time setup:**

1. The wizard sets `PROJECT_KEY` and `ENV_NAME` for you; to change them later, edit `app.env`:
   ```bash
   PROJECT_KEY=MY_PROJECT   # your DSS project key (uppercase, created automatically if missing)
   ENV_NAME=my-code-env     # a Python ≥3.11 code env on the DSS instance
   ```
   Leave `WEBAPP_ID=` empty — `make deploy` will create the webapp and write its ID back.

2. Make sure the code env is already created on DSS (DSS UI → Administration → Code envs),
   with at least `fastapi` and `uvicorn` installed.

**Deploy:**

```bash
make deploy
```

This builds the frontend, creates the DSS project and webapp if they don't exist yet,
uploads all code to the project library, patches the webapp definition, and restarts the
backend. The new webapp's ID is written back to `app.env` automatically so subsequent
deploys reuse the same webapp. Open the webapp in DSS — it should show your app.

---

## What even is a Dataiku webapp?

*This section is for readers who haven't built a DSS webapp before. Skip if you have.*

A DSS webapp is a small website that lives **inside a DSS project** and has direct access
to that project's datasets, models, LLMs, and variables. Users open it from the DSS
interface, which renders the webapp's HTML and JavaScript inside the project page.

### Two halves

Every webapp in this template has two parts that run in different places:

- **Frontend** — the HTML/CSS/JavaScript that runs in the **user's browser**. This is
  what the user sees and clicks. It can't read DSS data directly — it has to ask the backend.

- **Backend** — a Python process that runs **on the DSS server** (or on your laptop in
  local dev). It has access to all the Dataiku Python APIs: datasets, LLMs, project
  variables, everything. It exposes an HTTP API (`/api/...`) that the frontend calls.

### Two run modes

The same codebase runs in two different configurations:

```
LOCAL DEV
─────────────────────────────────────────────────────────
  Browser                     Your laptop
  ┌────────────┐    :5173      ┌─────────────────┐
  │  Vue SPA   │◄─────────────│  Vite dev server│  npm run dev
  │            │              └─────────────────┘
  │  /api/...  │─────────────►┌─────────────────┐
  └────────────┘   :5000      │  FastAPI         │  uv run uvicorn
                              │  + dss_client    │──► ~/.dataiku/config.json
                              └─────────────────┘
  Vite proxies /api to FastAPI. Hot reload on every save.
  No deploy needed to iterate.


IN DSS (after make deploy)
─────────────────────────────────────────────────────────
  Browser                     DSS server
  ┌─────────────────────────────────────────────────────┐
  │  DSS UI renders the webapp's html + js parameters   │
  │  ┌─────────────────────────────────────────────┐    │
  │  │  dss-main.js ── loads assets/index.js|css ──┼──► FastAPI /assets
  │  │  Vue SPA (#/evidence, #/shortlist, …)       │    │
  │  │  apiUrl('/api/…') ──────────────────────────┼──► FastAPI /api
  │  └─────────────────────────────────────────────┘    │   + dataiku Python API
  └─────────────────────────────────────────────────────┘
  FastAPI serves the built bundle from /assets AND answers
  /api calls. dataiku.getWebAppBackendUrl() (injected by
  DSS) turns both paths into the backend's real URL.
```

The key insight: **the exact same Python code** handles both modes. `dss_client.get_project()`
detects which mode it's in and connects to DSS accordingly.

---

## Architecture in detail

### Repository layout

```
my-app/
│
├── app.env              ← Single source of truth: app name, project key, webapp ID,
│                          code env, ports. Edit here before deploying. Never commit .env.
├── .env.example         ← Template for local overrides (DSS URL/key if not using dku CLI)
├── Makefile             ← dev / stop / status / logs / deploy / install
├── pyproject.toml       ← Python dependencies (FastAPI, dataiku-api-client, pandas…)
│
├── backend/             ← Python. Runs on the server (locally: your laptop; in DSS: DSS server)
│   ├── app.py           ← The wiring: CORS, register all route modules, mount static files in DSS
│   ├── config.py        ← Reads APP_PREFIX from env → derives all other config variables
│   ├── dss_client.py    ← The dual-mode connector: dataiku.api_client() in DSS, dataikuapi locally
│   ├── routes/
│   │   ├── system.py    ← /api/system/health
│   │   └── evidence.py, calibration.py, families.py, candidates.py ← one route file per act
│   └── services/
│       └── dataset_cache.py ← Reads and caches the act datasets
│
├── dss_webapp/          ← The thin DSS glue layer (not application logic)
│   ├── deploy.sh        ← Mirrors backend + built frontend to DSS, patches webapp definition
│   ├── backend.py       ← DSS-injected entry point: sets env vars, calls configure(app)
│   └── css.css          ← body { margin: 0 } — hides the outer page chrome
│
└── frontend/            ← TypeScript/Vue. Runs in the user's browser.
    ├── package.json     ← Node dependencies (Vue, Vite, Tailwind, the kit, bs-blueprint…)
    ├── vite.config.ts   ← Build tool config: /api proxy, base path, single-bundle output
    ├── tsconfig*.json   ← TypeScript config
    └── src/
        ├── main.ts          ← App entry point: create Vue app, add Pinia + router, mount
        ├── App.vue          ← Root component: applies the kit theme, then <router-view />
        ├── styles/kit.css   ← the @dataiku/ea-ui-kit theme, wired by bs-blueprint
        ├── style.css        ← imports kit.css, plus a few app-specific base rules
        ├── utils/seriesColours.ts ← the one table that maps chart meanings to kit colours
        ├── config.ts        ← App name + icon — the two things to change when you copy this
        ├── utils/api.ts     ← re-exports apiUrl() from bs-blueprint (see below)
        ├── router/index.ts  ← All pages live here; sidebar builds itself from route metadata
        ├── layouts/
        │   └── DefaultLayout.vue  ← bs-blueprint's AppLayout + the Glossary button and drawer
        ├── stores/          ← glossary drawer state, presenter notes (per browser)

        └── views/
            ├── EvidenceView.vue, CalibrationView.vue, TherapeuticAreaView.vue,
            │   ShortlistView.vue ← the four acts
            └── SettingsView.vue  ← per-browser display settings (presenter notes)
```

---

### The frontend, explained

The frontend is a **SPA** (Single-Page Application): one HTML file is loaded once, and
all navigation happens in JavaScript without full page reloads. We use **Vue 3** as the
framework — roughly similar to React or Angular if you've heard of those.

**Styling** comes from **Tailwind CSS** (utility classes like `text-sm`, `flex`, `gap-4`)
backed by the **`@dataiku/ea-ui-kit` theme** (imported through `src/styles/kit.css`), so
utilities like `bg-primary` and `text-muted-foreground` make the app look like a Dataiku
product. Chart colours come from `src/utils/seriesColours.ts`, which maps each meaning to a
kit token. Form controls, tables and buttons are the kit's own parts (`Button`, `Input`,
`Checkbox`, `NativeSelect`, `Table*`), and the few composites the kit lacks come from
bs-blueprint (`SelectField`, `EmptyState`, `SettingsSwitchItem`). The app copies none of them.

**Routing** — the sidebar is not manually built. Add a page like this in `router/index.ts`:

```typescript
{
  path: 'my-feature',
  name: 'myFeature',
  component: MyView,
  meta: { title: 'My Feature', icon: Dataset, menu: 'primary', order: 2 },
}
```

The `meta` object is all bs-blueprint's `AppLayout` needs: the sidebar item appears
automatically. Settings lives at the bottom (`menu: 'tertiary'`). Each view starts with
bs-blueprint's `PageHeader` and scrolls in its own body (`<div class="min-h-0 flex-1 overflow-auto">`),
because the shell does not scroll the content pane for you.

**State** is managed with **Pinia** (Vue's official state library, simpler than Redux).
Two small stores remain: `glossary.ts` (the drawer's open state and the term to scroll to) and
`presenter.ts` (whether presenter notes show, kept in the browser rather than the DSS project).

**API calls** always go through `apiUrl()` from `utils/api.ts`. See the non-obvious bits
section below for why.

---

### The backend, explained

The backend is a **FastAPI** application — a modern Python web framework, faster to write
than Flask and with automatic API documentation.

The central function is `configure(app)` in `backend/app.py`. It registers all the routes
and middleware onto a FastAPI app instance. In local dev, the module also creates its own
`app = FastAPI()` and calls `configure(app)`, so `uvicorn backend.app:app` works. In DSS,
the `dss_webapp/backend.py` entry point sets some environment variables and then calls
`configure(app)` on the DSS-injected `app` — it never creates its own instance.

The **dual-mode connector** in `backend/dss_client.py` is what makes the same code work
in both environments:

```python
def get_project():
    if config.DSS_MODE:                          # flag set by dss_webapp/backend.py in DSS
        import dataiku
        return dataiku.api_client().get_default_project()
    # local dev: read from ~/.dataiku/config.json
    return dataikuapi.DSSClient(...).get_project(config.PROJECT_KEY)
```

Every route that needs data calls `get_project()` — it never needs to know which mode it's in.
Detection is the explicit `DSS_MODE` flag, **not** `import dataiku` success: local dev installs
the real `dataiku` package, so that import succeeds locally too and would otherwise look like
in-DSS.

**Local dev installs `dataiku-internal-client` for real row previews.** The public
`dataiku-api-client` lists datasets and reads schemas, but its streaming reader differs from the
in-DSS one, so dataset *row* previews degrade to schema-only locally. The blueprint pulls in the
real internal `dataiku` (`dataiku-internal-client`, a required dev dependency) so `get_dataiku()`
in `dss_client.py` can run `dataiku.Dataset(...).get_dataframe()` against the remote instance —
identical to in-DSS. `dataikuapi` stays for the control-plane. See **Architecture decisions →
"Local dataset previews via `dataiku-internal-client`"** for the full rationale and trade-offs.

**Routes vs services** — routes handle HTTP (parse params, return JSON, raise HTTP errors).
Services contain the actual logic and Dataiku API calls. The act routes read their datasets
through `services/dataset_cache.py`.

---

### The DSS integration, explained

**Code env** — DSS runs Python in isolated environments called *code envs*. Your webapp
must have one specified (set `ENV_NAME` in `app.env`). It needs at least `fastapi`
and `uvicorn` installed. Python ≥3.11 is recommended (see tech notes).

**Project library** — each DSS project has a Python package directory (`python/`) that's
on `sys.path` for anything running in that project. `make deploy` uploads the backend and
the built frontend into `python/<LIB_NS>/` so DSS can import your code.

**Project variables** — a simple key-value store per DSS project, writable from Python
(`project.get_variables()` / `project.set_variables()`). The flow uses them (for example the demo
panel); this app only reads data and stores no settings of its own in DSS.

**What `make deploy` does, step by step:**

```
1. cd frontend && npm run build
     → Compiles Vue/TS → frontend/dist/: assets/index.js|css, plus dss-main.js and a
       body-only index.html emitted by @dataiku/vite-plugin-dku-webapp

2. dku project create --if-not-exists
     → Creates the DSS project if it doesn't exist yet (idempotent).

3. dku webapp create  (only when WEBAPP_ID is empty in app.env)
     → Creates a new STANDARD webapp; writes the generated ID back to app.env.

4. dku library sync --delete  (backend/ and frontend/dist/)
     → Mirrors to python/<LIB_NS>/backend/ and python/<LIB_NS>/frontend_dist/,
       deleting remote files that no longer exist locally

5. dku webapp get-definition → patch JSON → dku webapp set-definition
     → Sets backendFramework=FASTAPI, the code env, html = dist/index.html,
       js = dist/dss-main.js, css = dss_webapp/css.css

6. dku webapp stop + start
     → DSS imports <LIB_NS>.backend.app and calls configure(app) on its FastAPI instance
     → `dku webapp start` blocks until the backend is up or has crashed; on a crash it
       prints the reason and log tail and the script exits non-zero.
```

---

### The non-obvious bits, explained

These are the parts that look like magic until you know why they exist. Don't remove them.

**`apiUrl()` and hash routes — the frontend and backend live on different URLs**

DSS renders the webapp's page itself, but the FastAPI backend that answers `/api/...` lives at
its own URL (`…/web-apps-backends/<PROJECT>/<WEBAPP_ID>/`). A bare `fetch('/api/x')` would hit
DSS, not FastAPI. `apiUrl()` — re-exported from bs-blueprint in `utils/api.ts` — asks the
DSS-injected `dataiku.getWebAppBackendUrl()` for the real URL. Locally there is no `dataiku`
global, so it returns `/api/x` unchanged and Vite's proxy routes it to FastAPI.

DSS also owns the page URL, so the router uses `createWebHashHistory()`: act URLs are
`…#/evidence`, `…#/shortlist`, and a refresh keeps you on the act.

**`base: './'` and the single-bundle output — serving assets from a sub-path**

Vite's default is to produce assets with absolute paths (`/assets/index.js`). That breaks
in the DSS sub-path. Setting `base: './'` makes paths relative, so they resolve correctly
wherever the HTML file is served from.

Code-splitting (the default behavior where Vite produces many small JS chunks) also breaks
in DSS because the server doesn't reliably serve those extra files. The Vite config forces
a single output bundle:

```typescript
rollupOptions: {
  output: {
    entryFileNames: 'assets/index.js',
    chunkFileNames: 'assets/[name].js',
    assetFileNames: 'assets/index.[ext]',
  },
}
```

**`dedupe: ['vue', 'vue-router']` — preventing two copies of Vue**

Some dependencies (e.g. `reka-ui`) list Vue and vue-router as *peer dependencies*, meaning
they expect the consuming app to provide them. When npm resolves the dependency tree it can
sometimes install a second copy. Two Vue instances break reactivity silently and in
mysterious ways. The `dedupe` option in `vite.config.ts` forces Vite to always use the single
copy from the top-level `node_modules`.

**`from __future__ import annotations` / Python ≥3.11**

Modern Python type hints like `str | None` (union types) and `list[str]` (lowercase
generics) require Python 3.10+. DSS's default Python environment may be 3.9. The backend
uses `from __future__ import annotations` in every module as a compatibility shim. Better
still: create a code env with Python 3.11+ and set it in `app.env` as `ENV_NAME`.

---

## Configuration and renaming

All per-project settings live in `app.env`, which is checked into git. The identity
and DSS-target keys (`LIB_NS`, `APP_PREFIX`, `VITE_APP_NAME`, `ENV_NAME`, `PROJECT_KEY`,
`DKU_INSTANCE`) ship **empty** — fill them in, and `make dev` refuses to start until
they are set.

| Key | Used by | Purpose |
|-----|---------|---------|
| `LIB_NS` | `deploy.sh` | Python package namespace in the DSS library (`python/<LIB_NS>/`) |
| `APP_PREFIX` | `deploy.sh`, `backend/config.py` | Prefix for environment variables (`MYAPP_DSS_MODE`, etc.) |
| `VITE_APP_NAME` | `frontend/src/config.ts` | Display name in the sidebar header |
| `PROJECT_KEY` | `deploy.sh`, `backend/dss_client.py` | DSS project to deploy to and query locally |
| `WEBAPP_ID` | `deploy.sh` | ID of the webapp in that project |
| `ENV_NAME` | `deploy.sh` | Code env on the DSS instance (Python ≥3.11 recommended) |
| `BACKEND_PORT` | `Makefile` | Local dev port for FastAPI (default: 5000) |
| `FRONTEND_PORT` | `Makefile` | Local dev port for Vite (default: 5173) |
| `VITE_VISUAL_GRAPH_PROJECT_KEY` | `frontend/src/config.ts` | Project containing the Visual Graph Explorer |
| `VITE_VISUAL_GRAPH_WEBAPP_ID` | `frontend/src/config.ts` | Explorer backend webapp identifier, retained for identity and operational checks |
| `VITE_VISUAL_GRAPH_OBJECT_ID` | `frontend/src/config.ts` | Explorer navigation object identifier (webapp ID plus current slug) |
| `VITE_DSS_ORIGIN` | `frontend/src/config.ts` | Optional DSS origin for local development; deployed builds use their current origin |

Local secrets that shouldn't be committed (DSS URL, API key override) go in `.env`
(gitignored). Copy `.env.example` to get started.

**Renaming** — edit the identity keys in `app.env` (`LIB_NS`, `APP_PREFIX`,
`VITE_APP_NAME`, `ENV_NAME`) and restart `make dev`. There are no in-code identity
tokens to rewrite: the display name and the FastAPI title read `VITE_APP_NAME`, the
DSS webapp Python is generated from `LIB_NS`/`APP_PREFIX` at deploy time, and the
sidebar icon is a fixed brand mark in `frontend/src/config.ts` (swap it there if you
want a different one).

---

## Target Prioritizer Visual Graph Explorer integration

This application uses the Visual Graph Explorer as the single interactive graph surface for both Act 1
and Act 4. `VisualGraphExplorerCard` is the shared card; its **Open full Explorer** control is a plain
link (`target="_blank"`) to the Explorer, so the Explorer always opens in its own browser tab and never
inside this app. The link's URL is built from the four `VITE_VISUAL_GRAPH_*` / `VITE_DSS_ORIGIN` settings
above. In the deployed DSS webapp the origin is same-origin; local development needs `VITE_DSS_ORIGIN`
set to the relevant DSS host. With no URL the card shows the control disabled, with a note saying so.

The two Explorer identifiers intentionally differ. `wBcApLN` identifies the underlying webapp for DSS
status and log operations; `wBcApLN_graph-explorer` is the browser-navigation object used in
`/projects/DEMO_TARGET_IDENTIFICATION/webapps/wBcApLN_graph-explorer/view`. Do not replace one with the
other or add a graph snapshot ID to the configuration.

The object ID carries the webapp's current name slug, so **renaming the Explorer in DSS changes it**.
The webapp was renamed to *Graph Explorer* on 2026-09-03 and its object ID moved from
`wBcApLN_graph-search` to `wBcApLN_graph-explorer`; the webapp ID `wBcApLN` did not change. Because
`VITE_VISUAL_GRAPH_OBJECT_ID` is baked into the Vite bundle at build time, a rename is only live after
a rebuild and redeploy — the Act 1 and Act 4 graph cards keep pointing at the old slug until then.

The handoff is deliberately explicit and manual. The card shows the prepared Cypher with three numbered
steps: copy the query with **Copy query**, open the Explorer, then create a new query there, paste and
run it. Opening the link does not touch the clipboard. If clipboard access is unavailable the query stays
selectable and the card says so. Do not call a Visual Graph plug-in endpoint, embed the Explorer in an
iframe or claim an unconfirmed clipboard copy.

Act 1 offers three deterministic starters. Act 4 offers five independent bounded presets for the current
disease and target gene. The Target Prioritizer has no `/api/graph/*` endpoint and does not execute
Cypher, join graph results or render a graph/table canvas; those responsibilities belong to the Explorer.

---

## Extending the app

### Add a new page

1. Create `frontend/src/views/MyView.vue`
2. Add a route in `frontend/src/router/index.ts` — the sidebar builds itself from `meta`:
   ```typescript
   {
     path: 'my-feature',
     name: 'myFeature',
     component: MyView,
     meta: { title: 'My Feature', icon: Dataset, menu: 'primary', order: 2 },
   }
   ```
   Import your icon from `@dataiku/vue-icons` (the DSS icon set). `menu: 'primary'` puts it in the main
   navigation; `menu: 'tertiary'` puts it in the footer (like Settings).
   See [The frontend, explained](#the-frontend-explained) for how the router drives the sidebar.

### Add a backend API endpoint

1. Create `backend/routes/my_feature.py`:
   ```python
   from fastapi import APIRouter
   from ..dss_client import get_project

   router = APIRouter(prefix="/api/my-feature")

   @router.get("/items")
   def list_items():
       project = get_project()           # works locally and in DSS
       datasets = project.list_datasets()
       return [{"name": d["name"]} for d in datasets]
   ```
2. Register it in `backend/app.py`:
   ```python
   from .routes.my_feature import router as my_feature_router
   # inside configure():
   app.include_router(my_feature_router)
   ```
3. Call it from the frontend with `fetch(apiUrl('/api/my-feature/items'))`.
   See [The non-obvious bits](#the-non-obvious-bits-explained) for why `apiUrl()` is needed.

---

## Glossary

| Term | Plain-English definition |
|------|--------------------------|
| **SPA** | Single-Page Application — one HTML file, all navigation done in JS, no full page reloads |
| **Vite** | Build tool for the frontend: runs a fast dev server with hot reload and compiles TypeScript + Vue to plain JS/CSS for production |
| **Vue 3** | JavaScript framework for building UIs (comparable to React); uses `.vue` files with `<script>`, `<template>`, `<style>` |
| **Pinia** | Vue's state management library — a store is a reactive object shared across components |
| **Tailwind CSS** | Utility-class CSS library: instead of writing `.my-button { color: red }`, you write `class="text-red-500"` directly in HTML |
| **Design tokens** | CSS variables defined by the `@dataiku/ea-ui-kit` theme and exposed as Tailwind utilities, so `bg-primary` etc. look like a Dataiku product |
| **reka-ui** | Headless (unstyled) Vue UI primitives that the kit's components are built on |
| **FastAPI** | Python web framework: you decorate functions with `@router.get("/path")` and they become API endpoints |
| **`uv`** | Python package manager; `uv sync` reads `pyproject.toml` and creates a virtualenv with the right deps |
| **`npm`** | Node package manager (ships with Node.js); `npm install` reads `package.json` |
| **Code env** | DSS's isolated Python environment for a webapp or recipe; created in Administration → Code envs |
| **Project library** | The `python/` directory inside a DSS project that's on `sys.path` for everything in that project; `make deploy` uploads the backend here |
| **Project variables** | Key-value store per DSS project, readable and writable from Python at runtime; used here to persist app settings |
| **Managed folder** | DSS object for storing arbitrary files (PDFs, images, etc.) inside a project; use instead of the local filesystem (which isn't writable in DSS) |

---

## Architecture decisions & trade-offs

This blueprint makes several non-obvious choices. They are **deliberate**, documented here so your team can debate them, extend from them, or replace them when your app outgrows the starter constraints. Each entry follows the pattern: **Decision → Why → Trade-off → When to revisit.**

---

### Single-bundle Vite output (no code-splitting)

**Decision:** `vite.config.ts` forces a single JavaScript output file (`assets/index.js`) and uses `base: './'` for relative asset paths.

**Why:** the bundle is served by the FastAPI backend at a sub-path (e.g. `https://my-dss.company.com/web-apps-backends/PROJECT/WEBAPP_ID/assets/`). DSS's project-library serving does not reliably handle the chunk manifest that Vite's default code-splitting produces — requests for dynamically-imported chunks 404. A single bundle avoids this entirely.

**Trade-off:** the bundle cannot be lazy-loaded. It also means `import()` lazy routes cannot be used; all route components must be statically imported. The JS bundle is approximately 990 KB minified / 330 KB gzipped, most of it echarts, which the act charts use.

**When to revisit:** if the app grows to where the initial load time is noticeably slow (> 2–3 s on a reasonable connection), the right fix is to change the DSS library serving strategy (host the frontend externally or use a DSS API node with proper static-file handling) rather than fighting Vite's code-splitting within the current constraints.

---

### Dual-mode `get_project()` (one code path, two environments)

**Decision:** all DSS access goes through `backend/dss_client.py::get_project()`, which returns a `dataikuapi.DSSProject` in both local dev and in-DSS modes.

**Why:** the alternative — branching on `DSS_MODE` inside every route — produces duplicated logic that diverges over time. One accessor, two environments, no branching in business logic.

**Trade-off:** the local dev path adds a network round-trip to the remote DSS instance for every API call (no local mock). This is acceptable because the blueprint targets real-data development, not unit-testable mock data.

---

### Local dataset previews via `dataiku-internal-client`

**Decision:** local dev installs the **real in-DSS `dataiku` package** as a **required** dev dependency, pulled from the instance's own `dataiku-internal-client` tarball (`pyproject.toml` `[dependency-groups] dev`, pinned to the team instance URL `…/public/packages/dataiku-internal-client.tar.gz`). The public `dataiku-api-client` (`dataikuapi`) is kept. `backend/dss_client.py::get_dataiku()` configures the package for remote use (`set_remote_dss` + `set_default_project_key`) so `dataiku.Dataset(...).get_dataframe()` runs locally exactly as in DSS; `routes/example.py` and `tools/registry.py` read rows through it — **the single code path, no `dataikuapi` row-reading fallback** (run `uv sync` and it's always there).

**Why:** `dataiku-api-client` alone lists datasets and reads schemas, but its streaming `iter_rows()` diverges from the in-DSS implementation and raises mid-iteration — so dataset *row* previews silently degrade to schema-only locally. The internal `dataiku` reproduces the exact in-DSS data-plane. Two alternatives were rejected:
- *A local DSS kit on `PYTHONPATH`* — works, but requires every developer to have a kit installed and pins to whatever version they happen to have (e.g. a `14.4.2` kit against a `14.6.0` instance). The served tarball is **version-matched to the instance** and installs like any other dependency.
- *Dropping `dataikuapi` to "reduce dependencies"* — impossible. The internal `dataiku` is built **on top of** `dataikuapi` (`dataiku/core/intercom.py` → `from dataikuapi import DSSClient`; `dataiku.api_client()` returns a `dataikuapi.DSSClient`), and the entire control-plane the backend uses (`list_datasets`, `get_schema`, `list_llms`, `get_variables`/`set_variables`, managed folders, knowledge banks) is `dataikuapi`. The tarball neither bundles nor declares it. The two are **complementary**: `dataikuapi` = control-plane, `dataiku` = data-plane — and there's no weight to reclaim (`dataikuapi`'s deps are already pulled in).

**Trade-off:** the URL is **instance-specific and hardcoded** for our team, and unversioned — a DSS upgrade changes the tarball, so refresh the lock with `uv lock --upgrade-package dataiku-internal-client`. It's dev-only: inside DSS the runtime provides `dataiku`, and dev-group deps aren't shipped in the deployable wheel. Because there is no row-reading fallback, local dev **requires** `uv sync` (and DSS connectivity) — a stale checkout that skipped it will `ImportError` on `dataiku` rather than silently degrading. That's a deliberate trade for one simple code path.

**When to revisit:** when the blueprint must target **multiple instances**, derive the URL from the configured instance (`~/.dataiku/config.json` / `DKU_INSTANCE`) instead of hardcoding it; or, if the team standardizes on locally-installed kits, point at the kit instead.

---

## Tech notes

- **Python ≥3.11** — recommended for the code env. The backend uses `from __future__ import annotations` as a 3.9 compatibility shim, but type errors can still surface on very old envs.
- **Design tokens / UI** — the look comes from the team's design system (`@dataiku/ea-ui-kit` through bs-blueprint); the app owns no palette. Components come from the kit, and the few composites it lacks from bs-blueprint; the app keeps no local copies.
- **No writable local filesystem in DSS** — the plugin install directory is read-only. Use **Managed Folders** for user-uploaded files and **project variables** for configuration.
- **WebSockets** — DSS's WSGI layer doesn't support WebSocket upgrades. If you need push updates, use Server-Sent Events (SSE) instead (FastAPI's `sse-starlette` package, already in `pyproject.toml`).
