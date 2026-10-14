# Zone-10 feature signature capture. Read-only: opens each dataset, emits an
# order-independent fingerprint. No dataset is written and no recipe is run.
#
# Two signatures per dataset, deliberately:
#   row_xor  -- XOR of per-row uint64 hashes. Exact and order-independent, so it
#               catches any content change, but it is bit-strict: a difference in
#               float summation order inside Kuzu would flip it while being
#               numerically irrelevant.
#   agg      -- count / min / max / sum-of-rounded per numeric column. Tolerant of
#               last-bit float noise. If row_xor differs but agg matches, the
#               change is benign float ordering, not content.
import json
import numpy as np
import pandas as pd
import dataiku

DATASETS = [
    "enriched_degree_controls_1",
    "enriched_disease_context_1",
    "enriched_dwpc_GCD",
    "enriched_dwpc_GGD",
    "enriched_dwpc_GPGD",
    "enriched_guilt_by_association_1",
    "enriched_has_inflammatory_go_annotation_1",
    "enriched_module_size_1",
    "enriched_node_centrality_1",
    "enriched_shared_pathway_count_1",
]

ROUND_DP = 8

def signature(name):
    ds = dataiku.Dataset(name)
    n_rows = 0
    xor = np.uint64(0)
    xor_r = np.uint64(0)
    cols = None
    acc = {}
    for chunk in ds.iter_dataframes(chunksize=500000):
        if cols is None:
            cols = [str(c) for c in chunk.columns]
        n_rows += len(chunk)
        h = pd.util.hash_pandas_object(chunk, index=False).values.astype(np.uint64)
        if len(h):
            xor = np.bitwise_xor(xor, np.bitwise_xor.reduce(h))
        rounded = chunk.copy()
        for c in rounded.columns:
            if pd.api.types.is_float_dtype(rounded[c]):
                rounded[c] = rounded[c].round(6)
        hr = pd.util.hash_pandas_object(rounded, index=False).values.astype(np.uint64)
        if len(hr):
            xor_r = np.bitwise_xor(xor_r, np.bitwise_xor.reduce(hr))
        for c in chunk.columns:
            s = chunk[c]
            if not pd.api.types.is_numeric_dtype(s):
                continue
            a = acc.setdefault(str(c), {"nonnull": 0, "min": None, "max": None, "sum": 0.0})
            v = s.dropna()
            a["nonnull"] += int(v.shape[0])
            if v.shape[0]:
                lo, hi = float(v.min()), float(v.max())
                a["min"] = lo if a["min"] is None else min(a["min"], lo)
                a["max"] = hi if a["max"] is None else max(a["max"], hi)
                a["sum"] += float(np.round(v.astype("float64"), ROUND_DP).sum())
    for c in acc:
        acc[c]["sum"] = round(acc[c]["sum"], 4)
        if acc[c]["min"] is not None:
            acc[c]["min"] = round(acc[c]["min"], ROUND_DP)
            acc[c]["max"] = round(acc[c]["max"], ROUND_DP)
    return {"rows": n_rows, "columns": cols, "row_xor": str(int(xor)),
            "row_xor_round6": str(int(xor_r)), "agg": acc}

out = {}
for name in DATASETS:
    try:
        out[name] = signature(name)
        print("OK   " + name + "  rows=" + str(out[name]["rows"])
              + "  xor=" + out[name]["row_xor"]
              + "  xor6=" + out[name]["row_xor_round6"])
    except Exception as exc:
        out[name] = {"error": repr(exc)}
        print("FAIL " + name + "  " + repr(exc))

print("BEGIN_SIGNATURE_JSON")
print(json.dumps(out, sort_keys=True))
print("END_SIGNATURE_JSON")
