#!/usr/bin/env python3
"""Offline contract tests for the explicit current/history claim manifest."""

import json
import tempfile
import unittest
from unittest.mock import patch

from tools import build_index


class IndexManifestTests(unittest.TestCase):
    def test_manifest_is_explicit_and_current_paths_are_not_excluded(self):
        manifest, current, historical = build_index.load_manifest()
        self.assertTrue(current)
        self.assertTrue(historical)
        self.assertEqual(len({item["path"] for item in current}), len(current))
        excluded = manifest["current_scan_exclusions"]
        for item in current:
            self.assertNotIn(item["path"], excluded["files"])
            self.assertFalse(any(item["path"].startswith(p) for p in excluded["prefixes"]))

    def test_harness_cannot_enter_current_claim_manifest(self):
        manifest, _, _ = build_index.load_manifest()
        manifest["current_claim_documents"][0]["path"] = "AGENTS.md"
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(manifest, handle)
            handle.flush()
            with patch.object(build_index, "MANIFEST", handle.name):
                with self.assertRaisesRegex(ValueError, "excluded current claim document"):
                    build_index.load_manifest()

    def test_every_tracked_markdown_file_requires_a_manifest_role(self):
        manifest, _, _ = build_index.load_manifest()
        manifest["current_scan_exclusions"]["files"].remove(
            "docs/platform/DSS_CHEATSHEET.md")
        with tempfile.NamedTemporaryFile("w", suffix=".json") as handle:
            json.dump(manifest, handle)
            handle.flush()
            with patch.object(build_index, "MANIFEST", handle.name):
                with self.assertRaisesRegex(ValueError, "lacks a manifest role"):
                    build_index.load_manifest()

    def test_claim_rows_are_deterministic_for_manifest_paths(self):
        _, current, _ = build_index.load_manifest()
        paths = [item["path"] for item in current if item["index"] == "heuristic"]
        assertions = build_index.parse_assertions()
        self.assertEqual(build_index.build_claims(assertions, paths),
                         build_index.build_claims(assertions, list(reversed(paths))))


if __name__ == "__main__":
    unittest.main()
