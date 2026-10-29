"""Central config — reads from environment variables set by the Makefile
(via app.env) or by dss_webapp/backend.py in DSS.

All env vars are prefixed by APP_PREFIX (set by the Makefile via app.env, or by
dss_webapp/backend.py in DSS) so multiple webapps deployed to the same project
don't collide.
"""

from __future__ import annotations

import os

# The prefix drives all other env-var names.  In local dev it comes from
# app.env (exported by the Makefile). In DSS it is set explicitly by
# dss_webapp/backend.py before importing configure().
PREFIX: str = os.environ.get("APP_PREFIX", "")

# DSS project key — used by dss_client when running outside DSS.
PROJECT_KEY: str = os.environ.get("PROJECT_KEY", "")

# True when running inside a DSS webapp backend.
DSS_MODE: bool = bool(os.environ.get(f"{PREFIX}_DSS_MODE"))

# Log level for the Python logger.
LOG_LEVEL: str = os.environ.get(f"{PREFIX}_LOG_LEVEL", "INFO")

# Allowed CORS origins for local dev (the Vite dev server).
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get(
        f"{PREFIX}_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]

# The served datasets the flow migration rebuilt (docs/operations/FLOW_MIGRATION_WORKPLAN.md M4-M5).
# They carry the `_m4` suffix beside the old chains until M6 deletes the old datasets, renames these
# back and restores the original names here.
SHORTLIST: str = "dashboard_candidates_m4"
AUC_BY_DISEASE: str = "validation_auc_by_disease_m4"
AUC_BY_FAMILY: str = "family_auc_by_family_m4"
