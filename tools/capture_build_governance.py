#!/usr/bin/env python3
"""Capture one small, governed DSS leaf-build event without launching a build.

This pilot adapter is intentionally read-only with respect to DSS.  It captures the only
allowlisted Phase 5 leaf target, derives its governed measurements from the materialised output and
the producing job's diagnostic line, and emits a machine-event document for ``build_governance``.
``--append-ledger`` is local-only and appends exactly one JSON line after validating the existing
ledger is parseable JSONL.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

import build_governance as governance


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = "DEMO_TARGET_IDENTIFICATION"
TARGET = "breast_panel_metrics"
RECIPE = "compute_breast_panel"
BASELINE_ID = "phase5-pilot-breast-panel-20260831"
MAX_ROWS = 100
MAX_BYTES = 1024 * 1024
OVERLAP = re.compile(r"HER2\+ vs triple-negative, top-50 novel:\s+(\d+)/50\s+shared")


def dku_json(*args):
    completed = subprocess.run(
        ["dku", *args, "-o", "json"], cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(completed.stdout)


def dku_text(*args):
    completed = subprocess.run(
        ["dku", *args], cwd=ROOT, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def timestamp(value=None):
    if value:
        return value
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z")


def semantic_recipe(recipe):
    definition = recipe["definition"]
    refs = [item["ref"] for item in definition.get("inputs", {}).get("main", {}).get("items", [])]
    outputs = [item["ref"] for item in definition.get("outputs", {}).get("main", {}).get("items", [])]
    if (definition.get("projectKey") != PROJECT or definition.get("name") != RECIPE or
            sorted(refs) != sorted(set(refs)) or any("." in ref for ref in refs) or
            outputs != [TARGET] or "compute_kg" in governance.canonical_json(recipe).decode("utf-8")):
        raise governance.PolicyViolation("pilot topology is not the approved local leaf recipe")
    return {
        "name": definition["name"], "project_key": definition["projectKey"],
        "type": definition["type"], "params": definition.get("params", {}),
        "inputs": definition.get("inputs", {}), "outputs": definition.get("outputs", {}),
        "payload": recipe.get("payload", ""),
    }


def claim_values(rows, log):
    by_disease = {row.get("disease"): row for row in rows}
    her2 = by_disease.get("HER2 positive breast carcinoma")
    tnbc = by_disease.get("triple-negative breast carcinoma")
    match = OVERLAP.search(log)
    if not her2 or not tnbc or not match:
        raise governance.GovernanceError("live output/job log lacks required TI-VAL-009 evidence")
    return {"TI-VAL-009": {
        "her2_positive_auroc": her2["auc"],
        "her2_tnbc_novel_overlap": int(match.group(1)),
        "tnbc_known_targets": tnbc["n_known_targets"],
    }}


def capture(job_id, event_id, observed_at):
    status = dku_json("job", "status", job_id, "-P", PROJECT)
    activities = status.get("activities", [])
    if (status.get("job_id") != job_id or status.get("state") != "DONE" or
            status.get("error") is not None or len(activities) != 1 or
            activities[0].get("name") != RECIPE + "_NP" or
            activities[0].get("state") != "DONE"):
        raise governance.GovernanceError(
            "pilot job is not one completed non-recursive compute_breast_panel activity")
    info = dku_json("dataset", "info", TARGET, "-P", PROJECT, "--recompute")
    if info.get("rows", MAX_ROWS + 1) > MAX_ROWS or info.get("size_bytes", MAX_BYTES + 1) > MAX_BYTES:
        raise governance.GovernanceError("pilot target exceeds the approved small-output bound")
    recipe = dku_json("recipe", "get-definition", RECIPE, "-P", PROJECT)
    schema = dku_json("dataset", "schema", TARGET, "-P", PROJECT)
    rows = dku_json("dataset", "head", TARGET, "-P", PROJECT, "-n", str(MAX_ROWS))
    if len(rows) != info["rows"]:
        raise governance.GovernanceError("pilot capture did not retrieve the complete small output")
    log = dku_text("job", "log", job_id, "-P", PROJECT, "--tail", "240")
    claims = claim_values(rows, log)
    registry = governance.load_json(governance.DEFAULT_REGISTRY)
    registered = next(item for item in registry["claims"] if item["id"] == "TI-VAL-009")
    expected = {item["key"]: item["value"] for item in registered["measurements"]}
    tolerances = {item["key"]: item["absolute_tolerance"] or 0
                  for item in registered["measurements"]}
    claim_passes = all(governance._numeric_equal(
        claims["TI-VAL-009"][key], expected[key], tolerances[key]) for key in expected)
    assertions = [
        {"id": "TI-VAL-009", "status": "PASS" if claim_passes else "FAIL"},
        {"id": "breast-panel-contract", "status": "PASS"},
    ]
    return {
        "schema_version": 1, "event_id": event_id, "observed_at": timestamp(observed_at),
        "project_key": PROJECT, "job_id": job_id, "targets": [TARGET], "outcome": "SUCCESS",
        "accepted_baseline_id": BASELINE_ID,
        "fingerprints": {
            "recipe_settings": {RECIPE: governance.fingerprint_json(semantic_recipe(recipe))},
            "schemas": {TARGET: governance.fingerprint_json(schema)},
            "data": {TARGET: governance.fingerprint_json(sorted(
                rows, key=lambda row: governance.canonical_json(row)))},
            # Excludes build timestamps/job identity: they are audit metadata, not semantic state.
            "refresh_state": {TARGET: governance.fingerprint_json({
                "type": info["type"], "connection": info["connection"], "format": info["format"],
                "files": info["files"], "metrics_computed": info["metrics_computed"],
            })},
        },
        "metrics": {TARGET + ".row_count": info["rows"]}, "claim_values": claims,
        "assertions": assertions,
    }


def append_ledger(path, event):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                if line.strip():
                    json.loads(line)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--observed-at")
    parser.add_argument("--append-ledger")
    args = parser.parse_args()
    try:
        event = capture(args.job_id, args.event_id, args.observed_at)
        governance.validate_event(event)
        if args.append_ledger:
            append_ledger(args.append_ledger, event)
        print(json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True))
    except (governance.GovernanceError, OSError, subprocess.CalledProcessError,
            json.JSONDecodeError, StopIteration) as exc:
        print("build-governance capture: %s" % exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
