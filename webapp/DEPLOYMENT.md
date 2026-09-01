# Deploying this webapp

> **Lifecycle:** Canonical · **Audience:** webapp deployers and reviewers · **Authority:** deployment,
> embedding and runtime verification procedure · **Update when:** the build, upload, restart or iframe
> contract changes · **Generated dependencies:** the deployment scripts and current webapp structure ·
> **Excludes:** UI design rationale and analytical evidence.

**The one thing to know before anything else:**

> **`git push` does not deploy the webapp. `make deploy` does.**

Git is version control. Deployment is a separate, explicit step. They both put files
on the DSS instance, in different places, and only one of those places is executed.

---

## Why a build step exists at all

The browser cannot run `.vue` files. Vite compiles `frontend/src/**` into a single bundle
at `frontend/dist/assets/index.js`, and **that compiled bundle is what DSS serves.**

`frontend/dist/` is gitignored — correctly, because build artifacts do not belong in
version control. The consequence is unavoidable and worth stating plainly: **a built
bundle can never travel through git.** It reaches DSS only when `deploy.sh` uploads it.

This is the single most confusing thing about the setup. A colleague can commit, push,
and watch the project sync succeed, and the webapp will still serve the UI from whenever
someone last ran `make deploy`.

## Where things live on DSS

The project library ends up with two copies of this app if the repo is mirrored. Only
one of them runs:

| library path | what it is | runs? |
|---|---|---|
| `python/target_prioritizer/` | `backend/` + built `frontend_dist/`, written by `make deploy` | **yes** |
| `project/webapp/` | a mirror of the repo, if the whole repo is synced | no |

DSS puts the library's `python/` directory on the Python import path. The webapp's shim
does `importlib.import_module('target_prioritizer.backend.app')`, which can only resolve
under `python/`. Anything at `project/` is stored files — readable, never imported.

*(As of 2026-08-26 the `project/` mirror is being dropped: nothing depended on it, and
its presence made the webapp look "not linked to what is in the library".)*

---

## First time on a new machine

```bash
brew install node                 # or nodejs.org
curl -Lsf https://astral.sh/uv/install.sh | sh
dku auth login                    # authenticate the CLI against the DSS instance
```

`app.env` is already filled in and committed — do not change these unless you are
targeting a different project:

```
LIB_NS=target_prioritizer          APP_PREFIX=TARGET_PRIORITIZER
PROJECT_KEY=DEMO_TARGET_IDENTIFICATION
WEBAPP_ID=OlmPX9a                  ENV_NAME=primekg_kg
```

**Do not change `BACKEND_PORT`.** `frontend/vite.config.ts` hardcodes the `/api` proxy to
`127.0.0.1:5000`. Changing the port here alone breaks local dev with an `ECONNREFUSED`
that surfaces in the UI as an unexplained HTTP 500.

---

## Changing the webapp

### 1. Edit

| what you are changing | where |
|---|---|
| an API endpoint | `backend/routes/*.py` — then register it in `backend/app.py` |
| a screen | `frontend/src/views/*.vue` |
| shared card / layout | `frontend/src/components/act/ActCard.vue` |
| navigation, act order | `frontend/src/router/index.ts` |
| colours, fonts | `frontend/src/styles/tokens.css` (Dataiku brand — see below) |

### 2. Check it locally (optional)

```bash
make dev            # Vite on :5173, FastAPI on :5000
```

Live DSS data works locally. `dss_client._local_creds()` checks the environment first —
`DSS_URL` + `DSS_API_KEY`, or the `DKU_URL` + `DKU_API_KEY` pair that `dku` exports — and
falls back to `~/.dataiku/config.json`. So the reliable start is:

```bash
eval "$(dku auth export-env)"
make dev
```

**Why env comes first.** `dku` keeps its credential in the OS keyring, so
`~/.dataiku/config.json` can hold a long-dead `api_key` while `dku whoami` works perfectly.
Before 2026-09-01 the file was checked first with no way to override it, so every route
returned `Unknown API Key` while the CLI succeeded — which sends you debugging the CLI
instead of the credential lookup. If you get that error now, your env is not exported.

None of this affects deployment: `backend/dss_client.py` is dual-mode and uses
`dataiku.api_client()` inside DSS, where no local credential is involved.

Read logs with `tail .run/logs/backend.log`. Do not use `make logs` in a script — it
follows and will block.

### 3. Deploy

```bash
make deploy
```

Which does, in order: `npm run build` → upload `backend/` → upload `frontend/dist/` →
patch the webapp definition → restart the backend.

### 4. Verify it actually landed

Do not trust "deploy succeeded". Grep the deployed bundle for a string unique to your
change:

```bash
# note: `dku library read` takes the path as a POSITIONAL argument, with a leading slash
dku library read /python/target_prioritizer/frontend_dist/assets/index.js \
  -P DEMO_TARGET_IDENTIFICATION | grep -c "some new string you added"

dku webapp logs OlmPX9a -P DEMO_TARGET_IDENTIFICATION | tail -20
```

A `0` from the first command means the build did not include your change, or the upload
did not happen. This check has caught a stale deploy at least once.

**Also check the backend contract, not only the bundle.** On 2026-09-01 the deployed
`routes/families.py` was found still reading `family_panel` / `pairwise_overlap` — a whole
generation behind the repo's `demo_panel_config` / `family_panel_*` chain, and matching no
commit on any branch, so it had been deployed from an uncommitted tree. A bundle grep would
not have caught it:

```bash
dku library read /python/target_prioritizer/backend/routes/families.py \
  -P DEMO_TARGET_IDENTIFICATION | grep -c demo_panel_config    # expect 1+
```

If a deployed file is ever *larger* than its local counterpart, someone edited the library
directly and `make deploy` is about to overwrite it. Diff before deploying.

### 5. Commit and push

Separately, and for version control only. It updates nothing on DSS.

---

## Design system

The app uses the **Dataiku brand palette**, not the shadcn defaults the template shipped
with. `frontend/src/styles/tokens.css` holds the values:

```
dkBlack #1A1A1A   dkWhite #FEFEF9   dkDarkGreen #06312E
dkBeige #F8F4E4   dkGreen #3EDAB2   dkLightGreen #C7FFF1
dkBlue  #7092F2   dkOrange #EDAB4F   (data viz only)
```

Fonts: **Spectral** headings, **Roboto** body, **DM Mono** data — the sanctioned Google
substitutes for Signifier / Untitled Sans / Söhne Mono.

Two rules that are easy to break: `dkGreen` is a **light** mint, so anything on it takes
dark text (`--primary-foreground` is dkDarkGreen, never white). And Orange+Green or
Blue+Green must never be co-dominant surfaces.

## Guardrails the UI must keep

These are demo requirements, not style preferences. They are enforced in
`ShortlistView.vue` and documented in `docs/demo/WEBAPP_DESIGN.md`:

- **Drug badges and the liability flag render, but are never filter controls.** The badges
  are the ground truth the enrichment is measured against — filtering on them makes the
  claim circular. Filtering the liability flag deletes ERBB2 from its own disease's list.
- **`prediction` is never fetched or displayed.** 590 of 762 known obesity targets are
  negative at the F1 threshold.
- **Every funnel count renders its rank cut-off**, so a count cannot acquire two values.
- **No discovery-enrichment figure on a summary tile.** The demo makes a *reconstruction*
  claim; a headline enrichment number turns it into a discovery claim.
- **Every card names its source dataset.** A number with no provenance undercuts the
  platform argument the demo closes on.

## Known traps

| symptom | cause |
|---|---|
| Deployed, but the UI is unchanged | Browser cached `assets/index.js` — the filename has no content hash. The backend now sends `no-store`, so this should be historical. |
| Synced the project, UI still old | Git does not carry the built bundle. Run `make deploy`. |
| UI shows old *data* after a dataset rebuild | The route caches the dataframe per process — see “Dataset caching” below. Restart the backend (`dku webapp restart OlmPX9a`) until the fix lands. |
| Local dev: HTTP 502 `Unknown API Key` | No credential in the environment and a stale `api_key` in `~/.dataiku/config.json`. Run `eval "$(dku auth export-env)"`. `dku whoami` succeeding does **not** mean the webapp can authenticate — different credential store. |
| Local dev: HTTP 500 on every API call | `BACKEND_PORT` no longer matches the Vite proxy. |
| `nginx: could not open error log file` in the logs | Harmless. Gunicorn binds fine afterwards. |

## Dataset caching — the known staleness, and the fix

The act routes load their datasets once per process:

```python
@functools.lru_cache(maxsize=1)
def _frame():
    return get_dataiku().Dataset("dashboard_candidates").get_dataframe(columns=COLS)
```

That is deliberate — `dashboard_candidates` is 105,702 rows and re-reading it per request makes the
demo feel slow. (`dku dataset info` reports 129,253 for it; that field is a stored metric and was
stale. `dku dataset count` is the live figure and matches nb7's `7.3 served rows` assertion.) The cost is real: **if the dataset is rebuilt, the webapp keeps serving the old rows
until the backend restarts.** In front of an audience that is the worst kind of stale — the numbers
look fine and are simply out of date.

**The fix to apply: keep the cache, but key it on the dataset's last-build timestamp, so a rebuild
invalidates it automatically.**

```python
def _last_build(name: str) -> str:
    # Cheap identity for the current build: metadata, not a data read.
    ds = get_dataiku().Dataset(name)
    return str(ds.get_last_metric_values()
                 .get_metric_by_id("reporting:BUILD_END").get_value())

@functools.lru_cache(maxsize=4)
def _frame_at(name: str, build_stamp: str):
    # build_stamp is unused inside — it exists purely as part of the cache key.
    return get_dataiku().Dataset(name).get_dataframe(columns=COLS)

def _frame():
    return _frame_at("dashboard_candidates", _last_build("dashboard_candidates"))
```

The stamp lookup is a metadata call, so the per-request cost stays negligible, while a rebuild
changes the cache key and the next request reloads. `maxsize=4` keeps a generation or two rather
than thrashing.

Applies to every cached route: `candidates.py`, `calibration.py`, `families.py`, `evidence.py`.

> One caveat worth knowing before relying on it: DSS dataset **metrics can lag** — `rows` on
> `nb6_assertion_results` read 33 while the table held 34, and `family_panel` reported 670 rows while
> the file was an empty 2 KB parquet. `BUILD_END` is written by the build itself rather than by a
> metrics pass, so it is the reliable one to key on — but do not swap it for `rows`.
