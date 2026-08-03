"""
iter67d: BUILD THE SYSTEM - on tradable signals only (open->close), CSS convergence.

Rules from what the study proved:
  * Target MUST be next_open -> next_close. Close-to-close is bounce-contaminated.
  * Use only fields that survived the bounce test.
  * CSS method: independent families, each gates, require convergence.
  * Report the ACCURACY vs COVERAGE curve - 85% is reachable only on a subset,
    so the honest deliverable is "largest subset at >=85%".

Families (independent origins):
  A  own-candle shape      (body, wicks, close location)  - the chart
  B  tape microstructure   (ofi, tfi, whale, top10)       - the tape, not the chart
  C  cross-asset BTC hub   (BTC ofi + BTC return)         - a different asset
  D  regime state          (trailing accuracy, vol, activity) - CSS Tier-4 style
"""
import numpy as np, os, sys, datetime as dt

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

BTC=np.load('/tmp/ticks/ohlc_BTCUSDT.npy')
bts=BTC[:,0].astype(np.int64)

def panel(sym):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,0].astype(np.int64)
    o,h,l,c=A[:,1],A[:,2],A[:,3],A[:,4]
    vol,ntr,ofi=A[:,5],A[:,6],A[:,7]
    vwap,maxtr,top10=A[:,10],A[:,11],A[:,12]
    upt,rev,tfi,spr=A[:,13],A[:,14],A[:,15],A[:,16]
    lc=np.log(np.maximum(c,1e-12)); lo=np.log(np.maximum(o,1e-12))
    # TRADABLE target: enter next open, exit next close
    y=np.full(len(c),np.nan); y[:-1]=lc[1:]-lo[1:]
    good=np.zeros(len(c),bool); good[:-1]=(ts[1:]-ts[:-1]==60)
    # BTC hub aligned
    _,ia,ib=np.intersect1d(ts,bts,return_indices=True)
    bofi=np.zeros(len(c)); bret=np.zeros(len(c))
    bo=BTC[ib,4]; blc=np.log(np.maximum(bo,1e-12))
    br=np.zeros(len(bo)); br[1:]=np.diff(blc)
    bofi[ia]=BTC[ib,7]; bret[ia]=br
    ret=np.zeros(len(c)); ret[1:]=np.diff(lc)
    FAM={
     'A_shape': z((c-o)/np.maximum(vwap,1e-12),240),
     'B_tape' : z(tfi,240),
     'B_ofi'  : z(ofi,240),
     'C_hub'  : z(bofi,240),
     'C_hubret':z(bret,240),
     'W_whale': z(maxtr/np.maximum(vol,1e-12),240),
    }
    ctx={'vol_z':z(np.log(np.maximum(vol,1e-9)),240),
         'ntr_z':z(np.log(np.maximum(ntr,1)),240),
         'rng_z':z(spr,240)}
    return FAM,ctx,y,good,ts,ret

print("="*98)
print("SYSTEM BUILD | target = NEXT OPEN -> NEXT CLOSE (tradable) | OOS = last 40%")
print("="*98)
for sym in ('BTCUSDT','LTCBTC','NEOUSDT'):
    if not os.path.exists('/tmp/ticks/ohlc_%s.npy'%sym): continue
    FAM,ctx,y,good,ts,ret=panel(sym)
    n=len(y); cut=int(n*0.6)
    tr=np.zeros(n,bool); tr[:cut]=True; oo=(~tr)
    base=good&np.isfinite(y)
    print()
    print(f"--- {sym}  n={n:,} ---")
    # learn each family's sign on TRAIN only
    sgn={}
    for k,v in FAM.items():
        m=base&tr&np.isfinite(v)&(np.abs(v)>1.5)
        if m.sum()<300: sgn[k]=0; continue
        a=(np.sign(v[m])==np.sign(y[m])).mean()
        sgn[k]= 1 if a>=0.5 else -1
    # OOS single-family accuracy
    print(f"{'family':<11}{'sign':>5}{'n':>9}{'acc OOS':>10}")
    for k,v in FAM.items():
        if sgn[k]==0: continue
        m=base&oo&np.isfinite(v)&(np.abs(v)>1.5)
        if m.sum()<200: continue
        a=100*(np.sign(v[m])*sgn[k]==np.sign(y[m])).mean()
        print(f"{k:<11}{sgn[k]:>5}{int(m.sum()):>9}{a:>9.2f}%")
    # CSS convergence: vote
    print()
    print(f"{'convergence rule':<30}{'n OOS':>9}{'ACCURACY':>11}{'mean bp':>10}")
    for K in (1.5,2.0,2.5):
        V=np.zeros(n); NA=np.zeros(n)
        for k,v in FAM.items():
            if sgn[k]==0: continue
            vv=np.nan_to_num(v)
            s=np.zeros(n); s[vv>=K]=sgn[k]; s[vv<=-K]=-sgn[k]
            V+=s; NA+=(np.abs(vv)>=K).astype(int)
        for need in (2,3):
            m=base&oo&(np.abs(V)>=need)&(NA>=need)
            if m.sum()<100: continue
            a=100*(np.sign(V[m])==np.sign(y[m])).mean()
            bp=1e4*(np.sign(V[m])*y[m]).mean()
            print(f"{'|z|>%.1f, >=%d agree'%(K,need):<30}{int(m.sum()):>9}{a:>10.2f}%{bp:>+9.3f}")
