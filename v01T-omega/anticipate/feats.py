"""ANTICIPATORY FEATURE FUSION.

The old models were REACTIVE: wait for BB% extreme -> trade.
This one is ANTICIPATORY: predict WHERE volatility will be mispriced BEFORE it
expands, by fusing five classes of signal the reactive model throws away.

  INVISIBLE   intrabar structure only visible in 1m data: Parkinson vs close-to-
              close vol, Garman-Klass, intrabar realized vol, tick count
  HIDDEN      temporal: hour-of-day, day-of-week, time-since-last-squeeze
  SCATTERED   cross-sectional: how many OTHER instruments are compressed right
              now, market-wide vol, cross-instrument dispersion, BTC state
  NOISY       individually insignificant: return autocorrelation, run length,
              wick asymmetry, close-position-in-range
  DISREGARDED volume z-score, volume trend, bar gap counts, range/volume ratio

Target: option return-on-premium for a W-bar ATM straddle priced at IV=1.25x
trailing 20-bar vol. Predict it, rank, trade only the top slice.

Strict causality: every feature uses bars <= i. Entry at bar i+1 open.
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from load import load_1m, resample
import numpy as np

SY=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
W=4          # option tenor in hours
IVM=1.25     # market implied vol multiple

def Nd(x): return 0.5*(1.0+math.erf(x/math.sqrt(2.0)))
def straddle_prem(sig_T):
    return 2.0*(Nd(sig_T/2.0)-Nd(-sig_T/2.0))

def roll(x,k,fn='mean'):
    N=len(x); o=np.full(N,np.nan)
    v=np.nan_to_num(x,nan=0.0)
    c=np.cumsum(np.insert(v,0,0.0))
    m=(c[k:]-c[:-k])/k
    if fn=='mean':
        o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0))
        var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o

def build_one(sym_i, name):
    a=load_1m(name)
    if a is None or len(a)<50000: return None
    f=resample(a,60)
    if len(f)<400: return None
    t=f[:,0]; o=f[:,1]; c=f[:,2]; h=f[:,3]; l=f[:,4]; vol=f[:,5]; cnt=f[:,6]
    N=len(c)
    r=np.zeros(N); r[1:]=np.log(c[1:]/np.maximum(c[:-1],1e-12))

    # ---- volatility estimators (INVISIBLE: uses H/L, not just closes) ----
    s20=roll(r,20,'std')
    s5=roll(r,5,'std')
    s60=roll(r,60,'std')
    rng=np.log(np.maximum(h,1e-12)/np.maximum(l,1e-12))
    park=np.sqrt(np.maximum(roll(rng*rng,20)/(4*math.log(2)),0.0))     # Parkinson
    co=np.log(np.maximum(c,1e-12)/np.maximum(o,1e-12))
    gk=np.sqrt(np.maximum(roll(0.5*rng*rng-(2*math.log(2)-1)*co*co,20),0.0))  # Garman-Klass
    # intrabar vol signature: range-based vs close-based. >1 => intrabar churn
    vratio_pc=park/np.maximum(s20,1e-12)
    vratio_gc=gk/np.maximum(s20,1e-12)

    # ---- BB / HV (the original v01T primitives) ----
    sma=roll(c,20); sd=roll(c,20,'std')
    up=sma+2*sd; lo=sma-2*sd; wd=up-lo
    bb=np.where(wd>0,(c-lo)/np.maximum(wd,1e-12)*100.0,50.0)
    hv=s5/np.maximum(s20,1e-12)
    bandwidth=wd/np.maximum(sma,1e-12)          # squeeze WIDTH (disregarded!)
    bw_pct=np.full(N,np.nan)                     # bandwidth percentile vs own past
    for k in range(100,N):
        w=bandwidth[k-100:k]
        w=w[np.isfinite(w)]
        if len(w)>10: bw_pct[k]=(w<bandwidth[k]).mean()

    # ---- NOISY: autocorrelation, runs, wicks ----
    ac=np.full(N,np.nan)
    for k in range(30,N):
        seg=r[k-20:k]
        if seg.std()>0: ac[k]=np.corrcoef(seg[:-1],seg[1:])[0,1]
    sgn=np.sign(r)
    runlen=np.zeros(N)
    for k in range(1,N):
        runlen[k]=runlen[k-1]+1 if sgn[k]==sgn[k-1] and sgn[k]!=0 else 1
    uw=(h-np.maximum(o,c))/np.maximum(h-l,1e-12)
    lw=(np.minimum(o,c)-l)/np.maximum(h-l,1e-12)
    cpos=(c-l)/np.maximum(h-l,1e-12)
    wick_asym=uw-lw

    # ---- DISREGARDED: volume, activity, gaps ----
    lv=np.log(np.maximum(vol,1e-9))
    vz=(lv-roll(lv,20))/np.maximum(roll(lv,20,'std'),1e-12)
    vtrend=roll(lv,5)-roll(lv,20)
    cz=(cnt-roll(cnt,20))/np.maximum(roll(cnt,20,'std'),1e-12)
    rv_ratio=rng/np.maximum(np.log1p(vol),1e-12)     # range per unit volume = illiquidity
    rvz=(rv_ratio-roll(rv_ratio,20))/np.maximum(roll(rv_ratio,20,'std'),1e-12)

    # ---- HIDDEN: temporal ----
    hr=((t/3600000.0)%24).astype(float)
    dow=((t/86400000.0+4)%7).astype(float)
    hsin=np.sin(2*np.pi*hr/24); hcos=np.cos(2*np.pi*hr/24)
    dsin=np.sin(2*np.pi*dow/7); dcos=np.cos(2*np.pi*dow/7)

    # ---- trend / position ----
    m50=roll(c,50); m200=roll(c,200)
    dist50=(c-m50)/np.maximum(s20*c,1e-12)
    dist200=(c-m200)/np.maximum(s20*c,1e-12)
    volofvol=roll(s20,20,'std')/np.maximum(roll(s20,20),1e-12)
    accel=s5/np.maximum(s60,1e-12)

    # ---- TARGET: option return on premium ----
    idx=np.arange(250,N-W-2)
    e=idx+1
    S0=o[e]
    j=np.minimum(e+W,N-1)
    payoff=np.abs(c[j]-S0)/S0
    sigT=s20[idx]*math.sqrt(W)*IVM
    prem=np.array([straddle_prem(x) if np.isfinite(x) and x>0 else np.nan for x in sigT])
    y=(payoff-prem)/prem

    F={
     'bb':bb[idx],'bb_ext':np.abs(bb[idx]-50.0),'hv':hv[idx],
     'bandwidth':bandwidth[idx],'bw_pct':bw_pct[idx],
     's20':s20[idx],'s5_s60':accel[idx],'volofvol':volofvol[idx],
     'park_close':vratio_pc[idx],'gk_close':vratio_gc[idx],
     'ac':ac[idx],'runlen':runlen[idx],'wick_asym':wick_asym[idx],'cpos':cpos[idx],
     'vz':vz[idx],'vtrend':vtrend[idx],'cz':cz[idx],'rvz':rvz[idx],
     'hsin':hsin[idx],'hcos':hcos[idx],'dsin':dsin[idx],'dcos':dcos[idx],
     'dist50':dist50[idx],'dist200':dist200[idx],
    }
    return dict(t0=t[e], t1=t[np.minimum(e+W,N-1)], y=y, prem=prem, sym=np.full(len(idx),sym_i,float),
                s20v=s20[idx], bbv=bb[idx], F=F)

if __name__=='__main__':
    out=[]
    for i,s in enumerate(SY):
        d=build_one(i,s)
        if d is None: continue
        out.append(d); print("%-5s bars=%d"%(s,len(d['y'])),flush=True)
    keys=sorted(out[0]['F'].keys())
    X=np.concatenate([np.stack([d['F'][k] for k in keys],1) for d in out],0)
    y=np.concatenate([d['y'] for d in out])
    t0=np.concatenate([d['t0'] for d in out]); t1=np.concatenate([d['t1'] for d in out])
    prem=np.concatenate([d['prem'] for d in out]); sym=np.concatenate([d['sym'] for d in out])
    s20v=np.concatenate([d['s20v'] for d in out]); bbv=np.concatenate([d['bbv'] for d in out])
    ok=np.isfinite(y)&np.isfinite(X).all(1)&np.isfinite(prem)&(prem>0)
    X=X[ok];y=y[ok];t0=t0[ok];t1=t1[ok];prem=prem[ok];sym=sym[ok];s20v=s20v[ok];bbv=bbv[ok]
    o=np.argsort(t0)
    np.savez_compressed('feat.npz',X=X[o],y=y[o],t0=t0[o],t1=t1[o],prem=prem[o],
                        sym=sym[o],s20=s20v[o],bb=bbv[o],keys=np.array(keys))
    print("TOTAL %d rows x %d features"%X.shape)
