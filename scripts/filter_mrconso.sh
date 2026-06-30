#!/usr/bin/env bash
#
# Pre-filter UMLS MRCONSO.RRF before uploading to Dataiku DSS.
#
# Why: the full MRCONSO.RRF (UMLS 2024AB Metathesaurus) is ~16M+ rows / several GB.
# The PrimeKG UMLS->MONDO mapping (umls.py + map_umls_mondo.py) only ever uses:
#   - English rows                         LAT == "ENG"   (field 2)
#   - six bridge source vocabularies (SAB, field 12):
#       OMIM, NCI, MSH, MDR, ICD10, SNOMEDCT_US
# Everything else is dropped here so the upload to DSS is small.
#
# The output keeps the ORIGINAL RRF format (all pipe-delimited columns, verbatim
# lines) so PrimeKG's umls.py parses it unchanged.
#
# Usage:
#   ./filter_mrconso.sh /path/to/2024AB/META/MRCONSO.RRF [output.RRF]
#
# Output (default): MRCONSO.filtered.RRF in the current directory.

set -euo pipefail

IN="${1:?Usage: filter_mrconso.sh <MRCONSO.RRF> [output.RRF]}"
OUT="${2:-MRCONSO.filtered.RRF}"

if [[ ! -f "$IN" ]]; then
  echo "ERROR: input file not found: $IN" >&2
  exit 1
fi

echo "Filtering $IN -> $OUT"
echo "  keep LAT==ENG and SAB in {OMIM, NCI, MSH, MDR, ICD10, SNOMEDCT_US}"

# MRCONSO.RRF is pipe-delimited. Field 2 = LAT (language), field 12 = SAB (source).
# print $0 preserves each matching line exactly (incl. the trailing empty field).
awk -F'|' '
  BEGIN {
    split("OMIM NCI MSH MDR ICD10 SNOMEDCT_US", v, " ")
    for (i in v) keep[v[i]] = 1
  }
  $2 == "ENG" && ($12 in keep) { print }
' "$IN" > "$OUT"

IN_N=$(wc -l < "$IN")
OUT_N=$(wc -l < "$OUT")
echo "Done. Rows: $IN_N -> $OUT_N"
echo "Per-SAB counts in output:"
awk -F'|' '{c[$12]++} END {for (s in c) printf "  %-14s %d\n", s, c[s]}' "$OUT"
