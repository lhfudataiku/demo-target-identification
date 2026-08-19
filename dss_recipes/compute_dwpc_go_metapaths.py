# dwpc_GFGD + dwpc_GBGD — GO molecular-function / biological-process metapaths (Python).
#
# Replaces the Execute Cypher route, which OOM'd Kuzu's buffer pool: GO fans out far harder
# than Reactome (bioprocess_protein 251,858 edges and molfunc_protein 156,248 vs
# pathway_protein's 97,618; GO:0005515 "protein binding" alone annotates >10k genes), so the
# engine materializes an enormous path set before aggregating. Same precedent as
# compute_enriched_prox_closest_bfs_test and compute_enriched_rwr_score_1.
#
# METAPATH  g -<ann>_protein- A -<ann>_protein- m -disease_protein- D
# WEIGHT    pow( ann_g * ann_A^2 * ann_m * assoc_m * mod_D_loo, -0.4 )   (A on two metaedges -> squared)
# LOO       m <> g, and the module size drops g:  mod_D_loo = mod_raw(D) - [g in module(D)]
#
# WHY THIS IS CHEAP: the weight FACTORIZES, so the path sum never needs the gene x gene
# similarity matrix (which is what blows up -- sum_A deg_A^2 can reach ~10^8 nonzeros).
# Associating right-to-left keeps every intermediate small:
#     S = X @ (W_A @ (X.T @ (W_m @ Z)))
#       X: genes x annotations,  Z: genes x diseases
#     X.T @ (W_m @ Z)  ->  annotations x diseases   (~10k x 1.2k)
#     X   @ (...)      ->  genes x diseases         (~21k x 1.2k, the answer)
# then  dwpc(g,D) = ann_g^-0.4 * mod_D_loo^-0.4 * (S(g,D) - T(g,D))
# with  T the m == g self-path removed analytically (no masking pass needed).
import dataiku
import numpy as np
import pandas as pd
from scipy import sparse

DAMPING = -0.4
MIN_MODULE = 20
MAX_FANOUT = 500          # skip promiscuous GO terms; see module docstring

# Dataset DEMO_KG_LS.graph_edges renamed to DEMO_KG_graph_edges_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:18
# Dataset DEMO_KG_graph_edges_copy renamed to graph_edges by liheng.fu@dataiku.com on 2026-08-18 09:56:56
edges = dataiku.Dataset("graph_edges").get_dataframe(columns=["relation", "x_index", "y_index"])
# Dataset DEMO_KG_LS.graph_nodes renamed to DEMO_KG_graph_nodes_copy by liheng.fu@dataiku.com on 2026-08-18 09:38:35
# Dataset DEMO_KG_graph_nodes_copy renamed to graph_nodes by liheng.fu@dataiku.com on 2026-08-18 09:56:41
nodes = dataiku.Dataset("graph_nodes").get_dataframe(columns=["node_index", "node_type"])
genes = set(nodes.loc[nodes.node_type == "gene/protein", "node_index"])


def undirected_pairs(rel, left_types, right_types):
    """graph_edges is reverse-all'd; return one row per (left, right) with left of left_types."""
    e = edges.loc[edges.relation == rel, ["x_index", "y_index"]]
    left_ok = e.x_index.isin(left_types)
    return pd.DataFrame({
        "left": np.where(left_ok, e.x_index, e.y_index),
        "right": np.where(left_ok, e.y_index, e.x_index),
    }).drop_duplicates()


# ---- disease side (shared by both metapaths) --------------------------------
gd = undirected_pairs("disease_protein", genes, None).rename(
    columns={"left": "gene_index", "right": "disease_index"})
mod_raw = gd.groupby("disease_index").size()
eligible = mod_raw[mod_raw >= MIN_MODULE].index.to_numpy()
gd = gd[gd.disease_index.isin(set(eligible))]
assoc = gd.groupby("gene_index").size()          # disease_protein degree per gene

gene_ids = np.array(sorted(genes))
gpos = pd.Series(np.arange(len(gene_ids)), index=gene_ids)
dpos = pd.Series(np.arange(len(eligible)), index=eligible)

Z = sparse.csr_matrix(
    (np.ones(len(gd)), (gpos.loc[gd.gene_index].to_numpy(), dpos.loc[gd.disease_index].to_numpy())),
    shape=(len(gene_ids), len(eligible)))
Z.sum_duplicates(); Z.data[:] = 1.0

assoc_vec = np.zeros(len(gene_ids))
assoc_vec[gpos.loc[assoc.index].to_numpy()] = assoc.to_numpy()
mod_vec = mod_raw.loc[eligible].to_numpy().astype(float)


def dwpc(ann_relation, ann_type, out_name):
    ann_nodes = set(nodes.loc[nodes.node_type == ann_type, "node_index"])
    ga = undirected_pairs(ann_relation, genes, None).rename(
        columns={"left": "gene_index", "right": "ann_index"})
    ga = ga[ga.ann_index.isin(ann_nodes) & ga.gene_index.isin(genes)]

    fan = ga.groupby("ann_index").size()
    keep = fan[fan <= MAX_FANOUT].index
    dropped = len(fan) - len(keep)
    ga = ga[ga.ann_index.isin(set(keep))]
    print(f"[{out_name}] {ann_relation}: {len(fan)} terms, dropped {dropped} with fanout >{MAX_FANOUT}; "
          f"{len(ga)} gene-annotation pairs retained")

    ann_ids = np.array(sorted(set(ga.ann_index)))
    apos = pd.Series(np.arange(len(ann_ids)), index=ann_ids)
    X = sparse.csr_matrix(
        (np.ones(len(ga)), (gpos.loc[ga.gene_index].to_numpy(), apos.loc[ga.ann_index].to_numpy())),
        shape=(len(gene_ids), len(ann_ids)))
    X.sum_duplicates(); X.data[:] = 1.0

    ann_g = np.asarray(X.sum(axis=1)).ravel()     # annotation degree per gene
    ann_A = np.asarray(X.sum(axis=0)).ravel()     # fanout per annotation term

    def p(v):                                      # v ** -0.4, safe at 0
        out = np.zeros_like(v, dtype=float)
        nz = v > 0
        out[nz] = np.power(v[nz], DAMPING)
        return out

    W_m = sparse.diags(p(ann_g) * p(assoc_vec))    # weights on the middle gene m
    W_A = sparse.diags(np.power(ann_A, 2 * DAMPING, where=ann_A > 0,
                                out=np.zeros_like(ann_A, dtype=float)))

    # right-to-left: never materialize genes x genes
    S = X @ (W_A @ (X.T @ (W_m @ Z)))              # genes x diseases
    S = np.asarray(S.todense()) if sparse.issparse(S) else np.asarray(S)

    # remove the m == g self-path: contributes (sum_A X[g,A]*ann_A^-0.8) * W_m[g] where Z[g,D]=1
    self_term = np.asarray((X @ W_A).multiply(X).sum(axis=1)).ravel() * (p(ann_g) * p(assoc_vec))
    S -= np.asarray(Z.todense()) * self_term[:, None]

    zdense = np.asarray(Z.todense())
    mod_loo = mod_vec[None, :] - zdense            # LOO drops g from its own module
    scale = p(ann_g)[:, None] * p(mod_loo)
    out = S * scale

    gi, di = np.nonzero(out > 0)
    res = pd.DataFrame({"gene_index": gene_ids[gi], "disease_index": eligible[di],
                        out_name: out[gi, di]})
    print(f"[{out_name}] rows: {len(res):,}")
    print(res[out_name].describe().to_string())
    dataiku.Dataset(f"enriched_{out_name}").write_with_schema(res)


dwpc("molfunc_protein", "molecular_function", "dwpc_GFGD")
dwpc("bioprocess_protein", "biological_process", "dwpc_GBGD")

