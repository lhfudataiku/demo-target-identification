"""App settings persisted as DSS project variables.

The entire payload lives under a single project-variable key so one DSS
write covers every change. Only ALLOWED_KEYS are read/written for safety.

Key is scoped by APP_PREFIX so two webapps in the same project don't collide.
"""

from __future__ import annotations

from typing import Any

from ..config import PREFIX
from ..dss_client import get_project

# Project variable key — derived from the app prefix.
VARIABLE_KEY = f"{PREFIX.lower()}_app_settings"

# Whitelist of settings keys. Extend as needed.
ALLOWED_KEYS: frozenset[str] = frozenset({
    "llm_id",
})


def _blank() -> dict[str, Any]:
    return {"llm_id": None}


def get_settings() -> dict[str, Any]:
    project = get_project()
    standard: dict[str, Any] = project.get_variables().get("standard", {})
    stored: dict[str, Any] = standard.get(VARIABLE_KEY) or {}
    return {**_blank(), **{k: v for k, v in stored.items() if k in ALLOWED_KEYS}}


def update_settings(patch: dict[str, Any]) -> dict[str, Any]:
    unknown = set(patch) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Unknown settings keys: {sorted(unknown)}")

    project = get_project()
    variables: dict[str, Any] = project.get_variables()
    standard = variables.setdefault("standard", {})
    current: dict[str, Any] = dict(standard.get(VARIABLE_KEY) or {})
    current.update({k: v for k, v in patch.items() if k in ALLOWED_KEYS})
    standard[VARIABLE_KEY] = current
    project.set_variables(variables)
    return {**_blank(), **current}
