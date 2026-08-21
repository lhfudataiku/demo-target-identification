# Head-to-head comparison harness: DEMO_KG_LS (reconstruction) vs
# KNOWLEDGE_GRAPH_PRIMEKG (reference implementation).
#
# WHY: the graph project is being rebuilt from live sources, so it will NOT reproduce the
# reference's `node_index` (five of nine sources are unpinned "latest" endpoints -- see
# PROJECT_CONTEXT §5.1). The acceptance criterion is therefore STRUCTURAL, not exact:
# counts within tolerance, identical node-type/node-source inventory, identical relation
# inventory, and comparison keyed on NATIVE IDS rather than integers.
#
# WHY `kg` IS THE COMPARISON SURFACE: `graph_edges` is (relation, x_index, y_index) -- pure
# indices, meaningless across projects. `kg` carries the same edges with x_id/x_type/x_source
# and y_id/y_type/y_source alongside, so it can be compared without touching an index.
#
# Run this after each rebuilt zone. Datasets not yet built on the new side are reported as
# PENDING rather than failing the run, so the first execution doubles as a baseline capture.
import dataiku
import pandas as pd

REF = "KNOWLEDGE_GRAPH_PRIMEKG"

# natural keys are index-free by design; None = compare shape only
DATASETS = {
    "mondo_terms": ["mondo_id"], "mondo_references": None, "raw_disease_disease": None,
    "mondo_edges": None, "hpo_terms": ["hpo_id"], "raw_phenotype_hierarchy": None,
    "raw_phenotype_hierarchy_filtered": None, "raw_disease_phenotype": None,
    "raw_disease_phenotype_normalized": None, "raw_phenotype_protein": None,
    "go_terms": ["go_id"], "raw_go_hierarchy": None, "raw_go_protein": None,
    "go_terms_": None, "go_hierarchy_edges": None, "go_protein_edges": None,
    "reactome_terms": None, "raw_pathway_pathway": None, "raw_pathway_protein": None,
    "reactome_gp_edges": None, "reactome_pp_edges": None,
    "gene_names": None, "raw_ppi_merged": None, "raw_menche_ppi": None,
    "raw_huri_ppi": None, "raw_string_ppi": None, "ppi_edges": None,
    "raw_ot_assoc": None, "ot_disease_map": None, "ot_target_map": None,
    "gd_maps": None, "gd_joined": None, "gene_disease_edges": None,
    "raw_drug_indication": None, "raw_drug_protein": None, "drug_vocab": None,
    "dp_target": None, "dp_joined": None, "dp_grounded": None,
    "dp_grounded_with_overlap": None, "drug_disease_edges": None, "drug_protein_edges": None,
    "hp_mondo_overlap_raw": None, "hp_mondo_overlap": None,
    "ph_parent_checked": None, "ph_parent_checked_clean": None, "ph_both_checked": None,
    "phenotype_hierarchy_edges": None, "phenotype_protein_with_overlap": None,
    "phenotype_protein_edges": None, "phenotype_protein_edges_distinct": None,
    "disease_phenotype_edges": None, "disease_phenotype_edges_distinct": None,
    "disease_group_map": ["node_id"],
    # the four outputs of compute_kg
    "graph_nodes": ["node_id", "node_type", "node_source"],
    "graph_edges": None,                       # indices only -- shape + relation mix only
    "kg": None,                                # inventories computed separately below
    "edge_metadata": None,
}
TOLERANCE_PCT = 2.0          # structural, not exact: flag drift beyond this


def load(project, name, columns=None):
    try:
        ds = dataiku.Dataset(f"{project}.{name}") if project else dataiku.Dataset(name)
        return ds.get_dataframe(columns=columns) if columns else ds.get_dataframe()
    except Exception as e:
        return str(e)


rows = []
for name, key in DATASETS.items():
    ref = load(REF, name)
    new = load(None, name)
    rec = {"dataset": name,
           "rows_ref": len(ref) if isinstance(ref, pd.DataFrame) else None,
           "rows_new": len(new) if isinstance(new, pd.DataFrame) else None}
    if not isinstance(ref, pd.DataFrame):
        rec["status"] = "REF UNREADABLE"; rec["detail"] = ref[:120]
    elif not isinstance(new, pd.DataFrame):
        rec["status"] = "PENDING"; rec["detail"] = "not built on the new side yet"
    else:
        cr, cn = set(ref.columns), set(new.columns)
        rec["cols_only_ref"] = ",".join(sorted(cr - cn))[:120]
        rec["cols_only_new"] = ",".join(sorted(cn - cr))[:120]
        d = 100.0 * (len(new) - len(ref)) / max(len(ref), 1)
        rec["delta_pct"] = round(d, 3)
        flags = []
        if cr != cn:
            flags.append("SCHEMA DIFF")
        if abs(d) > TOLERANCE_PCT:
            flags.append(f"COUNT DRIFT {d:+.2f}%")
        if key and cr == cn:
            kr = set(map(tuple, ref[key].astype(str).values))
            kn = set(map(tuple, new[key].astype(str).values))
            rec["key_only_ref"] = len(kr - kn)
            rec["key_only_new"] = len(kn - kr)
            if kr != kn:
                flags.append(f"KEY DIFF -{len(kr-kn)}/+{len(kn-kr)}")
        rec["status"] = " | ".join(flags) if flags else "MATCH"
    rows.append(rec)

out = pd.DataFrame(rows)
print("=== per-dataset comparison ===")
cols = [c for c in ["dataset", "rows_ref", "rows_new", "delta_pct", "status"] if c in out]
print(out[cols].to_string(index=False))
pend = int((out.status == "PENDING").sum())
print(f"\n{pend} of {len(out)} datasets not yet built on the new side")

# ---- inventories: the structural checks that matter most -------------------------
def inventory(project, name, cols, label):
    df = load(project, name, columns=cols)
    if not isinstance(df, pd.DataFrame):
        print(f"  {label}: unavailable ({str(df)[:60]})")
        return None
    return df.groupby(cols).size().rename("n")

print("\n=== graph_nodes: node_type x node_source ===")
a = inventory(REF, "graph_nodes", ["node_type", "node_source"], "reference")
b = inventory(None, "graph_nodes", ["node_type", "node_source"], "new")
if a is not None:
    inv = pd.concat({"ref": a, "new": b} if b is not None else {"ref": a}, axis=1).fillna(0)
    if b is not None:
        inv["delta"] = inv["new"] - inv["ref"]
    print(inv.astype(int).to_string())

print("\n=== kg: relation inventory (index-free) ===")
a = inventory(REF, "kg", ["relation"], "reference")
b = inventory(None, "kg", ["relation"], "new")
if a is not None:
    inv = pd.concat({"ref": a, "new": b} if b is not None else {"ref": a}, axis=1).fillna(0)
    if b is not None:
        inv["delta"] = inv["new"] - inv["ref"]
    print(inv.astype(int).to_string())

dataiku.Dataset("reference_comparison").write_with_schema(out)
