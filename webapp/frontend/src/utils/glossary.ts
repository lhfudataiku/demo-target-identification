/**
 * One definition per term, for the whole app.
 *
 * WHY THIS FILE EXISTS. `backend/feature_glossary.py` already carries the rule:
 * "two hand-maintained copies of the same user-facing wording is how the two
 * acts start describing the same model differently." That had already happened
 * on the frontend before this file:
 *
 *  - `enrichment` was glossed twice, differently (act 2 and act 3);
 *  - `novel` was defined in act 4's tooltip and used undefined in act 3;
 *  - `top 50` was used nine times in act 3 and defined nowhere.
 *
 * So: define once here, cite everywhere via <ActTerm>. The feature entries are
 * NOT duplicated here -- they arrive from the backend glossary on the payload,
 * which stays the single authority for what the model reads.
 *
 * REGISTER. Every definition is written to be read by a business user and still
 * be exactly correct for a scientist, because both are in the room. Where a
 * definition depends on a governed threshold (trust_n_pos = 30, K = 50) the
 * number is stated, since a client will ask and a vague answer is worse than a
 * specific one.
 */

export interface GlossaryEntry {
  /** Canonical display form, used when <ActTerm> has no slot content. */
  term: string
  /** One or two sentences. Renders inside an ActInfo tooltip. */
  def: string
}

/** The three sections the drawer renders, in reading order. A term belongs to
    exactly one: a reader looking something up is asking "is this about the
    biology, the ranking, or the measurement", and a term in two places is a
    term whose definition is about to diverge. */
export type GlossaryGroup = 'graph' | 'ranking' | 'metrics'

export const GROUP_LABEL: Record<GlossaryGroup, string> = {
  graph: 'The graph, and the biology',
  ranking: 'How the ranking is produced',
  metrics: 'The measurements',
}

// ── The graph, and the biology ──────────────────────────────────────────────
const GRAPH: Record<string, GlossaryEntry> = {
  'knowledge-graph': {
    term: 'knowledge graph',
    def: 'A map of biology stored as things and the links between them — genes, diseases, drugs and pathways as nodes, and every known relationship as an edge. It lets you ask questions by following connections rather than by joining tables.',
  },
  node: {
    term: 'node',
    def: 'One thing in the graph: a gene, a disease, a drug, a pathway, a phenotype. Everything the graph knows about is a node of some type.',
  },
  edge: {
    term: 'edge',
    def: 'One link between two nodes — this drug targets that protein, this gene is associated with that disease. Edges are what the model follows.',
  },
  relation: {
    term: 'relation',
    def: 'The kind of link an edge is. There are 18 here — protein–protein interaction, drug indication, disease–gene association and so on.',
  },
  ppi: {
    term: 'protein–protein interaction',
    def: 'Two proteins that physically bind or act together, recorded by an experiment. Abbreviated PPI. These edges are the densest part of the graph and most of the model reads them.',
  },
  provenance: {
    term: 'provenance',
    def: 'The record of where a fact came from — which database asserted it, and how many independent ones agree. It says nothing about whether the fact is correct.',
  },
  interactome: {
    term: 'interactome',
    def: 'One database’s complete catalogue of protein–protein interactions. An edge corroborated by two interactomes was reported independently twice.',
  },
  ontology: {
    term: 'ontology',
    def: 'A curated, hierarchical vocabulary maintained by a scientific community — it fixes what each term means and which terms sit under which. Using one means the naming is somebody else’s published standard, not ours.',
  },
  primekg: {
    term: 'PrimeKG',
    def: 'The published biomedical knowledge graph this build reproduces. It is frozen here and used as the reference the assembled graph is checked against.',
  },
  association: {
    term: 'association',
    def: 'A curated link between a gene and a disease, recorded by a public source. This is the label the model is trained to reproduce — not a claim that the gene causes the disease.',
  },
  'evidence-type': {
    term: 'evidence type',
    def: 'How a gene–disease association was established. The types in this graph are not equally strong, and the model treats all of them as one label.',
  },
  target: {
    term: 'target',
    def: 'A protein a drug is designed to act on. "Finding a target" is choosing which protein to build a drug against — the decision this whole demo is about.',
  },
  tractable: {
    term: 'tractable',
    def: 'Open Targets judges the protein reachable by a drug — either by a small molecule (it has a drug-like pocket) or by an antibody (it is reachable from outside the cell).',
  },
  pathway: {
    term: 'pathway',
    def: 'A named chain of molecular steps cells use to get something done. Two genes in the same pathway are doing related work, which is one of the routes the model follows.',
  },
  subtype: {
    term: 'subtype',
    def: 'A narrower form of a disease, defined by molecular markers or by tissue — HER2-positive breast carcinoma is a subtype of breast cancer. Clinicians treat subtypes as different diseases.',
  },
  programme: {
    term: 'programme',
    def: 'The set of genes a therapeutic effort is built around. A "common programme" across subtypes means they converge on largely the same biology.',
  },
  'leaf-term': {
    term: 'leaf term',
    def: 'A disease term with no narrower term under it in the curated set — the most specific label available. Leaf is a curation call, not a depth rule.',
  },
  liability: {
    term: 'safety liability',
    def: 'A public annotation recording that an adverse effect has been observed and published for this protein. It is not dose-, modality- or indication-specific — so an unflagged gene is not safe, it is unstudied. Read it as evidence of attention, not of danger.',
  },
}

// ── How the ranking is produced ─────────────────────────────────────────────
const RANKING: Record<string, GlossaryEntry> = {
  'gene-disease-pair': {
    term: 'gene–disease pair',
    def: 'One gene considered for one disease. The model scores pairs, not genes — the same gene can rank first for one disease and nowhere for another.',
  },
  'candidate-pool': {
    term: 'candidate pool',
    def: 'Every gene the graph connects to a given disease by at least one route. These are the genes that get scored; anything not in the pool is never ranked.',
  },
  'eligibility-gate': {
    term: 'eligibility gate',
    def: 'The test a disease must pass before any of its genes are scored: it needs enough curated gene associations for the model to learn from and be tested on.',
  },
  'ranking-method': {
    term: 'how genes are ranked',
    def: 'Every gene the graph connects to the disease enters the candidate pool. The champion model scores each gene–disease pair from 14 graph-structure features, and the genes are sorted by that score within the disease. The score is uncalibrated, so the order carries the meaning, not the number — and ranks are never comparable between diseases.',
  },
  'champion-model': {
    term: 'champion model',
    def: 'The model currently in the flow — internally m7-f14, meaning the seventh candidate, trained on 14 features. It was promoted because its gain over the previous model survived a paired statistical test across 668 diseases.',
  },
  rank: {
    term: 'rank',
    def: 'Position in this disease’s list, highest score first. The score behind it is uncalibrated, so the ordering is what carries meaning — not the number.',
  },
  uncalibrated: {
    term: 'uncalibrated',
    def: 'The score sorts candidates correctly but is not a probability — 0.8 does not mean an 80% chance of being a real target. Compare positions, never the values.',
  },
  'top-50': {
    term: 'top 50',
    def: 'Every gene the graph connects to a disease is scored and ranked; the top 50 is the head of that list — the shortlist a team would actually look at. Nothing about 50 is special: it is a demo cut-off, and Act 4 lets you set your own.',
  },
  novel: {
    term: 'novel',
    def: 'No curated association exists between this gene and this disease at the evidence threshold we use. Novel means we have not recorded a link — not that no link is known to science.',
  },
  feature: {
    term: 'feature',
    def: 'One number the model reads about a gene–disease pair. All 14 here describe how the gene sits in the graph; none describes the biology of the protein itself.',
  },
  'feature-path': {
    term: 'path',
    def: 'Features that count the routes through the graph from the gene to the disease — through an interacting gene, a shared pathway, or a shared function.',
  },
  'feature-proximity': {
    term: 'proximity',
    def: 'Features that measure how close the gene sits to the genes already known for this disease, in hops or by diffusion.',
  },
  'feature-topology': {
    term: 'topology',
    def: 'Features that describe the gene’s position in the network overall — how many partners it has, how many it shares with the disease’s genes.',
  },
  'feature-provenance': {
    term: 'provenance features',
    def: 'Features that count how many independent sources back a gene’s interactions. They describe the strength of the evidence rather than the biology — and the model leans on them most.',
  },
  dwpc: {
    term: 'DWPC',
    def: 'Degree-weighted path count: how many routes reach the disease from this gene, with routes through very well-connected nodes counted for less. It stops popular hub genes from scoring highly on connectivity alone.',
  },
  shap: {
    term: 'SHAP',
    def: 'A method that splits one prediction into a contribution per input — how much each feature pushed this specific gene’s score up or down. It explains one decision, not the model in general.',
  },
  percentile: {
    term: 'percentile',
    def: 'Where this gene sits among the other candidates for this same disease, on this one feature. 96th percentile means it beats 96% of the pool — always within this disease, never globally.',
  },
}

// ── The measurements ────────────────────────────────────────────────────────
const METRICS: Record<string, GlossaryEntry> = {
  auc: {
    term: 'AUC',
    def: 'For one disease: the chance that a known target scores higher than a randomly picked non-target. 0.5 is a coin flip, 1.0 is perfect.',
  },
  'auc-per-disease': {
    term: 'per-disease AUC',
    def: 'One AUC computed inside a single disease — the chance a known target for that disease outranks a random non-target for it. One number per disease; this is what the histogram bins.',
  },
  'auc-macro': {
    term: 'macro AUC',
    def: 'The plain average of the per-disease AUCs. Every disease counts once, whether it has eight known targets or six hundred. This is the number we report.',
  },
  'auc-pooled': {
    term: 'pooled AUC',
    def: 'One AUC computed over every gene–disease pair at once, ignoring which disease each belongs to. It reads about seven points higher here, because a few large diseases carry all the small ones. We compute it and never quote it.',
  },
  precision: {
    term: 'precision',
    def: 'Of the candidates the model calls positive, the share that really are known targets. It answers "when it says yes, how often is it right?"',
  },
  recall: {
    term: 'recall',
    def: 'Of all the known targets that exist, the share the model calls positive. It answers "how many of the real ones did it find?"',
  },
  auprc: {
    term: 'average precision',
    def: 'The area under the precision–recall curve: precision averaged across every possible cut-off, so it does not depend on picking one threshold. A random ranker scores the base rate.',
  },
  'base-rate': {
    term: 'base rate',
    def: 'The share of the candidate pool that is already a known target — about 2%. It is what any metric has to beat: a model that says "no" to everything is 98% accurate and completely useless.',
  },
  'class-imbalance': {
    term: 'class imbalance',
    def: 'Positives are rare — roughly one candidate in fifty is a known target. It is why accuracy is meaningless here and why precision is quoted against the base rate.',
  },
  enrichment: {
    term: 'rank enrichment',
    def: 'Take a disease’s top 50 ranked genes and count how many are already-known targets, as a share of 50. Divide by the share of known targets in that disease’s whole candidate pool. 20× means the top of the list is twenty times as dense in real targets as the pool it was drawn from — and unlike AUC it stays readable for a disease with only a handful of known targets.',
  },
  'hits-at-k': {
    term: 'hits in the top 20',
    def: 'A plain count: how many already-known targets appear in the first 20 rows. No statistics involved — you can check it by eye, which is why it survives where AUC does not.',
  },
  'ci-95': {
    term: '95% confidence interval',
    def: 'The range the true score is likely to sit in, given how much data there was. A wide interval does not mean the estimate is wrong — it means it is unpinned.',
  },
  trustworthy: {
    term: 'trustworthy',
    def: 'A term whose AUC we are willing to quote: at least 30 known targets, and an upper confidence bound at or below 1.0. Below that the score is not wrong, it is unpinned — so we show it and never quote it.',
  },
  'held-out': {
    term: 'held out',
    def: 'Data the model never saw while training. Scores are only meaningful on held-out data; anything measured on what it learned from is a memory test.',
  },
  'grouped-split': {
    term: 'split by family',
    def: 'Train and test are divided by disease family, not at random. Random splitting puts "diabetes" and "type 2 diabetes" on opposite sides — the same programme wearing two labels — and inflates the score.',
  },
  leakage: {
    term: 'leakage',
    def: 'When something the model should not have seen leaks from the test set into training, so the score measures memory rather than generalisation. Splitting by family is the guard against it here.',
  },
  'positive-rate': {
    term: 'positive rate',
    def: 'The share of a split’s rows that are known targets. It is the floor precision must beat to mean anything.',
  },
  median: {
    term: 'median',
    def: 'The middle value: half the diseases sit above it, half below. Preferred to the average here because a few extreme diseases would drag a mean around.',
  },
  iqr: {
    term: 'interquartile range',
    def: 'The middle half of the diseases — from the 25th to the 75th percentile. It shows the spread without letting the two extremes define it.',
  },
  'reconstruction-not-prediction': {
    term: 'reconstruction, not prediction',
    def: 'These scores measure how faithfully the model rebuilds biology that is already known and was hidden from it — not how well it predicts biology nobody has found yet. The second claim would need prospective validation.',
  },
}

export const GLOSSARY: Record<string, GlossaryEntry> = { ...GRAPH, ...RANKING, ...METRICS }

/** Keys per group, in declaration order — which is reading order, not
    alphabetical: `node` before `edge` before `PPI` teaches better than a
    sort does. The drawer offers search for the alphabetical case. */
export const GLOSSARY_GROUPS: { group: GlossaryGroup; keys: string[] }[] = [
  { group: 'graph', keys: Object.keys(GRAPH) },
  { group: 'ranking', keys: Object.keys(RANKING) },
  { group: 'metrics', keys: Object.keys(METRICS) },
]

/** The definition for a key, or null when the key is unknown (never throws in
    front of an audience -- a missing entry renders as plain text). */
export function definitionOf(key: string): string | null {
  return GLOSSARY[key]?.def ?? null
}

export function termOf(key: string): string {
  return GLOSSARY[key]?.term ?? key
}
