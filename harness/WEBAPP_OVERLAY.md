# Webapp overlay

This is a Vue 3 + FastAPI Dataiku DSS webapp. Keep a change narrow: one view, route, and, when
needed, one backend route/service. Do not read the complete `webapp/README.md` before classifying
the task.

## Route by task

- First setup or configuration: read `README.md` **Quick start** and `.env.example`. The six identity
  values in `app.env` must come from the user or read-only discovery; do not guess them. Show derived
  values and ask for confirmation before writing them.
- UI change: read `README.md` **Extending the app** plus the relevant component. Use local `Ea*`
  primitives and the design tokens in `frontend/src/styles/tokens.css`; do not hard-code colors or add
  a component library without an explicit request.
- Frontend route or API call: inspect `frontend/src/router/` and use `apiUrl()` from
  `frontend/src/utils/api.ts`; bare `/api/...` calls break inside the DSS iframe.
- Backend/DSS data access: inspect `backend/dss_client.py` and the closest route/service. Use
  `get_project()` / `get_dataiku()` rather than environment branches or ad-hoc clients.
- Deployment or embedding: read `DEPLOYMENT.md` and the README's **DSS integration** and
  **non-obvious bits** sections. Deployment is a live DSS mutation and requires explicit user intent.
- Optional blocks, persistence, or chatbot work: read the matching README section and closest code.

## Load-bearing rules

- Preserve the iframe contract: `apiUrl()`, router base from `window.location.pathname`, Vite
  `base: './'`, single-bundle output, Vue dedupe, and the vendored design tokens.
- Keep disabled feature blocks zero-cost: guarded imports, no unintended SQLite file, backend route,
  or sidebar entry. SQLite is single-writer; do not add multiple Uvicorn workers.
- Use `dku` only for read-only discovery during development. Do not mutate a DSS project merely to
  develop or inspect this app.
- DSS libraries are text-only: use Lucide components rather than binary assets. Keep feature flags in
  sync across backend and frontend.

## Finish proportionately

For frontend work, run `npm run typecheck` from `frontend/`. Start local development or deploy only
when the requested work calls for it; run `make deploy` only with explicit user authorization.
