/**
 * What the shortlist reads, as the backend serves it: `/api/candidates` (one
 * disease's filtered list and its funnel), `/api/candidates/gene` (one
 * candidate's inputs, placed against its own disease's pool) and
 * `/api/candidates/drivers` (its top-5 SHAP drivers).
 */

export interface Row {
  gene_index: number
  gene_name: string; rank_in_disease: number; rank_percentile: number | null
  score: number; is_target: number
  druggability_class: string | null; ot_class_l1: string | null
  ot_sm_tractable: number; ot_ab_tractable: number
  has_safety_liability: number; approved_for_disease: number; investigational_for_disease: number
}

export interface Payload {
  disease_name: string; funnel: { step: string; n: number }[]; rows: Row[]; returned: number
}

/** One model feature, placed against this disease's own pool.
    `percentile` is the share of the pool this candidate is STRONGER than,
    measured in whichever direction the feature counts — `direction: 'lower'`
    means fewer is stronger, which is true of hop distance and nothing else. */
export interface Feature {
  key: string; label: string; kind: string
  direction: 'higher' | 'lower'
  value: number; percentile: number
}

export interface Detail {
  gene_index: number; pool_size: number | null; safety_events: string | null
  features: Feature[]
  /** Champion inputs `dashboard_candidates` does not carry — named, not hidden. */
  missing_features: string[]
}

/** `/api/candidates/identity`: the gene's HGNC record, preloaded from one dated HGNC
    complete-set file and joined to the graph by NCBI Gene ID (`candidate_identity`). */
export interface Identity {
  gene_index: number; found: boolean; source: string
  /** The dated HGNC file the record came from; null when no record matched. */
  source_file: string | null
  ncbi_gene_id: string; graph_symbol: string
  hgnc_id?: string; symbol?: string; name?: string; location?: string | null; ensembl_gene_id?: string | null
  alias_symbol?: string[]; prev_symbol?: string[]; gene_group?: string[]; uniprot_ids?: string[]
  locus_type?: string | null; date_modified?: string | null
}

/** One drug behind a pair's badges (`/api/candidates/drugs`, `drug_evidence_records`). The link
    is exact-node: a drug recorded on a broader disease term is not here. */
export interface DrugRecord {
  drug_id: string; drug_name: string | null
  /** Open Targets' highest clinical stage for this drug and this disease. */
  max_stage: string | null
  /** `indication` (approved or pre-approval) or `drug_investigated_for` (every other stage). */
  relation: string
  /** The drug's recorded action(s) on the protein. */
  action_type: string[]
  source_release: string
}

const STAGE_LABEL: Record<string, string> = {
  APPROVAL: 'Approved', PREAPPROVAL: 'Pre-approval', PHASE_3: 'Phase 3', PHASE_2_3: 'Phase 2/3',
  PHASE_2: 'Phase 2', PHASE_1_2: 'Phase 1/2', PHASE_1: 'Phase 1', EARLY_PHASE_1: 'Early phase 1',
  IND: 'IND filed', PRECLINICAL: 'Preclinical', UNKNOWN: 'Stage not recorded',
}
export const stageLabel = (s: string | null) => (s ? STAGE_LABEL[s] ?? s : 'Stage not recorded')

/** One of the pair's top-5 SHAP drivers (`/api/candidates/drivers`, `candidate_shap_top5`),
    strongest |SHAP| first. `percentile` follows the same rule as `Feature.percentile`, computed
    in the flow on full-precision values. */
export interface Driver {
  key: string; label: string | null; kind: string | null
  direction: 'higher' | 'lower'
  shap: number; value: number | null; percentile: number | null
}

export interface Drivers { n_features: number; drivers: Driver[] }

export const tractLabel = (r: Pick<Row, 'ot_sm_tractable' | 'ot_ab_tractable'>) =>
  r.ot_sm_tractable && r.ot_ab_tractable ? 'Small molecule + antibody'
    : r.ot_sm_tractable ? 'Small molecule' : r.ot_ab_tractable ? 'Antibody' : 'Not assessed'

/** The three links from the shortlist to the evidence page (scope §4.1). */
export const TRUST_LINKS = [
  { section: 'graph', label: '1 · What the model can see' },
  { section: 'reconstruction', label: '2 · How well it reconstructs this disease' },
  { section: 'family', label: '3 · Does it hold across the family' },
] as const
