// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_dwpc_GGD
// inputs: DEMO_KG_LS.Lg8lbpl5
// outputs: enriched_dwpc_GGD

// dwpc_GGD for every candidate (gene, disease) pair
// metapath g -PPI- m -assoc- D ; weight pow(deg*deg*deg*module, -0.4) ; LOO on g
// The count(DISTINCT) module_size is used ONLY to pick training diseases.
// The weight uses a scalar COUNT{} subquery (mod_raw) so the final sum() has
// no nested aggregation.

// 1) keep diseases with a real module (>= 20 protein seeds)
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20

// 2) expand the metapath from those diseases; per-node degrees via COUNT{} subqueries
MATCH (g:protein)-[:protein_protein]-(m:protein)-[:disease_protein]-(D)
WHERE m.node_index <> g.node_index
WITH g.node_index AS gene_index, D.node_index AS disease_index,
     CAST(COUNT { MATCH (g)-[:protein_protein]-() } AS DOUBLE) AS ppi_g,
     CAST(COUNT { MATCH (m)-[:protein_protein]-() } AS DOUBLE) AS ppi_m,
     CAST(COUNT { MATCH (m)-[:disease_protein]-() } AS DOUBLE) AS assoc_m,
     CAST(COUNT { MATCH (D)-[:disease_protein]-() } AS DOUBLE) AS mod_raw,
     CASE WHEN COUNT { MATCH (g)-[:disease_protein]-(D) } > 0 THEN 1 ELSE 0 END AS g_in_mod

// 3) degree-weight each path (LOO drops g from the module) and sum per pair
WITH gene_index, disease_index,
     sum( pow(ppi_g * ppi_m * assoc_m * (mod_raw - g_in_mod), -0.4) ) AS dwpc_GGD
RETURN gene_index, disease_index, dwpc_GGD
