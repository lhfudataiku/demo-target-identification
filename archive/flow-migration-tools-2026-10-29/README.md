# Flow-migration tools — archived 2026-10-29

> **Lifecycle:** Historical · **Audience:** maintainers investigating how the evidence project and the
> rebuilt serving flow were created · **Authority:** the one-shot DSS write scripts as they ran ·
> **Update when:** never, except to repair a successor pointer · **Generated dependencies:** none ·
> **Excludes:** current DSS topology, which is in
> [`../../docs/operations/FLOW_MAP.md`](../../docs/operations/FLOW_MAP.md) and
> [`../../docs/operations/FLOW_MAP_EVIDENCE.md`](../../docs/operations/FLOW_MAP_EVIDENCE.md). Do not
> load by default.

These scripts carried out the flow migration recorded in
[`../FLOW_MIGRATION_WORKPLAN.md`](../FLOW_MIGRATION_WORKPLAN.md) (`DEC-ARCH-006`, `DEC-ARCH-007`).
Each wrote to live DSS once, at the user's approval, and the migration closed on 2026-10-29. They
moved here from `tools/`; the workplan still names them by their old `tools/` path.

**Do not run them again.** Their dry runs now fail or would recreate retired objects: M6 deleted the
datasets they read and renamed the `_m4` objects they created, so a re-run collides with the
renamed objects on disk.

| script | workplan step | what it did |
|---|---|---|
| `setup_evidence_project.py` | M2 step 2 | created `DEMO_TI_EVIDENCE`, its code env, variables and `demo_identity` library |
| `build_evidence_flow.py` | M2 | created the evidence project's recipes and datasets as copies of the main project's |
| `clean_main_project.py` | M2 | removed from the main project what M2 retired or moved |
| `build_serving_m4.py` | M4 | built the rebuilt serving chains beside the old ones |
| `compare_serving_m4.py` | M4 | compared the rebuilt served datasets with the old ones (read-only) |
| `retire_serving_m6.py` | M6 | retired the old serving chains and renamed the rebuilt ones |

`tools/check_governed_values.py` still holds the evidence copies to the main project's mirrors, and
`tools/capture_webapp_payloads.py` remains in `tools/` as a reusable webapp regression check.
