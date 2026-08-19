# nb5 — Data exploration.  Backs TARGET_PRIORITIZER section 3, which had NO artifact of any kind.
# Three questions, each of which the document currently answers from the retired 4-persona build:
#   3.1  how study-biased is the association label?
#   3.2  is there any clean partition of the disease ontology?  (the durable half of that section)
#   3.3  does granularity really trade novelty against confidence?  (the half section 8.10 refutes)
import dataiku, numpy as np, pandas as pd
from collections import defaultdict

nodes=dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index","node_id","node_name","node_type"], infer_with_pandas=False)
nodes["node_index"]=nodes.node_index.astype(int); nodes["node_id"]=nodes.node_id.astype(str)
D=nodes[nodes.node_type=="disease"]; G=nodes[nodes.node_type=="gene/protein"]
dname=dict(zip(D.node_index,D.node_name)); did=dict(zip(D.node_id,D.node_index))
print(f"NODES|diseases={len(D):,} genes={len(G):,}")

# ==== 3.1  the association label is study-biased ====
nodes=dataiku.Dataset("graph_nodes").get_dataframe(
    columns=["node_index","node_type"], infer_with_pandas=False)
nodes["node_index"]=nodes.node_index.astype(int)
dset=set(nodes[nodes.node_type=="disease"].node_index)
gset=set(nodes[nodes.node_type=="gene/protein"].node_index)
e=dataiku.Dataset("graph_edges").get_dataframe(
    columns=["relation","x_index","y_index"], infer_with_pandas=False)
dp=e[e.relation.astype(str).str.contains("disease_protein",case=False,na=False)].copy()
dp["x_index"]=dp.x_index.astype(int); dp["y_index"]=dp.y_index.astype(int)
fwd=dp[dp.x_index.isin(dset)&dp.y_index.isin(gset)]
rev=dp[dp.y_index.isin(dset)&dp.x_index.isin(gset)]
print(f"DIR|total disease_protein rows={len(dp):,} | disease-in-x={len(fwd):,} | disease-in-y={len(rev):,}")
canon=pd.concat([fwd.rename(columns={"x_index":"d","y_index":"g"})[["d","g"]],
                 rev.rename(columns={"y_index":"d","x_index":"g"})[["d","g"]]]).drop_duplicates()
print(f"DIR|unique (disease,gene) associations={len(canon):,}")
for lbl,ser in [("per disease",canon.groupby("d").size()),("per gene",canon.groupby("g").size())]:
    q=ser.quantile([.5,.9,.99]).values
    t1=100*ser.nlargest(max(1,len(ser)//100)).sum()/ser.sum()
    t10=100*ser.nlargest(max(1,len(ser)//10)).sum()/ser.sum()
    print(f"BIAS|{lbl:12s} n={len(ser):,} median={q[0]:.0f} p90={q[1]:.0f} p99={q[2]:.0f} "
          f"max={ser.max():,} | top1%={t1:.1f}% | top10%={t10:.1f}%")


# ==== 3.2  no clean partition of the ontology exists ====
hh=dataiku.Dataset("raw_disease_disease").get_dataframe()
hh["p"]=hh.parent_id.astype(str).map(did); hh["c"]=hh.child_id.astype(str).map(did)
hh=hh.dropna(subset=["p","c"]).astype({"p":int,"c":int})
print(f"ONTO|hierarchy edges resolving onto graph: {len(hh):,}")
nparents=hh.groupby("c").p.nunique()
elig=set(dataiku.Dataset("enriched_graph_features_candidate_psplit")
         .get_dataframe(columns=["disease_index"]).disease_index.astype(int).unique())
print(f"ONTO|eligible diseases (in pool): {len(elig):,}")
ne=nparents[nparents.index.isin(elig)]
print(f"ONTO|eligible diseases with >1 direct parent: {100*(ne>1).mean():.1f}% ({int((ne>1).sum())} of {len(ne)})")
# undirected transitive closure via union-find
par={}
def find(x):
    while par.setdefault(x,x)!=x: par[x]=par[par[x]]; x=par[x]
    return x
def uni(a,b):
    ra,rb=find(a),find(b)
    if ra!=rb: par[ra]=rb
for a,b in zip(hh.p.to_numpy(),hh.c.to_numpy()): uni(int(a),int(b))
comp=defaultdict(int)
for d in elig: comp[find(d)]+=1
big=max(comp.values())
print(f"ONTO|undirected transitive closure: largest component holds {big:,} of {len(elig):,} "
      f"eligible ({100*big/len(elig):.1f}%)")
# undirected K-hop
adj=defaultdict(set)
for a,b in zip(hh.p.to_numpy(),hh.c.to_numpy()):
    adj[int(a)].add(int(b)); adj[int(b)].add(int(a))
for K in [1,2]:
    seen=set(); best=0
    for seed in list(elig):
        if seed in seen: continue
        frontier={seed}; grp={seed}
        for _ in range(K):
            nxt=set()
            for x in frontier: nxt|=adj.get(x,set())
            nxt-=grp; grp|=nxt; frontier=nxt
        ge=grp&elig
        seen|=ge
        best=max(best,len(ge))
    print(f"ONTO|undirected K={K}: largest group {best:,} of {len(elig):,} ({100*best/len(elig):.1f}%)")

# ==== 3.3  does granularity trade novelty for confidence?  Test parent vs child at scale ====
va=dataiku.Dataset("validation_auc_by_disease").get_dataframe(
    columns=["disease_index","n_pos","n_neg","auc_disease","hits_at_50"])
va["module"]=va.n_pos+va.n_neg
auc=dict(zip(va.disease_index.astype(int),va.auc_disease))
npos=dict(zip(va.disease_index.astype(int),va.n_pos))
pairs=[]
for a,b in zip(hh.p.to_numpy(),hh.c.to_numpy()):
    a,b=int(a),int(b)
    if a in auc and b in auc:
        pairs.append({"parent":a,"child":b,"parent_auc":auc[a],"child_auc":auc[b],
                      "parent_pos":npos[a],"child_pos":npos[b]})
pp=pd.DataFrame(pairs)
print(f"\nGRAN|parent-child pairs both in validation: {len(pp):,}")
if len(pp):
    pp["child_better"]=pp.child_auc>pp.parent_auc
    pp["parent_coarser"]=pp.parent_pos>pp.child_pos
    print(f"GRAN|child (more specific) scores HIGHER in {100*pp.child_better.mean():.1f}% of pairs")
    print(f"GRAN|mean parent AUC={pp.parent_auc.mean():.4f} | mean child AUC={pp.child_auc.mean():.4f} "
          f"| delta={pp.child_auc.mean()-pp.parent_auc.mean():+.4f}")
    sub=pp[pp.parent_coarser]
    print(f"GRAN|restricted to pairs where the parent really is coarser (more positives), n={len(sub)}: "
          f"child higher in {100*sub.child_better.mean():.1f}%")
    # is AUC driven by module size at all?
    rho=va.module.rank().corr(va.auc_disease.rank())
    rho2=va.n_pos.rank().corr(va.auc_disease.rank())
    print(f"GRAN|Spearman(module_size, AUC)={rho:+.3f} | Spearman(n_pos, AUC)={rho2:+.3f}")
