/**
 * The payloads "Why trust the list" reads, as the backend serves them:
 * `/api/evidence` (section 1), `/api/calibration` (section 2), and
 * `/api/families` + `/api/families/{id}` (section 3). Only the fields the
 * page uses are declared.
 */

export interface Count { label: string; count: number }

export interface EvidencePayload {
  node_types: Count[]
  relations: Count[]
  node_sources: Count[]
  ppi_provenance: Count[]
  label_evidence: Count[]
  totals: { nodes: number; edges: number; relations: number; node_types: number; sources: number }
}

export interface Bin { lo: number; hi: number; n: number }

/** One scored disease's place in the AUC distribution. */
export interface DiseaseAuc {
  disease_index: number; disease: string
  auc: number; auc_rank: number; enrichment: number | null; n_known: number
}

export interface CalibrationPayload {
  champion: { precision: number; base_rate: number }
  eligibility: { total: number; eligible: number; gate: string }
  routes: Count[]
  route_admissions: number
  duplicates_removed: number
  union_rows: number
  pos_rate: number
  n_families: number
  family_macro_auc: number | null
  splits: {
    split: string; rows: number; positives: number; pos_rate_pct: number
    n_diseases: number; n_anchor_families: number
  }[]
  leakage: Record<string, number>
  n_features: number
  diseases: DiseaseAuc[]
  enrichment: { median: number | null; q1: number | null; q3: number | null; max: number | null }
  n_diseases: number
  macro_auc: number
  median_auc: number | null
  histogram: Bin[]
  hub_bias: { quintile: number; median_degree: number; mean_proba: number }[]
  orthogonality: { n: number; pearson_r: number }
}

export interface FamilySummary {
  family: string; family_id: number; n_terms: number
  /** The panel's own terms, used to find the family of the selected disease. */
  disease_indexes: number[]
}

export interface Term {
  disease_index: number; disease_name: string; auc: number | null
  lo95: number | null; hi95: number | null; trustworthy: boolean
  n_pos: number; scored: boolean; enrichment: number | null
}

export interface Overlap { a: string; b: string; shared: number; shared_novel: number }

export interface FamilyPanel {
  family: string; family_id: number; n_terms: number; macro_auc: number | null
  terms: Term[]
  overlap: Overlap[]
  /** The matrix's two views, shaped by the backend as the live Act 3 card read them. */
  overlap_all: { a: string; b: string; shared: number }[]
  overlap_novel: { a: string; b: string; shared: number }[]
  programme: { leaves: string[]; common: string[]; n_common: number; specific: Record<string, string[]> }
  gene_grid: { name: string; ranks: Record<string, number>; n_terms: number }[]
  grid_columns: string[]
}

/** The disease open on both pages, with what section 2 and 3 need to know of it. */
export interface TrustDisease {
  disease_index: number; disease_name: string
  /** Null when the disease is not in the validation set. */
  auc: DiseaseAuc | null
  family: FamilySummary | null
}
