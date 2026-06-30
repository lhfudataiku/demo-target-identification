#!/usr/bin/env python3
"""Create the Visual Graph Editor webapp in KNOWLEDGE_GRAPH_PRIMEKG via the DSS
REST API, cloning a known-good definition and retargeting it to graph_nodes /
graph_edges. The dku CLI can't create plugin webapps, so we POST directly.
Uses stdlib urllib only."""
import base64
import json
import ssl
import urllib.request

cfg = json.load(open("/Users/li-hengfu/.dataiku/config.json"))["dss_instances"]["default"]
URL = cfg["url"].rstrip("/")
KEY = cfg["api_key"]
CTX = ssl.create_default_context()
if cfg.get("no_check_certificate", False):
    CTX.check_hostname = False
    CTX.verify_mode = ssl.CERT_NONE
AUTH = "Basic " + base64.b64encode(f"{KEY}:".encode()).decode()

TEMPLATE_PROJ, TEMPLATE_ID = "GRAPHRAG", "EUUWMoD"
PROJECT = "KNOWLEDGE_GRAPH_PRIMEKG"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(URL + path, data=data, method=method)
    req.add_header("Authorization", AUTH)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, context=CTX) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:800]


_, defn = call("GET", f"/public/api/projects/{TEMPLATE_PROJ}/webapps/{TEMPLATE_ID}")
for k in ("id", "storageFile", "apiKey", "versionTag", "creationTag",
          "isVirtual", "hasLegacyBackendURL"):
    defn.pop(k, None)
defn["projectKey"] = PROJECT
defn["name"] = "PrimeKG Graph Editor"
defn["config"] = {
    "db_query_timeout_seconds": 60,
    "log_level": "INFO",
    "nodes_datasets": ["graph_nodes"],
    "edges_datasets": ["graph_edges"],
    "metadata_ds": "vg_internal_storage_ds",
    "snapshots_ds": "vg_saved_config_ds",
    "build_graph_recipe_output_connection": "filesystem_managed",
    "logging_ds": "vg_llm_history_ds",
    "neo4j_configuration": {"mode": "NONE"},
}

status, out = call("POST", f"/public/api/projects/{PROJECT}/webapps/", defn)
print("CREATE:", status)
if isinstance(out, dict):
    print("webapp id:", out.get("id"), "| type:", out.get("type"))
else:
    print(out)
