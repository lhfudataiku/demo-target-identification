import json
import dataiku
import pandas as pd

# Dataset persona_scored renamed to persona2_scored by liheng.fu@dataiku.com on 2026-08-12 13:55:21
df = dataiku.Dataset("persona2_scored").get_dataframe()


def top_drivers(raw, n=2):
    if not isinstance(raw, str) or not raw:
        return ""
    try:
        contribs = json.loads(raw)
    except (ValueError, TypeError):
        return ""
    ranked = sorted(contribs.items(), key=lambda kv: abs(kv[1]), reverse=True)[:n]
    return ", ".join(f"{k} ({v:+.2f})" for k, v in ranked)


# Dataset persona_scored_shap renamed to persona2_scored_shap by liheng.fu@dataiku.com on 2026-08-12 13:55:21
df["top_shap_drivers"] = df["explanations"].map(top_drivers)

dataiku.Dataset("persona2_scored_shap").write_with_schema(df)

