"""Is 69-74% real or overfit? Test: (a) per-fold stability, (b) net of spread."""
import numpy as np, math
oof=np.load('/tmp/ticks/dirmodel_QTUMUSDT.npy')
SYMS=['BTCUSDT','BNBUSDT','NEOUSDT','QTUMUSDT','ETHBTC','LTCBTC']
D={s:np.load('/tmp/ticks/min_%s.npy'%s) for s in SYMS}
common=None
for s in SYMS:
    t=D[s][:,0]; common=t if common is None else np.intersect1d(common,t)
idx0=np.searchsorted(D['QTUMUSDT'][:,0],common)
P=D['QTUMUSDT'][idx0,1]
fwd=np.concatenate([np.log(np.maximum(P[1:],1e-12)/np.maximum(P[:-1],1e-12)),[np.nan]])
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
ii=np.arange(70,len(common)-2); ii=ii[(common[ii+1]-common[ii])==60.0]
y=fwd[ii]; s=sig[ii]; T=common[ii]
ok=np.isfinite(y)&np.isfinite(s)&(np.abs(y/np.maximum(s,1e-12))<20)
y=y[ok];T=T[ok]
v=np.isfinite(oof); pv=oof[v]; yv=y[v]; tv=T[v]
mb=((tv-tv.min())/86400.0/30.44).astype(int)
print("PER-MONTH STABILITY at top 1% confidence")
print("%-7s %7s %9s %11s"%("month","n","ACC","mean bp"))
accs=[]
for m in range(mb.max()+1):
    z=mb==m
    if z.sum()<2000: continue
    p2=pv[z];y2=yv[z]
    k=max(20,int(len(p2)*0.01))
    sel=np.argsort(-np.abs(p2))[:k]
    a=100*(np.sign(p2[sel])==np.sign(y2[sel])).mean()
    accs.append(a)
    print("%-7d %7d %8.2f%% %+10.3f"%(m,z.sum(),a,1e4*(np.sign(p2[sel])*y2[sel]).mean()))
accs=np.array(accs)
print("mean %.2f%%  min %.2f%%  months>=80%%: %d/%d"%(accs.mean(),accs.min(),(accs>=80).sum(),len(accs)))
print()
print("NET OF MEASURED SPREAD (QTUM round-trip 15.28bp from real prints)")
SP=15.284
print("%-12s %9s %9s %12s %12s"%("slice","n","ACC","gross bp","NET bp"))
for fr in (0.01,0.005,0.002,0.001):
    k=max(50,int(len(pv)*fr))
    sel=np.argsort(-np.abs(pv))[:k]
    acc=100*(np.sign(pv[sel])==np.sign(yv[sel])).mean()
    g=1e4*(np.sign(pv[sel])*yv[sel]).mean()
    print("top %-8s %9d %8.2f%% %+11.3f %+11.3f  %s"%("%.2f%%"%(100*fr),k,acc,g,g-SP,"PROFIT" if g>SP else "LOSS"))
