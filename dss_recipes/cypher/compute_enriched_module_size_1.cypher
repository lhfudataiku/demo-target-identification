// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_module_size_1
// inputs: ytvuniN8
// outputs: enriched_module_size_1

// per-disease module size (feature-quality context + the ≥20 training scope)
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D.node_index AS disease_index, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20
RETURN disease_index, module_size
