#!/bin/sh
# Verify every generated index is current. Suitable for a pre-commit hook:
#   ln -s ../../tools/check_indexes.sh .git/hooks/pre-commit
#
# Order matters: build_index.py emits .index/assertions.tsv, which build_recipe_index.py reads to
# cross-check the champion's recorded metrics. Run the doc index first.
set -e
cd "$(dirname "$0")/.."
python3 tools/build_index.py --check
python3 tools/build_recipe_index.py --check
python3 tools/check_harness.py
python3 tools/check_links.py
