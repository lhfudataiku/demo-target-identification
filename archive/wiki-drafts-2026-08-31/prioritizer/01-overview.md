<span id="version" style="color: grey; float: right">Version 1.0.0 draft</span><br/>

<!-- Governed claims consumed here: TI-MOD-001 TI-VAL-001 -->

<div class="alert">
This is a demonstration project. It is not a clinical decision-support system and is not a
production-ready target-nomination system.
</div>

# Knowledge Graph for Target Identification

An explainable target-prioritization experience for early drug discovery.
`DEMO_TARGET_IDENTIFICATION` is Part 2 of a two-project life-sciences proof of concept. It
consumes the governed biomedical knowledge graph from `DEMO_KG_LS`, derives graph features for
disease × gene pairs, and ranks candidates within each disease with an explainable XGBoost model.

## Industry Challenge

Selecting a drug target is an early, high-consequence decision. Discovery teams must connect
fragmented genetics, disease biology, pathways, protein interactions, and drug evidence before
committing experiments and capital. A graph can organize that evidence, but a scientist still needs
to know which candidates deserve attention, why they rank highly, and where the evidence or model
has limits.

The project turns graph context into an explainable, disease-specific ranking. It supports a
scientific investigation; it does not replace scientific judgement, causal validation, or
experimental work.

## Golden Demo Highlights

The Target Identification experience demonstrates:

- graph-derived feature engineering for disease × gene candidate pairs
- an explainable 14-feature XGBoost champion, `m7-f14`, with SHAP attributions
- leakage-aware evaluation that holds out related diseases by curated family rather than using a
  random split
- a scientist-facing ranked list with evidence, novelty, target-class, tractability, and known
  liability annotations
- a direct hand-off to graph evidence paths for inspection in the companion graph project

The current champion achieves macro per-disease AUROC **0.8230** across **670 held-out diseases**.
This is a reconstruction-fidelity measure for known associations under the project’s validation
design; it is not proof of therapeutic efficacy, causal validity, or prospective discovery success.

## Who This Demo Is For

The demo is framed for early discovery users who need to investigate disease-specific target
hypotheses with transparent supporting evidence. Representative users are:

- a computational biologist exploring diabetes-related networks across insulin signalling,
  inflammation, and metabolic regulation
- an oncology data scientist investigating breast-cancer signalling hubs, including the
  PI3K/AKT/mTOR axis and hormone-signalling context

It also supports discussions with R&D data leaders, translational-science teams, and platform
owners who need a governed route from biomedical evidence to a reviewable candidate list.

## Demo Value Proposition

The project helps a discovery organization:

- rank disease-specific candidate genes from an integrated biomedical evidence base
- inspect why a candidate scored highly through SHAP and graph-path evidence
- compare behaviour across disease families and related therapeutic-area terms
- filter and investigate candidates rather than receiving an opaque, pre-cut shortlist
- keep discovery evidence, model validation, and human scientific review connected in one platform

## What the Project Does

Within the current POC scope, the system:

- consumes the supported graph objects from `DEMO_KG_LS`
- derives network, proximity, pathway, topology, and evidence-provenance features for candidate
  disease × gene pairs
- trains and scores an XGBoost ranking model using the adopted champion feature set
- validates within-disease recovery of held-out known associations and reports performance by
  disease rather than relying on a pooled headline
- presents ranked candidates with SHAP explanations and display annotations for tractability,
  target class, known liabilities, novelty, and drug evidence

The system does not produce a final target nomination. Druggability and target class are display
annotations rather than model inputs, and the available indirect safety signals are not valid
filters. A real safety axis requires direct measurements.

## Why Dataiku Matters In This Demo

Dataiku connects graph features, visual ML, validation, scoring, and a scientist-facing webapp in a
governed environment. The project preserves a traceable path from imported graph objects to a
ranked candidate and its SHAP explanation, while the companion graph project remains the authority
for graph construction and provenance.

Keeping the projects separate is deliberate: the graph changes on a slower cadence, while feature
and model experiments can iterate without risking graph construction. Their explicit shared-object
contract makes the data hand-off auditable.

## How to Use

Start with a disease or therapeutic-area question, inspect model calibration and disease-family
context, then open the ranked candidate list. Use the annotations and SHAP drivers to investigate
why a gene was scored; follow graph evidence paths for biological context. Treat the resulting list
as an input to scientific review and downstream validation, not as a therapeutic recommendation.
