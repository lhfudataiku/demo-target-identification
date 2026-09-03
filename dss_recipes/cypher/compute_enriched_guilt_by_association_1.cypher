// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_guilt_by_association_1
// inputs: ytvuniN8
// outputs: enriched_guilt_by_association_1

// ppi neighbor-overlap features (guilt-by-association):
//   ppi_common_neighbors = |N_PPI(g) ∩ module(D)|
//   ppi_adamic_adar      = Σ_{m in overlap} 1/log(deg_PPI(m))
//   ppi_jaccard          = |overlap| / |N_PPI(g) ∪ module(D)|
// LOO: m <> g, and module excludes g in the Jaccard union (module_size - g_in_mod).
// PPI is stored BOTH directions in this Kuzu build (verified) -> undirected COUNT{} PPI
//   degree is 2x true, so /2.0; WITH DISTINCT collapses the doubled (g,m) edge.
//   disease_protein is single-stored -> no correction.

// 1) training diseases (>= 20 seeds)
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20

// 2) g's PPI neighbors that are module genes of D (collapse the doubled PPI edge)
MATCH (g:protein)-[:protein_protein]-(m:protein)-[:disease_protein]-(D)
WHERE m.node_index <> g.node_index
WITH DISTINCT g, m, D, module_size

// 3) true PPI degree of each shared neighbor m
WITH g, D, module_size, m,
     (CAST(COUNT { MATCH (m)-[:protein_protein]-() } AS DOUBLE) / 2.0) AS deg_m

// 4) aggregate over shared neighbors; carry per-(g,D) scalars as grouping keys
WITH g.node_index AS gene_index, D.node_index AS disease_index, module_size,
     (CAST(COUNT { MATCH (g)-[:protein_protein]-() } AS DOUBLE) / 2.0)               AS ppi_deg_g,
     (CASE WHEN COUNT { MATCH (g)-[:disease_protein]-(D) } > 0 THEN 1 ELSE 0 END)    AS g_in_mod,
     count(m)                                                                         AS ppi_common_neighbors,
     sum(CASE WHEN deg_m > 1.0 THEN 1.0 / log(deg_m) ELSE 0.0 END)                    AS ppi_adamic_adar

// 5) Jaccard from the union size (module excludes g via g_in_mod)
WITH gene_index, disease_index, ppi_common_neighbors, ppi_adamic_adar,
     (ppi_deg_g + (module_size - g_in_mod) - ppi_common_neighbors) AS union_size
RETURN gene_index, disease_index,
       ppi_common_neighbors,
       ppi_adamic_adar,
       CASE WHEN union_size > 0 THEN ppi_common_neighbors * 1.0 / union_size ELSE 0.0 END AS ppi_jaccard
