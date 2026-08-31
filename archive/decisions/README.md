# Historical decision log

> **Lifecycle:** Historical · **Audience:** maintainers investigating why a choice was made ·
> **Authority:** preservation and triage metadata for the retired turn-by-turn log · **Update when:**
> a preservation error is found; never rewrite the archived log · **Successor:**
> [`docs/decisions/DECISION_REGISTER.md`](../../docs/decisions/DECISION_REGISTER.md).

`DECISIONS_2026-08-31.md` is the former root `DECISIONS.md`, retired during Phase 4 of the
documentation restructure. Its contents are unchanged: 90,542 bytes, SHA-256
`f1e91ab25d4c1373a754623e9218a905b0c5fb9e5704fac591f9f9b8bc96c2b2`. Corrections and reversals
remain exactly where they were recorded.

The archived log is chronology, not current guidance. Query `.index/decisions_history.tsv` for a
classified jump table. Query `.index/decisions.tsv` for current durable decisions.

`TRIAGE.json` classifies every one of the 158 dated entries using the approved migration routes.
Classification does not alter the historical record and is mechanically checked by
`tools/build_index.py`. The generated historical index exposes both the category and successor
route, so a search does not require loading the archived log merely to decide where current truth
lives.

`PROJECT_CONTEXT_DECISION_APPENDIX_2026-08-31.md` preserves the former project-context appendix
byte-for-byte before its durable choices were routed into the register. It is 5,243 bytes, SHA-256
`25c4df1faf7f9f91329038ded4040f4397efaeac3fdbf14f59bdffa26014d169`. It remains supplemental
history; `.index/decisions_history.tsv` classifies the retired root log that triggered this phase.
