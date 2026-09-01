"""Dual-mode DSS project accessor.

Inside DSS (webapp backend):  dataiku.api_client().get_default_project()
Local dev, first choice:       DSS_URL + DSS_API_KEY env vars, or the
                               DKU_URL + DKU_API_KEY pair that
                               ``dku auth export-env`` emits
Local dev, fallback:           dataikuapi.DSSClient from ~/.dataiku/config.json
                               (instance picked by DKU_INSTANCE in app.env,
                               falling back to the file's default_instance)

Environment detection is the ``DSS_MODE`` flag (set by dss_webapp/backend.py in
DSS, never set locally) — NOT ``import dataiku`` success, because local dev
installs the real ``dataiku`` (``dataiku-internal-client``, see ``get_dataiku``
and pyproject.toml), so ``import dataiku`` succeeds locally and would otherwise be
mistaken for in-DSS.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import config


def _local_creds() -> tuple[str, str]:
    """(url, api_key) for the configured instance.

    Explicit environment wins: DSS_URL + DSS_API_KEY, or the DKU_URL +
    DKU_API_KEY pair that ``dku auth export-env`` emits. Otherwise read
    ~/.dataiku/config.json (instance picked by DKU_INSTANCE, falling back to
    the file's default_instance).

    ENV IS CHECKED FIRST DELIBERATELY. `dku` keeps its credential in the OS
    keyring, so ~/.dataiku/config.json can hold a long-dead api_key while the
    CLI works perfectly. With the file checked first there was no way to
    override it short of renaming the file: every local route failed with
    "Unknown API Key" while `dku whoami` succeeded, which points debugging at
    the CLI instead of at this function.
    """
    url = os.environ.get("DSS_URL") or os.environ.get("DKU_URL")
    key = os.environ.get("DSS_API_KEY") or os.environ.get("DKU_API_KEY")
    if url and key:
        return url.rstrip("/"), key

    cfg_path = Path.home() / ".dataiku" / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        name = os.environ.get("DKU_INSTANCE") or cfg.get("default_instance", "default")
        inst = cfg["dss_instances"][name]
        return inst["url"].rstrip("/"), inst["api_key"]

    raise RuntimeError(
        "No DSS credentials. Export DSS_URL + DSS_API_KEY, run "
        "eval \"$(dku auth export-env)\", or put a current api_key in "
        "~/.dataiku/config.json."
    )


def _local_client():
    """Build a dataikuapi client from ~/.dataiku/config.json or env vars."""
    import dataikuapi

    url, key = _local_creds()
    return dataikuapi.DSSClient(url, key)


def get_project():
    """Return a DSSProject handle for the current or configured project."""
    if config.DSS_MODE:
        import dataiku  # only available inside DSS

        return dataiku.api_client().get_default_project()

    return _local_client().get_project(config.PROJECT_KEY)


_remote_ready = False


def get_dataiku():
    """The configured ``dataiku`` module (always available).

    - Inside DSS (``DSS_MODE``): the runtime ``dataiku`` module, already configured.
    - Local dev: the installed ``dataiku-internal-client`` (a required dev dependency,
      see pyproject.toml) wired to the remote instance, so
      ``dataiku.Dataset(...).get_dataframe()`` works exactly like in-DSS.

    Run ``uv sync`` if ``import dataiku`` fails locally — the package is required.
    """
    import dataiku

    if config.DSS_MODE:
        return dataiku

    global _remote_ready
    if not _remote_ready:
        url, key = _local_creds()
        dataiku.set_remote_dss(url, key)
        dataiku.set_default_project_key(config.PROJECT_KEY)
        _remote_ready = True
    return dataiku
