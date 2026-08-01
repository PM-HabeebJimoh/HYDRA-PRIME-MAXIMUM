"""DIRECTION + MAGNITUDE. Every prior model predicted |move| and threw the SIGN away.

The tape has a natural directional variable that the candle destroys:
WHO was the aggressor. Aggressive buying is not the same as aggressive selling
even when the candle looks identical. That asymmetry is the direction signal.

Target here is SIGNED forward return, not absolute.
Strictly causal: hour h features -> signed return over h+1..h+W.
"""
import numpy as np, math, glob, os
W=4
def roll(x,k,fn='mean'):
    N=len(x);o=np.full(N,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
rows=[];ys=[];yabs=[];syms=[];TS=[];TE=[]
names=[]
for si,f in enumerate(sorted(glob.glob('/tmp/ticks/of_*.npy'))):
    A=np.load(f); nm=os.path.basename(f)[3:-4]; names.append(nm)
    t=A[:,0]; c=A[:,15]; N=len(A)
    r=np.zeros(N); r[1:]=np.log(np.maximum(c[1:],1e-12)/np.maximum(c[:-1],1e-12))
    s20=roll(r,20,'std')
    sma=roll(c,20); sd=roll(c,20,'std'); wd=4*sd
    bb=np.where(wd>0,(c-(sma-2*sd))/np.maximum(wd,1e-12)*100,50.0)
    def z(x,k=48): return (x-roll(x,k))/np.maximum(roll(x,k,'std'),1e-12)
    ofi=A[:,1]; inten=A[:,2]; clipr=A[:,4]; bigsh=A[:,5]; bigofi=A[:,6]
    lam=A[:,7]; vpin=A[:,8]; esp=A[:,9]; runs=A[:,10]; ac=A[:,11]; bs=A[:,12]; vol=A[:,13]
    # DIRECTIONAL features: signed, persistent, and interacted with liquidity
    ofi_1=np.concatenate([[np.nan],ofi[:-1]])
    ofi_2=np.concatenate([[np.nan]*2,ofi[:-2]])
    ofi_cum3=roll(ofi,3); ofi_cum12=roll(ofi,12)
    feats={
     # magnitude / regime (from before)
     'bb':bb,'bb_ext':np.abs(bb-50),'s20':s20,'vpin':vpin,'z_lam':z(lam),
     'z_inten':z(inten),'z_vol':z(np.log(np.maximum(vol,1e-9))),'runs':runs,'z_esp':z(esp),
     # DIRECTION: signed order flow at multiple horizons
     'ofi':ofi,'ofi_1':ofi_1,'ofi_2':ofi_2,'ofi_c3':ofi_cum3,'ofi_c12':ofi_cum12,
     'z_ofi':z(ofi),'bigofi':bigofi,'bigsh_x_bigofi':bigsh*bigofi,
     'ac':ac,'bestshare':bs,'z_clipr':z(clipr),
     # DIRECTION x LIQUIDITY: same flow moves price more when depth is thin
     'ofi_x_lam':ofi*np.nan_to_num(lam),
     'ofi_div_depth':ofi*np.nan_to_num(z(lam)),
     'ofi_x_vpin':ofi*vpin,
     'ofi_x_esp':ofi*np.nan_to_num(z(esp)),
     # position in band interacted with flow: buying INTO the upper band != buying at lower
     'ofi_x_bb':ofi*(bb-50)/50.0,
    }
    idx=np.arange(60,N-W-1)
    good=np.ones(len(idx),bool)
    for k in range(1,W+1): good&=(t[idx+k]-t[idx])==3600.0*k
    idx=idx[good]
    if len(idx)<500: continue
    fwd=np.log(np.maximum(c[idx+W],1e-12)/np.maximum(c[idx],1e-12))
    ysig=fwd/np.maximum(s20[idx]*math.sqrt(W),1e-12)      # vol-normalised signed return
    keys=sorted(feats.keys())
    Xs=np.stack([feats[k][idx] for k in keys],1)
    ok=np.isfinite(ysig)&np.isfinite(Xs).all(1)&(np.abs(ysig)<20)
    rows.append(Xs[ok]);ys.append(ysig[ok]);yabs.append(np.abs(ysig[ok]))
    syms.append(np.full(ok.sum(),si,float));TS.append(t[idx][ok]);TE.append(t[idx+W][ok])
    print("%-9s usable=%d"%(nm,ok.sum()),flush=True)
X=np.concatenate(rows);y=np.concatenate(ys);ya=np.concatenate(yabs)
sym=np.concatenate(syms);T0=np.concatenate(TS);T1=np.concatenate(TE)
o=np.argsort(T0)
np.savez_compressed('/tmp/ticks/dir.npz',X=X[o],y=y[o],yabs=ya[o],sym=sym[o],
                    t0=T0[o],t1=T1[o],keys=np.array(keys),names=np.array(names))
print("TOTAL %d x %d"%X.shape)
