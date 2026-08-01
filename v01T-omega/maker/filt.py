"""Naive MM loses at tight spreads (-2.84bp/fill at 5bp) = ADVERSE SELECTION.
Now add the cross-exchange signal as a QUOTE SKEW filter and measure the change.
Signal: Binance(leader) vs Bitfinex(follower) dislocation -> predicts NEO move."""
import numpy as np, zipfile, csv, io, glob, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
from mm import load_day

# build minute-indexed signal: Binance NEO leads; use its return + dislocation vs Bitfinex
B=np.load('/tmp/ticks/min_NEOUSDT.npy')
bt=B[:,0].astype(np.int64); bp=B[:,1]; bofi=B[:,2]
a=load_1m('NEO')
ft=(a[:,0]/1000.0).astype(np.int64); fp=a[:,2]
common,ia,ib=np.intersect1d(bt,ft,return_indices=True)
pn=bp[ia]; of=bofi[ia]; pf=fp[ib]
rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
lr=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pf,1e-12))
k=30
c=np.cumsum(np.insert(lr,0,0.0)); mu=np.full(len(lr),np.nan); mu[k-1:]=(c[k:]-c[:-k])/k
sd=np.full(len(lr),np.nan)
c2=np.cumsum(np.insert(lr*lr,0,0.0))
var=(c2[k:]-c2[:-k])/k-((c[k:]-c[:-k])/k)**2
sd[k-1:]=np.sqrt(np.maximum(var,0.0))
disl=(lr-mu)/np.maximum(sd,1e-12)
# predictive score for the NEXT minute on Binance NEO
score=np.nan_to_num(-disl)*1.0 + np.nan_to_num(rn)*50.0 + np.nan_to_num(of)*0.5
SIG={int(t):float(s) for t,s in zip(common,score)}
print("signal minutes: %d"%len(SIG))

def simulate(path, hs_bp, mode, thresh=1.0, max_inv=5.0, fee_bp=0.0):
    d=load_day(path)
    if d is None: return None
    ts,px,qty,sa=d
    unit=1000.0 if ts.max()>2e10 else 1.0
    T=ts/unit; m=np.floor(T/60.0).astype(np.int64)
    um,first=np.unique(m,return_index=True)
    if len(um)<60: return None
    grp=np.split(np.arange(len(T)),first[1:])
    inv=0.0; cash=0.0; fills=0.0; rows=[]
    for gi,g in enumerate(grp):
        p=px[g]; q=qty[g]; s=sa[g]
        mid=p[0]; hs=mid*hs_bp*1e-4
        bid=mid-hs; ask=mid+hs
        sc=SIG.get(int(um[gi]*60.0),0.0)
        want_bid=True; want_ask=True
        if mode=='skew':
            if sc> thresh: want_ask=False      # expect UP: don't sell
            if sc<-thresh: want_bid=False      # expect DOWN: don't buy
        elif mode=='step':
            if abs(sc)>thresh: want_bid=want_ask=False   # step aside on conviction
        if inv>=max_inv: want_bid=False
        if inv<=-max_inv: want_ask=False
        fb=fa=0.0
        if want_bid:
            hit=s&(p<bid)
            fb=min(qty[g][hit].sum(),1.0) if hit.any() else 0.0
        if want_ask:
            lift=(~s)&(p>ask)
            fa=min(qty[g][lift].sum(),1.0) if lift.any() else 0.0
        if fb>0: cash-=fb*bid*(1+fee_bp*1e-4); inv+=fb; fills+=fb
        if fa>0: cash+=fa*ask*(1-fee_bp*1e-4); inv-=fa; fills+=fa
        rows.append((cash+inv*p[-1],inv,p[-1]))
    r=np.array(rows)
    return r[-1,0]-r[0,0], fills, r[0,2], np.abs(r[:,1]).max()

files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/NEOUSDT/*.zip'))[:120]
print()
print("%-8s %-8s %8s %11s %11s %11s %8s"%("half-sp","mode","days","fills","pnl/day","bp/fill","maxinv"))
for hs in (5.0,10.0,20.0):
    for mode,th in (('none',0),('skew',0.5),('skew',1.0),('step',1.5)):
        tot=0.0;nf=0.0;nd=0;p0=None;mi=0
        for f in files:
            r=simulate(f,hs,mode if mode!='none' else 'x',th)
            if r is None: continue
            pnl,fl,px0,inv=r
            tot+=pnl;nf+=fl;nd+=1;mi=max(mi,inv)
            if p0 is None: p0=px0
        if nd==0 or nf==0: continue
        bp=1e4*(tot/nf)/max(p0,1e-9)
        lbl=mode if mode=='none' else "%s%.1f"%(mode,th)
        print("%-8.1f %-8s %8d %11.1f %11.4f %11.2f %8.1f"%(hs,lbl,nd,nf,tot/nd,bp,mi))
