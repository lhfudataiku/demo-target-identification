# nb4 — Results: the three axes.  Backs TARGET_PRIORITIZER section 8.
# Every table here already has a flow dataset; this notebook re-derives the quoted aggregates.
import dataiku, numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
KS=[10,20,50,100,200]
FAIL=[]
def check(name,doc,live,tol=0.0,fmt="{:,}"):
    ok=(abs(doc-live)<=tol) if isinstance(doc,(int,float)) else (doc==live)
    if not ok: FAIL.append((name,doc,live))
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:52s} doc={fmt.format(doc):>14s} live={fmt.format(live):>14s}")

# ==== 8.1  the curated therapeutic label ====
kd=dataiku.Dataset("known_drug_truth").get_dataframe()
k8=kd[kd.score>=0.8]
print(f"LABEL|known_drug rows={len(kd):,}|at>=0.8={len(k8):,}|diseases={k8.disease_index.nunique()}")
# 107,593 is the RAW extract; known_drug_truth holds only what resolved onto the graph.
raw=dataiku.Dataset("raw_ot_known_drug").get_dataframe(columns=[
    dataiku.Dataset("raw_ot_known_drug").read_schema()[0]["name"]])
check("8.1 raw known_drug rows",107593,len(raw),tol=0)
check("8.1 resolving onto graph",67748,int(kd.disease_index.notna().sum()),tol=0)

# ==== 8.3  discovery on the novel head ====
nde=dataiku.Dataset("novel_discovery_eval").get_dataframe()
for gt in ["approved","investigational","any"]:
    s=nde[nde.ground_truth==gt]
    if not len(s): continue
    l10=s.lift_top10.replace([np.inf],np.nan).mean(); l200=s.lift_top200.replace([np.inf],np.nan).mean()
    print(f"DISC|{gt:16s}|diseases={len(s):4d}|lift@10={l10:6.2f}|lift@200={l200:5.2f}|"
          f"hits@200={int(s.hits_top200.sum()):,}")
    if gt=="approved":
        check("8.3 approved lift@10",11.40,round(float(l10),2),tol=0.02,fmt="{:.2f}")
        check("8.3 approved lift@200",4.53,round(float(l200),2),tol=0.02,fmt="{:.2f}")
    if gt=="investigational":
        check("8.3 investigational lift@10",7.42,round(float(l10),2),tol=0.02,fmt="{:.2f}")

# ==== 8.3  FIGURE 1 — discovery lift vs K, by ground truth ====
# Replaces the per-K table in section 8.3: the shape (monotone decay toward a ~4x floor) is the point,
# and a table of 30 numbers hides it.
fig,ax=plt.subplots(1,2,figsize=(13,4.4))
for gt,c in [("approved","#c1121f"),("investigational","#4a7ba7"),("any","#6b9080")]:
    s_=nde[nde.ground_truth==gt]
    if not len(s_): continue
    lifts=[s_[f"lift_top{K}"].replace([np.inf],np.nan).mean() for K in KS]
    hits=[int(s_[f"hits_top{K}"].sum()) for K in KS]
    ax[0].plot(KS,lifts,"o-",color=c,label=f"{gt} (n={len(s_)})")
    ax[1].plot(KS,hits,"o-",color=c,label=gt)
ax[0].axhline(1,color="#888",ls="--",lw=1,label="chance")
ax[0].set_xscale("log"); ax[0].set_xticks(KS); ax[0].set_xticklabels(KS)
ax[0].set_xlabel("top-K novel candidates"); ax[0].set_ylabel("lift over novel base rate")
ax[0].set_title("Discovery lift decays toward a ~4x floor"); ax[0].legend()
ax[1].set_xscale("log"); ax[1].set_xticks(KS); ax[1].set_xticklabels(KS)
ax[1].set_xlabel("top-K novel candidates"); ax[1].set_ylabel("drug-linked targets recovered")
ax[1].set_title("Absolute recovery keeps rising"); ax[1].legend()
plt.tight_layout(); plt.savefig("/tmp/nb4_fig1_discovery_lift.png",dpi=110)
print("PLOT|nb4_fig1_discovery_lift.png")

# ==== 8.4  tractability, naive vs degree-matched ====
tx=dataiku.Dataset("tractability_axis").get_dataframe()
nv=tx[tx.scope=="novel only"]
print("TRACTHDR|K|pooled_dm|pooled_naive|macro_dm|macro_naive")
for K in [10,20,50,100,200]:
    obs=nv[f"demonstrated_obs{K}"].sum(); exp=nv[f"demonstrated_exp{K}"].sum()
    en=(nv[f"demonstrated_obs{K}"]/nv[f"demonstrated_naive{K}"].replace(0,np.nan)).sum()
    print(f"TRACT|{K}|{obs/exp:.2f}|{obs/en:.2f}|{nv[f'demonstrated_dm{K}'].mean():.2f}|"
          f"{nv[f'demonstrated_naive{K}'].mean():.2f}")
p10=nv.demonstrated_obs10.sum()/nv.demonstrated_exp10.sum()
p200=nv.demonstrated_obs200.sum()/nv.demonstrated_exp200.sum()
check("8.4 pooled dm lift @10",3.06,round(float(p10),2),tol=0.02,fmt="{:.2f}")
check("8.4 pooled dm lift @200",2.38,round(float(p200),2),tol=0.02,fmt="{:.2f}")
check("8.4 macro dm lift @10",2.86,round(float(nv.demonstrated_dm10.mean()),2),tol=0.02,fmt="{:.2f}")

# ==== 8.4  FIGURE 2 — the estimator crossover, which the table states but does not show ====
fig,ax=plt.subplots(figsize=(7.4,4.8))
pd_=[nv[f"demonstrated_obs{K}"].sum()/nv[f"demonstrated_exp{K}"].sum() for K in KS]
pn_=[nv[f"demonstrated_obs{K}"].sum()/
     (nv[f"demonstrated_obs{K}"]/nv[f"demonstrated_naive{K}"].replace(0,np.nan)).sum() for K in KS]
md_=[nv[f"demonstrated_dm{K}"].mean() for K in KS]
mn_=[nv[f"demonstrated_naive{K}"].mean() for K in KS]
ax.plot(KS,pd_,"o-",color="#c1121f",label="degree-matched (pooled)")
ax.plot(KS,pn_,"o--",color="#c1121f",alpha=.5,label="naive (pooled)")
ax.plot(KS,md_,"s-",color="#4a7ba7",label="degree-matched (macro)")
ax.plot(KS,mn_,"s--",color="#4a7ba7",alpha=.5,label="naive (macro)")
ax.axvline(20,color="#888",ls=":",lw=1.5)
ax.annotate("below rank 20 the hub correction\nSTRENGTHENS the result;\nat rank 10 it weakens it",
            xy=(20,2.2),xytext=(34,1.75),fontsize=8.5,
            arrowprops=dict(arrowstyle="->",color="#555",lw=.9))
ax.set_xscale("log"); ax.set_xticks(KS); ax.set_xticklabels(KS)
ax.set_xlabel("top-K novel candidates"); ax.set_ylabel("tractability lift")
ax.set_title("Tractability: naive vs degree-matched, both estimators")
ax.legend(fontsize=8.5); plt.tight_layout()
plt.savefig("/tmp/nb4_fig2_tractability_estimators.png",dpi=110)
print("PLOT|nb4_fig2_tractability_estimators.png")

# ==== 8.6  the three-axis filter ====
f3=dataiku.Dataset("filter_three_axes").get_dataframe()
print(f"FILTER|rows={len(f3)}|cols={list(f3.columns)[:8]}")

# ==== 8.7  persona selection ====
pc=dataiku.Dataset("persona_candidates").get_dataframe()
n5=int((pc.n_criteria==5).sum())
print(f"PERSONA|diseases={len(pc)}|passing all five={n5}")
check("8.7 diseases passing 5 criteria",62,n5)
check("8.7 validation diseases",670,len(pc))

# ==== 8.10  the breast panel ====
bm=dataiku.Dataset("breast_panel_metrics").get_dataframe()
print("BREASTHDR|disease|pool|known|auc|hits50|exp50|verdict")
for _,r in bm.sort_values("n_known_targets",ascending=False).iterrows():
    print(f"BREAST|{str(r.disease)[:34]:34s}|{int(r.pool):6d}|{int(r.n_known_targets):4d}|"
          f"{r.auc:.4f}|{int(r.hits_at_50):3d}|{r.expected_at_50:6.2f}|{str(r.hits50_verdict)[:34]}")
h=bm[bm.disease.str.contains("HER2")]; t=bm[bm.disease.str.contains("triple")]
if len(h): check("8.10 HER2+ AUC",0.9338,round(float(h.auc.iloc[0]),4),tol=0.0006,fmt="{:.4f}")
if len(t): check("8.10 TNBC known targets",8,int(t.n_known_targets.iloc[0]))
bo=dataiku.Dataset("breast_panel_overlap").get_dataframe()
kp=bo[(bo.disease_a.str.contains("HER2")&bo.disease_b.str.contains("triple"))|
      (bo.disease_b.str.contains("HER2")&bo.disease_a.str.contains("triple"))]
if len(kp): check("8.10 HER2+ vs TNBC novel overlap",2,int(kp.novel_overlap.iloc[0]))
print(f"\nSUMMARY|{len(FAIL)} STALE")
for n,d,l in FAIL: print(f"FAILED|{n}|doc={d}|live={l}")
