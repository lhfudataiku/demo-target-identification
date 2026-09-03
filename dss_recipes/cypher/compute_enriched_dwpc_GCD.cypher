// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_dwpc_GCD
// inputs: ytvuniN8
// outputs: enriched_dwpc_GCD

// dwpc_GCD for every candidate (gene, disease) pair
// metapath  g -targeted by- C(drug) -indication|drug_investigated_for- D(disease)
// weight    pow( drug_g * target_C * ind_C * dind_D, -0.4 )
// UPDATED 2026-08-06: drug_investigated_for now included alongside indication
// (both approved AND investigational drug-disease links) -- see decision to add
// drug_investigated_for to the graph, TARGET_PRIORITIZER.md §11. No LOO: metapath
// never touches g's disease_protein edge, so there is no label leakage.

// 1) same disease scope as GGD/GPGD (>= 20 seeds) so the join keys line up
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20

// 2) shared-drug metapath + per-node degrees via COUNT{} subqueries
MATCH (g:protein)-[:drug_protein]-(C:drug)-[:indication|drug_investigated_for]-(D)
WITH g.node_index AS gene_index, D.node_index AS disease_index,
     CAST(COUNT { MATCH (g)-[:drug_protein]-() } AS DOUBLE) AS drug_g,
     CAST(COUNT { MATCH (C)-[:drug_protein]-() } AS DOUBLE) AS target_C,
     CAST(COUNT { MATCH (C)-[:indication|drug_investigated_for]-() } AS DOUBLE) AS ind_C,
     CAST(COUNT { MATCH (D)-[:indication|drug_investigated_for]-() } AS DOUBLE) AS dind_D

// 3) degree-weight each path and sum per pair
WITH gene_index, disease_index,
     sum( pow(drug_g * target_C * ind_C * dind_D, -0.4) ) AS dwpc_GCD
RETURN gene_index, disease_index, dwpc_GCD

