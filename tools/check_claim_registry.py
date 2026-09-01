#!/usr/bin/env python3
"""Validate and index the governed target-prioritizer claim registry.

The registry is deliberately JSON and this checker uses only the Python standard library.  It
verifies schema shape, stable IDs, authoritative values and explicit consumer markers, then renders
one deterministic TSV used in review.  `--check` never writes.
"""

import argparse
import json
import os
import re
import sys

import build_index


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "docs/prioritizer/CLAIM_REGISTRY.json")
OUTPUT = os.path.join(ROOT, ".index/governed_claims.tsv")
CLAIM_FIELDS = {
    "id", "status", "statement", "interpretation", "measurements",
    "documentation_consumers", "webapp_api_consumers", "review_policy",
}
MEASUREMENT_FIELDS = {
    "key", "value", "unit", "display_precision", "absolute_tolerance", "authority",
}
CONSUMER_EXTENSIONS = {".html", ".js", ".md", ".py", ".ts", ".vue"}


def fail(errors, message):
    errors.append(message)


def json_pointer(document, pointer):
    value = document
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        raise ValueError("JSON pointer must start with /")
    for token in pointer[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def same_value(actual, expected, tolerance):
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual == expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(float(actual) - float(expected)) <= float(tolerance)
    return actual == expected


def load_notebook_assertions():
    rows = {}
    for section, value, notebook, check in build_index.parse_assertions():
        rows.setdefault((notebook, section or "-", check), []).append(value)
    return rows


def marked_consumers():
    """Return every current docs/webapp file that names a governed claim ID.

    Declared-consumer checks alone are one-way: they cannot catch a new document that copies a claim
    but is omitted from the registry.  This reverse scan is deliberately ID-based rather than another
    numeric prose scan; current consumers opt in once, then remain cheap and deterministic to audit.
    """
    found = {}
    reference_pattern = re.compile(r"TI-(?:DATA|MOD|VAL|LIM)-[0-9]{3}")
    for prefix in ("docs", "webapp"):
        base = os.path.join(ROOT, prefix)
        for directory, names, files in os.walk(base):
            names[:] = [name for name in names if name not in {"node_modules", "dist", "__pycache__"}]
            for name in files:
                if os.path.splitext(name)[1] not in CONSUMER_EXTENSIONS:
                    continue
                path = os.path.join(directory, name)
                relative = os.path.relpath(path, ROOT)
                if relative == "docs/prioritizer/CLAIM_REGISTRY.json":
                    continue
                try:
                    with open(path, encoding="utf-8") as handle:
                        claim_ids = set(reference_pattern.findall(handle.read()))
                except UnicodeDecodeError:
                    continue
                for claim_id in claim_ids:
                    found.setdefault(claim_id, set()).add(relative)
    return found


def validate(registry):
    errors = []
    pattern_text = registry.get("id_pattern", "")
    try:
        pattern = re.compile(pattern_text)
    except re.error as exc:
        fail(errors, "invalid id_pattern: %s" % exc)
        pattern = re.compile(r"a^")

    claims = registry.get("claims")
    if registry.get("schema_version") != 1:
        fail(errors, "schema_version must be 1")
    if not registry.get("tolerance_semantics"):
        fail(errors, "tolerance_semantics must explain registry matching versus live checks")
    if not isinstance(claims, list) or not claims:
        return ["claims must be a non-empty list"]

    assertions = load_notebook_assertions()
    ids = []
    for claim in claims:
        claim_id = claim.get("id", "<missing>") if isinstance(claim, dict) else "<invalid>"
        if not isinstance(claim, dict):
            fail(errors, "claim entry must be an object")
            continue
        missing = CLAIM_FIELDS - set(claim)
        extra = set(claim) - CLAIM_FIELDS
        if missing:
            fail(errors, "%s missing fields: %s" % (claim_id, ", ".join(sorted(missing))))
        if extra:
            fail(errors, "%s unknown fields: %s" % (claim_id, ", ".join(sorted(extra))))
        if not pattern.fullmatch(claim_id):
            fail(errors, "%s does not match id_pattern" % claim_id)
        ids.append(claim_id)
        if claim.get("status") != "current":
            fail(errors, "%s is not current; historical claims do not belong in this registry" % claim_id)
        if not claim.get("statement") or not claim.get("interpretation"):
            fail(errors, "%s needs a statement and interpretation" % claim_id)
        if not claim.get("review_policy"):
            fail(errors, "%s needs a review policy" % claim_id)
        measurements = claim.get("measurements")
        if not isinstance(measurements, list) or not measurements:
            fail(errors, "%s needs at least one measurement" % claim_id)
            continue
        keys = []
        for measurement in measurements:
            key = measurement.get("key", "<missing>")
            keys.append(key)
            missing_m = MEASUREMENT_FIELDS - set(measurement)
            extra_m = set(measurement) - MEASUREMENT_FIELDS
            if missing_m:
                fail(errors, "%s/%s missing fields: %s" %
                     (claim_id, key, ", ".join(sorted(missing_m))))
            if extra_m:
                fail(errors, "%s/%s unknown fields: %s" %
                     (claim_id, key, ", ".join(sorted(extra_m))))
            authority = measurement.get("authority", {})
            kind = authority.get("kind")
            expected = measurement.get("value")
            tolerance = measurement.get("absolute_tolerance")
            precision = measurement.get("display_precision")
            if isinstance(expected, (int, float)) and not isinstance(expected, bool):
                if not isinstance(precision, int) or isinstance(precision, bool) or precision < 0:
                    fail(errors, "%s/%s needs a non-negative integer display_precision" %
                         (claim_id, key))
                if not isinstance(tolerance, (int, float)) or tolerance < 0:
                    fail(errors, "%s/%s needs a non-negative numeric tolerance" % (claim_id, key))
                    continue
                # This is an authority-literal matching tolerance, not the notebook's live-data
                # tolerance. Keep it no wider than half a displayed unit so a rounded neighbour
                # cannot silently become the governed expected value.
                if isinstance(precision, int) and tolerance > 0.5 * (10 ** -precision) + 1e-15:
                    fail(errors, "%s/%s tolerance is wider than half its display unit" %
                         (claim_id, key))
            elif tolerance is not None:
                fail(errors, "%s/%s non-numeric values require null tolerance" % (claim_id, key))
                continue
            elif precision is not None:
                fail(errors, "%s/%s non-numeric values require null display_precision" %
                     (claim_id, key))
                continue
            if kind == "notebook_assertion":
                authority_fields = {"kind", "notebook", "section", "check"}
                if set(authority) != authority_fields:
                    fail(errors, "%s/%s notebook authority fields must be exactly %s" %
                         (claim_id, key, sorted(authority_fields)))
                    continue
                assertion_key = (authority["notebook"], authority["section"], authority["check"])
                candidates = assertions.get(assertion_key, [])
                if not any(same_value(value, expected, tolerance) for value in candidates):
                    fail(errors, "%s/%s has no matching notebook assertion (found %r)" %
                         (claim_id, key, candidates))
            elif kind == "repository_json":
                authority_fields = {"kind", "path", "pointer"}
                if set(authority) != authority_fields:
                    fail(errors, "%s/%s repository authority fields must be exactly %s" %
                         (claim_id, key, sorted(authority_fields)))
                    continue
                path = os.path.join(ROOT, authority["path"])
                try:
                    with open(path, encoding="utf-8") as handle:
                        actual = json_pointer(json.load(handle), authority["pointer"])
                except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                    fail(errors, "%s/%s cannot read repository authority: %s" %
                         (claim_id, key, exc))
                    continue
                if not same_value(actual, expected, tolerance):
                    fail(errors, "%s/%s authority is %r, registry says %r" %
                         (claim_id, key, actual, expected))
            else:
                fail(errors, "%s/%s has unknown authority kind %r" % (claim_id, key, kind))
        if len(keys) != len(set(keys)):
            fail(errors, "%s has duplicate measurement keys" % claim_id)

        docs = claim.get("documentation_consumers", [])
        runtime = claim.get("webapp_api_consumers", [])
        if not isinstance(docs, list) or not docs:
            fail(errors, "%s needs at least one documentation consumer" % claim_id)
            docs = []
        if not isinstance(runtime, list):
            fail(errors, "%s webapp_api_consumers must be a list" % claim_id)
            runtime = []
        if len(docs) != len(set(docs)) or len(runtime) != len(set(runtime)):
            fail(errors, "%s has duplicate consumers" % claim_id)
        for consumer in docs + runtime:
            path = os.path.join(ROOT, consumer)
            if not os.path.isfile(path):
                fail(errors, "%s consumer does not exist: %s" % (claim_id, consumer))
                continue
            with open(path, encoding="utf-8") as handle:
                if claim_id not in handle.read():
                    fail(errors, "%s consumer lacks its claim marker: %s" % (claim_id, consumer))
        for consumer in runtime:
            if not consumer.startswith("webapp/"):
                fail(errors, "%s runtime consumer is outside webapp/: %s" % (claim_id, consumer))

    if len(ids) != len(set(ids)):
        fail(errors, "claim IDs are not unique")
    category_order = {"DATA": 0, "MOD": 1, "VAL": 2, "LIM": 3}
    ordered_ids = sorted(ids, key=lambda value: (
        category_order.get(value.split("-")[1] if len(value.split("-")) > 1 else "", 99), value))
    if ids != ordered_ids:
        fail(errors, "claims must be sorted by category (DATA, MOD, VAL, LIM) and stable ID")

    declared = {
        claim["id"]: set(claim.get("documentation_consumers", [])) |
        set(claim.get("webapp_api_consumers", []))
        for claim in claims if isinstance(claim, dict) and "id" in claim
    }
    for claim_id, paths in marked_consumers().items():
        for path in sorted(paths - declared.get(claim_id, set())):
            fail(errors, "%s is referenced by an undeclared consumer: %s" % (claim_id, path))
    return errors


def render(registry):
    columns = [
        "claim_id", "status", "statement", "interpretation", "measurements",
        "documentation_consumers", "webapp_api_consumers", "review_policy",
    ]
    lines = ["\t".join(columns)]
    for claim in registry["claims"]:
        values = []
        for measurement in claim["measurements"]:
            authority = measurement["authority"]
            if authority["kind"] == "notebook_assertion":
                source = "%s:%s:%s" % (
                    authority["notebook"], authority["section"], authority["check"])
            else:
                source = "%s#%s" % (authority["path"], authority["pointer"])
            values.append("%s=%s [%s; precision=%s; authority_tol=%s] @ %s" %
                          (measurement["key"], measurement["value"], measurement["unit"],
                           measurement["display_precision"], measurement["absolute_tolerance"],
                           source))
        row = {
            "claim_id": claim["id"],
            "status": claim["status"],
            "statement": claim["statement"],
            "interpretation": claim["interpretation"],
            "measurements": " | ".join(values),
            "documentation_consumers": " | ".join(claim["documentation_consumers"]),
            "webapp_api_consumers": " | ".join(claim["webapp_api_consumers"]) or "-",
            "review_policy": claim["review_policy"],
        }
        lines.append("\t".join(str(row[column]).replace("\t", " ").replace("\n", " ")
                               for column in columns))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with open(REGISTRY, encoding="utf-8") as handle:
        registry = json.load(handle)
    errors = validate(registry)
    if errors:
        for error in errors:
            print("ERROR %s" % error, file=sys.stderr)
        return 1
    body = render(registry)
    if args.check:
        if not os.path.exists(OUTPUT) or open(OUTPUT, encoding="utf-8").read() != body:
            print("STALE index: .index/governed_claims.tsv — run tools/check_claim_registry.py",
                  file=sys.stderr)
            return 1
        print("claim registry valid and index current (%d claims)" % len(registry["claims"]))
        return 0
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        handle.write(body)
    print("wrote .index/governed_claims.tsv (%d claims)" % len(registry["claims"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
