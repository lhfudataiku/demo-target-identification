# nb2 — Splitting strategy & the candidate pool.  Backs TARGET_PRIORITIZER section 5.
# Reads the flow's own result datasets wherever they exist; recomputes only what has no artifact.
import dataiku, numpy as np, pandas as pd
FAIL=[]
def check(name, doc, live, tol=0.0, fmt="{:,}"):
    ok=(abs(doc-live)<=tol) if isinstance(doc,(int,float)) else (doc==live)
    if not ok: FAIL.append((name,doc,live))
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:50s} doc={fmt.format(doc):>15s} live={fmt.format(live):>15s}")
M=200_000

# ==== 5.2  the pool, and its route composition ====
pool=dataiku.Dataset("enriched_graph_features_candidate_psplit").get_dataframe(
    columns=["disease_index","gene_index","is_target"])
print(f"POOL|rows={len(pool):,} diseases={pool.disease_index.nunique()} "
      f"positives={int(pool.is_target.sum()):,} rate={100*pool.is_target.mean():.3f}%")
check("5.2 pool rows",6754128,len(pool))
check("5.2 pool positive rate %",1.89,round(100*pool.is_target.mean(),2),tol=0.02,fmt="{:.2f}")
pk=np.unique((pool.disease_index.to_numpy(np.int64)*M)+pool.gene_index.to_numpy(np.int64))
def keys(ds):
    d=dataiku.Dataset(ds).get_dataframe(columns=["disease_index","gene_index"])
    return np.unique((d.disease_index.to_numpy(np.int64)*M)+d.gene_index.to_numpy(np.int64))
GGD,GPGD,GCD=keys("enriched_dwpc_GGD"),keys("enriched_dwpc_GPGD"),keys("enriched_dwpc_GCD")
check("5.2 GGD rows",3380853,len(GGD)); check("5.2 GPGD rows",5373706,len(GPGD))
check("5.2 GCD rows",42227,len(GCD))
union=np.union1d(np.union1d(GGD,GPGD),GCD)
print(f"ROUTE|union={len(union):,} equals pool: {len(union)==len(pk)}")
gcd_only=np.setdiff1d(GCD,np.union1d(GGD,GPGD))
check("5.2.1 GCD-only pairs",10337,len(gcd_only))
check("5.2.1 GCD-only pct of pool",0.153,round(100*len(gcd_only)/len(pk),3),tol=0.002,fmt="{:.3f}")

# ==== 5.2.1  the selection bias, from its own recipe output ====
sb=dataiku.Dataset("pool_selection_bias").get_dataframe()
for lab,docA,docS in [("approved join",0.6911,0.7337),("curated known_drug >=0.8",0.6852,0.7195)]:
    r=sb[sb.label==lab]
    if not len(r): print(f"MISS|{lab}"); continue
    a=r.auc_all.mean(); s=r.auc_supported_only.mean()
    print(f"SEL|{lab}|diseases={len(r)}|auc_all={a:.4f}|auc_supported={s:.4f}|delta={s-a:+.4f}")
    check(f"5.2.1 {lab} auc_all",docA,round(float(a),4),tol=0.0006,fmt="{:.4f}")
    check(f"5.2.1 {lab} auc_supported",docS,round(float(s),4),tol=0.0006,fmt="{:.4f}")

# ==== 5.2.1  reachability ceiling ====
pr=dataiku.Dataset("pool_reachability").get_dataframe()
cov=100*pr.n_reachable.sum()/pr.n_curated.sum()
print(f"REACH|diseases={len(pr)}|curated={int(pr.n_curated.sum()):,}|"
      f"reachable={int(pr.n_reachable.sum()):,}|coverage={cov:.1f}%")
check("10.4 reachability ceiling %",98.5,round(cov,1),tol=0.15,fmt="{:.1f}")
check("10.4 diseases at 100% coverage",181,int((pr.coverage_pct>=99.99).sum()))
check("10.4 diseases below 50%",2,int((pr.coverage_pct<50).sum()))
sp=pr[["pool_size","coverage_pct"]].dropna()
rho=sp.pool_size.rank().corr(sp.coverage_pct.rank())
print(f"REACH|Spearman(pool_size,coverage)={rho:+.3f}")
check("10.4 Spearman pool_size vs coverage",0.081,round(float(rho),3),tol=0.02,fmt="{:+.3f}")

# ==== 5.4  split integrity ====
sa=dataiku.Dataset("split_audit_2").get_dataframe()
print("SPLITAUDIT|"+sa.to_string(index=False)[:600].replace("\n","  ||  "))
for c in ["overlap_train_test_keys","overlap_train_val_keys","overlap_test_val_keys","straddling_split_keys"]:
    if c in sa.columns: check(f"5.4 {c}",0,int(sa[c].max()))
print(f"\nSUMMARY|{len(FAIL)} STALE")
for n,d,l in FAIL: print(f"FAILED|{n}|doc={d}|live={l}")
