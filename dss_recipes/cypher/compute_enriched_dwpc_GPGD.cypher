// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_dwpc_GPGD
// inputs: ytvuniN8
// outputs: enriched_dwpc_GPGD

// dwpc_GPGD for every candidate (gene, disease) pair
// metapath  g -in- P(pathway) -contains- m(gene) -assoc- D(disease)
// weight    pow( path_g * path_P^2 * path_m * assoc_m * mod_D, -0.4 )
//           P sits on two pathway_protein metaedges -> weighted twice
// LOO       m <> g  (m=g would traverse g's own disease_protein edge = leak)
//           AND module-size drops g  (mod_raw - g_in_mod)

// 1) training diseases (>= 20 protein seeds) -- filter only
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20

// 2) shared-pathway metapath + per-node degrees via COUNT{} subqueries
MATCH (g:protein)-[:pathway_protein]-(P:pathway)-[:pathway_protein]-(m:protein)-[:disease_protein]-(D)
WHERE m.node_index <> g.node_index
WITH g.node_index AS gene_index, D.node_index AS disease_index,
     CAST(COUNT { MATCH (g)-[:pathway_protein]-() } AS DOUBLE) AS path_g,
     CAST(COUNT { MATCH (P)-[:pathway_protein]-() } AS DOUBLE) AS path_P,
     CAST(COUNT { MATCH (m)-[:pathway_protein]-() } AS DOUBLE) AS path_m,
     CAST(COUNT { MATCH (m)-[:disease_protein]-() } AS DOUBLE) AS assoc_m,
     CAST(COUNT { MATCH (D)-[:disease_protein]-() } AS DOUBLE) AS mod_raw,
     CASE WHEN COUNT { MATCH (g)-[:disease_protein]-(D) } > 0 THEN 1 ELSE 0 END AS g_in_mod

// 3) degree-weight each path (P twice; LOO on module) and sum per pair
WITH gene_index, disease_index,
     sum( pow(path_g * path_P * path_P * path_m * assoc_m * (mod_raw - g_in_mod), -0.4) ) AS dwpc_GPGD
RETURN gene_index, disease_index, dwpc_GPGD
