#!/usr/bin/env python3
"""Check harness-copy parity, routing constraints, and the webapp cold-start budget."""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRIES = {
    "Codex": (ROOT / "AGENTS.md", ROOT / "webapp/AGENTS.md"),
    "Claude": (ROOT / "CLAUDE.md", ROOT / "webapp/CLAUDE.md"),
}
BUDGET = 3000
# Claude Code discovers the skill package; a harness without a skill mechanism can only reach it by
# path. The routing rule "load the target-ID skill first" therefore dead-ends unless the entry files
# name this file, and the traps it carries are load-bearing rather than convenience.
SKILL_PATH = "harness/skills/target-id/SKILL.md"


def words(text: str) -> int:
    return len(text.split())


def token_measure(text: str) -> tuple[int, str]:
    """Use a local tokenizer when installed; otherwise report a clearly marked proxy.

    The fallback divides UTF-8 bytes by three, deliberately more conservative than ordinary English
    BPE compression. It is repeatable but is not a guarantee of either harness's hidden tokenizer.
    """
    try:
        import tiktoken  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return math.ceil(len(text.encode("utf-8")) / 3), "conservative byte proxy (not exact tokenizer)"
    return len(tiktoken.get_encoding("cl100k_base").encode(text)), "cl100k_base"


def main() -> int:
    result = subprocess.run(
        [sys.executable, "tools/sync_harness.py", "--check"], cwd=ROOT, text=True, capture_output=True
    )
    if result.returncode:
        sys.stderr.write(result.stderr or result.stdout)
        return result.returncode

    failed = False
    for harness, paths in ENTRIES.items():
        text = "\n".join(path.read_text() for path in paths)
        # Match the old imperative only. The overlays must be able to state its negation.
        forbidden = ("**read `readme.md` first**", "read `webapp/readme.md` first")
        if any(phrase in text.lower() for phrase in forbidden):
            print(f"{harness}: unconditional README loading found", file=sys.stderr)
            failed = True
        if SKILL_PATH not in text:
            print(f"{harness}: skill unreachable without a skill mechanism -- name {SKILL_PATH}", file=sys.stderr)
            failed = True
        tokens, method = token_measure(text)
        print(
            f"{harness}: {len(text.encode('utf-8'))} bytes; {words(text)} words; "
            f"{tokens} tokens by {method}; budget {BUDGET}"
        )
        if tokens > BUDGET:
            print(f"{harness}: exceeds ordinary webapp budget", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
