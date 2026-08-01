"""Binance LEADS Bitfinex (+0.1185 BTC, +0.1476 NEO, asymmetric = real discovery).
Now: can we PREDICT the Bitfinex follower move using the Binance leader?
This is 'know it before that chart reacts'."""
import numpy as np, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
PAIRS=[('BTCUSDT','BTC'),('NEOUSDT','NEO'),('LTCBTC','LTC'),('ETHBTC','ETH')]
for bn,bf in PAIRS:
    B=np.load('/tmp/ticks/min_%s.npy'%bn)
    a=load_1m(bf)
    if a is None: continue
    bt=(a[:,0]/1000.0).astype(np.int64); bc=a[:,2]
    nt=B[:,0].astype(np.int64); nc=B[:,1]; nofi=B[:,2]
    common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
    if len(common)<20000: continue
    pb=bc[ia]; pn=nc[ib]; of=nofi[ib]
    rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
    rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
    # DISLOCATION: log price ratio vs its own short mean  -> the gap to be closed
    lr=np.log(np.maximum(pn,1e-12))-np.log(np.maximum(pb,1e-12))
    k=30
    c=np.cumsum(np.insert(lr,0,0.0)); mu=np.full(len(lr),np.nan); mu[k-1:]=(c[k:]-c[:-k])/k
    disloc=lr-mu
    idx=np.arange(k+2,len(common)-2)
    g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60)
    i2=idx[g]
    fwd=rb[i2+1]                      # BITFINEX next-minute return (the follower)
    feats={'binance_ret':rn[i2],'binance_ofi':of[i2],'disloc':disloc[i2],
           'bfx_ret':rb[i2]}
    ok=np.isfinite(fwd)
    for v in feats.values(): ok&=np.isfinite(v)
    print()
    print("=== %s : predict BITFINEX t+1 from BINANCE t ==="%bf)
    print("  n=%d"%ok.sum())
    for nm,v in feats.items():
        print("   corr(%-13s, bfx_fwd) = %+.4f"%(nm,np.corrcoef(v[ok],fwd[ok])[0,1]))
    # simple tradable rule: dislocation reverts
    d=disloc[i2][ok]; f=fwd[ok]
    q=np.quantile(d,[0.05,0.95])
    lo=d<=q[0]; hi=d>=q[1]
    print("   dislocation extreme: BFX cheap n=%d fwd %+0.3f bp | BFX rich n=%d fwd %+0.3f bp"%(
        lo.sum(),1e4*f[lo].mean(),hi.sum(),1e4*f[hi].mean()))
    print("   L/S spread = %+0.3f bp per trade"%(1e4*(f[lo].mean()-f[hi].mean())/2))
