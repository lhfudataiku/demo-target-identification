/** The scientific role of an A4 Explorer route. */
export type A4ExplorerQueryClassification = 'feature' | 'context'

/** One independently runnable default query shown by the A4 Explorer card. */
export interface A4ExplorerQueryDefinition {
  readonly id: 'ppi' | 'pathway' | 'molecular-function' | 'biological-process' | 'drug'
  readonly label: string
  readonly description: string
  readonly classification: A4ExplorerQueryClassification
  /** The model feature represented by this route, or null for context-only routes. */
  readonly feature: string | null
  readonly cap: number
  readonly cypher: string
}

export type A4ExplorerQuerySet = readonly [
  A4ExplorerQueryDefinition,
  A4ExplorerQueryDefinition,
  A4ExplorerQueryDefinition,
  A4ExplorerQueryDefinition,
  A4ExplorerQueryDefinition,
]

type QueryTemplate = (diseaseIndex: number, geneIndex: number) => string

interface QueryMetadata {
  readonly id: A4ExplorerQueryDefinition['id']
  readonly label: string
  readonly description: string
  readonly classification: A4ExplorerQueryClassification
  readonly feature: string | null
  readonly cap: number
  readonly template: QueryTemplate
}

const queryMetadata: readonly QueryMetadata[] = [
  {
    id: 'ppi',
    label: 'PPI interaction',
    description: 'Physical interaction route through a shared protein mediator.',
    classification: 'feature',
    feature: 'dwpc_GGD',
    cap: 100,
    template: (diseaseIndex, geneIndex) => `MATCH (D:disease {node_index: ${diseaseIndex}})
MATCH (g:protein {node_index: ${geneIndex}})
MATCH (g)-[r1:protein_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, D, r1, m, a
ORDER BY m.node_index, OFFSET(id(r1)), OFFSET(id(a))
LIMIT 100`,
  },
  {
    id: 'pathway',
    label: 'Shared pathway',
    description: 'Shared pathway route through a protein mediator.',
    classification: 'feature',
    feature: 'dwpc_GPGD',
    cap: 100,
    template: (diseaseIndex, geneIndex) => `MATCH (D:disease {node_index: ${diseaseIndex}})
MATCH (g:protein {node_index: ${geneIndex}})
MATCH (g)-[r1:pathway_protein]-(x:pathway)-[r2:pathway_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 100`,
  },
  {
    id: 'molecular-function',
    label: 'Shared molecular function',
    description: 'Shared molecular-function route with a GO-term degree filter.',
    classification: 'feature',
    feature: 'dwpc_GFGD',
    cap: 60,
    template: (diseaseIndex, geneIndex) => `MATCH (D:disease {node_index: ${diseaseIndex}})
MATCH (g:protein {node_index: ${geneIndex}})
MATCH (g)-[r1:molfunc_protein]-(x:molecular_function)-[r2:molfunc_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
  AND COUNT { MATCH (x)-[:molfunc_protein]-() } <= 200
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 60`,
  },
  {
    id: 'biological-process',
    label: 'Shared biological process',
    description: 'Shared biological-process route with a GO-term degree filter.',
    classification: 'feature',
    feature: 'dwpc_GBGD',
    cap: 100,
    template: (diseaseIndex, geneIndex) => `MATCH (D:disease {node_index: ${diseaseIndex}})
MATCH (g:protein {node_index: ${geneIndex}})
MATCH (g)-[r1:bioprocess_protein]-(x:biological_process)-[r2:bioprocess_protein]-(m:protein)-[a:disease_protein]-(D)
WHERE m.node_index <> g.node_index
  AND COUNT { MATCH (x)-[:bioprocess_protein]-() } <= 200
RETURN g, D, r1, x, r2, m, a
ORDER BY x.node_index, m.node_index,
         OFFSET(id(r1)), OFFSET(id(r2)), OFFSET(id(a))
LIMIT 100`,
  },
  {
    id: 'drug',
    label: 'Drug context',
    description: 'Additional drug context through indication or investigation evidence.',
    classification: 'context',
    feature: null,
    cap: 40,
    template: (diseaseIndex, geneIndex) => `MATCH (D:disease {node_index: ${diseaseIndex}})
MATCH (g:protein {node_index: ${geneIndex}})
MATCH (g)-[r1:drug_protein]-(x:drug)-[r2]-(D)
WHERE LABEL(r2) IN ['indication', 'drug_investigated_for']
RETURN g, D, r1, x, r2
ORDER BY x.node_index, LABEL(r2), OFFSET(id(r1)), OFFSET(id(r2))
LIMIT 40`,
  },
] as const

function assertValidIndex(name: string, value: number): void {
  if (!Number.isFinite(value) || !Number.isSafeInteger(value) || value < 0) {
    throw new RangeError(`${name} must be a finite safe non-negative integer`)
  }
}

/** Build the five approved, independent A4 queries for a selected pair. */
export function buildA4ExplorerQueries(diseaseIndex: number, geneIndex: number): A4ExplorerQuerySet {
  assertValidIndex('diseaseIndex', diseaseIndex)
  assertValidIndex('geneIndex', geneIndex)

  return queryMetadata.map(({ template, ...metadata }) => ({
    ...metadata,
    cypher: template(diseaseIndex, geneIndex),
  })) as unknown as A4ExplorerQuerySet
}
