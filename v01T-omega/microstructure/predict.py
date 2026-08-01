"""DOES THE TAPE PREDICT THE CANDLE?
Features from hour h (order flow) -> outcome over h+1..h+4 (the option payoff).
If tape features add nothing beyond chart features, my thesis is wrong."""
import numpy as np, math, glob, os
COLS=['t','ofi','intensity','mean_clip','clip_ratio','big_share','big_ofi',
      'lam','vpin','espread','runs','ac','bestshare','vol','n','close']
W=4; IVM=1.25
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem(s): return 2*(Nd(s/2)-Nd(-s/2))
def roll(x,k,fn='mean'):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
rows=[];ys=[];syms=[];ts=[];te=[]
for si,f in enumerate(sorted(glob.glob('/tmp/ticks/of_*.npy'))):
    A=np.load(f); nm=os.path.basename(f)[3:-4]
    t=A[:,0]; c=A[:,15]
    # keep only contiguous hours
    N=len(A)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20,'std')
    # chart-only baseline features
    sma=roll(c,20); sd=roll(c,20,'std')
    up=sma+2*sd; lo=sma-2*sd; wd=up-lo
    bb=np.where(wd>0,(c-lo)/np.maximum(wd,1e-12)*100,50.0)
    hv=roll(r,5,'std')/np.maximum(s20,1e-12)
    # tape features (z-scored vs own trailing 48h)
    def z(x,k=48):
        return (x-roll(x,k))/np.maximum(roll(x,k,'std'),1e-12)
    ofi=A[:,1]; inten=A[:,2]; clipr=A[:,4]; bigsh=A[:,5]; bigofi=A[:,6]
    lam=A[:,7]; vpin=A[:,8]; esp=A[:,9]; runs=A[:,10]; ac=A[:,11]
    bs=A[:,12]; vol=A[:,13]
    feats={
      'bb':bb,'bb_ext':np.abs(bb-50),'hv':hv,'s20':s20,                  # CHART
      'ofi':ofi,'absofi':np.abs(ofi),'z_ofi':z(ofi),                      # TAPE
      'z_inten':z(inten),'z_clipr':z(clipr),'bigsh':bigsh,'bigofi':bigofi,
      'z_lam':z(lam),'vpin':vpin,'z_vpin':z(vpin),'z_esp':z(esp),
      'runs':runs,'ac':ac,'bestshare':bs,'z_vol':z(np.log(np.maximum(vol,1e-9))),
      'ofi_x_vpin':ofi*vpin,'absofi_x_lam':np.abs(ofi)*np.nan_to_num(lam),
    }
    idx=np.arange(60,N-W-1)
    # contiguity: require the next W hours to be consecutive
    good=np.ones(len(idx),bool)
    for k in range(1,W+1):
        good&= (t[idx+k]-t[idx]) == 3600.0*k
    idx=idx[good]
    if len(idx)<500: continue
    S0=c[idx]; payoff=np.abs(c[idx+W]-S0)/S0
    sigT=s20[idx]*math.sqrt(W)*IVM
    pr=np.array([prem(x) if np.isfinite(x) and x>0 else np.nan for x in sigT])
    y=(payoff-pr)/pr
    keys=sorted(feats.keys())
    Xs=np.stack([feats[k][idx] for k in keys],1)
    ok=np.isfinite(y)&np.isfinite(Xs).all(1)
    rows.append(Xs[ok]);ys.append(y[ok]);syms.append(np.full(ok.sum(),si,float))
    ts.append(t[idx][ok]);te.append(t[idx+W][ok])
    print("%-9s hours=%d usable=%d"%(nm,N,ok.sum()),flush=True)
X=np.concatenate(rows);y=np.concatenate(ys);sym=np.concatenate(syms)
T0=np.concatenate(ts);T1=np.concatenate(te)
o=np.argsort(T0)
np.savez_compressed('/tmp/ticks/micro.npz',X=X[o],y=y[o],sym=sym[o],t0=T0[o],t1=T1[o],keys=np.array(keys))
print("TOTAL %d x %d"%X.shape)
print("keys:",keys)
