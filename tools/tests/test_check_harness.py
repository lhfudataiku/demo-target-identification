#!/usr/bin/env python3
"""Contract tests for the harness routing, budget and magnitude checks.

The routing check exists because a literal blocklist of one historical phrasing let every reworded
unconditional read through. These cases pin the property instead: an unconditional read is caught
whatever document it names, and the overlays stay able to forbid the same read.
"""

import unittest

from tools import check_harness


class UnconditionalReadTests(unittest.TestCase):
    def test_catches_the_phrasing_that_caused_the_check(self):
        # A character class excluding "." silently missed this: the dot is inside the filename.
        self.assertTrue(check_harness.unconditional_reads("**Read `README.md` first**, then classify."))
        self.assertTrue(check_harness.unconditional_reads("read `webapp/README.md` first"))

    def test_catches_rephrasings_a_blocklist_would_miss(self):
        for text in ("Always read the deployment guide.",
                     "Read the whole `TARGET_PRIORITIZER.md`.",
                     "Read the entire flow map."):
            self.assertTrue(check_harness.unconditional_reads(text), text)

    def test_an_overlay_may_still_forbid_the_same_read(self):
        for text in ("Do not read the complete `webapp/README.md` before classifying the task.",
                     "Never read the full file.",
                     "Use bounded searches rather than read the complete TSV."):
            self.assertEqual(check_harness.unconditional_reads(text), [], text)

    def test_a_conditional_read_is_allowed(self):
        for text in ("Read `docs/overview/PROJECT_CONTEXT.md` only when the contract matters.",
                     "Read one section. Classify the request first."):
            self.assertEqual(check_harness.unconditional_reads(text), [], text)


class RouteBulletTests(unittest.TestCase):
    def test_only_routing_sections_contribute_and_triggers_are_required(self):
        bullets = check_harness.route_bullets(
            "## Route by task\n- UI change: read X\n- do everything always\n## Other\n- ignored")
        self.assertEqual(bullets, ["- UI change: read X", "- do everything always"])
        self.assertEqual([b for b in bullets if ":" not in b], ["- do everything always"])


class LiveHarnessTests(unittest.TestCase):
    def test_shipped_entry_points_and_skill_pass_every_check(self):
        for _, paths in check_harness.ENTRIES.items():
            text = "\n".join(path.read_text() for path in paths)
            self.assertEqual(check_harness.unconditional_reads(text), [])
            self.assertIn(check_harness.SKILL_PATH, text)
            for bullet in check_harness.route_bullets(text):
                self.assertIn(":", bullet)
            self.assertLessEqual(check_harness.proxy_tokens(text), check_harness.BUDGET)

    def test_every_magnitude_anchor_still_matches_the_skill(self):
        text = check_harness.SKILL.read_text()
        for label, pattern, _, _ in check_harness.MAGNITUDES:
            self.assertIsNotNone(pattern.search(text), label)

    def test_budget_decisions_never_depend_on_an_installed_tokenizer(self):
        # proxy_tokens must be pure arithmetic on bytes; reference_tokens is display-only.
        self.assertEqual(check_harness.proxy_tokens("abcdef"), 2)


if __name__ == "__main__":
    unittest.main()
