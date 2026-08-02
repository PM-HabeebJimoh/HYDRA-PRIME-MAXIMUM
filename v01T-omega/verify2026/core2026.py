"""What CAN be verified on 2026 with XLM+BTC 6h perp data:
the CORE HYPOTHESIS of the volatility-magnitude system -
that a straddle's payoff (|move|) is PREDICTABLE from prior-bar features.

If that predictive relationship has decayed in 2026, the system is dead
regardless of cross-section. If it holds, the system's foundation holds."""
import numpy as np, math, json, os, glob

def load(fn):
    d=json.load(open(fn))
    a=np.array(d,dtype=float)
    a=a[np.argsort(a[:,0])]
    _,u=np.unique(a[:,0],return_index=True)
    return a[np.sort(u)]

def roll(x,k,fn='mean'):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o

def analyse(a,label,W=4):
    # bitfinex candle: MTS, OPEN, CLOSE, HIGH, LOW, VOL
    t=a[:,0]; o=a[:,1]; c=a[:,2]; h=a[:,3]; l=a[:,4]; v=a[:,5]
    N=len(c)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20,'std')
    rng=np.log(np.maximum(h,1e-12)/np.maximum(l,1e-12))
    park=np.sqrt(np.maximum(roll(rng*rng,20)/(4*math.log(2)),0.0))
    sma=roll(c,20); sd=roll(c,20,'std'); wd=4*sd
    bb=np.where(wd>0,(c-(sma-2*sd))/np.maximum(wd,1e-12)*100,50.0)
    bw=wd/np.maximum(sma,1e-12)
    hv=roll(r,5,'std')/np.maximum(s20,1e-12)
    lv=np.log(np.maximum(v,1e-9)); vz=(lv-roll(lv,20))/np.maximum(roll(lv,20,'std'),1e-12)
    idx=np.arange(60,N-W-1)
    fwd=np.array([np.max(np.abs(c[i+1:i+1+W]-c[i]))/c[i] for i in idx])
    feats={'s20':s20[idx],'park':park[idx],'bandwidth':bw[idx],
           'hv':hv[idx],'bb_ext':np.abs(bb[idx]-50),'vz':vz[idx]}
    print("=== %s : %d bars, 2026 ==="%(label,N))
    print("   forward |move| over %d bars: mean %.4f%%  median %.4f%%"%(W,100*fwd.mean(),100*np.median(fwd)))
    for k,x in feats.items():
        m=np.isfinite(x)&np.isfinite(fwd)
        if m.sum()<100: continue
        cc=np.corrcoef(x[m],fwd[m])[0,1]
        print("   corr(%-11s, forward |move|) = %+.4f"%(k,cc))
    # THE key one: does trailing vol predict forward vol? (vol clustering)
    m=np.isfinite(s20[idx])&np.isfinite(fwd)
    print("   >>> VOL PERSISTENCE (the foundation) = %+.4f"%np.corrcoef(s20[idx][m],fwd[m])[0,1])
    return feats,fwd

fs=sorted(glob.glob('/tmp/y26/*.json'))
if not fs:
    print("no 2026 files staged yet")
else:
    for f in fs:
        a=load(f); analyse(a,os.path.basename(f))
