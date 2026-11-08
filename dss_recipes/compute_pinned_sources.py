# DEMO_KG_PREP -- PIN ON FIRST PULL (decision D9; graph revision R3, 2026-11-08).
# Zero-input recipe -> managed folder `pinned_sources`.
# ----------------------------------------------------------------------------
# Every source below has no versioned URL: re-downloading it later returns a different file.
# This recipe downloads each one ONCE and never again. A file already in the folder is left
# untouched, so rebuilding this recipe, or the whole flow, reproduces the same pull. The extract
# recipes read these files and never the URLs.
#
# MANIFEST.json in the folder records, per file: URL, retrieval time (UTC), size, SHA-256, the
# server's Last-Modified header, and the source's own version string where it publishes one
# (OBO `data-version`, Reactome database version).
#
# To take a NEW release of a source deliberately: delete its file(s) from the folder, rebuild
# this recipe, then rebuild the extracts that read it. The new manifest entry replaces the old.
# Never edit a pinned file in place.
#
# Pinned elsewhere, not here:
#   Open Targets 26.06 and STRING v12.0 -- the version is in the URL;
#   HGNC complete set (compute_hgnc_identity) -- a dated monthly file;
#   Menche interactome (raw_files) and the disease grouping map (upload) -- uploaded files.
# ----------------------------------------------------------------------------
import datetime
import hashlib
import json
import os
import re
import tempfile

import dataiku
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
REACTOME = "https://reactome.org/download/current/"
HGNC_CUSTOM = (
    "https://www.genenames.org/cgi-bin/download/custom"
    "?col=gd_app_sym&col=gd_app_name&col=gd_pub_eg_id&col=md_eg_id"
    "&col=md_prot_id&col=md_mim_id&col=gd_pub_refseq_ids"
    "&status=Approved&hgnc_dbtag=on&order_by=gd_app_sym_sort"
    "&format=text&submit=submit"
)

# (path in the folder, URL, recipe that reads it)
SOURCES = [
    ("mondo/mondo.obo", "http://purl.obolibrary.org/obo/MONDO.obo", "extract_mondo"),
    ("hpo/hp.obo", "http://purl.obolibrary.org/obo/hp/hp.obo", "extract_hpo"),
    ("hpo/phenotype.hpoa", "https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa", "extract_hpo"),
    ("hpo/genes_to_phenotype.txt",
     "https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt", "extract_hpo"),
    ("go/go-basic.obo", "http://purl.obolibrary.org/obo/go/go-basic.obo", "compute_go_terms"),
    ("go/gene2go.gz", "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2go.gz", "compute_go_terms"),
    ("reactome/ReactomePathways.txt", REACTOME + "ReactomePathways.txt", "extract_reactome"),
    ("reactome/NCBI2Reactome.txt", REACTOME + "NCBI2Reactome.txt", "extract_reactome"),
    ("reactome/ReactomePathwaysRelation.txt", REACTOME + "ReactomePathwaysRelation.txt",
     "extract_reactome"),
    ("huri/HI-union.tsv", "http://interactome-atlas.org/data/HI-union.tsv", "extract_huri"),
    ("ncbi/gene2ensembl.gz", "https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz",
     "extract_huri"),
    ("hgnc/gene_names_custom.tsv", HGNC_CUSTOM, "compute_gene_names"),
]
DATA_VERSION_RE = re.compile(rb"^data-version:\s*(\S+)", re.MULTILINE)

folder = dataiku.Folder("pinned_sources")
present = {p.lstrip("/") for p in folder.list_paths_in_partition()}

manifest = {}
if "MANIFEST.json" in present:
    with folder.get_download_stream("MANIFEST.json") as s:
        manifest = json.loads(s.read().decode("utf-8"))

reactome_version = None
pulled, kept = [], []
for path, url, reader in SOURCES:
    if path in present:
        kept.append(path)
        continue
    sha, size, head = hashlib.sha256(), 0, b""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        with requests.get(url, headers=HEADERS, timeout=900, stream=True) as r:
            r.raise_for_status()
            last_modified = r.headers.get("Last-Modified")
            for chunk in r.iter_content(chunk_size=1 << 20):
                if len(head) < 4096:
                    head += chunk[: 4096 - len(head)]
                sha.update(chunk)
                size += len(chunk)
                tmp.write(chunk)
        tmp_path = tmp.name
    if size == 0:
        os.unlink(tmp_path)
        raise ValueError(f"{url} returned an empty body; nothing pinned for {path}")
    with open(tmp_path, "rb") as f:
        folder.upload_stream(path, f)
    os.unlink(tmp_path)

    entry = {
        "url": url, "read_by": reader,
        "retrieved_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "bytes": size, "sha256": sha.hexdigest(), "last_modified": last_modified,
    }
    m = DATA_VERSION_RE.search(head) if path.endswith(".obo") else None
    if m:
        entry["data_version"] = m.group(1).decode("utf-8", "replace")
    if path.startswith("reactome/"):
        if reactome_version is None:
            v = requests.get("https://reactome.org/ContentService/data/database/version",
                             headers=HEADERS, timeout=60)
            reactome_version = v.text.strip() if v.ok else None
        entry["data_version"] = f"Reactome release {reactome_version}"
    manifest[path] = entry
    pulled.append(path)
    print(f"pinned {path}: {size:,} bytes, sha256 {entry['sha256'][:12]}, "
          f"version {entry.get('data_version')}, Last-Modified {last_modified}")

missing = [p for p, _, _ in SOURCES if p not in manifest]
assert not missing, f"files present without a manifest entry: {missing}"
if pulled:
    folder.upload_data("MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"))
print(f"pulled now: {len(pulled)} | already pinned, left untouched: {len(kept)}")
