"""CROSS-EXCHANGE PRICE DISCOVERY: Binance vs Bitfinex, same asset, same minute.
If one venue leads, the follower's chart has NOT yet reacted. That is a signal
that exists strictly before the follower's candle prints."""
import numpy as np, glob, os, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/inversion')
from load import load_1m
PAIRS=[('BTCUSDT','BTC'),('LTCBTC','LTC'),('NEOUSDT','NEO'),('ETHBTC','ETH')]
print("%-10s %9s %11s %11s %11s"%("asset","overlap","BFX->BNB","BNB->BFX","contemp"))
for bn,bf in PAIRS:
    B=np.load('/tmp/ticks/min_%s.npy'%bn)
    a=load_1m(bf)
    if a is None: continue
    # bitfinex 1m: MTS,OPEN,CLOSE,HIGH,LOW,VOL  -> seconds
    bt=(a[:,0]/1000.0).astype(np.int64); bc=a[:,2]
    nt=B[:,0].astype(np.int64); nc=B[:,1]
    common,ia,ib=np.intersect1d(bt,nt,return_indices=True)
    if len(common)<20000: 
        print("%-10s %9d  (insufficient overlap)"%(bf,len(common))); continue
    pb=bc[ia]; pn=nc[ib]
    rb=np.zeros(len(pb)); rb[1:]=np.log(np.maximum(pb[1:],1e-12)/np.maximum(pb[:-1],1e-12))
    rn=np.zeros(len(pn)); rn[1:]=np.log(np.maximum(pn[1:],1e-12)/np.maximum(pn[:-1],1e-12))
    cont=np.diff(common)==60
    idx=np.arange(1,len(common)-1)
    g=(common[idx+1]-common[idx]==60)&(common[idx]-common[idx-1]==60)
    i2=idx[g]
    m=np.isfinite(rb[i2])&np.isfinite(rn[i2])
    i2=i2[m]
    if len(i2)<5000: continue
    # BFX return at t -> BNB return at t+1
    c1=np.corrcoef(rb[i2],rn[i2+1])[0,1]
    c2=np.corrcoef(rn[i2],rb[i2+1])[0,1]
    c0=np.corrcoef(rb[i2],rn[i2])[0,1]
    print("%-10s %9d %+11.4f %+11.4f %+11.4f"%(bf,len(i2),c1,c2,c0))
