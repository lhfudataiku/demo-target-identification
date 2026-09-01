#!/usr/bin/env python3
"""Synchronise generated Codex and Claude instruction entry points from harness/ sources."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HEADER = "<!-- GENERATED FILE: edit the canonical harness source, then run python3 tools/sync_harness.py --write. -->\n\n"


def generated(source: Path) -> str:
    return HEADER + source.read_text()


def mappings() -> list[tuple[Path, Path, bool]]:
    return [
        (ROOT / "harness/PROJECT_INSTRUCTIONS.md", ROOT / "AGENTS.md", True),
        (ROOT / "harness/PROJECT_INSTRUCTIONS.md", ROOT / "CLAUDE.md", True),
        (ROOT / "harness/WEBAPP_OVERLAY.md", ROOT / "webapp/AGENTS.md", True),
        (ROOT / "harness/WEBAPP_OVERLAY.md", ROOT / "webapp/CLAUDE.md", True),
        (ROOT / "harness/skills/target-id/SKILL.md", ROOT / ".codex/skills/target-id/SKILL.md", False),
        (ROOT / "harness/skills/target-id/SKILL.md", ROOT / ".claude/skills/target-id/SKILL.md", False),
        (ROOT / "harness/skills/target-id/references/number-update.md", ROOT / ".codex/skills/target-id/references/number-update.md", False),
        (ROOT / "harness/skills/target-id/references/number-update.md", ROOT / ".claude/skills/target-id/references/number-update.md", False),
    ]


def expected(source: Path, include_header: bool) -> str:
    return generated(source) if include_header else source.read_text()


def write() -> int:
    for source, target, include_header in mappings():
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_symlink():
            target.unlink()
        target.write_text(expected(source, include_header))
        print(f"wrote {target.relative_to(ROOT)}")
    return 0


def check() -> int:
    stale = []
    for source, target, include_header in mappings():
        if not target.is_file() or target.read_text() != expected(source, include_header):
            stale.append(target.relative_to(ROOT).as_posix())
    if stale:
        print("stale harness copies: " + ", ".join(stale), file=sys.stderr)
        print("run: python3 tools/sync_harness.py --write", file=sys.stderr)
        return 1
    print("harness copies are current")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="write deterministic generated copies")
    group.add_argument("--check", action="store_true", help="fail if a generated copy is stale")
    args = parser.parse_args()
    return write() if args.write else check()


if __name__ == "__main__":
    raise SystemExit(main())
