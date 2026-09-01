# ──────────────────────────────────────────────────────────────────────────────
# Load per-app config then allow local .env to override.
# app.env is checked in; .env is gitignored (local secrets / port overrides).
# ──────────────────────────────────────────────────────────────────────────────
ifneq (,$(wildcard app.env))
  include app.env
  export
endif
ifneq (,$(wildcard .env))
  include .env
  export
endif

BACKEND_PORT  ?= 5000
FRONTEND_PORT ?= 5173

RUN_DIR  := .run
LOG_DIR  := $(RUN_DIR)/logs
UV_STAMP := $(RUN_DIR)/.uv-synced
NPM_STAMP := $(RUN_DIR)/.npm-installed

.PHONY: dev stop status logs logs-follow deploy help deps copy

# ──────────────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  Setup: fill in the identity/target values in app.env, then run make dev."
	@echo ""
	@echo "  make dev              Install deps if needed, then start backend + frontend"
	@echo "  make deps             Force re-run uv sync + npm install"
	@echo "  make stop             Kill processes on both ports"
	@echo "  make status           Show which ports are bound"
	@echo "  make logs             Show the last 200 lines of each .run/logs/*.log"
	@echo "  make logs-follow      Follow .run/logs/*.log interactively"
	@echo "  make deploy           Build + deploy to DSS; creates project/webapp if missing"
	@echo "  make copy DEST=~/path Copy source to a new directory (then edit app.env)"
	@echo ""

# ── Dependency installation (stamp-file pattern) ──────────────────────────────
# Make compares the stamp's mtime against the input files. If pyproject.toml
# or uv.lock is newer, uv sync runs. Same for package.json / package-lock.json.
# On first run the stamps don't exist, so both installs always run.

$(UV_STAMP): pyproject.toml $(wildcard uv.lock) | $(LOG_DIR)
	uv sync
	@touch $@

$(NPM_STAMP): frontend/package.json $(wildcard frontend/package-lock.json) | $(LOG_DIR)
	cd frontend && npm install
	@touch $@

deps:
	@rm -f $(UV_STAMP) $(NPM_STAMP)
	@$(MAKE) $(UV_STAMP) $(NPM_STAMP)

# ──────────────────────────────────────────────────────────────────────────────
dev: $(UV_STAMP) $(NPM_STAMP) $(LOG_DIR)
	@m=""; \
	[ -n "$(LIB_NS)" ]        || m="$$m LIB_NS"; \
	[ -n "$(APP_PREFIX)" ]    || m="$$m APP_PREFIX"; \
	[ -n "$(VITE_APP_NAME)" ] || m="$$m VITE_APP_NAME"; \
	[ -n "$(ENV_NAME)" ]      || m="$$m ENV_NAME"; \
	[ -n "$(PROJECT_KEY)" ]   || m="$$m PROJECT_KEY"; \
	[ -n "$(DKU_INSTANCE)" ]  || m="$$m DKU_INSTANCE"; \
	if [ -n "$$m" ]; then \
	  echo ""; \
	  echo "  ✗ App not configured. Missing in app.env:$$m"; \
	  echo ""; \
	  echo "    Fill these in app.env, then re-run make dev."; \
	  echo ""; \
	  exit 1; \
	fi
	@nohup uv run uvicorn backend.app:app \
	    --host 127.0.0.1 --port $(BACKEND_PORT) --reload \
	    > $(LOG_DIR)/backend.log 2>&1 & echo $$! > $(RUN_DIR)/backend.pid
	@nohup sh -c 'cd frontend && npm run dev' \
	    > $(LOG_DIR)/frontend.log 2>&1 & echo $$! > $(RUN_DIR)/frontend.pid
	@echo ""
	@echo "  Started. Open: http://localhost:$(FRONTEND_PORT)"
	@echo "  Tail logs : make logs"
	@echo "  Stop      : make stop"
	@echo ""

# Two sweeps, because a port sweep alone leaves orphans. Observed 2026-09-01:
# four backend processes from three different days were alive at once, two of them
# holding :5000 via SO_REUSEPORT so requests round-robined between generations of
# the code -- a route answered from a build six days old. `lsof -ti` only finds the
# ones currently holding the socket, and plain `kill` left two of them running.
#   1. by port   -- whatever is serving now
#   2. by command-- this project's own uvicorn/vite orphans that hold no socket,
#                   matched on $(CURDIR) so another checkout's servers are untouched
#   3. escalate  -- SIGTERM, then SIGKILL only what survived
stop:
	@all=""; \
	for port in $(BACKEND_PORT) $(FRONTEND_PORT); do \
	  pids=$$(lsof -ti:$$port 2>/dev/null || true); \
	  if [ -n "$$pids" ]; then echo "  port $$port: $$(echo $$pids | tr '\n' ' ')"; all="$$all $$pids"; \
	  else echo "  port $$port: nothing listening"; fi; \
	done; \
	orph=$$(ps -eo pid=,command= \
	        | grep -E "uvicorn backend.app:app|$(CURDIR)/frontend.*vite" \
	        | grep -F "$(CURDIR)" | grep -v grep | awk '{print $$1}'); \
	[ -n "$$orph" ] && echo "  orphans:  $$(echo $$orph | tr '\n' ' ')"; \
	all=$$(echo "$$all $$orph" | tr ' ' '\n' | sed '/^$$/d' | sort -u); \
	if [ -z "$$all" ]; then echo "  nothing to stop"; else \
	  kill $$all 2>/dev/null || true; \
	  for i in 1 2 3 4 5 6 7 8 9 10; do \
	    left=$$(for p in $$all; do kill -0 $$p 2>/dev/null && echo $$p; done); \
	    [ -z "$$left" ] && break; sleep 0.3; \
	  done; \
	  if [ -n "$$left" ]; then echo "  SIGKILL: $$(echo $$left | tr '\n' ' ')"; kill -9 $$left 2>/dev/null || true; fi; \
	  echo "  stopped"; \
	fi
	@rm -f $(RUN_DIR)/*.pid

status:
	@echo ""
	@for entry in backend:$(BACKEND_PORT) frontend:$(FRONTEND_PORT); do \
	  port=$${entry##*:}; name=$${entry%%:*}; \
	  if lsof -ti:$$port >/dev/null 2>&1; then \
	    printf "  %-9s :%-5s RUNNING\n" "$$name" "$$port"; \
	  else \
	    printf "  %-9s :%-5s stopped\n" "$$name" "$$port"; \
	  fi; \
	done
	@echo ""

logs:
	@tail -n 200 $(LOG_DIR)/*.log

logs-follow:
	@tail -f $(LOG_DIR)/*.log

# ──────────────────────────────────────────────────────────────────────────────
deploy: $(NPM_STAMP)
	@if [ -z "$(PROJECT_KEY)" ]; then \
	  echo "✗ Set PROJECT_KEY in app.env before deploying"; exit 1; fi
	@cd frontend && npm run build
	@./dss_webapp/deploy.sh "$(PROJECT_KEY)" "$(WEBAPP_ID)" "$(DKU_INSTANCE)"

# ──────────────────────────────────────────────────────────────────────────────
# Copy blueprint source to a new directory, excluding generated dirs.
# node_modules and .venv are skipped — `make dev` will recreate them.
# After copying, edit app.env in the new directory to set the app identity.
#
# Usage:  make copy DEST=~/my-new-app
#
copy:
	@if [ -z "$(DEST)" ]; then echo "Usage: make copy DEST=~/my-new-app"; exit 1; fi
	@rsync -a \
	    --exclude='.git' \
	    --exclude='.venv' \
	    --exclude='node_modules' \
	    --exclude='.run' \
	    --exclude='dist' \
	    --exclude='__pycache__' \
	    --exclude='*.pyc' \
	    --exclude='.env' \
	    . "$(DEST)/"
	@echo "✓ Copied to $(DEST)  (source files only, ~500 KB)"
	@echo "  cd $(DEST) && edit app.env && make dev"

# ──────────────────────────────────────────────────────────────────────────────
$(LOG_DIR):
	@mkdir -p $@
