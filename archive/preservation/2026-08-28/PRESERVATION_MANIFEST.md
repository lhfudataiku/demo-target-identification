# Phase 0 preservation manifest — 2026-08-28

**Purpose:** Content-addressed preservation record for the documentation-restructure baseline.
**Method:** SHA-256 is computed over bytes in the listed working-tree source. A Git blob ID identifies the matching `HEAD` object where one exists. `modified` means the recorded working-tree SHA is authoritative for this snapshot, and the physical copy below is the preservation source.

## Physical snapshots

| source | archived snapshot | bytes | SHA-256 | source state |
|---|---|---:|---|---|
| `DECISIONS.md` | `DECISIONS_2026-08-28.snapshot` | 90,542 | `f1e91ab25d4c1373a754623e9218a905b0c5fb9e5704fac591f9f9b8bc96c2b2` | clean; HEAD blob `31f8044ff81362f1e37d53b0583fdaeee503c550` |
| `docs/demo/DOC_RESTRUCTURE_PLAN.md` | `DOC_RESTRUCTURE_PLAN_2026-08-28.snapshot` | 19,082 | `2b5132e4a63849e1fac85e815ceeb245b0f425ee223918c198119c2d390b47a7` | **modified**; HEAD blob before approval `cc842582ab09e07854c4055fe0c55554692630e1` |

The superseded 2026-08-26 plan was already physically archived at `archive/DOC_RESTRUCTURE_PLAN_2026-08-26.md`; it remains in place rather than being duplicated. Its captured SHA-256 is `0cc6aa07a1f16d5c60c59d99abf77a24900c4d39f767e46a8320ec780d14e28b` and its HEAD blob is `aa586f61a22e78cef1619f4bea7f4db981c367ef`.

## Versioned presentation artifacts

These files are already versioned, clean at capture, and remain in their active paths. Hash-and-blob preservation is sufficient at Phase 0: copying them would create duplicate non-authoritative mockups before the approved Phase 2 classification names the current and historical iterations.

| path | bytes | SHA-256 | HEAD blob |
|---|---:|---|---|
| `docs/demo/DASHBOARD_MOCKUP.html` | 69,363 | `ded088936d1e3120be15413977489b7531a8d8ae06a6768c7c79befc1f8174ba` | `7171e8bd65739bc9fbd8be7e4a887069767bdc80` |
| `docs/demo/DASHBOARD_MOCKUP_V2.html` | 103,585 | `42ce396cfc7409da9f42b391eaf02d57bcfc8246a8e499dc4ee5c47049437b31` | `f1c44b5a9f6fa89da6c3f10752b7f5d00e4405d3` |
| `docs/demo/DASHBOARD_MOCKUP_V3.html` | 122,424 | `7f0747a44c9c4608de0713342ed8edc0f8219447d772f15ce82878d03f1ca5f9` | `782b97103d2068b425ff0e9ca67acf8c3496e432` |
| `docs/demo/mockup_parity.html` | 14,252 | `c743f911bd956cbc3ccf1ffba83a472894044aa55a051e33ca8efc7d634ed71a` | `1791a6fb95991dac9d22f78f23608f132d818299` |
| `docs/demo/panel_selection.html` | 31,976 | `a4bc1237e96d8e35f8017c0b29616489f3d3f61d9a25d2b7955dc59e320a3eb7` | `b1981c99c3f1faaf12a368f462c772cc192133555e51` |
| `docs/demo/flow_map.html` | 37,845 | `924e1eff4db02635a30ce3e7e294da1d55fd7e533eccc3b448db782fbb3d4425` | `be155a99c3bfa05b84c455ba4daafcd0fcbb5894` |
| `archive/webapp-v1/body.html` | 6,614 | `a63e3afaa9f28aac4ab38e622b95811ba03f548e14cbd1f940b159f8942bcb0b` | `804c9512420f1f427ad2baf298889f8a92b24330` |

## Fidelity verification

Phase 0 completion requires all of the following:

1. `cmp -s` confirms both physical snapshots equal their sources.
2. SHA-256 of each physical snapshot equals the manifest.
3. SHA-256 of every listed versioned presentation artifact equals the manifest and `git diff --quiet -- <path>` reports clean.

No preservation copy is an active authority. The `.snapshot` files retain the source bytes but avoid being scanned as current Markdown by the existing broad claims index. The source documents and active mockup paths remain unchanged by this preservation action.
