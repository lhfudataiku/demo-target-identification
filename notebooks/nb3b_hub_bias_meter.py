# 7.2 hub-bias meter, recomputed on the CHAMPION (m7-f14 as of 2026-08-21). Reads `scored_champion`,
# so it follows whatever the champion indirection points at -- the label below must track it.
# The documented comparison row is the retired 13-feature generation, kept fixed as the contrast.
# Method, unchanged: known targets ONLY (biology held constant, every row a true positive), bin by
# interactome degree, compare mean predicted probability in the lowest vs highest quintile.
import dataiku, numpy as np, pandas as pd
sc=dataiku.Dataset("scored_champion").get_dataframe(
    columns=["disease_index","gene_index","is_target","proba_1","gene_ppi_degree"])
kt=sc[sc.is_target==1].copy()
print(f"KT|known-target rows in validation: {len(kt):,}")
kt["dq"]=pd.qcut(kt.gene_ppi_degree.rank(method="first"),5,labels=False)
g=kt.groupby("dq").agg(n=("proba_1","size"), med_degree=("gene_ppi_degree","median"),
                       mean_proba=("proba_1","mean"))
print("HHDR|quintile|n|median_degree|mean_proba_1")
for q,r in g.iterrows():
    print(f"H|Q{int(q)+1}|{int(r.n):6d}|{r.med_degree:8.1f}|{r.mean_proba:.4f}")
q1=float(g.loc[0,"mean_proba"]); q5=float(g.loc[4,"mean_proba"])
rho=kt.gene_ppi_degree.rank().corr(kt.proba_1.rank())
print(f"HSUM|champion m7-f14|Q1={q1:.4f}|Q5={q5:.4f}|spread={q5-q1:+.4f}|rho(degree,proba)={rho:+.4f}")
print(f"HDOC|retired 13-feature|Q1=0.6516|Q5=0.7615|spread=+0.1099|rho=+0.2424")
print(f"HDELTA|Q1 {q1-0.6516:+.4f} | Q5 {q5-0.7615:+.4f} | spread {(q5-q1)-0.1099:+.4f} | rho {rho-0.2424:+.4f}")
# the detection-swing baseline quoted in the section (predicted-positive share at the F1 threshold)
THR=0.860
for q in [0,4]:
    sub=kt[kt.dq==q]
    print(f"HPP|Q{q+1}|median degree {sub.gene_ppi_degree.median():.1f}|"
          f"predicted positive at {THR}: {100*(sub.proba_1>=THR).mean():.1f}%")

# ---- assertions (section 7.2's table and its REFUTED verdict) ----
FAIL=[]
def check(name,doc,live,tol=0.0,fmt="{:,}"):
    ok=(abs(doc-live)<=tol) if isinstance(doc,(int,float)) else (doc==live)
    if not ok: FAIL.append((name,doc,live))
    print(f"CHK|{'PASS ' if ok else 'STALE'}|{name:44s} doc={fmt.format(doc):>12s} live={fmt.format(live):>12s}")

check("7.2 known-target rows",73829,len(kt))
check("7.2 champion Q1 probability",0.5938,round(q1,4),tol=0.0006,fmt="{:.4f}")
check("7.2 champion Q5 probability",0.7873,round(q5,4),tol=0.0006,fmt="{:.4f}")
check("7.2 champion spread",0.1935,round(q5-q1,4),tol=0.0006,fmt="{:+.4f}")
check("7.2 champion rho(degree,proba)",0.3273,round(float(rho),4),tol=0.0006,fmt="{:+.4f}")
# the verdict itself: the champion is WORSE than the retired generation on spread and rho
check("7.2 REFUTED: spread worse than retired",True,bool((q5-q1)>0.1099),tol=0,fmt="{}")
check("7.2 REFUTED: rho worse than retired",True,bool(float(rho)>0.2424),tol=0,fmt="{}")
print(f"SUMMARY|{len(FAIL)} STALE")
for f in FAIL: print("FAILED|%s|doc=%s|live=%s"%f)
