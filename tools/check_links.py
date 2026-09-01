#!/usr/bin/env python3
"""Verify every relative markdown link and file mention resolves.

Built before the 2026-08-21 doc reorganisation so the move could be proven safe rather than hoped
safe. Section-reference retargeting has already bitten this repo once (refs that still resolved but
pointed at different content), so a move of nine files needed a mechanical check.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r"\[[^\]]*\]\(([^)#]+?)(?:#[^)]*)?\)")
# bare mentions of a repo markdown file, e.g. `TARGET_PRIORITIZER.md` in prose or a backtick
MENTION = re.compile(r"`?([A-Za-z0-9_./-]+\.md)`?")


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout
    return [f for f in out.split("\n") if f.strip()]


def main():
    files = tracked()
    md = [f for f in files if f.endswith(".md") and not f.startswith(".index/")]
    known = set(files)
    basenames = {}
    directories = set()
    for f in files:
        basenames.setdefault(os.path.basename(f), []).append(f)
        directory = os.path.dirname(f)
        while directory:
            directories.add(directory)
            directory = os.path.dirname(directory)

    # These two dated records name the former root DECISIONS.md as the object being migrated. Allow
    # only that historical filename; all their other file mentions still receive normal stale checks.
    ALLOWED_HISTORICAL_MENTIONS = {
        ("docs/demo/DOC_RESTRUCTURE_PLAN.md", "DECISIONS.md"),
        ("docs/operations/PHASE_0_BASELINE_2026-08-28.md", "DECISIONS.md"),
    }
    current_md = [f for f in md if not f.startswith("archive/")]
    archive_md = [f for f in md if f.startswith("archive/")]
    bad_links, archive_bad_links, bad_mentions = [], [], []
    for f in current_md + archive_md:
        d = os.path.dirname(f)
        text = open(os.path.join(ROOT, f), errors="ignore").read()
        for i, line in enumerate(text.split("\n"), 1):
            for target in LINK.findall(line):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = os.path.normpath(os.path.join(d, target))
                if resolved not in known and not os.path.exists(os.path.join(ROOT, resolved)):
                    if f.startswith("archive/"):
                        # Archives are immutable dated records. A relocated target is still
                        # recoverable when its basename exists elsewhere in the checkout; do not
                        # rewrite the old relative path merely to make it current-valid.
                        suffix = os.path.normpath(target).replace("\\", "/")
                        while suffix.startswith("../"):
                            suffix = suffix[3:]
                        suffix = suffix.lstrip("./")
                        if target.rstrip().endswith("/"):
                            candidates = [path for path in directories
                                          if path == suffix or path.endswith("/" + suffix)]
                        elif "/" in suffix:
                            candidates = [path for path in files
                                          if path == suffix or path.endswith("/" + suffix)]
                        else:
                            candidates = basenames.get(suffix, [])
                        base = os.path.basename(suffix.rstrip("/"))
                        legacy = base == "DECISIONS.md" and os.path.exists(os.path.join(
                            ROOT, "archive/decisions/DECISIONS_2026-08-31.md"))
                        if len(candidates) != 1 and not legacy:
                            archive_bad_links.append((f, i, target))
                    else:
                        bad_links.append((f, i, target))
            if f.startswith("archive/"):
                continue
            # A bare .md mention is stale if (a) its basename matches no file, or (b) it carries a
            # PATH that does not resolve. (b) was added after the 2026-08-21 reorganisation left
            # `docs/FEATURE_AUDIT.md` in prose when the file had moved to docs/prioritizer/ -- the
            # basename still matched, so the original check passed it.
            for m in MENTION.findall(line):
                if (f, m) in ALLOWED_HISTORICAL_MENTIONS:
                    continue
                base = os.path.basename(m)
                if base not in basenames and m not in known:
                    bad_mentions.append((f, i, m))
                elif "/" in m and m not in known and not os.path.exists(
                        os.path.join(ROOT, os.path.normpath(os.path.join(d, m)))):
                    bad_mentions.append((f, i, m + "  (basename exists; this PATH does not)"))

    for f, i, t in bad_links:
        print("BROKEN LINK    %s:%d -> %s" % (f, i, t))
    for f, i, t in archive_bad_links:
        print("BROKEN ARCHIVE LINK    %s:%d -> %s" % (f, i, t))
    for f, i, t in sorted(set(bad_mentions)):
        print("STALE MENTION  %s:%d -> %s" % (f, i, t))
    print("checked %d current markdown files: %d broken links, %d stale mentions; "
          "%d archive files: %d integrity-link failures"
          % (len(current_md), len(bad_links), len(set(bad_mentions)), len(archive_md), len(archive_bad_links)))
    return 1 if (bad_links or archive_bad_links or bad_mentions) else 0


if __name__ == "__main__":
    sys.exit(main())
