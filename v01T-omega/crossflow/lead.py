"""DOES BTC's TAPE LEAD THE ALT's CHART? Directed lead-lag at 1-minute resolution.
For each alt: corr(BTC OFI at minute t, alt return over t+1..t+k).
This is a signal that exists BEFORE the alt's candle prints."""
import numpy as np
SYMS=['BNBUSDT','NEOUSDT','QTUMUSDT','ETHBTC','LTCBTC','BCCUSDT']
B=np.load('/tmp/ticks/min_BTCUSDT.npy')
bt=B[:,0]; bpx=B[:,1]; bofi=B[:,2]
br=np.zeros(len(B)); br[1:]=np.log(np.maximum(bpx[1:],1e-12)/np.maximum(bpx[:-1],1e-12))
print("BTC minutes: %d"%len(B))
print()
print("%-9s %8s %9s %9s %9s %9s %9s"%("alt","n","BTCofi->1m","->2m","->3m","->5m","BTCret->1m"))
for s in SYMS:
    A=np.load('/tmp/ticks/min_%s.npy'%s)
    at=A[:,0]; apx=A[:,1]
    # align on shared minutes
    common,ia,ib=np.intersect1d(at,bt,return_indices=True)
    if len(common)<5000: continue
    ap=apx[ia]; bo=bofi[ib]; brr=br[ib]
    ar=np.zeros(len(ap)); ar[1:]=np.log(np.maximum(ap[1:],1e-12)/np.maximum(ap[:-1],1e-12))
    cont=np.diff(common)==60.0
    row=[]
    for k in (1,2,3,5):
        idx=np.arange(len(common)-k-1)
        g=np.ones(len(idx),bool)
        for j in range(1,k+1): g&=(common[idx+j]-common[idx])==60.0*j
        i2=idx[g]
        if len(i2)<1000: row.append(np.nan); continue
        fwd=np.log(np.maximum(ap[i2+k],1e-12)/np.maximum(ap[i2],1e-12))
        x=bo[i2]
        m=np.isfinite(fwd)&np.isfinite(x)
        row.append(np.corrcoef(x[m],fwd[m])[0,1] if m.sum()>500 and x[m].std()>0 else np.nan)
    # also BTC RETURN (not flow) -> alt forward
    idx=np.arange(len(common)-2)
    g=(common[idx+1]-common[idx])==60.0
    i2=idx[g]
    fwd=np.log(np.maximum(ap[i2+1],1e-12)/np.maximum(ap[i2],1e-12))
    x=brr[i2]
    m=np.isfinite(fwd)&np.isfinite(x)
    cr=np.corrcoef(x[m],fwd[m])[0,1] if m.sum()>500 else np.nan
    print("%-9s %8d %+9.4f %+9.4f %+9.4f %+9.4f %+9.4f"%(s,len(common),row[0],row[1],row[2],row[3],cr))
