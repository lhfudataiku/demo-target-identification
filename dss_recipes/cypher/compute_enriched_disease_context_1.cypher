// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_disease_context_1
// inputs: DEMO_KG_LS.Lg8lbpl5
// outputs: enriched_disease_context_1

// # of D's disease_disease-neighbors that candidate g is also associated with
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20
MATCH (D)-[:disease_disease]-(D2:disease)-[:disease_protein]-(g:protein)
WHERE D2.node_index <> D.node_index
WITH g.node_index AS gene_index, D.node_index AS disease_index,
     count(DISTINCT D2.node_index) AS disease_context
RETURN gene_index, disease_index, disease_context
