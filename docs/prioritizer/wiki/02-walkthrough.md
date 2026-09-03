# Case Study

<!-- Governed claims consumed here: TI-VAL-001 -->

Early drug-discovery teams need to decide which genes or proteins are worth deeper investigation
for a disease. The relevant evidence is spread across genetics, disease ontologies, pathways,
protein interactions, phenotypes, and drug mechanisms. Even when that evidence is integrated in a
knowledge graph, scientists still need a transparent way to prioritize candidates and challenge the
reasoning behind a ranking.

## Project Background

`DEMO_TARGET_IDENTIFICATION` is the modelling, validation, and serving half of the target
identification POC. Its companion project, `DEMO_KG_LS`, constructs and explores the biomedical
knowledge graph. Part 2 consumes the defined graph contract, turns graph context into features for
disease × gene pairs, and produces an explainable ranked list for each disease.

The purpose is to demonstrate reproducibility, lineage, model governance, and scientific
explainability around an industry-standard supervised prioritization approach. It does not claim a
new biological discovery method or a replacement for experimental validation.

## Initial Situation

Teams can be overwhelmed by thousands of potential genes for a disease and disconnected evidence
tables that do not explain how a candidate relates to known biology. A generic global score is not
enough: users need a disease-specific ranking, a realistic test of whether the model can recover
held-out associations, and a way to inspect what drove an individual prediction.

**Goals:**

- rank candidates within each disease using graph-derived evidence
- avoid optimistic evaluation caused by related diseases appearing on both sides of a split
- provide model and graph explanations that a scientist can interrogate
- keep tractability, class, drug evidence, novelty, and known-liability context visible during
  review

## Target-Prioritization Flow

The flow begins with the shared graph objects and produces candidate-level features, training and
validation datasets, a champion model, scored rankings, and serving tables for the demo.

The champion uses 14 graph-derived features. They capture complementary signals such as network
proximity, graph paths, protein-interaction topology, pathway context, and evidence depth. The
model is XGBoost; SHAP explains which inputs moved each individual score higher or lower.

Candidate eligibility and evaluation are governed boundaries. Related diseases are assigned to
curated families and held out together, so the model is not rewarded for seeing a near-duplicate
disease in training. Results are reported macro per disease because pooled results let large disease
populations dominate the headline.

## Calibration and Validation

The key validation question is: *when known disease-gene associations are held out, can the model
rank them highly using the remaining graph evidence?* The current champion’s macro per-disease AUROC
is 0.8230 across 670 held-out diseases.

This validates reconstruction fidelity under the documented split and candidate-pool boundaries.
It does not validate a novel target prospectively, establish causality, or predict clinical success.
The project also evaluates association ranking, therapeutic evidence, tractability, discovery, and
hub-bias behaviour rather than relying on one aggregate metric.

## User Journey

### Computational biologist: diabetes

The user begins with diabetes mellitus and asks which candidates warrant closer investigation in
the context of insulin signalling, inflammation, and metabolic regulation. They inspect the ranked
list, use filters and annotations to focus the scientific question, review SHAP drivers, and follow
the evidence back into the graph where needed.

### Oncology data scientist: breast cancer

The user begins with a breast-cancer question and investigates candidate targets in the context of
the PI3K/AKT/mTOR axis and hormone-signalling biology. They compare related disease terms, inspect
whether signals are common or subtype-specific, and check the evidence behind the most relevant
candidates before proposing further work.

### From ranking to scientific review

The ranked list is deliberately filterable rather than pre-cut. The user can consider novelty,
tractability, target class, known liabilities, and existing drug evidence, then inspect SHAP and
graph context. The scientist decides which candidates advance to experimental or domain-expert
review.

## Suggested Demo Talk Track

1. Start with the problem of turning a graph of known biology into a disease-specific target
   investigation.
2. Show the evidence and calibration views before showing a ranked list.
3. Explain the family-based holdout and macro per-disease evaluation so the audience understands
   what the quality claim means.
4. Use the diabetes or breast-cancer persona to inspect a candidate’s annotations, SHAP drivers,
   and graph evidence.
5. Finish with the limits: the system prioritizes hypotheses; it does not prove causality, safety,
   efficacy, or clinical utility.
