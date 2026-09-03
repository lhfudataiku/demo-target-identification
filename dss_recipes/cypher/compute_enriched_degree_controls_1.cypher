// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_degree_controls_1
// inputs: ytvuniN8
// outputs: enriched_degree_controls_1

// per-gene hubness controls. PPI is double-stored -> /2 to recover true degree.
MATCH (g:protein)
RETURN g.node_index AS gene_index,
       CAST(COUNT { MATCH (g)-[:protein_protein]-() } AS DOUBLE) / 2.0 AS gene_ppi_degree,
       COUNT { MATCH (g)-[:disease_protein]-() }                       AS gene_n_diseases,
       COUNT { MATCH (g)-[:pathway_protein]-() }                       AS gene_n_pathways
