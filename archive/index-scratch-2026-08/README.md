# Index scratch files — archived 2026-10-29

> **Lifecycle:** Historical · **Audience:** maintainers investigating early webapp and flow mapping ·
> **Authority:** none; working files preserved as they were · **Update when:** never · **Generated
> dependencies:** none · **Excludes:** every current index, listed in `../../.index/index_metadata.tsv`.
> Do not load by default.

These four JSON files sat in `.index/` without being generated, read or checked by any tool. They
were moved here so that `.index/` holds only indexes that `index_metadata.tsv` describes.

| file | last changed | what it was |
|---|---|---|
| `_map.json` | 2026-08-26 | an early dataset-to-zone map; the zone names predate the 2026-10-29 flow migration. Superseded by [`../../docs/operations/FLOW_MAP.md`](../../docs/operations/FLOW_MAP.md) |
| `_z90.json` | 2026-08-25 | a prune list for the old zone 90 |
| `_mockup_cards.json` | 2026-08-26 | the card inventory of the dashboard mockups in [`../dashboard-mockup-iterations/`](../dashboard-mockup-iterations/) |
| `_webapp_cards.json` | 2026-09-03 | the card inventory of the first webapp; the webapp was redesigned in October |

`.index/_dead.json` stayed in place: the flow map and its generator read it.
