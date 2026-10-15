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
