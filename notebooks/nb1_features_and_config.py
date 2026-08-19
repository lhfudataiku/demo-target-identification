# nb1 — Feature engineering & model configuration.  Backs sections 4.1, 4.2, 6.1, 6.2, 6.3.
# Sampled deliberately: the full 2.19M x 31 frame plus a Spearman matrix OOM-killed the kernel
# (exit 137). A 25% random sample resolves null rates to ~0.1pp and correlations to ~0.005, which is
# far finer than any claim in the document.
import dataiku, numpy as np, pandas as pd
FAIL=[]
def check(name,doc,live,tol=0.0,fmt="{:,}"):
    ok=(abs(doc-live)<=tol) if isinstance(doc,(int,float)) else (doc==live)
    if not ok: FAIL.append((name,doc,live))
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:48s} doc={fmt.format(doc):>14s} live={fmt.format(live):>14s}")

FEATS12=["dwpc_GBGD","dwpc_GFGD","dwpc_GGD","dwpc_GPGD","gene_n_pathways","gene_ppi_degree",
         "ppi_adamic_adar","ppi_common_neighbors_z","ppi_evidence_depth","ppi_jaccard",
         "ppi_multi_source_frac","shared_pathway_frac"]
REJ=["dwpc_GCD","gene_n_diseases","module_size","degree","eigenvector_centrality","pagerank",
     "triangles","clustering_coefficient","ppi_common_neighbors","prox_closest","rwr_score"]
cols=["disease_index","gene_index","is_target"]+FEATS12+REJ
tr=dataiku.Dataset("psplit_train_set").get_dataframe(columns=cols, sampling="random", ratio=0.25)
print(f"FEAT|sample={len(tr):,} rows ({len(cols)} cols) | positives={int(tr.is_target.sum()):,} "
      f"({100*tr.is_target.mean():.3f}%)")

# ==== 4.1 / 4.2  null rate by label class -- the leak-2 channel ====
pos=tr.is_target==1
rows=[{"feature":c,"null_pos_pct":100*tr.loc[pos,c].isna().mean(),
       "null_neg_pct":100*tr.loc[~pos,c].isna().mean(),"in_model":c in FEATS12}
      for c in FEATS12+REJ if c in tr.columns]
nulls=pd.DataFrame(rows); nulls["gap_pp"]=nulls.null_pos_pct-nulls.null_neg_pct
nulls=nulls.sort_values("gap_pp")
print("NULLHDR|feature|null_in_positives_%|null_in_negatives_%|gap_pp|role")
for _,r in nulls.iterrows():
    print(f"NULL|{r.feature:26s}|{r.null_pos_pct:7.2f}|{r.null_neg_pct:7.2f}|{r.gap_pp:+8.2f}|"
          f"{'MODEL' if r.in_model else 'rejected'}")
w=float(nulls.gap_pp.min())
print(f"NULLMIN|worst gap {w:+.1f} pp ({nulls.iloc[0].feature}) | features <= -20pp: "
      f"{int((nulls.gap_pp<=-20).sum())}")
check("6.2 worst null gap pp",-31.6,round(w,1),tol=1.5,fmt="{:+.1f}")

# ==== 6.1  collinearity: the hub cluster ====
HUB=[c for c in ["gene_ppi_degree","degree","eigenvector_centrality","pagerank","triangles",
                 "clustering_coefficient","module_size"] if c in tr.columns]
cm=tr[HUB].sample(n=min(120_000,len(tr)),random_state=1337).corr(method="spearman")
print("COLHDR|"+"|".join(HUB))
for a in HUB: print("COL|"+a+"|"+"|".join(f"{cm.loc[a,b]:+.3f}" for b in HUB))
top=sorted(((abs(cm.loc["degree",b]),b) for b in HUB if b!="degree"),reverse=True)[:3]
print("DEGTOP3|"+", ".join(f"{b}={v:.3f}" for v,b in top))
check("6.1 highest |rho| vs degree",0.975,round(float(top[0][0]),3),tol=0.03,fmt="{:.3f}")

# ==== 6.1  gene-only vs pair-level: can the feature answer "for THIS disease"? ====
print("VARHDR|feature|pct_genes_varying_across_diseases")
for c in ["gene_ppi_degree","gene_n_pathways","gene_n_diseases","dwpc_GGD","dwpc_GPGD","module_size"]:
    if c in tr.columns:
        nun=tr.groupby("gene_index")[c].nunique(dropna=True)
        print(f"VAR|{c:22s}|{100*(nun>1).mean():6.2f}%")

# ==== 6.1  single-feature within-disease AUC ====
sm=tr.sample(n=min(250_000,len(tr)),random_state=7)
def macro_auc(df,col):
    out=[]
    v=df[[col,"is_target","disease_index"]].dropna(subset=[col])
    for _,g in v.groupby("disease_index"):
        y=g.is_target.to_numpy(); n1=int(y.sum()); n0=len(y)-n1
        if n1==0 or n0==0: continue
        r=g[col].rank().to_numpy()
        out.append((r[y==1].sum()-n1*(n1+1)/2)/(n1*n0))
    return float(np.mean(out)) if out else float("nan")
sf={}
for c in ["dwpc_GPGD","dwpc_GGD","gene_ppi_degree","gene_n_diseases","module_size"]:
    if c in sm.columns:
        sf[c]=macro_auc(sm,c); print(f"AUC1|{c:22s}|{sf[c]:.4f}")
check("6.1 dwpc_GPGD single-feature AUC",0.641,round(sf.get("dwpc_GPGD",0),3),tol=0.06,fmt="{:.3f}")
check("6.1 dwpc_GGD single-feature AUC",0.601,round(sf.get("dwpc_GGD",0),3),tol=0.06,fmt="{:.3f}")
del tr, sm

# ==== 6.3  the threshold is not the ranking ====
sc=dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index","is_target","proba_1"])
ob=sc[sc.disease_index==37143]
tot=int(ob.is_target.sum())
best=(0.0,0.0)
for t in np.arange(0.05,0.99,0.01):
    p=(ob.proba_1>=t).to_numpy(); y=ob.is_target.to_numpy()==1
    tp=int((p&y).sum()); fp=int((p&~y).sum()); fn=int((~p&y).sum())
    f1=2*tp/max(2*tp+fp+fn,1)
    if f1>best[0]: best=(f1,float(t))
f1,thr=best
tp=int(((ob.proba_1>=thr).to_numpy()&(ob.is_target.to_numpy()==1)).sum())
print(f"THR|obesity known targets={tot} | F1-opt threshold={thr:.3f} F1={f1:.3f} | "
      f"recall={100*tp/max(tot,1):.1f}% | missed={tot-tp}")
check("6.3 F1 threshold",0.875,round(thr,3),tol=0.08,fmt="{:.3f}")
check("6.3 obesity known targets",762,tot)
print(f"\nSUMMARY|{len(FAIL)} STALE")
for n,d,l in FAIL: print(f"FAILED|{n}|doc={d}|live={l}")
