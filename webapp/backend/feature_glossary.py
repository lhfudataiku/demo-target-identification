"""The model's features, in words a reader can check.

ONE copy, deliberately. Act 2 names the features in its glossary card and Act 4
names them again on the candidate-detail card, and two hand-maintained copies of
the same user-facing wording is how the two acts start describing the same model
differently. Both import from here.

The vocabulary is the guardrail, not decoration. Act 4's spec says "must not
appear: the feature column list -- show the PATHS", so every entry describes the
evidence route the feature measures rather than restating its column name.

AUTHORITY: `.index/features.tsv` column `in_champion` is what defines the
champion's inputs; `CHAMPION` below must equal that set. Re-derive it after a
model change rather than editing this list from memory:

    awk -F'\\t' '$5=="y"{print $1}' .index/features.tsv
"""

from __future__ import annotations

# feature -> (kind, standalone label, what it measures). Order is the reading
# order both acts use: path, then proximity, then topology, then provenance.
#
# TWO strings per feature, and the reason is act 4. `what` is prose for act 2's
# glossary card, where the entries are read as a list and "the same, through a
# shared pathway" resolves against the line above it. `label` names the feature
# on its OWN, beside a bar or a SHAP contribution, where there is no line above
# and "the same" means nothing. A single string cannot do both jobs.
#
# CORRECTION 2026-09-01: this list carried `module_size` and omitted
# `shared_pathway_frac`. `module_size` is a property of the DISEASE, not of the
# gene-disease pair, and it is not an input to m7-f14 -- so the card titled
# "what the 14 features actually are" named 13 of them plus one that is not a
# feature. Checked against `.index/features.tsv`, which is the authority.
GLOSSARY: list[tuple[str, str, str, str]] = [
    ("dwpc_GGD", "path", "paths via an interacting gene",
     "degree-weighted count of paths reaching the disease through an interacting gene"),
    ("dwpc_GPGD", "path", "paths via a shared pathway",
     "the same, through a shared pathway"),
    ("dwpc_GBGD", "path", "paths via a shared biological process",
     "the same, through a shared biological process"),
    ("dwpc_GFGD", "path", "paths via a shared molecular function",
     "the same, through a shared molecular function"),
    ("prox_closest", "proximity", "hops to the nearest annotated gene",
     "hops to the nearest gene already annotated for this disease"),
    ("prox_kernel", "proximity", "diffusion proximity to the module",
     "diffusion proximity to the whole disease module, distance-weighted"),
    ("ppi_common_neighbors_z", "topology", "shared partners, degree-corrected",
     "partners shared with the module, z-scored against what degree alone predicts"),
    ("ppi_adamic_adar", "topology", "shared partners, rarity-weighted",
     "shared partners, weighted so rare partners count for more"),
    ("ppi_jaccard", "topology", "shared partners, as a fraction of the union",
     "shared partners as a fraction of the union"),
    ("shared_pathway_frac", "topology", "pathways shared with the module",
     "pathways shared with the module, as a share of every pathway the gene belongs to"),
    ("gene_ppi_degree", "topology", "interaction partners in total",
     "how many interaction partners the gene has at all"),
    ("gene_n_pathways", "topology", "pathways the gene belongs to",
     "how many pathways the gene belongs to"),
    ("ppi_evidence_depth", "provenance", "independent sources per interaction",
     "how many independent sources assert the gene's interactions"),
    ("ppi_multi_source_frac", "provenance", "interactions with more than one source",
     "the share of its interactions carrying more than one source"),
]

# The champion's inputs, in glossary order. Act 2's card counts these.
CHAMPION: list[str] = [f for f, _, _, _ in GLOSSARY]

# Which way is "more evidence". Everything here counts UP -- more paths, more
# shared partners, more sources -- except hop distance, where the strongest
# possible answer is the smallest one.
#
# This is not cosmetic. Ranking `prox_closest` the same way as the rest puts
# a gene one hop from the disease module at the 0th percentile and draws it an
# empty bar, which reads as "no evidence" for what is in fact the best value the
# feature can take.
LOWER_IS_STRONGER: frozenset[str] = frozenset({"prox_closest"})

# Standalone name (act 4's bars) and prose (act 2's glossary card).
LABEL: dict[str, str] = {f: n for f, _, n, _ in GLOSSARY}
WHAT: dict[str, str] = {f: w for f, _, _, w in GLOSSARY}

# feature -> kind, for the driver-frequency bars. Wider than GLOSSARY on purpose:
# `shap_driver_frequency` is computed over whatever the scoring recipe emitted,
# which includes features the champion dropped, and an unmapped one would fall
# back to the wrong colour rather than no colour.
KIND: dict[str, str] = {
    **{f: k for f, k, _, _ in GLOSSARY},
    # Not champion inputs -- carried so an older driver name still colours right.
    "rwr_score": "proximity", "rwr_norm": "proximity", "disease_context": "proximity",
    "ppi_common_neighbors": "topology", "gene_n_diseases": "topology",
    "module_size": "topology", "shared_pathway_count": "topology",
    "ppi_edges_with_provenance": "provenance",
}
