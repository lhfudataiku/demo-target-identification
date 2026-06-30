# Drug layer from Open Targets (ChEMBL-derived). Input: gene_names.
# Outputs grounded parsed tables for the conformant assembly:
#   drug_target    : drugbank_id, drug_name, entrez_id, symbol, action_type
#   drug_indication: drugbank_id, drug_name, mondo_id (colon form), max_phase
# Drug node identity = DrugBank ID (via drug_molecule.crossReferences); ChEMBL drugs
# without a DrugBank xref are dropped (matches PrimeKG's DrugBank-only drug universe).
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


# --- drug nodes: CHEMBL -> DrugBank id + name -------------------------------
mol = read_ot("drug_molecule", columns=["id", "name", "crossReferences"])
mol["drugbank_id"] = mol["crossReferences"].map(drugbank_id)
mol = mol.dropna(subset=["drugbank_id"])
chembl2db = dict(zip(mol.id, mol.drugbank_id))
chembl2name = dict(zip(mol.id, mol.name))

# --- ENSG -> entrez/symbol (OT target + HGNC) -------------------------------
tgt = read_ot("target", columns=["id", "approvedSymbol"])
gn = dataiku.Dataset("gene_names").get_dataframe()[["symbol", "entrez_id"]]
sym2ent = dict(zip(gn.symbol, gn.entrez_id.astype("int64")))
tgt["entrez_id"] = tgt["approvedSymbol"].map(sym2ent)
ensg2ent = dict(zip(tgt.id, tgt.entrez_id))
ensg2sym = dict(zip(tgt.id, tgt.approvedSymbol))

# --- EFO -> MONDO (colon form) ----------------------------------------------
dis = read_ot("disease", columns=["id", "dbXRefs"]).rename(columns={"id": "diseaseId"})


def to_mondo(row):
    did = row["diseaseId"]
    if isinstance(did, str) and did.startswith("MONDO_"):
        return did.replace("MONDO_", "MONDO:")
    xrefs = row["dbXRefs"]
    if xrefs is not None and len(xrefs):
        for x in xrefs:
            if isinstance(x, str) and (x.startswith("MONDO:") or x.startswith("MONDO_")):
                return x.replace("MONDO_", "MONDO:")
    return None


dis["mondo_id"] = dis.apply(to_mondo, axis=1)
efo2mondo = dict(zip(dis.diseaseId, dis.mondo_id))

# --- drug -> target (mechanism of action), explode chemblIds x targets ------
moa = read_ot("drug_mechanism_of_action", columns=["actionType", "chemblIds", "targets"])
dt_rows = []
for _, r in moa.iterrows():
    chembls, targets, act = r["chemblIds"], r["targets"], r["actionType"]
    if chembls is None or targets is None:
        continue
    for c in chembls:
        db = chembl2db.get(c)
        if db is None:
            continue
        for ensg in targets:
            ent = ensg2ent.get(ensg)
            if pd.isna(ent) if ent is not None else True:
                continue
            dt_rows.append({"drugbank_id": db, "drug_name": chembl2name.get(c),
                            "entrez_id": int(ent), "symbol": ensg2sym.get(ensg),
                            "action_type": act})
drug_target = pd.DataFrame(dt_rows).dropna().drop_duplicates()

# --- drug -> indication -----------------------------------------------------
ind = read_ot("clinical_indication", columns=["drugId", "diseaseId", "maxClinicalStage"])
ind["drugbank_id"] = ind["drugId"].map(chembl2db)
ind["drug_name"] = ind["drugId"].map(chembl2name)
ind["mondo_id"] = ind["diseaseId"].map(efo2mondo)
drug_indication = (ind.dropna(subset=["drugbank_id", "mondo_id"])
                   .rename(columns={"maxClinicalStage": "max_phase"})
                   [["drugbank_id", "drug_name", "mondo_id", "max_phase"]]
                   .drop_duplicates())

dataiku.Dataset("drug_target").write_with_schema(drug_target)
dataiku.Dataset("drug_indication").write_with_schema(drug_indication)
