"""
iter66b: WHY did convergence not lift? CSS's precision comes from INDEPENDENCE.
Measure it directly, then re-run convergence at a threshold that actually fires.

n=25 at 3+ families is too few to conclude anything. Fix the experiment.
"""
import numpy as np, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(c[k:]-c[:-k])/k; return o
def rollstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    c=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(c[k:]-c[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rollstd(x,k),1e-12)

B=np.load('/tmp/ticks/min_LTCBTC.npy'); BTC=np.load('/tmp/ticks/min_BTCUSDT.npy')
bfx=load_1m('LTC'); bt=(bfx[:,0]/1000).astype(np.int64); bc=bfx[:,2]
common,ia,ib=np.intersect1d(bt,B[:,0].astype(np.int64),return_indices=True)
pb=bc[ia]; pn=B[ib,1]; ofi=B[ib,2]; vol=B[ib,3]
_,ic,ig=np.intersect1d(common,BTC[:,0].astype(np.int64),return_indices=True)
btc_o=np.zeros(len(common)); btc_o[ic]=BTC[ig,2]
rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
disloc=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))
T1=z(disloc,60); T2=z(ofi,60); T3=z(btc_o,60); T4=-z(np.log(np.maximum(vol,1e-9)),60)

idx=np.arange(70,len(common)-2)
g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60); idx=idx[g]
ok=np.isfinite(rb[idx+1])&np.isfinite(T1[idx])&np.isfinite(T2[idx])&np.isfinite(T3[idx])&np.isfinite(T4[idx])
idx=idx[ok]; y=rb[idx+1]
F={'T1 cross-venue':T1[idx],'T2 order-flow':T2[idx],'T3 BTC-hub':T3[idx],'T4 absence':T4[idx]}
names=list(F)

print("="*80)
print("INDEPENDENCE MATRIX - CSS requires families from DIFFERENT origins")
print("="*80)
print(f"{'':<17}"+"".join(f"{n[:12]:>13}" for n in names))
for a in names:
    row=f"{a:<17}"
    for b in names:
        row+=f"{np.corrcoef(F[a],F[b])[0,1]:>13.3f}"
    print(row)
print()
mx=max(abs(np.corrcoef(F[a],F[b])[0,1]) for a in names for b in names if a!=b)
print(f"max |off-diagonal correlation| = {mx:.3f}")
print("CSS needs these near 0. Values here:", "GOOD - genuinely independent" if mx<0.2 else "TOO CORRELATED")

n=len(idx); cut=int(n*0.6); yo=y[cut:]
print()
print("="*80)
print("RE-RUN CONVERGENCE AT THRESHOLDS THAT ACTUALLY FIRE")
print("="*80)
print(f"{'thr':>5}{'need':>6}{'n fired':>10}{'ACC':>9}{'mean bp':>10}{'vs best single':>16}")
for K in (0.5,1.0,1.5,2.0):
    # learn signs on train
    sg={}
    for nm in names:
        f=F[nm][:cut]; m=np.abs(f)>=K
        sg[nm]= 1 if (m.sum()>50 and (np.sign(f[m])==np.sign(y[:cut][m])).mean()>=0.5) else -1
    # best single OOS at this threshold
    bs=0
    for nm in names:
        f=F[nm][cut:]; m=np.abs(f)>=K
        if m.sum()>100:
            a=100*(np.sign(f[m]*sg[nm])==np.sign(yo[m])).mean()
            bs=max(bs,a)
    V=np.zeros(len(yo)); NA=np.zeros(len(yo))
    for nm in names:
        f=F[nm][cut:]
        v=np.zeros(len(f)); v[f>=K]=sg[nm]; v[f<=-K]=-sg[nm]
        V+=v; NA+=(np.abs(f)>=K).astype(int)
    for need in (2,3,4):
        m=(np.abs(V)>=need)&(NA>=need)
        if m.sum()<50: continue
        acc=100*(np.sign(V[m])==np.sign(yo[m])).mean()
        bp=1e4*(np.sign(V[m])*yo[m]).mean()
        print(f"{K:>5.1f}{need:>6}{int(m.sum()):>10}{acc:>8.2f}%{bp:>+9.3f}{acc-bs:>+15.2f}")
    print(f"      (best single at thr {K}: {bs:.2f}%)")
