// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_shared_pathway_count_1
// inputs: ytvuniN8
// outputs: enriched_shared_pathway_count_1

// pathways that contain BOTH candidate g and a module gene of D (shared-pathway overlap)
MATCH (D:disease)-[:disease_protein]-(seed:protein)
WITH D, count(DISTINCT seed.node_index) AS module_size
WHERE module_size >= 20
MATCH (g:protein)-[:pathway_protein]-(P:pathway)-[:pathway_protein]-(m:protein)-[:disease_protein]-(D)
WHERE m.node_index <> g.node_index
// distinct bridging pathways
WITH DISTINCT g, D, P                                   
WITH g.node_index AS gene_index, D.node_index AS disease_index,
     CAST(COUNT { MATCH (g)-[:pathway_protein]-() } AS DOUBLE) AS n_pathways_g,  
     count(P) AS shared_pathway_count
RETURN gene_index, disease_index,
       shared_pathway_count,
       CASE WHEN n_pathways_g > 0 THEN shared_pathway_count * 1.0 / n_pathways_g ELSE 0.0 END AS shared_pathway_frac
