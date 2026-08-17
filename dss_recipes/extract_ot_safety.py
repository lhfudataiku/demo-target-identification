# Open Targets — EXTRACT safety / tolerability annotations.
#
# The other half of target prioritisation (PROJECT_CONTEXT stage 2). Efficacy ranking says
# "this target is plausible"; this says "and here is what it would cost you".
#
# WHY NO NEW SOURCE: both signals below already live in the OT `target` parquet we ingest for
# druggability, so this is one more extraction over a file we already download. DepMap
# essentiality is the one genuinely new source and is deliberately NOT here -- get the free
# signals through the lift gate first (compute_safety_lift).
#
# Fields pulled:
#   safetyLiabilities  list<struct<event, eventId, effects:list<struct<direction, dosing>>, ...>>
#                      curated adverse-event liabilities per target.
#   constraint         list<struct<constraintType, score, exp, obs, oe, oeLower, oeUpper,
#                                 upperRank, upperBin, upperBin6>>
#                      gnomAD genetic constraint. The `lof` entry's `oe` is the
#                      observed/expected loss-of-function ratio -- low means human LoF variants
#                      are depleted, i.e. knocking this gene out is not tolerated.
#
# THE ASYMMETRY THAT GOVERNS THE SCHEMA: an absent liability is NOT evidence of safety, it
# usually means nobody looked. This is the same structural trap as the missingness leak in
# TARGET_PRIORITIZER §5 -- if a consumer treats blank as clean, it systematically favours
# under-studied genes, which is exactly the study bias the feature set was built to control.
# So `safety_assessed` is emitted SEPARATELY from `n_safety_liabilities`, and downstream must
# distinguish "assessed, nothing found" from "not assessed".
#
# NODE_INDEX SAFETY: emits a per-gene ATTRIBUTE table only. No nodes, no edges, so the graph
# and its node_index assignment are untouched.
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
COLS = ["id", "approvedSymbol", "safetyLiabilities", "constraint"]


def read_ot(subdir, columns):
    html = requests.get(BASE + subdir + "/", timeout=120, headers=HEADERS).text
    files = sorted(f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f)
    frames = []
    for f in files:
        rr = requests.get(BASE + subdir + "/" + f, timeout=600, headers=HEADERS)
        rr.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(rr.content)
            tmp = tf.name
        try:
            frames.append(pd.read_parquet(tmp, columns=columns))
        finally:
            os.remove(tmp)
    return pd.concat(frames, ignore_index=True)


t = read_ot("target", COLS)
print(f"OT target rows: {len(t):,}")


def present(v):
    """True when the field EXISTS (even if empty). Distinguishing null from empty is the whole
    point here -- an empty list means assessed-and-clean, null means never assessed."""
    return v is not None and hasattr(v, "__len__")


def n_liab(v):
    return len(v) if present(v) else None


def liab_events(v, cap=5):
    if not present(v) or len(v) == 0:
        return None
    ev = sorted({str(e.get("event")) for e in v if e.get("event")})
    s = "|".join(ev[:cap])
    return s + (f"|+{len(ev) - cap} more" if len(ev) > cap else "")


def liab_dosing(v):
    """Whether any liability is dose-related. A dose-dependent effect is manageable by
    formulation; a dose-independent one is a property of hitting the target at all."""
    if not present(v) or len(v) == 0:
        return None
    dosings = set()
    for e in v:
        # NOT `e.get("effects") or []` -- parquet gives a numpy array here, and `array or []`
        # evaluates its truth value, which raises for length > 1.
        effects = e.get("effects")
        if not present(effects):
            continue
        for eff in effects:
            if eff.get("dosing"):
                dosings.add(str(eff.get("dosing")))
    return "|".join(sorted(dosings)) if dosings else None


def constraint_field(v, ctype, field):
    if not present(v):
        return None
    for e in v:
        if e.get("constraintType") == ctype:
            return e.get(field)
    return None


out = pd.DataFrame({
    "ensg": t["id"],
    "symbol": t["approvedSymbol"],
    "safety_assessed": t.safetyLiabilities.apply(lambda v: int(present(v))),
    "n_safety_liabilities": t.safetyLiabilities.apply(n_liab),
    "safety_events": t.safetyLiabilities.apply(liab_events),
    "safety_dosing": t.safetyLiabilities.apply(liab_dosing),
    "lof_oe": t.constraint.apply(lambda v: constraint_field(v, "lof", "oe")),
    "lof_oe_upper": t.constraint.apply(lambda v: constraint_field(v, "lof", "oeUpper")),
    "lof_bin6": t.constraint.apply(lambda v: constraint_field(v, "lof", "upperBin6")),
    "mis_oe": t.constraint.apply(lambda v: constraint_field(v, "mis", "oe")),
})
out["has_safety_liability"] = (out.n_safety_liabilities.fillna(0) > 0).astype(int)

print(f"\n=== COVERAGE (of {len(out):,} OT targets) ===")
for c in ["safety_assessed", "n_safety_liabilities", "safety_events", "safety_dosing",
          "lof_oe", "lof_oe_upper", "lof_bin6", "mis_oe"]:
    print(f"  {c:24s} non-null {out[c].notna().sum():6,d}  ({out[c].notna().mean():.1%})")

n_ass = int(out.safety_assessed.sum())
n_liab_pos = int(out.has_safety_liability.sum())
print(f"\n=== the assessed / clean / flagged split (do NOT collapse these) ===")
print(f"  field present (assessed)      : {n_ass:6,d}  ({n_ass/len(out):.1%})")
print(f"    of which >=1 liability      : {n_liab_pos:6,d}")
print(f"    of which assessed and clean : {n_ass - n_liab_pos:6,d}")
print(f"  field absent (NOT assessed)   : {len(out)-n_ass:6,d}  <- blank here means unknown, not safe")

if out.n_safety_liabilities.notna().any():
    print("\n=== liability count distribution (assessed targets only) ===")
    print(out.loc[out.safety_assessed == 1, "n_safety_liabilities"]
          .value_counts().sort_index().head(10).to_string())
if out.safety_events.notna().any():
    print("\n=== most frequent liability events ===")
    ev = out.safety_events.dropna().str.split("|").explode()
    print(ev[~ev.str.startswith("+")].value_counts().head(12).to_string())
print("\n=== LoF constraint (lof_oe: low = intolerant of knockout) ===")
print(out.lof_oe.describe().to_string())

dataiku.Dataset("raw_ot_safety").write_with_schema(out)
