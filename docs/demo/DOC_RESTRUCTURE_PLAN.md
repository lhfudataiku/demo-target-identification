# Documentation restructure — the request, and a plan to revisit

**Status: NOT STARTED.** Raised 2026-08-26, deliberately deferred so it does not block the webapp
build. This file exists so the reasoning is not lost and the work can be picked up cold.

## The problem

Part 2 of this project is three distinct kinds of work:

| | work | current home |
|---|---|---|
| 1 | **Model building** — features, split, training, the ablation ladder | `TARGET_PRIORITIZER.md` |
| 2 | **Validation** — assertions, notebooks, due diligence | split between `TARGET_PRIORITIZER.md` and the notebooks |
| 3 | **Presentation** — the demo, the webapp | `DEMO_NARRATIVE.md` + `DASHBOARD_DESIGN.md` |

`TARGET_PRIORITIZER.md` (~38k tokens) currently spans all three: model building, most of validation,
**and** some results presentation. That overlap is why it is hard to know which document to update
when a number changes, and it is the root cause of the drift this project keeps finding.

`DASHBOARD_DESIGN.md` has the mirror problem: it is named for a dashboard we are not building, and it
carries flow-and-zone material that now belongs elsewhere.

## Target state

| document | scope | explicitly not |
|---|---|---|
| `TARGET_PRIORITIZER.md` | **model building only** — features, split, training, ablation, why the champion won | validation evidence, presentation |
| *(new)* validation doc, or the notebooks themselves | **validation** — what is asserted, where, and the traps | model rationale |
| `DEMO_NARRATIVE.md` | **the story** — what we claim, in what order, in whose voice | how anything is built |
| *(renamed)* `WEBAPP_DESIGN.md` | **the webapp only** — architecture, routes, data contract per act, guardrails — plus the analytic reasoning supporting the narrative | flow/zone description, build history |
| `FLOW_MAP.md` | zones, datasets, consumers | everything else |

**The rename.** `DASHBOARD_DESIGN.md` → **`WEBAPP_DESIGN.md`**. We are building a Vue SPA deployed as a
DSS STANDARD webapp; the native-dashboard route was evaluated and rejected. The filename is the last
place still asserting otherwise.

## What is already stale in `DASHBOARD_DESIGN.md`

Found while repositioning the narrative on 2026-08-26 — fix these whenever the restructure happens,
or sooner if they mislead someone first:

1. **Acts 5 and 6 are described as app content with serving-layer needs.** They are now a talk track,
   and parts of them have moved into the notebooks (`nb6` computes the three refuted gates directly).
   The act-by-act data contract in §4 still reads as though six acts need routes.
2. **The zone description in §10 duplicates `FLOW_MAP.md`**, which is generated from live DSS. A
   hand-written copy of generated content is a drift source; §10 should shrink to a pointer plus the
   two rules the map exists to enforce.
3. **§3 mixes architecture with build history.** The "why not the native dashboard" evaluation is a
   decision, not a design — it belongs in `DECISIONS.md` with a one-line pointer here.
4. **The `60 Dashboard (serving)` zone it references no longer exists.** Serving is now `A1`–`A4` plus
   the shared `40 Candidate ranking`.

## Sequencing

**Do the webapp first.** Building it will settle questions the restructure would otherwise guess at —
which parts of the design doc are load-bearing, what the backend contract actually needs, and whether
the analytic reasoning belongs beside the design or beside the narrative.

Then, in one pass: rename, split `TARGET_PRIORITIZER.md`, shrink §10 to a pointer, move the
native-dashboard evaluation to `DECISIONS.md`, and re-run `tools/check_links.py` plus
`tools/build_index.py` — both indexes key off filenames, so the rename touches `code.tsv` and
`claims.tsv`.
