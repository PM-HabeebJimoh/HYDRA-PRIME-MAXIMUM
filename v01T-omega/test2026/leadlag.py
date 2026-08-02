"""THE 2026 TEST: does OKX lead Kraken (or vice versa) on LTC?
This is the exact mechanism behind the +1,234%/mo result."""
import json, numpy as np
d=json.load(open('/tmp/ltc2026.json'))
t=np.array(d['ts']); a=np.array(d['okx']); b=np.array(d['krk'])
ra=np.zeros(len(a)); ra[1:]=np.log(a[1:]/a[:-1])
rb=np.zeros(len(b)); rb[1:]=np.log(b[1:]/b[:-1])
cont=np.diff(t)==60
print("2026 LTC, OKX vs Kraken, %d overlapping minutes"%len(t))
print("contiguous minute pairs: %d"%cont.sum())
print()
idx=np.arange(1,len(t)-1)
g=(t[idx+1]-t[idx]==60)&(t[idx]-t[idx-1]==60)
i2=idx[g]
print("usable for lead-lag: %d"%len(i2))
print()
c0=np.corrcoef(ra[i2],rb[i2])[0,1]
c_ab=np.corrcoef(ra[i2],rb[i2+1])[0,1]   # OKX now -> Kraken next
c_ba=np.corrcoef(rb[i2],ra[i2+1])[0,1]   # Kraken now -> OKX next
print("contemporaneous corr(OKX, Kraken)     = %+.4f"%c0)
print("OKX(t) -> Kraken(t+1)                 = %+.4f"%c_ab)
print("Kraken(t) -> OKX(t+1)                 = %+.4f"%c_ba)
print()
print("2018-19 benchmark: Binance->Bitfinex +0.1185 vs reverse +0.0455 (2.6x asymmetry)")
print("2026 asymmetry ratio: %.2fx"%(abs(c_ab)/max(abs(c_ba),1e-9)))
print()
# dislocation signal
lr=np.log(b)-np.log(a)
k=15
mu=np.convolve(lr,np.ones(k)/k,mode='full')[:len(lr)]
mu[:k-1]=np.nan
dis=lr-mu
m=np.isfinite(dis[i2])
cd=np.corrcoef(dis[i2][m],rb[i2+1][m])[0,1] if m.sum()>10 else float('nan')
print("dislocation(t) -> Kraken(t+1)          = %+.4f  (2018-19 NEO was +0.2778)"%cd)
print()
print("directional accuracy of sign(OKX ret) predicting sign(Kraken next):")
nz=(np.abs(ra[i2])>1e-9)&(np.abs(rb[i2+1])>1e-9)
if nz.sum()>5:
    acc=100*(np.sign(ra[i2][nz])==np.sign(rb[i2+1][nz])).mean()
    print("  n=%d  accuracy %.2f%%   (need >80%% to match the 2018-19 claim)"%(nz.sum(),acc))
