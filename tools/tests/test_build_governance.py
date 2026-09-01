#!/usr/bin/env python3
"""Offline tests for deterministic build governance; no DSS or network access."""

import copy
import hashlib
import importlib.util
import json
import math
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "tools/tests/fixtures/build_governance")
MODULE_PATH = os.path.join(ROOT, "tools/build_governance.py")
SPEC = importlib.util.spec_from_file_location("build_governance", MODULE_PATH)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)


def read_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def different_digest(character):
    return "sha256:" + character * 64


def markdown_snapshot():
    snapshot = {}
    for directory, names, files in os.walk(ROOT):
        names[:] = [name for name in names if name not in {".git", ".venv", "node_modules"}]
        for name in files:
            if name.endswith(".md"):
                path = os.path.join(directory, name)
                with open(path, "rb") as handle:
                    snapshot[os.path.relpath(path, ROOT)] = hashlib.sha256(handle.read()).hexdigest()
    return snapshot


class BuildGovernanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = read_json(os.path.join(FIXTURES, "accepted-baseline.json"))
        cls.event = read_json(os.path.join(FIXTURES, "no-change-event.json"))
        cls.policy = read_json(governance.DEFAULT_POLICY)
        cls.registry = read_json(governance.DEFAULT_REGISTRY)

    def classify(self, mutate=None):
        event = copy.deepcopy(self.event)
        if mutate:
            mutate(event)
        return governance.classify(
            event, copy.deepcopy(self.baseline), self.policy, self.registry)

    def test_canonical_fingerprint_is_order_independent(self):
        first = {"z": [3, 2, 1], "a": {"second": 2, "first": "é"}}
        second = {"a": {"first": "é", "second": 2}, "z": [3, 2, 1]}
        self.assertEqual(governance.fingerprint_json(first), governance.fingerprint_json(second))
        with self.assertRaises(governance.GovernanceError):
            governance.fingerprint_json({"not_allowed": math.nan})

    def test_fixture_top_level_fields_match_schema_contracts(self):
        cases = [
            ("machine-event.schema.json", self.event),
            ("accepted-baseline.schema.json", self.baseline),
            ("review-packet.schema.json", self.classify()),
        ]
        schema_dir = os.path.join(ROOT, "docs/operations/build-governance")
        for schema_name, value in cases:
            with self.subTest(schema=schema_name):
                schema = read_json(os.path.join(schema_dir, schema_name))
                self.assertEqual(set(schema["required"]), set(value))
                self.assertEqual(set(schema["properties"]), set(value))

        review_schema = read_json(os.path.join(schema_dir, "review-packet.schema.json"))
        claim_packet = self.classify(
            lambda event: event["claim_values"]["TI-VAL-009"].update(
                her2_positive_auroc=0.937))
        contract_packet = self.classify(
            lambda event: event["fingerprints"]["schemas"].update(
                breast_panel_metrics=different_digest("e")))
        incident_packet = self.classify(
            lambda event: event["assertions"][0].update(status="FAIL"))
        nested = [
            ("claimDelta", claim_packet["changed_claims"][0]),
            ("contractDelta", contract_packet["changed_contracts"][0]),
            ("failedAssertion", incident_packet["failed_assertions"][0]),
        ]
        for definition, value in nested:
            with self.subTest(definition=definition):
                self.assertEqual(set(review_schema["$defs"][definition]["required"]), set(value))

    def test_all_six_classifications(self):
        cases = [
            ("NO_CHANGE", None, False),
            ("REFRESH_ONLY", lambda event: event["fingerprints"]["refresh_state"].update(
                breast_panel_metrics=different_digest("e")), False),
            ("EXPECTED_DATA_DELTA", lambda event: event["fingerprints"]["data"].update(
                breast_panel_metrics=different_digest("f")), False),
            ("CLAIM_DELTA", lambda event: event["claim_values"]["TI-VAL-009"].update(
                her2_positive_auroc=0.937), True),
            ("CONTRACT_DELTA", lambda event: event["fingerprints"]["schemas"].update(
                breast_panel_metrics=different_digest("e")), True),
            ("INCIDENT", lambda event: event["assertions"][0].update(status="FAIL"), True),
        ]
        for expected, mutate, review_required in cases:
            with self.subTest(expected=expected):
                packet = self.classify(mutate)
                self.assertEqual(expected, packet["classification"])
                self.assertEqual(review_required, packet["review_required"])
                self.assertEqual("DEMO_TARGET_IDENTIFICATION", packet["project_key"])
                self.assertEqual(["breast_panel_metrics"], packet["targets"])

    def test_claim_and_contract_packets_name_only_mapped_consumers(self):
        claim = self.classify(lambda event: event["claim_values"]["TI-VAL-009"].update(
            her2_positive_auroc=0.937))
        registered = next(item for item in self.registry["claims"] if item["id"] == "TI-VAL-009")
        expected = sorted(set(registered["documentation_consumers"] +
                              registered["webapp_api_consumers"]))
        self.assertEqual(expected, claim["consumers"])
        contract = self.classify(lambda event: event["fingerprints"]["schemas"].update(
            breast_panel_metrics=different_digest("e")))
        self.assertEqual(
            sorted(self.policy["contract_consumers"]["schema:breast_panel_metrics"]),
            contract["consumers"],
        )

    def test_missing_evidence_and_unmapped_contract_are_incidents(self):
        missing = self.classify(lambda event: event["claim_values"].clear())
        self.assertEqual("INCIDENT", missing["classification"])
        missing_check = self.classify(lambda event: event["assertions"].clear())
        self.assertEqual("INCIDENT", missing_check["classification"])
        missing_metric = self.classify(lambda event: event["metrics"].clear())
        self.assertEqual("INCIDENT", missing_metric["classification"])
        event = copy.deepcopy(self.event)
        baseline = copy.deepcopy(self.baseline)
        event["fingerprints"]["schemas"]["unmapped_output"] = different_digest("f")
        packet = governance.classify(event, baseline, self.policy, self.registry)
        self.assertEqual("INCIDENT", packet["classification"])

    def test_empty_or_omitted_capture_cannot_be_no_change(self):
        def empty_capture(event):
            for group in governance.FINGERPRINT_GROUPS:
                event["fingerprints"][group].clear()
            event["metrics"].clear()
            event["claim_values"].clear()
            event["assertions"].clear()

        self.assertEqual("INCIDENT", self.classify(empty_capture)["classification"])
        self.assertEqual(
            "INCIDENT",
            self.classify(lambda event: event["fingerprints"]["data"].clear())["classification"],
        )
        baseline = copy.deepcopy(self.baseline)
        for group in governance.FINGERPRINT_GROUPS:
            baseline["fingerprints"][group].clear()
        baseline["metrics"].clear()
        baseline["claim_values"].clear()
        baseline["required_assertions"].clear()
        with self.assertRaises(governance.GovernanceError):
            governance.classify(self.event, baseline, self.policy, self.registry)

    def test_claim_measurement_scope_is_fail_closed(self):
        extra = self.classify(
            lambda event: event["claim_values"]["TI-VAL-009"].update(unapproved=123))
        self.assertEqual("INCIDENT", extra["classification"])
        partial_baseline = copy.deepcopy(self.baseline)
        del partial_baseline["claim_values"]["TI-VAL-009"]["tnbc_known_targets"]
        packet = governance.classify(self.event, partial_baseline, self.policy, self.registry)
        self.assertEqual("INCIDENT", packet["classification"])

    def test_audit_timestamps_require_timezone(self):
        for invalid in ("not-a-timestamp", "2026-08-31T12:00:00",
                        "2026-08-31 12:00:00+00:00"):
            with self.subTest(value=invalid):
                event = copy.deepcopy(self.event)
                event["observed_at"] = invalid
                with self.assertRaises(governance.GovernanceError):
                    governance.classify(event, self.baseline, self.policy, self.registry)

    def test_frozen_graph_and_compute_kg_are_hard_denied(self):
        event = copy.deepcopy(self.event)
        baseline = copy.deepcopy(self.baseline)
        event["project_key"] = "KNOWLEDGE_GRAPH_PRIMEKG"
        baseline["project_key"] = "KNOWLEDGE_GRAPH_PRIMEKG"
        with self.assertRaises(governance.PolicyViolation):
            governance.classify(event, baseline, self.policy, self.registry)

        event = copy.deepcopy(self.event)
        event["fingerprints"]["recipe_settings"]["compute_kg"] = different_digest("f")
        with self.assertRaises(governance.PolicyViolation):
            governance.classify(event, self.baseline, self.policy, self.registry)

    def test_unlisted_part2_target_is_denied(self):
        event = copy.deepcopy(self.event)
        baseline = copy.deepcopy(self.baseline)
        event["targets"] = ["scored_champion"]
        baseline["targets"] = ["scored_champion"]
        with self.assertRaises(governance.PolicyViolation):
            governance.classify(event, baseline, self.policy, self.registry)

    def test_no_change_requires_no_review_and_writes_no_markdown(self):
        before = markdown_snapshot()
        packet = self.classify()
        after = markdown_snapshot()
        self.assertEqual("NO_CHANGE", packet["classification"])
        self.assertFalse(packet["review_required"])
        self.assertEqual("append_machine_event_only", packet["recommended_action"])
        self.assertEqual([], packet["consumers"])
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
