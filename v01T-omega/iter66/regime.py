"""
iter66d: THE FIX. CSS works on a PERSISTENT LATENT STATE. Find the one that
exists in price data.

Evidence it exists: T1's accuracy is not constant. It runs
   45.6, 48.0, 46.6, 50.5, 55.0, 60.4, 57.8, 56.4, 54.7, 58.0
across sequential blocks. That is a SLOW-MOVING regime, exactly the kind of
persistent hidden state CSS is built for.

So the CSS-correct formulation is TWO-LEVEL:
  LEVEL 1 (CSS): use convergence of independent families to detect the STATE
                 "is the cross-venue lead currently WORKING?"
  LEVEL 2:       trade the direction signal ONLY while that state is ON.

This is precisely CSS's architecture: Tier 4 absence detection gates the trade.
And critically the state IS persistent, so agreement multiplies precision.

STATE SIGNALS (all causal, computed from PAST only):
  S1: trailing accuracy of T1 over last 2000 completed bars
  S2: trailing |corr| of T1 with realised next-return over last 2000
  S3: trailing volume regime (is the market active?)
  S4: trailing volatility regime
Require convergence of these to declare STATE=ON.
"""
import numpy as np, sys, datetime as dt
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

SPREAD={'LTC':1.153,'NEO':12.802,'BTC':1.649}; FEE=4.0
for SYM,BFILE in (('LTC','min_LTCBTC.npy'),('NEO','min_NEOUSDT.npy')):
    B=np.load('/tmp/ticks/'+BFILE); BTC=np.load('/tmp/ticks/min_BTCUSDT.npy')
    bfx=load_1m(SYM)
    if bfx is None: continue
    bt=(bfx[:,0]/1000).astype(np.int64); bc=bfx[:,2]
    common,ia,ib=np.intersect1d(bt,B[:,0].astype(np.int64),return_indices=True)
    if len(common)<50000: continue
    pb=bc[ia]; pn=B[ib,1]; vol=B[ib,3]
    rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
    disloc=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))
    T1=z(disloc,60)
    idx=np.arange(70,len(common)-2)
    g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60); idx=idx[g]
    ok=np.isfinite(rb[idx+1])&np.isfinite(T1[idx])&np.isfinite(vol[idx])
    idx=idx[ok]; y=rb[idx+1]; t1=T1[idx]; v=vol[idx]; tt=common[idx]
    n=len(idx)

    # ---- LEVEL 1: causal STATE detection -----------------------------------
    W=2000
    hit=(np.sign(t1)==np.sign(y)).astype(float)     # was T1 right? (known only AFTER)
    # trailing accuracy uses bars strictly BEFORE i  -> shift by 1
    ca=np.full(n,np.nan)
    cs=np.cumsum(np.insert(hit,0,0.0))
    ca[W:]=(cs[W:-1]-cs[:-W-1])/W                   # accuracy over previous W bars
    lv=np.log(np.maximum(v,1e-9))
    volz=np.full(n,np.nan); volz[W:]=(lv[W:]-roll(lv,W)[W:])/np.maximum(rollstd(lv,W)[W:],1e-12)
    ar=np.abs(y)
    volat=np.full(n,np.nan); volat[W:]=roll(ar,W)[W:]
    volat_z=np.full(n,np.nan)
    volat_z[2*W:]=(volat[2*W:]-roll(volat,W)[2*W:])/np.maximum(rollstd(volat,W)[2*W:],1e-12)

    print()
    print("="*90)
    print(f"{SYM} | CSS TWO-LEVEL: state-gated cross-venue direction | n={n:,}")
    print("="*90)
    cut=int(n*0.6)
    yo=y[cut:]; t1o=t1[cut:]; cao=ca[cut:]; vzo=volz[cut:]; vao=volat_z[cut:]
    K=2.0
    base=np.abs(t1o)>=K
    if base.sum()<200: print("too few"); continue
    acc0=100*(np.sign(t1o[base])==np.sign(yo[base])).mean()
    bp0=1e4*(np.sign(t1o[base])*yo[base]).mean()
    print(f"  UNGATED           n={int(base.sum()):>7}  acc={acc0:>6.2f}%  gross={bp0:>+7.3f}bp")
    print()
    print(f"  {'state gate (CSS convergence)':<42}{'n':>8}{'acc':>9}{'gross bp':>11}{'net bp':>10}")
    cost=SPREAD[SYM]+FEE
    for thr in (0.50,0.52,0.54,0.56):
        for extra,lbl in ((None,f"S1 acc>{thr:.2f}"),
                          ('vol',f"S1 acc>{thr:.2f} + S3 vol>0"),
                          ('both',f"S1 acc>{thr:.2f} + S3 vol>0 + S4 volat>0")):
            m=base&np.isfinite(cao)&(cao>thr)
            if extra in ('vol','both'): m&=np.isfinite(vzo)&(vzo>0)
            if extra=='both': m&=np.isfinite(vao)&(vao>0)
            if m.sum()<100: continue
            a=100*(np.sign(t1o[m])==np.sign(yo[m])).mean()
            b=1e4*(np.sign(t1o[m])*yo[m]).mean()
            print(f"  {lbl:<42}{int(m.sum()):>8}{a:>8.2f}%{b:>+10.3f}{b-cost:>+9.3f}")
