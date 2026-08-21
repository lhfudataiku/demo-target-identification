# nb3 — Model selection & validation, with the plots.  Backs sections 6.4 and 7.
# Plots use the Agg backend so this also runs headless in a scenario; in the notebook they render inline.
import dataiku, numpy as np, pandas as pd, math
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
FAIL=[]
def check(name,doc,live,tol=0.0,fmt="{:,}"):
    ok=(abs(doc-live)<=tol) if isinstance(doc,(int,float)) else (doc==live)
    if not ok: FAIL.append((name,doc,live))
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:48s} doc={fmt.format(doc):>13s} live={fmt.format(live):>13s}")

# ==== 7.1  the headline: macro per-disease AUC ====
va=dataiku.Dataset("validation_auc_by_disease").get_dataframe()
print(f"AUC|diseases={len(va)}|macro={va.auc_disease.mean():.4f}|"
      f"pos>=10 macro={va[va.n_pos>=10].auc_disease.mean():.4f}")
check("10.1 macro per-disease AUC",0.8230,round(float(va.auc_disease.mean()),4),tol=0.0006,fmt="{:.4f}")
check("10.1 validation diseases",670,len(va))

# ==== 7.3  per-family validation, and the plot that replaces a 45-number table ====
fa=dataiku.Dataset("family_auc_by_family").get_dataframe()
col=[c for c in fa.columns if "auc" in c.lower()][0]
print(f"FAM|families={len(fa)}|macro={fa[col].mean():.4f}|median={fa[col].median():.4f}")
check("7.3 per-family macro AUC",0.8009,round(float(fa[col].mean()),4),tol=0.0006,fmt="{:.4f}")
check("7.3 families",505,len(fa))
fig,ax=plt.subplots(1,2,figsize=(13,4.2))
ax[0].hist(fa[col].dropna(),bins=32,color="#4a7ba7",edgecolor="white")
ax[0].axvline(fa[col].mean(),color="#c1121f",lw=2,label=f"macro mean {fa[col].mean():.3f}")
ax[0].axvline(0.5,color="#888",ls="--",lw=1,label="chance")
ax[0].set_xlabel("per-family AUC"); ax[0].set_ylabel("families"); ax[0].legend()
ax[0].set_title(f"Per-family AUC, {len(fa)} disease families")
srt=fa[col].dropna().sort_values(ascending=False).reset_index(drop=True)
ax[1].plot(srt.index,srt.values,color="#4a7ba7"); ax[1].axhline(0.5,color="#888",ls="--",lw=1)
ax[1].fill_between(srt.index,0.5,srt.values,where=srt.values>=0.5,alpha=.25,color="#4a7ba7")
ax[1].set_xlabel("family rank"); ax[1].set_ylabel("AUC"); ax[1].set_title("Ranked, worst-case visible")
plt.tight_layout(); plt.savefig("/tmp/nb3_family_auc.png",dpi=110)
print("PLOT|nb3_family_auc.png")

# ==== 7.4  THE key plot: association AUC does not predict therapeutic relevance ====
db=dataiku.Dataset("drug_target_benchmark").get_dataframe()
j=va.merge(db,on="disease_index",suffixes=("","_d"))
j=j[["disease_index","auc_disease","auc_drug_targets","n_validated_targets","n_pos"]].dropna(
    subset=["auc_disease","auc_drug_targets"])
x=j.auc_disease.to_numpy(); y=j.auc_drug_targets.to_numpy(); n=len(j)
r=np.corrcoef(x,y)[0,1]; slope,inter=np.polyfit(x,y,1)
rs=pd.Series(x).rank().corr(pd.Series(y).rank())
t=r*math.sqrt((n-2)/max(1e-12,1-r*r))
print(f"ORTH|n={n}|pearson={r:+.4f}|R2={r*r:.4f}|spearman={rs:+.4f}|slope={slope:+.4f}|t={t:+.2f}")
wp=j[j.n_validated_targets>=10]
rw=np.corrcoef(wp.auc_disease,wp.auc_drug_targets)[0,1] if len(wp)>5 else float("nan")
print(f"ORTH|well-powered n={len(wp)}|pearson={rw:+.4f}")
check("7.4 orthogonality pearson r",0.002,round(float(r),3),tol=0.004,fmt="{:+.3f}")
check("7.4 orthogonality R2",0.0000,round(float(r*r),4),tol=0.0004,fmt="{:.4f}")
fig,ax=plt.subplots(figsize=(7.2,6))
sc=ax.scatter(x,y,s=np.clip(j.n_validated_targets*3,12,300),alpha=.55,
              c=np.log10(j.n_pos.clip(lower=1)),cmap="viridis",edgecolor="white",linewidth=.5)
xs=np.linspace(x.min(),x.max(),50)
ax.plot(xs,slope*xs+inter,color="#c1121f",lw=2.2,
        label=f"fit: slope {slope:+.3f}   r={r:+.3f}   R²={r*r:.4f}")
ax.axhline(0.5,color="#888",ls="--",lw=1); ax.axvline(0.5,color="#888",ls="--",lw=1)
ax.set_xlabel("association AUC  (does the model rank known biology?)")
ax.set_ylabel("therapeutic AUC  (does it agree with drugs?)")
ax.set_title(f"The two axes are orthogonal — n={n} diseases\nassociation AUC explains {100*r*r:.2f}% of therapeutic variance")
ax.legend(loc="lower left"); plt.colorbar(sc,label="log10 known targets")
plt.tight_layout(); plt.savefig("/tmp/nb3_orthogonality.png",dpi=110)
print("PLOT|nb3_orthogonality.png")

# ==== 7.4  drug-target benchmark aggregates ====
print(f"DRUG|diseases={len(db)}|macro drug AUC={db.auc_drug_targets.mean():.4f}|"
      f"below 0.5={int((db.auc_drug_targets<0.5).sum())}")
check("7.4 drug-target macro AUC",0.6886,round(float(db.auc_drug_targets.mean()),4),tol=0.0006,fmt="{:.4f}")

# ==== 7.2  hub-bias meter -- it has no recipe, so this notebook IS its artifact ====
sc3=dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index","gene_index","is_target","proba_1","gene_ppi_degree",
             "disease_split_key"])
sc3["dq"]=pd.qcut(sc3.gene_ppi_degree.rank(method="first"),5,labels=False)
top=sc3.sort_values("proba_1",ascending=False).groupby("disease_index").head(50)
print("HUBHDR|degree_quintile|pool_share_%|top50_share_%|over_rep")
for q in range(5):
    ps=100*(sc3.dq==q).mean(); ts=100*(top.dq==q).mean()
    print(f"HUB|Q{q+1}|{ps:6.2f}|{ts:6.2f}|{ts/ps:5.2f}x")
q5=100*(top.dq==4).mean()/(100*(sc3.dq==4).mean())
print(f"HUBTOP|highest-degree quintile over-representation at top-50: {q5:.2f}x")
# ==== header block: POOLED and PER-SPLIT-KEY, the two metrics the header quotes and nothing
# ==== asserted. Their absence is why the status line once mixed m7's macro with m3's pooled.
def _auc(y,s_):
    npos=int(y.sum()); nneg=len(y)-npos
    if npos==0 or nneg==0: return float("nan")
    r=pd.Series(s_).rank(method="average").to_numpy()   # ties -> average ranks
    return (r[y==1].sum()-npos*(npos+1)/2)/(npos*nneg)

_pooled=_auc(sc3.is_target.to_numpy(), sc3.proba_1.to_numpy())
def _macro(key):
    d=sc3[["is_target","proba_1",key]].copy()
    d["r"]=d.groupby(key)["proba_1"].rank(method="average")
    g=d.groupby(key).agg(npos=("is_target","sum"), n=("is_target","size"))
    g["rsum"]=d[d.is_target==1].groupby(key)["r"].sum().reindex(g.index).fillna(0.0)
    g["nneg"]=g.n-g.npos
    g=g[(g.npos>0)&(g.nneg>0)]
    return ((g.rsum-g.npos*(g.npos+1)/2)/(g.npos*g.nneg)).mean(), len(g)
_sk,_nsk=_macro("disease_split_key")
print(f"HEADER|pooled={_pooled:.4f}|per_split_key={_sk:.4f}|split_keys={_nsk}")
check("header pooled AUC",0.8932,round(float(_pooled),4),tol=0.0006,fmt="{:.4f}")
check("header per-split-key AUC",0.8046,round(float(_sk),4),tol=0.0006,fmt="{:.4f}")

print(f"\nSUMMARY|{len(FAIL)} STALE")
for nm,d,l in FAIL: print(f"FAILED|{nm}|doc={d}|live={l}")
