#!/bin/sh
# Verify every generated index is current. Suitable for a pre-commit hook:
#   ln -s ../../tools/check_indexes.sh .git/hooks/pre-commit
#
# Order matters: build_index.py emits .index/assertions.tsv, which build_recipe_index.py reads to
# cross-check the champion's recorded metrics. Run the doc index first.
set -e
cd "$(dirname "$0")/.."
python3 tools/build_index.py --check
python3 tools/check_claim_registry.py --check
python3 tools/build_recipe_index.py --check
python3 tools/check_governed_values.py
python3 tools/check_harness.py
python3 tools/check_links.py

# ── Checks that need a live DSS ───────────────────────────────────────────────
# Everything above reads the committed .index/dss_snapshot.json and needs no
# credentials, no network and no `dku`. The three below query DSS through the
# `dku` CLI, so they cannot run on a CI runner -- and when they were added to
# this script (f3123dc, c313301, 30b272c) they turned every GitHub check red
# with `FileNotFoundError: 'dku'`, masking the checks that DO work there.
#
# They are skipped when `dku` is absent, and the skip is printed rather than
# silent: a check that quietly does not run is worse than one that fails.
# Set REQUIRE_DSS_CHECKS=1 to make a missing `dku` an error instead -- use that
# in a pre-commit hook, where the CLI is expected to be there.
if command -v dku >/dev/null 2>&1; then
  # FLOW_MAP.md is generated from live DSS, so --check queries DSS.
  python3 tools/build_flow_map.py --check
  # The DSS project library holds a generated copy of notebooks/*.py that the
  # validate_notebooks scenario executes. Catch repo/library drift here, because a
  # stale library copy means the scenario is asserting against code nobody reviewed.
  python3 tools/push_assertions.py --check
  # Dataset and column descriptions live in tools/dataset_descriptions.json, not only in DSS, so a
  # stale one is visible in review. Feature wording comes from webapp/backend/feature_glossary.py.
  python3 tools/push_descriptions.py --check
elif [ "${REQUIRE_DSS_CHECKS:-0}" = "1" ]; then
  echo "REQUIRE_DSS_CHECKS=1, but 'dku' is not on PATH" >&2
  exit 1
else
  echo "SKIPPED, no 'dku' on PATH: FLOW_MAP.md, assertion library, dataset descriptions"
  echo "  These query live DSS. Run tools/check_indexes.sh locally before merging a change"
  echo "  to the flow, notebooks/*.py or tools/dataset_descriptions.json."
fi
