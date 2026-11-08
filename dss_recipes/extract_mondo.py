# Diseases zone — EXTRACT (Python: parse MONDO.obo + ground).
# Outputs: mondo_terms (vocab, bare-integer id), mondo_references (vocab),
#          raw_disease_disease (grounded parent/child names, for disease_disease edges).
# ----------------------------------------------------------------------------
# SOURCE PROVENANCE  (recorded 2026-08-13)
# Source        : MONDO disease ontology (OBO format)
# PINNED (R3, 2026-11-08): DEMO_KG_PREP reads this file from `pinned_sources` (compute_pinned_sources);
# the URL above is where it was pulled from, recorded in the folder's MANIFEST.json.
# URL in use    : http://purl.obolibrary.org/obo/MONDO.obo      <-- UNPINNED, serves latest
# Version used  : releases/2026-08-04   (confirmed 2026-08-13)
# Verified      : 32,102 live terms + 306 obsolete-but-still-referenced = 32,408 rows in
#                 `mondo_terms`; all 32,408 ids resolve inside that release.
# TO FREEZE     : swap the URL for the dated release (verified to work):
#                 http://purl.obolibrary.org/obo/mondo/releases/2026-08-04/mondo.obo
# Why 306 nulls : obonet keeps live terms AND bare nodes for obsolete terms that are still
#                 referenced by is_a/xref, and those bare nodes carry no `name`.
# ----------------------------------------------------------------------------

import io

import dataiku
import obonet
import pandas as pd

# Pinned by compute_pinned_sources (decision D9, R3 2026-11-08): this recipe reads the copy in
# the `pinned_sources` folder and never the URL, so a rebuild reproduces the same pull. The
# folder's MANIFEST.json records each file's URL, retrieval time, SHA-256 and release version.
PINNED = dataiku.Folder("pinned_sources")


def pinned(path):
    with PINNED.get_download_stream(path) as s:
        return s.read()


def mondo_int(cid):
    try:
        return str(int(cid.replace("MONDO_", "MONDO:").split(":")[-1]))
    except (ValueError, AttributeError):
        return None


g = obonet.read_obo(io.StringIO(pinned("mondo/mondo.obo").decode("utf-8")))

terms, parents, refs = [], [], []
for node_id, data in g.nodes(data=True):
    mi = mondo_int(node_id) if node_id.startswith("MONDO:") else None
    if mi is None:
        continue
    terms.append({"mondo_id": mi, "name": data.get("name")})
    for p in data.get("is_a", []):
        if p.startswith("MONDO:"):
            parents.append({"child_id": mi, "parent_id": mondo_int(p)})
    for x in data.get("xref", []):
        tok = x.split()[0]
        if ":" in tok:
            onto, oid = tok.split(":", 1)
            refs.append({"ontology": onto, "ontology_id": oid, "mondo_id": mi})

terms_df = pd.DataFrame(terms).dropna(subset=["mondo_id"]).drop_duplicates("mondo_id")
# Native ids only — names are resolved at assembly from mondo_terms (Design: option 1).
parents_df = pd.DataFrame(parents).dropna().drop_duplicates()[["parent_id", "child_id"]]

dataiku.Dataset("mondo_terms").write_with_schema(terms_df)
dataiku.Dataset("mondo_references").write_with_schema(
    pd.DataFrame(refs).drop_duplicates())
dataiku.Dataset("raw_disease_disease").write_with_schema(parents_df)


