# Diseases zone — EXTRACT (Python: parse MONDO.obo + ground).
# Outputs: mondo_terms (vocab, bare-integer id), mondo_references (vocab),
#          raw_disease_disease (grounded parent/child names, for disease_disease edges).
import dataiku
import obonet
import pandas as pd


def mondo_int(cid):
    try:
        return str(int(cid.replace("MONDO_", "MONDO:").split(":")[-1]))
    except (ValueError, AttributeError):
        return None


g = obonet.read_obo("http://purl.obolibrary.org/obo/MONDO.obo")

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
