# Does the pool's drug route DEPRESS the drug-target metrics that section 7.4 reads as an
# "objective limitation"?
#
# Established: dwpc_GCD is Gene-Compound-Disease (100% of approved-join pairs carry it) and it is one
# of three routes admitting pairs to the candidate pool -- but it is role=REJECT as a model feature.
# So the drug relationship selects the POPULATION without informing the FEATURES.
#
# CONSEQUENCE, stated as a falsifiable prediction: a GCD-ONLY pair has, by definition, no GGD and no
# GPGD route, so two of the twelve model inputs are null and imputed. The model cannot score such a
# pair on anything disease-specific. Those pairs are 25.4% of approved positives. Therefore the
# drug-target AUC should RISE when they are excluded -- and if it rises a lot, section 7.4's
# "the objectives are genuinely in tension" is partly an artifact of how the pool was built, not a
# property of the biology.
#
# If the AUC does NOT move, the tension in section 7.4 is real and this is a non-finding. Either way
# it is cheap to know before retraining anything.
import dataiku, numpy as np, pandas as pd
M = 200_000
OUT = []

def keys(ds):
    df = dataiku.Dataset(ds).get_dataframe(columns=["disease_index","gene_index"])
    return np.unique((df.disease_index.to_numpy(np.int64)*M)+df.gene_index.to_numpy(np.int64))

GGD, GPGD, GCD = keys("enriched_dwpc_GGD"), keys("enriched_dwpc_GPGD"), keys("enriched_dwpc_GCD")
supported = np.union1d(GGD, GPGD)          # pairs the model actually has route features for
gcd_only  = np.setdiff1d(GCD, supported)
print(f"H|supported(GGD|GPGD) {len(supported):,} | GCD-only {len(gcd_only):,}")

sc = dataiku.Dataset("scored_m3").get_dataframe(
    columns=["disease_index","gene_index","proba_1"])
sc["k"]=(sc.disease_index.to_numpy(np.int64)*M)+sc.gene_index.to_numpy(np.int64)

kd = dataiku.Dataset("known_drug_truth").get_dataframe()
LABELS = {"curated known_drug >=0.8": kd[kd.score>=0.8],
          "approved join":            kd[kd.in_approved_join==1],
          "all known_drug":           kd}

def auc(y, s):
    n1=int(y.sum()); n0=len(y)-n1
    if n1==0 or n0==0: return np.nan
    r=pd.Series(s).rank().to_numpy()
    return (r[y==1].sum()-n1*(n1+1)/2)/(n1*n0)

for lname, sub in LABELS.items():
    tk=np.unique((sub.disease_index.to_numpy(np.int64)*M)+sub.gene_index.to_numpy(np.int64))
    sc["pos"]=np.isin(sc.k.to_numpy(), tk).astype(int)
    sc["is_gcd_only"]=np.isin(sc.k.to_numpy(), gcd_only)
    rows=[]
    for di,g in sc.groupby("disease_index"):
        if g.pos.sum()==0: continue
        a_all=auc(g.pos.to_numpy(), g.proba_1.to_numpy())
        # drop ONLY the GCD-only positives; keep every negative so the pool is unchanged
        keep=~(g.is_gcd_only.to_numpy() & (g.pos.to_numpy()==1))
        gg=g[keep]
        a_sup=auc(gg.pos.to_numpy(), gg.proba_1.to_numpy()) if gg.pos.sum()>0 else np.nan
        n_only=int((g.is_gcd_only.to_numpy() & (g.pos.to_numpy()==1)).sum())
        rows.append({"disease_index":di,"n_pos":int(g.pos.sum()),"n_gcd_only_pos":n_only,
                     "auc_all":a_all,"auc_supported_only":a_sup})
    r=pd.DataFrame(rows)
    tot=r.n_pos.sum(); only=r.n_gcd_only_pos.sum()
    print(f"\nL|{lname}|diseases={len(r)}|positives={tot:,}|GCD-only positives={only:,} "
          f"({100*only/max(tot,1):.1f}%)")
    print(f"  A|macro AUC all positives      {r.auc_all.mean():.4f}")
    print(f"  A|macro AUC supported only     {r.auc_supported_only.mean():.4f}"
          f"   delta {r.auc_supported_only.mean()-r.auc_all.mean():+.4f}")
    r["label"]=lname
    OUT.append(r)
    aff=r[r.n_gcd_only_pos>0]
    if len(aff):
        print(f"  A|on the {len(aff)} affected diseases: {aff.auc_all.mean():.4f} -> "
              f"{aff.auc_supported_only.mean():.4f}  delta {aff.auc_supported_only.mean()-aff.auc_all.mean():+.4f}")
    # what score do GCD-only positives actually get?
    m=sc[(sc.pos==1)&sc.is_gcd_only].proba_1
    n=sc[(sc.pos==1)&~sc.is_gcd_only].proba_1
    if len(m): print(f"  S|mean proba_1  GCD-only positives {m.mean():.4f}  vs supported {n.mean():.4f}")

res = pd.concat(OUT, ignore_index=True)
res["auc_delta"] = res.auc_supported_only - res.auc_all
dataiku.Dataset("pool_selection_bias").write_with_schema(res)
