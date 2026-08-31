#!/usr/bin/env python3
"""Deterministic, repository-side classification for governed DSS build events.

The DSS side eventually owns execution and the append-only event ledger.  This module owns the
stable fingerprint primitive, policy boundary, accepted-baseline comparison, and compact review
packet.  It deliberately has no Dataiku dependency and never starts a build or edits documentation.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_POLICY = os.path.join(ROOT, "docs/operations/build-governance/POLICY.json")
DEFAULT_REGISTRY = os.path.join(ROOT, "docs/prioritizer/CLAIM_REGISTRY.json")
CLASSIFICATIONS = (
    "NO_CHANGE",
    "REFRESH_ONLY",
    "EXPECTED_DATA_DELTA",
    "CLAIM_DELTA",
    "CONTRACT_DELTA",
    "INCIDENT",
)
FINGERPRINT_GROUPS = ("recipe_settings", "schemas", "data", "refresh_state")
CAPTURE_FIELDS = FINGERPRINT_GROUPS + ("metrics", "claim_values", "assertions")
HARD_DENIED_PROJECTS = frozenset({"KNOWLEDGE_GRAPH_PRIMEKG"})
HARD_DENIED_TARGETS = frozenset({"KNOWLEDGE_GRAPH_PRIMEKG"})
HARD_DENIED_RECIPES = frozenset({"compute_kg"})
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
RFC3339 = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


class GovernanceError(ValueError):
    """Invalid event, baseline, registry, or policy."""


class PolicyViolation(GovernanceError):
    """The requested project, target, or recipe is outside the approved boundary."""


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def canonical_json(value):
    """Return the UTF-8 canonical form used by every governance fingerprint."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except ValueError as exc:
        raise GovernanceError("JSON value cannot be fingerprinted: %s" % exc) from exc


def fingerprint_json(value):
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def fingerprint_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _need(document, fields, label):
    missing = sorted(set(fields) - set(document))
    if missing:
        raise GovernanceError("%s missing fields: %s" % (label, ", ".join(missing)))


def _exact(document, fields, label):
    _need(document, fields, label)
    extra = sorted(set(document) - set(fields))
    if extra:
        raise GovernanceError("%s has unknown fields: %s" % (label, ", ".join(extra)))


def _validate_fingerprints(fingerprints, label):
    _exact(fingerprints, FINGERPRINT_GROUPS, label)
    for group in FINGERPRINT_GROUPS:
        values = fingerprints[group]
        if not isinstance(values, dict):
            raise GovernanceError("%s.%s must be an object" % (label, group))
        for name, digest in values.items():
            if not isinstance(name, str) or not name:
                raise GovernanceError("%s.%s has an empty key" % (label, group))
            if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
                raise GovernanceError("%s.%s.%s is not a sha256 fingerprint" %
                                      (label, group, name))


def _validate_timestamp(value, label):
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        raise GovernanceError("%s must be a non-empty RFC 3339 timestamp" % label)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise GovernanceError("%s must be an RFC 3339 timestamp" % label) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GovernanceError("%s must include a timezone" % label)


def _string_list(value, label, allow_empty=False):
    if (not isinstance(value, list) or
            not all(isinstance(item, str) and item for item in value)):
        raise GovernanceError("%s must be a list of non-empty strings" % label)
    if not allow_empty and not value:
        raise GovernanceError("%s must not be empty" % label)
    if len(value) != len(set(value)):
        raise GovernanceError("%s contains duplicates" % label)
    if value != sorted(value):
        raise GovernanceError("%s must be sorted" % label)


def validate_event(event):
    fields = {
        "schema_version", "event_id", "observed_at", "project_key", "job_id", "targets",
        "outcome", "accepted_baseline_id", "fingerprints", "metrics", "claim_values",
        "assertions",
    }
    _exact(event, fields, "event")
    if event["schema_version"] != 1:
        raise GovernanceError("event.schema_version must be 1")
    if event["outcome"] not in {"SUCCESS", "FAILED", "ABORTED"}:
        raise GovernanceError("event.outcome must be SUCCESS, FAILED, or ABORTED")
    for name in ("event_id", "observed_at", "project_key", "job_id", "accepted_baseline_id"):
        if not isinstance(event[name], str) or not event[name]:
            raise GovernanceError("event.%s must be a non-empty string" % name)
    _validate_timestamp(event["observed_at"], "event.observed_at")
    if (not isinstance(event["targets"], list) or not event["targets"] or
            not all(isinstance(item, str) and item for item in event["targets"])):
        raise GovernanceError("event.targets must be a non-empty list")
    if len(event["targets"]) != len(set(event["targets"])):
        raise GovernanceError("event.targets contains duplicates")
    if event["targets"] != sorted(event["targets"]):
        raise GovernanceError("event.targets must be sorted")
    if not isinstance(event["metrics"], dict) or not isinstance(event["claim_values"], dict):
        raise GovernanceError("event.metrics and event.claim_values must be objects")
    if not isinstance(event["assertions"], list):
        raise GovernanceError("event.assertions must be a list")
    assertion_ids = []
    for assertion in event["assertions"]:
        if not isinstance(assertion, dict):
            raise GovernanceError("assertion must be an object")
        _exact(assertion, {"id", "status"}, "assertion")
        if not isinstance(assertion["id"], str) or not assertion["id"]:
            raise GovernanceError("assertion.id must be a non-empty string")
        if assertion["status"] not in {"PASS", "FAIL", "ERROR"}:
            raise GovernanceError("assertion.status must be PASS, FAIL, or ERROR")
        assertion_ids.append(assertion["id"])
    if len(assertion_ids) != len(set(assertion_ids)):
        raise GovernanceError("event.assertions contains duplicate IDs")
    if assertion_ids != sorted(assertion_ids):
        raise GovernanceError("event.assertions must be sorted by ID")
    _validate_fingerprints(event["fingerprints"], "event.fingerprints")
    canonical_json({"metrics": event["metrics"], "claim_values": event["claim_values"]})
    if not all(isinstance(value, dict) for value in event["claim_values"].values()):
        raise GovernanceError("event.claim_values entries must be objects")


def validate_baseline(baseline):
    fields = {
        "schema_version", "baseline_id", "accepted_at", "project_key", "targets",
        "source_event_id", "accepted_by", "acceptance_reason", "fingerprints", "metrics",
        "claim_values", "required_assertions",
    }
    _exact(baseline, fields, "baseline")
    if baseline["schema_version"] != 1:
        raise GovernanceError("baseline.schema_version must be 1")
    for name in ("baseline_id", "accepted_at", "project_key", "source_event_id", "accepted_by",
                 "acceptance_reason"):
        if not isinstance(baseline[name], str) or not baseline[name]:
            raise GovernanceError("baseline.%s must be a non-empty string" % name)
    _validate_timestamp(baseline["accepted_at"], "baseline.accepted_at")
    if (not isinstance(baseline["targets"], list) or not baseline["targets"] or
            not all(isinstance(item, str) and item for item in baseline["targets"])):
        raise GovernanceError("baseline.targets must be a non-empty list")
    if baseline["targets"] != sorted(baseline["targets"]):
        raise GovernanceError("baseline.targets must be sorted")
    if len(baseline["targets"]) != len(set(baseline["targets"])):
        raise GovernanceError("baseline.targets contains duplicates")
    if not isinstance(baseline["metrics"], dict) or not isinstance(baseline["claim_values"], dict):
        raise GovernanceError("baseline.metrics and baseline.claim_values must be objects")
    if (not isinstance(baseline["required_assertions"], list) or
            not all(isinstance(item, str) and item for item in baseline["required_assertions"]) or
            len(baseline["required_assertions"]) != len(set(baseline["required_assertions"]))):
        raise GovernanceError("baseline.required_assertions must be a unique list")
    if baseline["required_assertions"] != sorted(baseline["required_assertions"]):
        raise GovernanceError("baseline.required_assertions must be sorted")
    _validate_fingerprints(baseline["fingerprints"], "baseline.fingerprints")
    canonical_json({"metrics": baseline["metrics"], "claim_values": baseline["claim_values"]})
    if not all(isinstance(value, dict) for value in baseline["claim_values"].values()):
        raise GovernanceError("baseline.claim_values entries must be objects")


def _lower_set(values):
    return {value.casefold() for value in values}


def validate_policy(policy):
    fields = {
        "schema_version", "scope", "allowed_projects", "allowed_targets",
        "target_requirements", "denied_projects", "denied_targets", "denied_recipes",
        "contract_consumers",
    }
    _exact(policy, fields, "policy")
    if policy["schema_version"] != 1:
        raise GovernanceError("policy.schema_version must be 1")
    if not isinstance(policy["scope"], str) or not policy["scope"]:
        raise GovernanceError("policy.scope must be a non-empty string")
    for field in ("allowed_projects", "denied_projects", "denied_targets", "denied_recipes"):
        _string_list(policy[field], "policy.%s" % field, allow_empty=field != "allowed_projects")
    if not isinstance(policy["allowed_targets"], dict) or not isinstance(
            policy["target_requirements"], dict):
        raise GovernanceError("policy target maps must be objects")
    if set(policy["allowed_targets"]) != set(policy["allowed_projects"]):
        raise GovernanceError("policy.allowed_targets must cover exactly the allowed projects")
    if set(policy["target_requirements"]) != set(policy["allowed_projects"]):
        raise GovernanceError("policy.target_requirements must cover exactly the allowed projects")
    for project in policy["allowed_projects"]:
        targets = policy["allowed_targets"][project]
        _string_list(targets, "policy.allowed_targets.%s" % project)
        requirements = policy["target_requirements"][project]
        if not isinstance(requirements, dict) or set(requirements) != set(targets):
            raise GovernanceError("policy target requirements disagree for %s" % project)
        for target in targets:
            requirement = requirements[target]
            _exact(requirement, CAPTURE_FIELDS,
                   "policy.target_requirements.%s.%s" % (project, target))
            for field in CAPTURE_FIELDS:
                _string_list(requirement[field],
                             "policy.target_requirements.%s.%s.%s" %
                             (project, target, field))
    consumers = policy["contract_consumers"]
    if not isinstance(consumers, dict):
        raise GovernanceError("policy.contract_consumers must be an object")
    for contract, paths in consumers.items():
        if not isinstance(contract, str) or not contract.startswith(("recipe:", "schema:")):
            raise GovernanceError("policy has invalid contract key: %r" % contract)
        _string_list(paths, "policy.contract_consumers.%s" % contract)


def _capture_requirements(policy, project, targets):
    combined = {field: set() for field in CAPTURE_FIELDS}
    for target in targets:
        for field, values in policy["target_requirements"][project][target].items():
            combined[field].update(values)
    return {field: sorted(values) for field, values in combined.items()}


def enforce_policy(event, baseline, policy):
    validate_policy(policy)
    project = event["project_key"]
    targets = event["targets"]
    recipes = sorted(event["fingerprints"]["recipe_settings"])
    denied_projects = _lower_set(policy["denied_projects"]) | _lower_set(HARD_DENIED_PROJECTS)
    denied_targets = _lower_set(policy["denied_targets"]) | _lower_set(HARD_DENIED_TARGETS)
    denied_recipes = _lower_set(policy["denied_recipes"]) | _lower_set(HARD_DENIED_RECIPES)
    if project.casefold() in denied_projects:
        raise PolicyViolation("project is hard-denied: %s" % project)
    if project not in policy["allowed_projects"]:
        raise PolicyViolation("project is not approved: %s" % project)
    allowed_targets = set(policy["allowed_targets"].get(project, []))
    for target in targets:
        if target.casefold() in denied_targets:
            raise PolicyViolation("target is hard-denied: %s" % target)
        if target not in allowed_targets:
            raise PolicyViolation("target is not on the explicit Part 2 allowlist: %s" % target)
    for recipe in recipes:
        if recipe.casefold() in denied_recipes:
            raise PolicyViolation("recipe is hard-denied: %s" % recipe)
    if baseline["project_key"] != project or baseline["targets"] != targets:
        raise GovernanceError("event project/targets do not match the accepted baseline")
    if event["accepted_baseline_id"] != baseline["baseline_id"]:
        raise GovernanceError("event does not name the supplied accepted baseline")
    requirements = _capture_requirements(policy, project, targets)
    baseline_actual = {
        **{group: sorted(baseline["fingerprints"][group]) for group in FINGERPRINT_GROUPS},
        "metrics": sorted(baseline["metrics"]),
        "claim_values": sorted(baseline["claim_values"]),
        "assertions": sorted(baseline["required_assertions"]),
    }
    for field in CAPTURE_FIELDS:
        if baseline_actual[field] != requirements[field]:
            raise GovernanceError(
                "accepted baseline %s scope disagrees with policy; expected=%s observed=%s" %
                (field, requirements[field], baseline_actual[field]))
    return requirements


def _capture_scope_errors(event, requirements):
    actual = {
        **{group: set(event["fingerprints"][group]) for group in FINGERPRINT_GROUPS},
        "metrics": set(event["metrics"]),
        "claim_values": set(event["claim_values"]),
        "assertions": {item["id"] for item in event["assertions"]},
    }
    errors = []
    for field in CAPTURE_FIELDS:
        expected = set(requirements[field])
        missing = sorted(expected - actual[field])
        extra = sorted(actual[field] - expected)
        if missing:
            errors.append("event omitted required %s: %s" % (field, ", ".join(missing)))
        if extra:
            errors.append("event contains unapproved %s: %s" % (field, ", ".join(extra)))
    return errors


def _changed_keys(current, accepted):
    return sorted(key for key in set(current) | set(accepted)
                  if current.get(key) != accepted.get(key))


def _claim_registry(registry):
    _need(registry, {"schema_version", "claims"}, "claim registry")
    if registry["schema_version"] != 1:
        raise GovernanceError("claim registry schema_version must be 1")
    ids = [claim["id"] for claim in registry["claims"]]
    if len(ids) != len(set(ids)):
        raise GovernanceError("claim registry contains duplicate IDs")
    return {claim["id"]: claim for claim in registry["claims"]}


def _numeric_equal(current, accepted, tolerance):
    if isinstance(current, bool) or isinstance(accepted, bool):
        return current == accepted
    if isinstance(current, (int, float)) and isinstance(accepted, (int, float)):
        if not math.isfinite(float(current)) or not math.isfinite(float(accepted)):
            return False
        return abs(float(current) - float(accepted)) <= float(tolerance)
    return current == accepted


def _claim_deltas(event, baseline, registry_by_id):
    deltas = []
    missing = []
    expected_claims = baseline["claim_values"]
    observed_claims = event["claim_values"]
    for claim_id in sorted(expected_claims):
        claim = registry_by_id.get(claim_id)
        if claim is None:
            missing.append("claim is absent from registry: %s" % claim_id)
            continue
        measurements = {item["key"]: item for item in claim["measurements"]}
        observed = observed_claims.get(claim_id)
        if not isinstance(observed, dict):
            missing.append("event omitted governed claim: %s" % claim_id)
            continue
        accepted_keys = set(expected_claims[claim_id])
        registered_keys = set(measurements)
        observed_keys = set(observed)
        if accepted_keys != registered_keys:
            missing.append("accepted baseline measurement scope disagrees with registry: %s" %
                           claim_id)
        omitted = sorted(accepted_keys - observed_keys)
        unexpected = sorted(observed_keys - accepted_keys)
        if omitted:
            missing.append("event omitted governed measurements for %s: %s" %
                           (claim_id, ", ".join(omitted)))
        if unexpected:
            missing.append("event contains unapproved governed measurements for %s: %s" %
                           (claim_id, ", ".join(unexpected)))
        for key, accepted in sorted(expected_claims[claim_id].items()):
            if key not in observed:
                missing.append("event omitted governed measurement: %s/%s" % (claim_id, key))
                continue
            measurement = measurements.get(key)
            if measurement is None:
                missing.append("measurement is absent from registry: %s/%s" % (claim_id, key))
                continue
            tolerance = measurement["absolute_tolerance"]
            tolerance = 0 if tolerance is None else tolerance
            if not _numeric_equal(accepted, measurement["value"], tolerance):
                missing.append("accepted baseline is stale against registry: %s/%s" %
                               (claim_id, key))
            current = observed[key]
            if not _numeric_equal(current, accepted, tolerance):
                deltas.append({
                    "claim_id": claim_id,
                    "measurement": key,
                    "accepted": accepted,
                    "observed": current,
                    "absolute_tolerance": measurement["absolute_tolerance"],
                    "documentation_consumers": sorted(claim["documentation_consumers"]),
                    "webapp_api_consumers": sorted(claim["webapp_api_consumers"]),
                    "review_policy": claim["review_policy"],
                })
    extra_claims = sorted(set(observed_claims) - set(expected_claims))
    if extra_claims:
        missing.append("event contains claims outside baseline scope: %s" % ", ".join(extra_claims))
    return deltas, missing


def _contract_deltas(event, baseline, policy):
    changes = []
    missing_mappings = []
    mappings = policy["contract_consumers"]
    for group, prefix in (("recipe_settings", "recipe"), ("schemas", "schema")):
        for name in _changed_keys(event["fingerprints"][group], baseline["fingerprints"][group]):
            key = "%s:%s" % (prefix, name)
            consumers = mappings.get(key)
            if consumers is None:
                missing_mappings.append("changed contract has no consumer mapping: %s" % key)
                consumers = []
            changes.append({
                "contract": key,
                "accepted": baseline["fingerprints"][group].get(name),
                "observed": event["fingerprints"][group].get(name),
                "consumers": sorted(consumers),
            })
    return changes, missing_mappings


def classify(event, baseline, policy, registry):
    validate_event(event)
    validate_baseline(baseline)
    requirements = enforce_policy(event, baseline, policy)
    registry_by_id = _claim_registry(registry)

    failed = sorted(
        ({"id": item["id"], "status": item["status"]} for item in event["assertions"]
         if item["status"] != "PASS"),
        key=lambda item: item["id"],
    )
    claim_changes, claim_errors = _claim_deltas(event, baseline, registry_by_id)
    contract_changes, contract_errors = _contract_deltas(event, baseline, policy)
    data_changes = _changed_keys(
        event["fingerprints"]["data"], baseline["fingerprints"]["data"])
    refresh_changes = _changed_keys(
        event["fingerprints"]["refresh_state"], baseline["fingerprints"]["refresh_state"])
    metric_changes = _changed_keys(event["metrics"], baseline["metrics"])
    observed_assertions = {item["id"] for item in event["assertions"]}
    missing_assertions = sorted(set(baseline["required_assertions"]) - observed_assertions)
    missing_metrics = sorted(set(baseline["metrics"]) - set(event["metrics"]))
    incident_reasons = claim_errors + contract_errors + _capture_scope_errors(event, requirements)
    if missing_assertions:
        incident_reasons.append("event omitted required assertions: %s" %
                                ", ".join(missing_assertions))
    if missing_metrics:
        incident_reasons.append("event omitted configured metrics: %s" % ", ".join(missing_metrics))
    if event["outcome"] != "SUCCESS":
        incident_reasons.append("build outcome is %s" % event["outcome"])
    if failed:
        incident_reasons.append("one or more assertions did not pass")

    if incident_reasons:
        classification = "INCIDENT"
    elif contract_changes:
        classification = "CONTRACT_DELTA"
    elif claim_changes:
        classification = "CLAIM_DELTA"
    elif data_changes or metric_changes:
        classification = "EXPECTED_DATA_DELTA"
    elif refresh_changes:
        classification = "REFRESH_ONLY"
    else:
        classification = "NO_CHANGE"

    consumers = set()
    for change in claim_changes:
        consumers.update(change["documentation_consumers"])
        consumers.update(change["webapp_api_consumers"])
    for change in contract_changes:
        consumers.update(change["consumers"])
    actions = {
        "NO_CHANGE": "append_machine_event_only",
        "REFRESH_ONLY": "refresh_machine_state_only",
        "EXPECTED_DATA_DELTA": "rerun_mapped_checks_and_refresh_generated_status",
        "CLAIM_DELTA": "targeted_claim_review",
        "CONTRACT_DELTA": "targeted_contract_review",
        "INCIDENT": "fail_or_flag_and_preserve_diagnostics",
    }
    reasons = list(incident_reasons)
    if contract_changes:
        reasons.append("recipe settings or schema contract changed")
    if claim_changes:
        reasons.append("governed claim changed outside its accepted tolerance")
    if data_changes or metric_changes:
        reasons.append("data or non-claim metric changed")
    if refresh_changes:
        reasons.append("refresh state changed")
    if not reasons:
        reasons.append("all accepted semantic fingerprints and values match")
    return {
        "schema_version": 1,
        "event_id": event["event_id"],
        "job_id": event["job_id"],
        "project_key": event["project_key"],
        "targets": list(event["targets"]),
        "outcome": event["outcome"],
        "baseline_id": baseline["baseline_id"],
        "classification": classification,
        "review_required": classification in {"CLAIM_DELTA", "CONTRACT_DELTA", "INCIDENT"},
        "reasons": sorted(set(reasons)),
        "changed_claims": claim_changes,
        "changed_contracts": contract_changes,
        "changed_data": data_changes,
        "changed_metrics": metric_changes,
        "changed_refresh_state": refresh_changes,
        "failed_assertions": failed,
        "consumers": sorted(consumers),
        "recommended_action": actions[classification],
    }


def _write_json(value, output):
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    fp = subparsers.add_parser("fingerprint", help="fingerprint canonical JSON or raw file bytes")
    fp.add_argument("path")
    fp.add_argument("--raw-file", action="store_true")
    compare = subparsers.add_parser("classify", help="classify one event against an accepted baseline")
    compare.add_argument("--event", required=True)
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--policy", default=DEFAULT_POLICY)
    compare.add_argument("--claim-registry", default=DEFAULT_REGISTRY)
    compare.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        if args.command == "fingerprint":
            result = fingerprint_file(args.path) if args.raw_file else fingerprint_json(load_json(args.path))
            sys.stdout.write(result + "\n")
        else:
            packet = classify(
                load_json(args.event), load_json(args.baseline), load_json(args.policy),
                load_json(args.claim_registry))
            _write_json(packet, args.output)
    except (GovernanceError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write("build-governance: %s\n" % exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
