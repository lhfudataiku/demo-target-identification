"""Run the assertion scripts locally against a DSS project (DEC-OPS-007).

The scripts in `notebooks/` read the evidence datasets by bare name, so those resolve in whichever
project is the dataiku client's default; the main-project inputs are read by qualified name
(`DEMO_TARGET_IDENTIFICATION.<name>`), so they resolve the same either way. This sets that default, then executes each script through
`tools/nb_assertions/runner.py`, which raises when a script's own FAIL list is non-empty -- the
failure contract the `validate_notebooks` scenario used to provide.

    uv sync --project notebooks
    uv run --project notebooks python tools/run_notebooks.py --project DEMO_TARGET_IDENTIFICATION
    uv run --project notebooks python tools/run_notebooks.py --only nb3_validation_and_plots

Credentials come from DKU_URL + DKU_API_KEY (as `dku auth export-env` emits them), or DSS_URL +
DSS_API_KEY, else ~/.dataiku/config.json -- the same order as webapp/backend/dss_client.py, and for
the same reason: `dku` keeps its key in the OS keyring, so the file can hold a dead one.

Every script runs even when an earlier one is stale; the exit code is non-zero if any did not pass.
`--out` writes the per-script result as JSON (keep it under data/, which is never committed).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NOTEBOOKS = ROOT / "notebooks"

# The lifecycle order in notebooks/README.md. The scripts are independent; the order is for reading
# the output, not a dependency. nb5 (data exploration) is left out: it defines no check(), and the
# runner refuses a script that asserts nothing. Run it directly.
ORDER = [
    "nb1_features_and_config",
    "nb2_splitting_and_pool",
    "nb3_validation_and_plots",
    "nb3b_hub_bias_meter",
    "nb4_results_three_axes",
    "nb6_interrogation_and_close",
    "nb7_panel_selection",
]

# The evidence project (ADR-003). --project DEMO_TARGET_IDENTIFICATION reruns M2's baseline.
DEFAULT_PROJECT = "DEMO_TI_EVIDENCE"


def credentials() -> tuple[str, str]:
    url = os.environ.get("DKU_URL") or os.environ.get("DSS_URL")
    key = os.environ.get("DKU_API_KEY") or os.environ.get("DSS_API_KEY")
    if url and key:
        return url.rstrip("/"), key
    cfg_path = Path.home() / ".dataiku" / "config.json"
    if cfg_path.exists():
        cfg = json.loads(cfg_path.read_text())
        name = os.environ.get("DKU_INSTANCE") or cfg.get("default_instance", "default")
        inst = cfg["dss_instances"][name]
        return inst["url"].rstrip("/"), inst["api_key"]
    raise SystemExit("no DSS credentials: run `eval \"$(dku auth export-env)\"` first")


def run_one(runner, name: str) -> dict:
    """Execute one script through the runner, echo its output, and summarise it."""
    buf = io.StringIO()
    started = time.monotonic()
    status, error = "PASS", None
    try:
        with contextlib.redirect_stdout(buf):
            runner.run(name)
    except AssertionError as exc:
        status, error = "STALE", str(exc)
    except Exception as exc:  # noqa: BLE001 -- an unreadable dataset must not stop the other scripts
        status, error = "ERROR", "%s: %s" % (type(exc).__name__, exc)
    out = buf.getvalue()
    sys.stdout.write(out)
    checks = None
    for line in out.splitlines():
        if line.startswith("ASSERT|%s|" % name):
            checks = int(line.split("checks_executed=")[1].split("|")[0])
    stale = [line.split("|", 2)[2] for line in out.splitlines() if line.startswith("STALE|%s|" % name)]
    return {"script": name, "status": status, "checks": checks, "stale": stale, "error": error,
            "seconds": round(time.monotonic() - started, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project", default=DEFAULT_PROJECT,
                    help="default project the scripts' bare dataset names resolve in")
    ap.add_argument("--only", action="append", choices=ORDER, help="run only this script (repeatable)")
    ap.add_argument("--out", help="write the per-script results as JSON to this path")
    args = ap.parse_args()

    os.environ.setdefault("MPLBACKEND", "Agg")
    import dataiku

    url, key = credentials()
    dataiku.set_remote_dss(url, key)
    dataiku.set_default_project_key(args.project)

    # The runner resolves scripts next to itself, as laid out in the DSS library. Locally they live
    # in notebooks/, so point it there rather than copying them.
    sys.path.insert(0, str(ROOT / "tools"))
    from nb_assertions import runner
    runner.HERE = str(NOTEBOOKS)

    results = [run_one(runner, name) for name in (args.only or ORDER)]

    print("\n" + "=" * 78)
    print("project %s" % args.project)
    for r in results:
        print("%-30s %-5s checks=%-4s stale=%-3d %7.1fs%s" % (
            r["script"], r["status"], r["checks"], len(r["stale"]), r["seconds"],
            "  " + r["error"] if r["status"] == "ERROR" else ""))
    print("=" * 78)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps({"project": args.project, "results": results}, indent=1))
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
