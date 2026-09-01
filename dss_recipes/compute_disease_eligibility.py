# Disease eligibility, derived directly.
#
# This used to be a Group over `disease_hierarchy_annotation` -- a 27-column,
# 27,153-row ontology table (anchors, hop depth, antichain checks) reduced to
# two numbers. The annotation was analysis, not pipeline: nothing else consumed
# it, and it is published as an appendix CSV where the analysis belongs.
#
# The eligible set IS `enriched_module_size_1`: one row per disease whose module
# clears the seed gate. The total is the disease node count. Nothing else needed.
#
# Verified identical to the old chain on 2026-08-26: 25,996 / 1,157 of 27,153.
import dataiku
import pandas as pd

eligible = len(dataiku.Dataset("enriched_module_size_1").get_dataframe(columns=["disease_index"]))

types = dataiku.Dataset("graph_node_type_counts").get_dataframe()
total = int(types.loc[types.node_type == "disease", "count"].iloc[0])

out = pd.DataFrame([
    {"is_eligible": 0, "count": total - eligible},
    {"is_eligible": 1, "count": eligible},
])
print(f"eligible {eligible:,} of {total:,} disease nodes "
      f"({100.0 * eligible / total:.1f}%) — excluded {total - eligible:,}")
dataiku.Dataset("disease_eligibility").write_with_schema(out)

