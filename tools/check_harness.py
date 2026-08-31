#!/usr/bin/env python3
"""Check harness parity, routing shape, cold-start budgets and the skill's magnitude claims."""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRIES = {
    "Codex": (ROOT / "AGENTS.md", ROOT / "webapp/AGENTS.md"),
    "Claude": (ROOT / "CLAUDE.md", ROOT / "webapp/CLAUDE.md"),
}
BUDGET = 3000
SKILL = ROOT / "harness/skills/target-id/SKILL.md"
SKILL_BUDGET = 2400
# Claude Code discovers the skill package; a harness without a skill mechanism can only reach it by
# path. The routing rule "load the target-ID skill first" therefore dead-ends unless the entry files
# name this file, and the traps it carries are load-bearing rather than convenience.
SKILL_PATH = "harness/skills/target-id/SKILL.md"

# An unconditional read defeats the routing design whatever document it names, so match the shape of
# the directive rather than the single phrasing that caused it. The overlays must stay able to forbid
# the same read, so a directive negated just before it does not count.
# `(?!\. )` lets a filename's dot through while still stopping at a sentence break: the phrasing
# that caused this check, "Read `README.md` first", is invisible to a class that excludes ".".
DIRECTIVE = re.compile(
    r"\b(?:always read|read (?:(?!\. )[^\n]){0,60}? first|read the (?:complete|full|whole|entire)\b)", re.I)
NEGATION = re.compile(r"\b(?:do not|don't|never|rather than|without|instead of)\b[^.]{0,40}$", re.I)

# Rhetorical magnitudes in the entry-point skill: they justify "do not read the docs" and no claim
# index guards them, because harness material is excluded from the claim manifest by design. Each
# anchor must keep matching, so a reworded sentence fails here instead of drifting unnoticed.
MAGNITUDES = (
    ("docs corpus (description)", re.compile(r"loading about (\d+)k tokens of markdown"), "docs/", ".md"),
    ("docs corpus", re.compile(r"docs are about (\d+)k tokens"), "docs/", ".md"),
    ("recipe corpus", re.compile(r"recipes about (\d+)k"), "dss_recipes/", ""),
    ("retired chronology", re.compile(r"The (\d+)k-token retired chronology"), "archive/decisions/DECISIONS_", ".md"),
)
TOLERANCE = 0.20


def words(text: str) -> int:
    return len(text.split())


def proxy_tokens(text: str) -> int:
    """Divide UTF-8 bytes by three, deliberately more conservative than ordinary English BPE.

    This is what every budget decision uses. An installed tokenizer is reported alongside it but
    never gates, so the same commit cannot pass locally and fail in CI because one machine happens
    to have tiktoken installed for an unrelated project.
    """
    return math.ceil(len(text.encode("utf-8")) / 3)


def reference_tokens(text: str) -> str:
    try:
        import tiktoken  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        return ""
    # cl100k is an OpenAI encoding. It is a second datapoint, not either harness's real tokenizer.
    return f"; {len(tiktoken.get_encoding('cl100k_base').encode(text))} by cl100k_base (OpenAI, informational)"


def tracked(prefix: str, suffix: str) -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True).stdout
    return [ROOT / f for f in out.split("\n")
            if f.strip() and f.startswith(prefix) and f.endswith(suffix)]


def unconditional_reads(text: str) -> list[str]:
    found = []
    for match in DIRECTIVE.finditer(text):
        if NEGATION.search(text[:match.start()]):
            continue
        found.append(match.group(0).strip())
    return found


def route_bullets(text: str) -> list[str]:
    """First line of every bullet under a heading whose title mentions routing."""
    bullets, inside = [], False
    for line in text.split("\n"):
        if line.startswith("#"):
            inside = "route" in line.lower()
        elif inside and line.startswith("- "):
            bullets.append(line)
    return bullets


def check_entry(harness: str, text: str) -> bool:
    failed = False
    for directive in unconditional_reads(text):
        print(f"{harness}: unconditional read {directive!r}", file=sys.stderr)
        failed = True
    if SKILL_PATH not in text:
        print(f"{harness}: skill unreachable without a skill mechanism -- name {SKILL_PATH}", file=sys.stderr)
        failed = True
    # The design is "classify the request, then load only its authority", so a routing bullet has to
    # state the condition it routes on. A bullet with no trigger is an instruction that always fires.
    for bullet in route_bullets(text):
        if ":" not in bullet:
            print(f"{harness}: routing bullet states no condition: {bullet[:70]!r}", file=sys.stderr)
            failed = True
    tokens = proxy_tokens(text)
    print(f"{harness}: {len(text.encode('utf-8'))} bytes; {words(text)} words; "
          f"{tokens} tokens by conservative byte proxy; budget {BUDGET}{reference_tokens(text)}")
    if tokens > BUDGET:
        print(f"{harness}: exceeds ordinary webapp budget", file=sys.stderr)
        failed = True
    return failed


def check_skill() -> bool:
    failed = False
    text = SKILL.read_text()
    tokens = proxy_tokens(text)
    print(f"skill: {tokens} tokens by conservative byte proxy; budget {SKILL_BUDGET}")
    if tokens > SKILL_BUDGET:
        print(f"skill: exceeds on-demand budget", file=sys.stderr)
        failed = True
    for label, pattern, prefix, suffix in MAGNITUDES:
        match = pattern.search(text)
        if not match:
            print(f"skill: magnitude anchor missing for {label} ({pattern.pattern})", file=sys.stderr)
            failed = True
            continue
        claimed = int(match.group(1)) * 1000
        measured = math.ceil(sum(p.stat().st_size for p in tracked(prefix, suffix)) / 3)
        if not measured:
            print(f"skill: {label} measures nothing -- prefix {prefix!r} matched no tracked file", file=sys.stderr)
            failed = True
            continue
        drift = abs(claimed - measured) / measured
        status = "ok" if drift <= TOLERANCE else "DRIFTED"
        print(f"skill: {label} claims {claimed:,}, measures {measured:,} ({drift:.0%}) {status}")
        if drift > TOLERANCE:
            print(f"skill: {label} claim is {drift:.0%} off, tolerance {TOLERANCE:.0%}", file=sys.stderr)
            failed = True
    return failed


def main() -> int:
    result = subprocess.run(
        [sys.executable, "tools/sync_harness.py", "--check"], cwd=ROOT, text=True, capture_output=True
    )
    if result.returncode:
        sys.stderr.write(result.stderr or result.stdout)
        return result.returncode

    failed = False
    for harness, paths in ENTRIES.items():
        if check_entry(harness, "\n".join(path.read_text() for path in paths)):
            failed = True
    if check_skill():
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
