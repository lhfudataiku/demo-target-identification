# Disease nodes + hierarchy + xrefs from MONDO (parsed with obonet).
# Zero-input recipe → mondo_terms, mondo_parents, mondo_references.
import dataiku
import obonet
import pandas as pd

URL = "http://purl.obolibrary.org/obo/MONDO.obo"
g = obonet.read_obo(URL)

terms, parents, refs = [], [], []
for node_id, data in g.nodes(data=True):
    if not node_id.startswith("MONDO:"):
        continue
    terms.append({
        "mondo_id": node_id,
        "name": data.get("name"),
        "definition": data.get("def"),
    })
    for p in data.get("is_a", []):
        if p.startswith("MONDO:"):
            parents.append({"mondo_id": node_id, "parent_id": p})
    for x in data.get("xref", []):
        tok = x.split()[0]  # drop trailing "{source=...}" annotations
        if ":" in tok:
            onto, oid = tok.split(":", 1)
            refs.append({"ontology": onto, "ontology_id": oid, "mondo_id": node_id})

terms_df = pd.DataFrame(terms).drop_duplicates("mondo_id")
parents_df = pd.DataFrame(parents).drop_duplicates()
refs_df = pd.DataFrame(refs).drop_duplicates()

dataiku.Dataset("mondo_terms").write_with_schema(terms_df)
dataiku.Dataset("mondo_parents").write_with_schema(parents_df)
dataiku.Dataset("mondo_references").write_with_schema(refs_df)
