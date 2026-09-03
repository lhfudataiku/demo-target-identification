/**
 * Act 1 launch presets are part of the evidence-base narrative, rather than
 * saved Explorer state. They prepare Cypher only: Visual Graph Explorer owns
 * execution, rendering, and open-ended query generation.
 */
export const ACT1_EXPLORER_QUERIES = [
  {
    id: 'breast-cancer-evidence-neighbourhood',
    label: 'Breast cancer evidence neighbourhood',
    description: 'How the graph connects breast cancer to associated proteins and the interactions among them.',
    cypher: `// Breast cancer evidence neighbourhood
MATCH (d:disease)<-[e1:disease_protein]-(p1:protein)
      -[e2:protein_protein]-(p2:protein)-[e3:disease_protein]->(d)
WHERE LOWER(d.node_name) = LOWER("breast cancer")
RETURN d, e1, p1, e2, p2, e3
ORDER BY p1.node_index, p2.node_index,
         OFFSET(id(e1)), OFFSET(id(e2)), OFFSET(id(e3))
LIMIT 40`,
  },
  {
    id: 'tp53-pathway-context',
    label: 'TP53 pathway context',
    description: 'What curated pathway context the graph shows for a familiar protein.',
    cypher: `// TP53 pathway context
MATCH (p:protein)-[e:pathway_protein]-(w:pathway)
WHERE LOWER(p.node_name) = LOWER("TP53")
RETURN p, e, w
ORDER BY w.node_index, OFFSET(id(e))
LIMIT 30`,
  },
  {
    id: 'tp53-drug-context',
    label: 'TP53 drug context',
    description: 'What tractability context the graph contains for a familiar protein.',
    cypher: `// TP53 drug context
MATCH (p:protein)-[e:drug_protein]-(dr:drug)
WHERE LOWER(p.node_name) = LOWER("TP53")
RETURN p, e, dr
ORDER BY dr.node_index, OFFSET(id(e))
LIMIT 25`,
  },
]
