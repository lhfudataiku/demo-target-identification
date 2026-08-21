// MIRRORED FROM DSS by tools/build_recipe_index.py --refresh. Do not edit here:
// this file is a copy for review and grep. The live query is in the DSS recipe.
// recipe: compute_enriched_inflammatory_go
// inputs: DEMO_KG_LS.Lg8lbpl5
// outputs: enriched_has_inflammatory_go_annotation_1

MATCH (bp:biological_process)
WHERE bp.node_name CONTAINS "inflamm"
   OR bp.node_name CONTAINS "cytokine"
   OR bp.node_name CONTAINS "interleukin"
   OR bp.node_name CONTAINS "tumor necrosis factor"
   OR bp.node_name CONTAINS "chemokine"
   OR bp.node_name CONTAINS "NF-kappaB"
   OR bp.node_name CONTAINS "toll-like receptor"
   OR bp.node_name CONTAINS "interferon"
WITH bp
MATCH (g:protein)-[:bioprocess_protein]-(bp)
WITH g.node_index AS gene_index, count(*) AS n_hits
RETURN gene_index, 1 AS has_inflammatory_go_annotation
