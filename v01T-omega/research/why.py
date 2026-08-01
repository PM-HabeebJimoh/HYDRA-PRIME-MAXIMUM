"""807 trades/month act like 8. WHY? Three candidate causes, tested separately."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
t0=A[:,0].min(); R=P[:,2]; sym=P[:,3].astype(int)
mb=((P[:,0]-t0)/86400000/30.44).astype(int)

# CAUSE 1: all symbols long/short the SAME WAY at the same time (crypto beta).
# proxy: within a month, do all symbols' mean R move together?
Ms=sorted(set(mb)); syms=sorted(set(sym))
G=np.full((len(syms),len(Ms)),np.nan)
for a,s in enumerate(syms):
    for b,m in enumerate(Ms):
        v=R[(sym==s)&(mb==m)]
        if len(v)>=5: G[a,b]=v.mean()
Gm=np.ma.masked_invalid(G)
C=np.ma.corrcoef(Gm).data; iu=np.triu_indices(len(syms),1)
print("1) CROSS-SYMBOL: mean pairwise corr of monthly edge = %.4f"%np.nanmean(C[iu]))

# CAUSE 2: WITHIN a month, are individual trades autocorrelated / clustered in time?
# Compare sd of monthly mean to iid prediction sd/sqrt(n).
rows=[]
for m in Ms:
    v=R[mb==m]
    if len(v)>=50: rows.append((len(v),v.mean(),v.std(ddof=1)))
rows=np.array(rows)
iid_se=(rows[:,2]/np.sqrt(rows[:,0])).mean()
act_se=rows[:,1].std(ddof=1)
print("2) WITHIN-MONTH: iid SE of monthly mean = %.4f ; ACTUAL sd of monthly means = %.4f"%(iid_se,act_se))
print("   inflation factor = %.1fx  -> effective n per month = %.0f (of %.0f)"%(
    act_se/iid_se, rows[:,0].mean()/(act_se/iid_se)**2, rows[:,0].mean()))

# CAUSE 3: is the EDGE ITSELF time-varying (regime), i.e. good months and bad months?
print("3) REGIME: monthly mean R  min %+.3f  p25 %+.3f  median %+.3f  p75 %+.3f  max %+.3f"%(
    np.percentile(rows[:,1],0),np.percentile(rows[:,1],25),np.percentile(rows[:,1],50),
    np.percentile(rows[:,1],75),np.percentile(rows[:,1],100)))
print("   fraction of months with NEGATIVE mean R = %.1f%%"%(100*(rows[:,1]<0).mean()))
print()
print("VERDICT: the binding constraint is the SPREAD OF MONTHLY EDGE (regime),")
print("not trade count. Adding trades inside a month does not add information.")
print()
# What would fix it: reduce monthly dispersion. Test vol-targeting per month.
print("TEST: does scaling risk INVERSELY to recent realised dispersion help?")
# walk-forward: risk_m proportional to 1/var of previous 6 months
mm=rows[:,1]; nn=rows[:,0]
lr_flat=[]; lr_vt=[]
hist=[]
for i in range(len(mm)):
    if len(hist)>=6:
        s=np.std(hist[-6:],ddof=1)
        w=min(3.0, 0.15/max(s,1e-6))
    else: w=1.0
    lr_flat.append(mm[i]); lr_vt.append(w*mm[i]); hist.append(mm[i])
lr_flat=np.array(lr_flat); lr_vt=np.array(lr_vt)
print("   flat      : mean %+.4f sd %.4f Sharpe %.3f"%(lr_flat.mean(),lr_flat.std(ddof=1),lr_flat.mean()/lr_flat.std(ddof=1)))
print("   vol-target: mean %+.4f sd %.4f Sharpe %.3f"%(lr_vt.mean(),lr_vt.std(ddof=1),lr_vt.mean()/lr_vt.std(ddof=1)))
