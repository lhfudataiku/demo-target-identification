# Data-source licence review — `DEMO_KG_LS`

> **Lifecycle:** Preliminary legal-review draft · **Audience:** internal Legal, product, data
> governance and project owners · **Authority:** source-lineage and licence triage, not legal advice
> or approval · **Reviewed:** 2026-09-03 · **Update when:** a source, source version, extracted field,
> upstream licence, distribution model or intended use changes · **Excludes:** software licences,
> LLM/provider terms, patents, clinical-device regulation and production privacy assessment.

## 1. Preliminary conclusion

**Do not represent the assembled graph, its derived feature tables or a graph-backed commercial
product as commercially cleared yet.** Several direct inputs are permissively licensed, but four
issues require resolution before commercial use or external distribution:

1. **The Open Targets association extraction loses source-level provenance.** The project reads
   `association_by_datatype_direct`, keeps only `genetic_association` and `somatic_mutation`, and
   aggregates to target–disease pairs. The resulting rows retain a datatype but not the original
   `datasourceId`. Legal cannot therefore determine whether a given edge came from ClinGen, COSMIC,
   Genomics England PanelApp, a UK Biobank burden analysis or another source with different terms.
2. **Open Targets' licence statements need written reconciliation.** Its licence page marks Platform
   data CC0 and says even sources labelled “commercial use for Open Targets” may be used without
   restriction by all Platform users. Its terms also say original contributors retain ownership,
   third-party rights may apply, and users are responsible for non-infringement. This draft treats
   that inconsistency as a required legal clarification, not as evidence that the CC0 statement is
   invalid.
3. **The Menche interactome is a flattened compilation with no licence or per-edge source in the
   uploaded file.** Its upstreams include TRANSFAC, KEGG, CORUM and PhosphoSitePlus, whose current
   terms include commercial or non-commercial restrictions. A journal supplement being publicly
   downloadable is not, by itself, a commercial reuse licence.
4. **HPO annotation files have custom integrity conditions and restricted upstream identifiers.**
   The project transforms the HPO hierarchy and disease/gene annotations. HPO's published terms say
   file content and logical relationships must not be altered; the annotations incorporate OMIM,
   Orphanet and DECIPHER records. OMIM commercial reuse and DECIPHER clinical-data terms need
   separate review.

Other material issues are ChEMBL's CC BY-SA 3.0 database obligations, DrugBank identifiers used as
canonical drug node IDs, and licence/version ambiguity in Open Targets tractability and safety
annotations. These are potentially resolvable through written permissions, field removal or
source-preserving architecture; they should not be left implicit.

This inventory is **exhaustive to the level recoverable from the live `DEMO_KG_LS` recipes, the
repository and the publishers' current documentation**. It cannot be record-level exhaustive for
Open Targets or Menche because the current project discards that lineage. That is itself a finding.

## 2. Review method and intended-use assumptions

The review compared the repository's canonical graph-building document with the live DSS project
and inspected the extraction code for all source recipes. It then traced aggregators to the original
source families identified by their publishers. Licence statements were checked against publisher
or institutional pages where available; where no explicit dataset grant was found, the row says so.

The risk assessment assumes the broadest plausible commercial use: internal R&D, displaying facts
in a customer-facing application, providing graph-backed analysis as a paid service, and exporting
all or part of the graph or derived tables. A narrower internal-only use may lower some risks, but
that determination belongs to Legal and may require a contract.

Risk labels mean:

- **Low:** no commercial prohibition found; attribution, notice, versioning or disclaimer duties
  still apply.
- **Medium:** commercial use appears possible, but a condition, licence mismatch, third-party-rights
  caveat or transformation question needs review.
- **High:** an explicit restriction, missing commercial grant or mixed lineage is capable of
  blocking the intended use.
- **Unresolved:** the project does not preserve enough evidence to make a source-specific decision.

## 3. Direct inputs used by the project

| Data source | Dataset / project use | URL | Licence type stated by publisher | Potential legal barrier for commercial use |
|---|---|---|---|---|
| HGNC | Live custom export of approved symbols, names and mapped Entrez, UniProt, OMIM and RefSeq identifiers; the grounding vocabulary for all gene edges. | [HGNC custom downloads](https://www.genenames.org/download/custom/) · [licence](https://hgnc.genenames.org/about/license/) | **CC0 1.0** for HGNC data; attribution requested. | **Low for HGNC-curated fields. Medium for mapped third-party identifiers:** the export itself distinguishes HGNC-curated data from mapped external IDs. Retain source attribution; review or remove OMIM identifiers if not needed. |
| MONDO | `MONDO.obo` disease backbone, hierarchy and cross-reference hub; build used the 2026-08-04 release. | [file used](http://purl.obolibrary.org/obo/MONDO.obo) · [release/downloads](https://mondo.monarchinitiative.org/pages/download/) | **CC BY 4.0** | **Low:** commercial reuse allowed with attribution, licence link and modification notice. Imported ontology components and xrefs remain subject to any applicable third-party rights. |
| Gene Ontology | `go-basic.obo` hierarchy and terms; build used the 2026-07-26 release. | [file used](http://purl.obolibrary.org/obo/go/go-basic.obo) · [citation and licence policy](https://geneontology.org/docs/go-citation-policy/) | **CC BY 4.0** | **Low:** implement attribution, licence link, release date and change notice. |
| NCBI Gene | `gene2go.gz` and `gene2ensembl.gz` mappings used for GO annotation and HuRI identifier grounding. | [`gene2go.gz`](https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2go.gz) · [`gene2ensembl.gz`](https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene2ensembl.gz) · [NCBI policies](https://www.ncbi.nlm.nih.gov/home/about/policies/) | U.S.-government data are generally public domain; NCBI says it places no restrictions on molecular data, while warning that third-party rights may exist. | **Low–Medium:** acknowledge NCBI and preserve file/version provenance. NCBI does not grant patent or third-party rights, and the continuously overwritten files make proof of the exact input difficult. |
| Reactome | Current-release `ReactomePathways.txt`, `NCBI2Reactome.txt` and `ReactomePathwaysRelation.txt`; build resolved to release 97. | [downloads](https://reactome.org/download-data) · [licence explanation](https://reactome.org/about/news/97-updated-license-agreement) | **CC0** for annotation, identifier-mapping and specialised data files; other Reactome assets can be CC BY 4.0. | **Low for the three data files:** cite Reactome anyway and do not assume the same licence for pathway diagrams, software or website assets. |
| STRING v12 | Human aliases and detailed protein links, filtered into PPI edges. | [v12 data access](https://version-12.string-db.org/cgi/access) | **CC BY 4.0** | **Low:** commercial use allowed with credit and disclosure of changes. Preserve the v12 source and score/filter methodology. |
| HuRI / Human Reference Interactome | Unversioned `HI-union.tsv` binary PPI network plus NCBI identifier mapping. | [`HI-union.tsv`](http://interactome-atlas.org/data/HI-union.tsv) · [HuRI About](https://www.interactome-atlas.org/about/) · [FAQ](https://interactome-atlas.org/faq/) | **No explicit dataset licence located** on the download, About or FAQ pages; citation is requested. | **High pending written permission:** free download and a citation request do not expressly grant commercial reuse or redistribution. Obtain a licence statement and archive it with the exact file. |
| Menche et al. 2015 interactome | Uploaded `DataS1_interactome.tsv`, a flattened union of regulatory, PPI, metabolic, complex, kinase and signalling sources. | [paper and supplement](https://pmc.ncbi.nlm.nih.gov/articles/PMC4435741/) · [source-lineage description](https://www.nature.com/articles/s41467-021-21770-8) | **No dataset licence found in the uploaded file or article record.** The paper/supplement publication terms are not a blanket licence to the underlying databases. | **High / likely blocker:** upstream sources include commercial-use and non-commercial terms, while the file drops per-edge provenance. Replace with cleared sources or obtain a licence covering the compilation and its upstream content. |
| HPO ontology | `hp.obo` terms and hierarchy; build used the 2026-06-23 release. | [download](http://purl.obolibrary.org/obo/hp.obo) · [HPO licence](https://human-phenotype-ontology.github.io/license.html) | **Custom HPO terms:** acknowledgement, public version/date display, and no alteration of content or logical relationships. | **Medium–High:** the graph transforms/reverses hierarchy edges and may publicly display modified subsets. Legal should confirm whether these operations comply; include the required product acknowledgement and version. |
| HPO annotations | `phenotype.hpoa` and `genes_to_phenotype.txt`, transformed into positive/negative disease–phenotype and phenotype–gene edges. | [`phenotype.hpoa`](https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa) · [`genes_to_phenotype.txt`](https://purl.obolibrary.org/obo/hp/hpoa/genes_to_phenotype.txt) · [provenance](https://human-phenotype-ontology.github.io/downloads.html) | Same **custom HPO terms**; the annotations derive from **OMIM, Orphanet and DECIPHER**. Open Targets separately labels its own imported HPO data CC0, which does not govern these direct downloads. | **High:** the custom no-alteration condition and upstream OMIM/DECIPHER terms require confirmation for transformation, commercial display and redistribution. |
| PrimeKG disease-grouping map | 6,392-row local snapshot made from Harvard Dataverse file 6180623 after the pinned endpoint stopped returning data; creates grouped disease nodes. | [original datafile endpoint](https://dataverse.harvard.edu/api/access/datafile/6180623) · [PrimeKG repository](https://github.com/mims-harvard/PrimeKG) · [catalog record](https://datasetcatalog.nlm.nih.gov/dataset?q=0000115440) | Catalog record states **CC0 1.0** for the PrimeKG dataset; repository code is separately MIT and warns that source-data licences remain relevant. | **Medium:** confirm that datafile 6180623 itself was covered by the dataset's CC0 grant and record the original checksum/metadata. The local snapshot is transformed and currently lacks a complete immutable licence record. |
| Open Targets Platform 26.06 — associations | `association_by_datatype_direct`; keeps scores ≥0.3 for `genetic_association` and `somatic_mutation`, then collapses to target–disease pairs. | [26.06 exports](https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/26.06/output/) · [licence](https://platform-docs.opentargets.org/licence) · [terms](https://platform-docs.opentargets.org/licence/terms-of-use) | Platform data marked **CC0 1.0**; source-specific licence table and third-party-rights terms also apply. | **High pending provenance and written clarification:** the recipe discards `datasourceId`; restricted and conditional upstreams cannot be separated. See §4. |
| Open Targets Platform 26.06 — drugs | `drug_molecule`, `drug_mechanism_of_action` and `clinical_indication`; outputs drug vocabulary, drug–protein and staged drug–disease edges. Only molecules with a DrugBank xref survive, and DrugBank IDs become graph node IDs. | [drug documentation](https://platform-docs.opentargets.org/drug) · [clinical-report sources](https://platform-docs.opentargets.org/drug/clinical-report) | Open Targets **CC0 claim**, with ChEMBL **CC BY-SA 3.0** and other source-specific terms underneath. | **High pending clarification:** source report provenance is discarded; ChEMBL ShareAlike, DrugBank identifier dependence and TTD/clinical-report source terms require review. |
| Open Targets Platform 26.06 — target annotations | `target` fields: ChEMBL target class, SM/AB tractability buckets, HPA/UniProt subcellular locations, curated safety liabilities and gnomAD constraint. | [target sources](https://platform-docs.opentargets.org/target) · [tractability](https://platform-docs.opentargets.org/target/tractability) · [safety](https://platform-docs.opentargets.org/target/safety) | Open Targets **CC0 claim** over an aggregate built from CC0, CC BY, CC BY-SA, terms-of-use and unclear inputs. | **High pending field-level lineage:** the extracted scalar flags/events do not retain the source record or licence version. See §4. |

## 4. Open Targets: original-source lineage

### 4.1 What the project actually retains

The Platform contains many datasets that this project does **not** use. The table below limits the
scope to source families capable of contributing to the exported fields that `DEMO_KG_LS` reads.

| Project output | Open Targets export / retained fields | Original sources capable of contributing | Lineage retained in this project? |
|---|---|---|---|
| Gene–disease edges | `association_by_datatype_direct`: datatype and maximum score | GWAS/Gentropy, gene-burden studies, ClinVar/EVA, PanelApp, Gene2Phenotype, UniProt, Orphanet, ClinGen, Cancer Gene Census, IntOGen and somatic ClinVar/EVA | **No.** Datatype only; original datasource and evidence record are lost. |
| Drug nodes | `drug_molecule`: name and xrefs | ChEMBL molecule records; DrugBank cross-reference used as the admission gate and node ID | ChEMBL ID exists only during extraction; final canonical ID is DrugBank. |
| Drug–protein edges | `drug_mechanism_of_action`: targets and actions | ChEMBL mechanism and target records | No source/version column in final edge. |
| Drug–disease edges | `clinical_indication`: disease and maximum clinical stage | ClinicalTrials.gov via AACT, ChEMBL curated indications, Therapeutic Target Database, EMA and PMDA according to the current clinical-report documentation; the exact 26.06 report manifest is not retained | **No.** The final edge keeps stage-derived relation, not the clinical report/source. |
| Druggability | `target`: `targetClass`, SM/AB bucket IDs, subcellular location | ChEMBL, PDB/PDBe, DrugEBIlity, Finan druggable genome, UniProt, GO and HPA; Open Targets also names Pfam, InterPro, Complex Portal, DrugBank and BioModels as tractability-pipeline inputs | Bucket ID is kept, but underlying source record, version and licence are not. |
| Safety / tolerance | `target`: event/dosing fields and gnomAD constraint | ToxCast, AOP-Wiki, ClinPGx/PharmGKB, selected publications and gnomAD | Event text is kept; original source/citation and record licence are not. |
| Entity grounding | `target` and `disease`: Ensembl IDs, EFO/MONDO IDs and xrefs | Ensembl, HGNC, EFO, MONDO and imported ontologies | Partial identifiers only; no licence/version manifest. |

### 4.2 Original-source licence register

Repeated direct sources are included here when Open Targets uses them under a potentially different
licence statement or for a different field. “Open Targets position” means the Platform's current
licence table, not an independent waiver from the original publisher.

| Original data source | Short description / path into this project | URL | Licence type | Potential legal barrier for commercial use |
|---|---|---|---|---|
| Open Targets Platform aggregate | Normalised entities, scored associations and derived target annotations. | [licence](https://platform-docs.opentargets.org/licence) · [terms](https://platform-docs.opentargets.org/licence/terms-of-use) | **CC0 1.0 stated for Platform data.** Terms preserve source ownership and third-party rights. | **Medium–High:** obtain written confirmation that 26.06 bulk exports and downstream graph/feature redistribution are covered, including sources labelled commercial-only for Open Targets. |
| Ensembl | Target backbone and stable ENSG identifiers. | [Open Targets source table](https://platform-docs.opentargets.org/licence) | **CC BY 4.0** per Open Targets. | **Low:** attribution and notice. Third-party annotations may carry separate rights. |
| EFO | Disease/phenotype backbone and mappings in Open Targets. | [EFO ontology record](https://www.ebi.ac.uk/ols4/ontologies/efo?tab=properties) | **Apache 2.0** | **Low:** preserve notice/licence and imported-ontology attribution. |
| HGNC within Open Targets | Target symbols/names and identifiers. | [HGNC licence](https://hgnc.genenames.org/about/license/) | **CC0 1.0** | **Low**, with attribution requested. |
| MONDO within Open Targets | Disease cross-references and MONDO mappings. | [MONDO downloads](https://mondo.monarchinitiative.org/pages/download/) | **CC BY 4.0** | **Low:** attribution/change notice. |
| GWAS Catalog / Open Targets Gentropy | GWAS studies and credible sets used by the Locus-to-Gene pipeline that produces genetic-association evidence. Gentropy also integrates functional-genomics/QTL inputs. | [Gentropy sources](https://platform-docs.opentargets.org/gentropy/data-sources) · [GWAS downloads](https://www.ebi.ac.uk/gwas/docs/file-downloads) | **EMBL-EBI terms** for Catalog records; summary statistics **CC0** per Open Targets; individual study/source terms can vary. | **Medium–High:** the project retains only the resulting association score. Preserve study and datasource IDs and determine whether each contributing summary-statistics/cohort licence permits the intended product use. |
| Gene-burden collections | Rare-variant burden evidence from REGENERON/UK Biobank, AstraZeneca PheWAS/UK Biobank, Genebass, SPARK, SCHEMA, Epi25, Autism Sequencing Consortium, INTERVAL, Akbari et al., AMP-PD, Riveros-McKay et al., Soh et al., FinnGen R12 and Broad CVDI (UK Biobank, All of Us, MGB Biobank). | [Open Targets evidence documentation](https://platform-docs.opentargets.org/evidence) | **No single licence.** Examples: Genebass results are CC BY 4.0 but remain tied to UK Biobank terms; FinnGen release terms and individual-study supplements vary. | **High / unresolved:** association aggregation hides the cohort/study. Build a 26.06 evidence-level manifest before commercial use; review biobank and study-result terms individually. |
| ClinVar via EVA, germline and somatic | Submitted variant–phenotype assertions used in both selected datatypes. | [ClinVar submission/data statement](https://www.ncbi.nlm.nih.gov/clinvar/docs/submit/) · [EMBL-EBI terms](https://www.ebi.ac.uk/about/terms-of-use/) | ClinVar says submitted data are available for unrestricted distribution; Open Targets lists **EMBL-EBI terms** for the EVA feed. | **Low–Medium:** broad reuse is expressly expected, but EMBL-EBI does not extinguish residual submitter/third-party rights. Keep accessions and source attribution. |
| Genomics England PanelApp | Expert/crowdsourced diagnostic gene panels contributing genetic-association evidence. | [PanelApp](https://panelapp.genomicsengland.co.uk/) | Open Targets: **“Commercial use for Open Targets.”** PanelApp disclaimer says lists may come from commercial and academic providers and users must verify ownership. | **High:** obtain written confirmation of downstream commercial rights or filter these records. |
| Gene2Phenotype | Expert literature-curated diagnostic gene–disease assertions. | [G2P disclaimer](https://www.ebi.ac.uk/gene2phenotype/disclaimer) | **EMBL-EBI terms** per Open Targets. | **Medium:** original publications/contributors retain rights; preserve provenance and confirm commercial redistribution of the curated compilation. |
| UniProt | Curated disease literature/variants, subcellular location and parts of tractability. | [UniProt licence](https://www.uniprot.org/help/license/) | **CC BY 4.0** | **Low–Medium:** attribution required; UniProt disclaims patents and other third-party rights. Keep source accessions and avoid copying protected publication text. |
| Orphanet / Orphadata Science | Rare-disease gene associations contributing genetic evidence. | [legal notice](https://www.orphadata.com/legal-notice/) | **CC BY 4.0** for Orphadata Science datasets. | **Low:** attribute Orphanet/Orphadata, version and changes; confirm the exact feed Open Targets used is an Orphadata Science file, not a separately contracted product. |
| ClinGen | Curated gene–disease validity. | [publication/data policy](https://www.clinicalgenome.org/site/assets/files/6075/clingen_publication_policy_jan2021_final.pdf) | **CC0 1.0** for curated ClinGen content; attribution requested. | **Low:** retain attribution and distinguish external annotations displayed by ClinGen, such as OMIM/DECIPHER, from ClinGen's own CC0 curation. |
| COSMIC Cancer Gene Census | Curated cancer-driver genes contributing `somatic_mutation`. | [COSMIC licensing](https://www.cosmickb.org/licensing/) | Open Targets: **“Commercial use for Open Targets.”** COSMIC directly requires a commercial licence for commercial use. | **High:** written confirmation from Open Targets/COSMIC is required for downstream commercial use or remove CGC-derived associations. |
| IntOGen | Computed consensus cancer-driver evidence contributing `somatic_mutation`. | [IntOGen](https://www.intogen.org/) · [Open Targets source table](https://platform-docs.opentargets.org/licence) | **CC0 1.0** per Open Targets. | **Low–Medium:** retain release and attribution; verify that incorporated tumour-study results do not add record-specific restrictions. |
| ChEMBL | Drug molecules, target class, mechanisms, indications and clinical/tractability buckets. | [ChEMBL licensing FAQ](https://chembl.gitbook.io/chembl-interface-documentation/frequently-asked-questions/general-questions) | **CC BY-SA 3.0** | **Medium–High:** commercial use is allowed, but attribution and ShareAlike can attach to an adapted database. Legal must define which graph exports/derived tables are adaptations and how compatible licensing will be provided. Open Targets' claimed unrestricted downstream grant should be confirmed in writing. |
| DrugBank cross-references | Eligibility gate for Open Targets drugs and canonical `node_id` in this graph. No direct DrugBank download occurs. | [DrugBank terms](https://trust.drugbank.com/drugbank-trust-center/terms-of-use) | Direct access is **non-commercial unless commercially licensed**; derivative/combined database restrictions are explicit. | **High-priority clarification, not a finding of infringement:** determine whether identifier-only xrefs delivered by Open Targets are covered by its grant. Prefer ChEMBL IDs as canonical IDs if DrugBank permission is not documented. |
| ClinicalTrials.gov via AACT | Clinical-trial reports feeding `clinical_indication`. | [ClinicalTrials.gov terms](https://clinicaltrials.gov/about-site/terms-conditions) · [AACT](https://aact.ctti-clinicaltrials.org/learn_more) | Public at no charge; U.S. government database with attribution, currency and modification requirements; third-party copyrights may apply. | **Medium:** the project does not preserve report ID, source, processing date or modification notice. Reintroduce those fields and avoid proprietary claims over the source data. |
| Therapeutic Target Database (TTD) | Curated drug–indication reports in the Open Targets clinical-mining pipeline. | [Open Targets clinical-report documentation](https://platform-docs.opentargets.org/drug/clinical-report) · [TTD](https://ttd.idrblab.cn/) | **No clear commercial dataset grant located**; the TTD publication is CC BY-NC, but an article licence is not necessarily the database licence. | **High pending source confirmation:** ask Open Targets/TTD what downstream commercial rights attach to TTD-derived clinical indications. |
| European Medicines Agency | Authorised-medicine and indication records in Open Targets clinical mining. | [EMA legal notice](https://www.ema.europa.eu/en/about-us/about-website/legal-notice) | Reuse, including commercial reuse, allowed with **EMA attribution** for EMA-owned content; third-party content excluded. | **Medium:** preserve source attribution and identify any third-party label content. The current project discards report provenance. |
| PMDA | Japanese approval information in Open Targets clinical mining. | [PMDA website policy](https://www.pmda.go.jp/english/0013.html) | Japan **Public Data License 1.0** unless otherwise stated; source citation required. | **Low–Medium:** record-level exceptions and third-party content must be checked; keep source and citation. |
| Protein Data Bank / PDBe | Structures with ligands used in the small-molecule tractability bucket. | [RCSB PDB policies](https://www.rcsb.org/pages/policies) | **CC0 1.0** for PDB archive/API data, subject to integrated-resource exceptions. | **Low:** keep structure/accession provenance; do not assume linked external resources are CC0. |
| DrugEBIlity | Pocket/druggability scores used in small-molecule tractability buckets. | [Open Targets tractability documentation](https://platform-docs.opentargets.org/target/tractability) | **No explicit dataset licence located in this review.** | **High pending clarification:** the project keeps only bucket IDs, preventing removal or separate treatment of this input. Obtain terms or omit the affected buckets. |
| Finan et al. “druggable genome” | Family-based small-molecule tractability bucket; derived using target-family/domain resources. | [tractability pipeline](https://github.com/chembl/tractability_pipeline_v2) | Paper/supplement and upstream resource terms; **no single dataset licence established here**. | **Medium–High:** archive the exact input and source list (including Pfam/InterPro where applicable) and confirm whether redistribution of the bucket is licensed. |
| Gene Ontology within tractability | Cellular-location evidence for antibody buckets. | [GO policy](https://geneontology.org/docs/go-citation-policy/) | **CC BY 4.0** | **Low:** attribution/change notice. |
| Human Protein Atlas | Subcellular locations and antibody-tractability evidence. | [HPA licence](https://www.proteinatlas.org/about/licence) | Current HPA page: **CC BY 4.0**; Open Targets' licence table states **CC BY-SA 3.0**. | **Medium:** determine which HPA release and licence governed Open Targets 26.06; satisfy the more restrictive terms until confirmed. |
| Pfam, InterPro, Complex Portal and BioModels | Named by Open Targets as supporting tractability-pipeline resources; contribution to retained bucket IDs is not exposed. | [Open Targets tractability documentation](https://platform-docs.opentargets.org/target/tractability) · [EMBL-EBI terms](https://www.ebi.ac.uk/about/terms-of-use/) | Primarily EMBL-EBI resource terms/open licences, but record-level and imported-content rights can vary. | **Medium / unresolved:** exact contributing records cannot be identified from the bucket. Request the 26.06 tractability input manifest and licences. |
| UniProt SignalP/TMHMM annotations | Predicted signal peptide/transmembrane evidence used in an antibody bucket. | [Open Targets tractability documentation](https://platform-docs.opentargets.org/target/tractability) | Delivered through UniProt/Open Targets; the underlying predictor/software terms are not recorded with the bucket. | **Medium:** clarify whether the retained output is licensed solely as UniProt data or also subject to historical prediction-tool restrictions. |
| gnomAD | Loss-of-function and missense constraint values used as safety/tolerance attributes. | [Open Targets source table](https://platform-docs.opentargets.org/licence) | **CC0 1.0** per Open Targets. | **Low:** preserve release/method attribution and ethical-use context; the project currently stores no gnomAD release. |
| ToxCast / Tox21 | Experimental toxicity evidence used by Open Targets safety curation. | [EPA downloadable data](https://www.epa.gov/comptox-tools/downloadable-computational-toxicology-data) | U.S. government/open data; Open Targets lists **Tox21 CC0 1.0**. | **Low–Medium:** keep assay/source provenance and distinguish EPA-produced data from third-party study content. |
| AOP-Wiki | Adverse-outcome pathway evidence contributing safety liabilities. | [AOP-Wiki content licensing](https://www.aopwiki.org/handbooks/6) | Default **CC BY-SA**; individual AOPs may temporarily be **All Rights Reserved**. | **High without record provenance:** exact page licence and rolling-period status are lost. Restore source-page/version/licence fields or exclude these liabilities. |
| ClinPGx / PharmGKB | Pharmacogenetic adverse-response evidence contributing safety liabilities. | [ClinPGx API](https://api.pharmgkb.org/) · [academic annotations licence](https://s3.pgkb.org/attachment/PharmGKB_Academic_License_Annotations.pdf) | Current API states **CC BY-SA 4.0**; a separately published annotations agreement limits use to research and excludes commercial clinical uses/redistribution. | **High:** identify the exact asset supplied to Open Targets 26.06 and the governing agreement. Do not rely on a generic API notice. |
| Selected safety publications | Curated safety liabilities from Brennan/Lamore/Lynch and other publications. | [Open Targets safety documentation](https://platform-docs.opentargets.org/target/safety) | Publication-specific copyright/open-access terms. Open Targets asserts CC0 for its resulting Platform data. | **Medium–High:** curated facts may be reusable, but copied text/selection and third-party database rights require record-level citation and confirmation; the current project stores event text without citation. |

### 4.3 Sources explicitly not pulled through the selected association datatypes

The release also contains Europe PMC literature, animal-model, RNA-expression, Reactome
affected-pathway, Cancer Genome Interpreter biomarker and CRISPR-screen evidence. Those sources do
not contribute to the current gene–disease extraction because the recipe filters to only
`genetic_association` and `somatic_mutation`. They must be added to this review if the datatype
filter changes. FAERS pharmacovigilance and baseline-expression fields are likewise present in the
Platform but are not extracted by the current recipes.

## 5. Nested lineage outside Open Targets

### 5.1 HPO annotations

HPO states that its phenotype annotation file includes annotations of **OMIM, Orphanet and DECIPHER**
entries. The project also downloads `genes_to_phenotype.txt`, which is generated from syndrome
phenotypes and causal genes. Because the processed graph drops the annotation's source-record
details, the following terms cannot be separated after assembly.

| Original data source | Short description | URL | Licence type | Potential legal barrier for commercial use |
|---|---|---|---|---|
| OMIM | Mendelian disease descriptions/identifiers underlying many HPO disease annotations and HGNC xrefs. | [OMIM entry via NCBI Bookshelf](https://www.ncbi.nlm.nih.gov/sites/books/NBK21101/) · [OMIM](https://www.omim.org/) | Personal, educational and research access; commercial use/redistribution generally requires an OMIM licence. | **High:** determine whether identifier-only use is permissible and whether HPO's distribution covers transformed annotations. Remove unused OMIM xrefs and retain source IDs for any kept records. |
| Orphanet | Rare-disease phenotype annotations. | [Orphadata legal notice](https://www.orphadata.com/legal-notice/) | **CC BY 4.0** for Orphadata Science. | **Low** if the exact source file is within Orphadata Science and attribution/version/change duties are met. |
| DECIPHER | Clinical genotype/phenotype records and derived annotations. | [EMBL-EBI licensing overview](https://www.ebi.ac.uk/licencing/) · [DECIPHER](https://www.deciphergenomics.org/) | Special restrictions may apply because data derive from clinical data and data owners impose privacy/use conditions. | **High:** establish whether HPO redistributes only cleared public annotations and whether commercial derivative use is granted. Preserve source/accession lineage or filter. |

### 5.2 Menche interactome

The original Menche paper describes seven interaction classes; a later peer-reviewed methods paper
identifies the underlying sources as TRANSFAC; high-throughput yeast-two-hybrid studies; IntAct;
MINT; BioGRID; HPRD; KEGG; BiGG; CORUM; PhosphoSitePlus; and the Vinayagam signalling network. The
uploaded graph file contains only endpoints, so the source and licence of an individual edge cannot
be recovered.

| Original data source | Short description | URL | Licence type | Potential legal barrier for commercial use |
|---|---|---|---|---|
| TRANSFAC | Transcription-factor regulatory interactions. | [publisher disclaimer](https://gene-regulation.com/pub/databases/transfac/disclaimer.html) | Free web use for **non-commercial** users; redistribution, derivative distribution and modification require permission. | **High / likely blocker.** |
| High-throughput Y2H study supplements | Binary PPIs from several published yeast-two-hybrid maps. | [Menche paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4435741/) | Publication- and supplement-specific; no uniform dataset licence established. | **High until exact studies/files and terms are enumerated.** |
| IntAct | Curated molecular interactions. | [IntAct](https://www.ebi.ac.uk/intact) · [EMBL-EBI terms](https://www.ebi.ac.uk/about/terms-of-use/) | **EMBL-EBI terms**; original data owners retain rights. | **Medium:** commercial access is generally allowed, but source-owner terms and attribution remain. |
| MINT | Molecular interaction records, now consolidated with IntAct. | [MINT publication](https://academic.oup.com/nar/article/40/D1/D857/2903552) | Exact historical dataset terms unresolved; the publication itself is **CC BY-NC 3.0**, which is not necessarily the data licence. | **High pending historical licence evidence.** |
| BioGRID | Curated interaction data. | [BioGRID downloads](https://downloads.thebiogrid.org/BioGRID) | Current downloads state **MIT**, free for academic and commercial users. | **Low for current data**, but archive the licence applicable to the Menche-era release and cite original contributors. |
| HPRD | Human protein reference/interaction records. | [HPRD](http://www.hprd.org/) | Historical terms are not available from a stable publisher page in this review; secondary records conflict between CC0 and academic-only/commercial-licence descriptions. | **High:** obtain the applicable historical terms or replace. |
| KEGG | Metabolic enzyme-coupled interactions. | [KEGG copyright](https://www.genome.jp/kegg/legal.html) · [commercial licensing](https://kegg.net/en/licensing.html) | Commercial/non-academic use requires a **commercial licence**. | **High / likely blocker:** a current KEGG licence does not automatically cure redistribution of the old compiled edge set; obtain scope confirmation or replace. |
| BiGG Models | Metabolic reconstructions used for enzyme-coupled interactions. | [BiGG paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7145653/) | Dataset described as restricted to **academic and non-profit use**; code is separately MIT. | **High:** commercial use of database content requires permission. |
| CORUM | Mammalian protein-complex memberships expanded into interactions. | [CORUM](https://mips.helmholtz-muenchen.de/corum/) | Current site states **CC BY-NC 4.0**; a 2024 paper says CC BY 4.0 for its then-current release. | **High for Menche-era data:** licence version is uncertain and current site is non-commercial. Obtain release-specific permission. |
| PhosphoSitePlus | Kinase–substrate interactions. | [licensing](https://www.phosphosite.org/staticLicensing) · [commercial agreement](https://www.phosphosite.org/suppData/Licensing/PSP%20License.pdf) | Formal licence required; commercial agreement is internal-use, non-transferable and non-sublicensable unless otherwise negotiated. | **High / likely blocker** for redistributing compiled edges or exposing them in a product. |
| Vinayagam et al. signalling network | Directed signalling interactions derived from a publication supplement. | [article record](https://pubmed.ncbi.nlm.nih.gov/21900206/) | No standalone dataset licence established in this review; article/supplement rights apply. | **High pending permission or a release-specific open licence.** |

### 5.3 PrimeKG grouping snapshot

PrimeKG's dataset-level CC0 declaration is helpful, but its repository expressly distinguishes its
MIT-licensed code from the licences of aggregated data. The project uses only the disease-grouping
map, apparently derived from MONDO, rather than the full PrimeKG graph. Legal should obtain the
Harvard Dataverse metadata for **datafile 6180623**, verify that this file was included in the CC0
dataset version, and store the original checksum and licence text beside the local snapshot. Until
then the row remains Medium rather than Low.

## 6. Required actions before commercial approval

### P0 — legal blockers / written clarification

1. Ask Open Targets to confirm in writing that the **26.06 bulk exports**, including downstream
   commercial products and redistribution of derived graph/feature data, are covered by its CC0
   statement notwithstanding ChEMBL ShareAlike, COSMIC CGC, Genomics England PanelApp, DrugBank
   xrefs, TTD, HPA, AOP-Wiki and ClinPGx/PharmGKB source terms.
2. Remove or quarantine **Menche** edges until a commercial licence covering the compilation and
   all underlying sources is documented. A practical replacement should use sources with explicit
   current commercial grants and preserve per-edge provenance.
3. Obtain written commercial-use terms for **HuRI**, or remove it from the commercial build.
4. Resolve direct **HPO** transformation rights and the OMIM/DECIPHER annotation chain. If clearance
   is incomplete, keep only permitted HPO vocabulary/hierarchy content and filter affected
   annotation rows by retained source.

### P1 — provenance controls

5. Replace `association_by_datatype_direct` with an evidence- or datasource-level Open Targets
   extraction. Carry at least `datasourceId`, evidence/study accession, source release and source
   licence key through harmonisation and into `edge_metadata`.
6. Preserve the clinical-report source and report ID for every drug–disease edge. Do not retain only
   `maxClinicalStage`.
7. Add a machine-readable source manifest for every build: source URL, resolved URL, file name,
   release, retrieval date, SHA-256, licence identifier, licence URL, archived licence text and
   required attribution. Snapshot all “latest/current” sources.
8. Store source provenance for Open Targets tractability and safety fields, including the source
   record/citation and licence version. If the export cannot supply it, treat each field family as
   indivisible under the most restrictive plausible terms.

### P1 — design changes that reduce exposure

9. Use **ChEMBL IDs**, not DrugBank IDs, as canonical drug node IDs unless DrugBank supplies a clear
   downstream grant. Keep DrugBank xrefs optional and separately governed.
10. Separate CC BY-SA/other reciprocal data from proprietary exports until Legal decides whether the
    resulting graph or database is adapted material and specifies the required licence/notice model.
11. Add an attribution and notices page to every internal or external graph interface and to data
    exports. Include source, release, retrieval date, licence link, changes and required citations.
12. Do not copy publication abstracts, descriptions or safety narrative into the graph unless the
    record's text licence is known; prefer source-linked facts and accessions.

## 7. Questions for Legal

1. Does Open Targets' affirmative CC0/unrestricted-downstream statement constitute sufficient
   permission for 26.06 exports when its terms simultaneously preserve original-owner restrictions?
2. Is the assembled graph, an exported subgraph, or a feature table an “Adapted Material” or adapted
   database under ChEMBL CC BY-SA 3.0, HPA's applicable licence, AOP-Wiki or ClinPGx terms?
3. Does commercial display/search of identifiers alone trigger database-contract restrictions for
   DrugBank or OMIM when those identifiers arrived through Open Targets/HGNC/HPO rather than direct
   access?
4. Do HPO's no-alteration terms permit filtering, bidirectional edge creation, deduplication,
   identifier grounding and reclassification in this graph?
5. Can any Menche edges be retained based on facts/public-domain analysis, or do the selection,
   arrangement, source contracts and database rights require removal absent permission?
6. What commercial scenario is being approved: internal R&D only, hosted query service, customer
   display, downloadable graph, downloadable derived scores, or model training? The permitted answer
   may differ by scenario and jurisdiction, especially for EU/UK database rights.

## 8. Proposed approval status

| Use case | Preliminary status | Conditions |
|---|---|---|
| Internal proof-of-concept demonstration with no data export | **Conditional** | Limit access, show source acknowledgements, do not imply legal clearance, and begin P0 remediation. Contractual restrictions can still apply to internal commercial R&D. |
| Internal commercial R&D / decision support | **Hold for Legal** | Resolve Menche, HuRI, HPO and Open Targets written scope; implement manifest and lineage. |
| Customer-facing hosted graph/search | **Not approved on current evidence** | Complete P0/P1; preserve per-record source and required notices; assess ShareAlike and database rights. |
| Redistribution of graph, subgraphs or feature tables | **Not approved on current evidence** | Requires source-specific clearance and a compatible outbound licence. |
| Clinical decision-making or safety-critical use | **Out of scope / not approved** | Separate clinical, regulatory, validation, privacy and product-liability review required. |

---

**Drafting note:** this report records preliminary factual findings for counsel. It does not decide
copyrightability of individual facts, the application of database rights, contractual privity,
fair-use/fair-dealing exceptions, patent freedom to operate or the legal effect of an intermediary's
licence representation.
