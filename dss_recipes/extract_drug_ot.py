# Drugs zone — EXTRACT (Python: OT ChEMBL drug layer, parse only).
# Drug id = DrugBank ID (from molecule crossReferences). Native ids otherwise;
# gene grounding (ENSG→Entrez) and any joins happen in visual Join recipes.
# Outputs: drug_vocab (drugbank_id, drug_name),
#          raw_drug_protein (drugbank_id, ensg, action_type),
#          raw_drug_indication (drugbank_id, mondo_id bare-int).
import os
import re
import tempfile

import dataiku
import pandas as pd
import requests

BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def read_ot(subdir, columns=None):
    html = requests.get(BASE + subdir + "/", timeout=120, headers=HEADERS).text
    files = [f for f in re.findall(r'href="([^"]+\.parquet)"', html) if "/" not in f]
    frames = []
    for f in sorted(files):
        rr = requests.get(BASE + subdir + "/" + f, timeout=600, headers=HEADERS)
        rr.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tf:
            tf.write(rr.content)
            tmp = tf.name
        try:
            frames.append(pd.read_parquet(tmp, columns=columns))
        finally:
            os.remove(tmp)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def drugbank_id(xr):
    if xr is None:
        return None
    try:
        for e in xr:
            if e.get("source") == "drugbank":
                ids = e.get("ids")
                if ids is not None and len(ids):
                    return str(ids[0])
    except TypeError:
        pass
    return None


# drug vocab: ChEMBL -> DrugBank id + name (parse molecule's own crossReferences)
mol = read_ot("drug_molecule", columns=["id", "name", "crossReferences"])
mol["drugbank_id"] = mol["crossReferences"].map(drugbank_id)
mol = mol.dropna(subset=["drugbank_id"])
chembl2db = dict(zip(mol.id, mol.drugbank_id))
drug_vocab = mol[["drugbank_id", "name"]].rename(columns={"name": "drug_name"}).drop_duplicates("drugbank_id")

# drug -> target (native ENSG; ENSG→Entrez done via visual join downstream)
moa = read_ot("drug_mechanism_of_action", columns=["actionType", "chemblIds", "targets"])
rows = []
for _, r in moa.iterrows():
    chembls, targets, act = r["chemblIds"], r["targets"], r["actionType"]
    if chembls is None or targets is None:
        continue
    for c in chembls:
        db = chembl2db.get(c)
        if db is None:
            continue
        for ensg in targets:
            rows.append({"drugbank_id": db, "ensg": ensg, "action_type": act if act else "targets"})
raw_dp = pd.DataFrame(rows).dropna().drop_duplicates()

# drug -> indication (EFO/MONDO -> bare-int MONDO parsed from disease dbXRefs)
def to_mondo_int_row(row):
    did = row["id"]
    if isinstance(did, str) and did.startswith("MONDO_"):
        return str(int(did.split("_")[-1]))
    xrefs = row["dbXRefs"]
    if xrefs is not None and len(xrefs):
        for x in xrefs:
            if isinstance(x, str) and (x.startswith("MONDO:") or x.startswith("MONDO_")):
                return str(int(x.replace("MONDO_", "MONDO:").split(":")[-1]))
    return None


dis = read_ot("disease", columns=["id", "dbXRefs"])
dis["mondo_id"] = dis.apply(to_mondo_int_row, axis=1)
efo2mondo = dict(zip(dis.id, dis.mondo_id))

ind = read_ot("clinical_indication", columns=["drugId", "diseaseId"])
ind["drugbank_id"] = ind["drugId"].map(chembl2db)
ind["mondo_id"] = ind["diseaseId"].map(efo2mondo)
raw_di = ind.dropna(subset=["drugbank_id", "mondo_id"])[["drugbank_id", "mondo_id"]].drop_duplicates()

dataiku.Dataset("drug_vocab").write_with_schema(drug_vocab)
dataiku.Dataset("raw_drug_protein").write_with_schema(raw_dp)
dataiku.Dataset("raw_drug_indication").write_with_schema(raw_di)
