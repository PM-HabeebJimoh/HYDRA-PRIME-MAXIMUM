"""QTUM hits 69.14% at top 1%. Push to 80%: tighter confidence + magnitude filter
(only trade when predicted move is large relative to spread). And price it."""
import numpy as np, math
oof=np.load('/tmp/ticks/dirmodel_QTUMUSDT.npy')
SYMS=['BTCUSDT','BNBUSDT','NEOUSDT','QTUMUSDT','ETHBTC','LTCBTC']
D={s:np.load('/tmp/ticks/min_%s.npy'%s) for s in SYMS}
common=None
for s in SYMS:
    t=D[s][:,0]; common=t if common is None else np.intersect1d(common,t)
idx0=np.searchsorted(D['QTUMUSDT'][:,0],common)
P=D['QTUMUSDT'][idx0,1]
def roll(x,k,fn='mean'):
    M=len(x);o=np.full(M,np.nan);v=np.nan_to_num(x)
    c=np.cumsum(np.insert(v,0,0.0));m=(c[k:]-c[:-k])/k
    if fn=='mean': o[k-1:]=m
    else:
        c2=np.cumsum(np.insert(v*v,0,0.0));var=(c2[k:]-c2[:-k])/k-m*m
        o[k-1:]=np.sqrt(np.maximum(var,0.0)*k/(k-1))
    return o
R=np.concatenate([[0.0],np.log(np.maximum(P[1:],1e-12)/np.maximum(P[:-1],1e-12))])
sig=roll(R,30,'std')
fwd=np.concatenate([np.log(np.maximum(P[1:],1e-12)/np.maximum(P[:-1],1e-12)),[np.nan]])
ii=np.arange(70,len(common)-2)
cont=(common[ii+1]-common[ii])==60.0
ii=ii[cont]
y=fwd[ii]; s=sig[ii]
ok=np.isfinite(y)&np.isfinite(s)&(np.abs(y/np.maximum(s,1e-12))<20)
y=y[ok]; s=s[ok]
v=np.isfinite(oof); pv=oof[v]; yv=y[v] if len(y)==len(oof) else y[:len(oof)][v]
print("QTUM: n=%d"%len(pv))
print()
print("ACCURACY vs CONFIDENCE (extreme tail)")
print("%-12s %9s %10s %12s"%("slice","n","ACCURACY","mean bp"))
for fr in (0.02,0.01,0.005,0.002,0.001,0.0005):
    k=max(50,int(len(pv)*fr))
    sel=np.argsort(-np.abs(pv))[:k]
    acc=100*(np.sign(pv[sel])==np.sign(yv[sel])).mean()
    bp=1e4*(np.sign(pv[sel])*yv[sel]).mean()
    print("top %-9s %9d %9.2f%% %+11.3f"%("%.2f%%"%(100*fr),k,acc,bp))
print()
print("MEASURED QTUM round-trip spread was 15.3bp (iter37).")
print("=> even at 69%% accuracy, mean gross is ~+14.5bp < 15.3bp spread.")
print()
# accuracy conditional on predicted magnitude being large
print("ACCURACY when predicted move is LARGE relative to recent vol")
sv=s[v] if len(s)==len(oof) else s[:len(oof)][v]
thr=np.abs(pv)/np.maximum(sv/sv.mean(),1e-9)
for q in (0.90,0.95,0.99,0.995,0.999):
    cut=np.quantile(thr,q); sel=thr>=cut
    if sel.sum()<50: continue
    acc=100*(np.sign(pv[sel])==np.sign(yv[sel])).mean()
    bp=1e4*(np.sign(pv[sel])*yv[sel]).mean()
    print("  q%.3f n=%7d ACC %6.2f%%  mean %+8.3f bp"%(q,sel.sum(),acc,bp))
