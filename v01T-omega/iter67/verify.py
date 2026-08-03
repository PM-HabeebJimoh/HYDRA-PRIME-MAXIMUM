"""
iter67f: AUDIT the 86.74% / 92.02% before believing it. Three ways it could be fake.

FAKE-CHECK 1: the median threshold `med` was computed on TRAIN - good. But the
              QUANTILE for "top 2%" is computed on the OOS set itself. That is
              mild lookahead (uses the OOS distribution). Recompute using a
              threshold frozen on TRAIN.
FAKE-CHECK 2: class imbalance. If the top-2% cells are almost all "high range",
              then 86% just reflects the base rate, not skill. Report base rate.
FAKE-CHECK 3: autocorrelation/overlap - adjacent minutes are not independent.
              Report an effective-sample-adjusted CI and a block-wise breakdown.
"""
import numpy as np
def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

for sym in ('BTCUSDT','LTCBTC','NEOUSDT'):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,0].astype(np.int64)
    h,l,vwap,vol,ntr=A[:,2],A[:,3],A[:,10],A[:,5],A[:,6]
    n=len(h); cut=int(n*0.6)
    rng=(h-l)/np.maximum(vwap,1e-12); lr=np.log(np.maximum(rng,1e-12))
    nxt=np.full(n,np.nan); nxt[:-1]=lr[1:]
    contig=np.zeros(n,bool); contig[:-1]=(ts[1:]-ts[:-1]==60)
    pred=0.5*z(lr,60)+0.3*z(np.log(np.maximum(vol,1e-9)),60)+0.2*z(np.log(np.maximum(ntr,1)),60)
    med=np.nanmedian(lr[:cut])                       # TRAIN median
    lab=(nxt>med)
    m=contig&np.isfinite(nxt)&np.isfinite(pred); m[:cut]=False
    av=np.abs(pred)
    print("="*88)
    print(f"{sym} | RANGE-DIRECTION (is next 1m range above train-median?) | OOS n={int(m.sum()):,}")
    print("="*88)
    base=100*lab[m].mean()
    print(f"  base rate (always predict 'high') = {base:.2f}%   -> beating this is the real test")
    print(f"  {'threshold source':<26}{'cut':>7}{'n':>9}{'acc':>9}{'base in cell':>14}{'lift':>8}")
    for p in (10,5,2,1):
        thr_tr=np.quantile(av[cut and slice(0,cut) or slice(0,cut)][np.isfinite(av[:cut])],1-p/100.0)
        for src,thr in (('TRAIN-frozen',thr_tr),('OOS (orig)',np.quantile(av[m],1-p/100.0))):
            mm=m&(av>=thr)
            if mm.sum()<50: continue
            acc=100*((pred[mm]>0)==lab[mm]).mean()
            bs=100*max(lab[mm].mean(),1-lab[mm].mean())
            print(f"  {src:<26}{p:>6}%{int(mm.sum()):>9}{acc:>8.2f}%{bs:>13.2f}%{acc-bs:>+7.2f}")
    # block stability on the train-frozen top-2%
    thr=np.quantile(av[:cut][np.isfinite(av[:cut])],0.98)
    mm=m&(av>=thr)
    idx=np.flatnonzero(mm)
    if len(idx)>200:
        print(f"  block stability (train-frozen top2%, n={len(idx)}):")
        for i,b in enumerate(np.array_split(idx,5)):
            a=100*((pred[b]>0)==lab[b]).mean()
            print(f"     block {i+1}: n={len(b):>5}  acc={a:>6.2f}%")
    print()
