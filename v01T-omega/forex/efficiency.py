"""Depth helps capacity but HURTS edge - deeper markets are more efficient.
Test on the real Kraken EURUSD 2026 minutes: is there ANY predictability?"""
import json, numpy as np
K=json.load(open('/tmp/krk_eurusd.json'))
ts=np.array(sorted(int(k) for k in K)); px=np.array([K[str(t)] for t in ts])
r=np.zeros(len(px)); r[1:]=np.log(px[1:]/px[:-1])
cont=np.diff(ts)==60
i=np.arange(1,len(ts)-1)
g=(ts[i+1]-ts[i]==60)&(ts[i]-ts[i-1]==60)
i2=i[g]
print("EURUSD Kraken 2026: %d bars, %d usable"%(len(ts),len(i2)))
print()
print("PREDICTABILITY TESTS (the thing depth destroys)")
ac1=np.corrcoef(r[i2],r[i2+1])[0,1]
n=len(i2); t1=ac1*np.sqrt((n-2)/(1-ac1**2))
print("  1-min return autocorrelation  : %+.4f  (t=%.2f)"%(ac1,t1))
mv=np.abs(r)
acv=np.corrcoef(mv[i2],mv[i2+1])[0,1]
print("  |return| autocorrelation (vol): %+.4f"%acv)
print()
print("MOVE SIZE — the other half of the problem")
print("  median |1-min move| : %.4f bp"%(1e4*np.median(np.abs(r[i2]))))
print("  mean   |1-min move| : %.4f bp"%(1e4*np.abs(r[i2]).mean()))
print("  EURUSD spread       : 0.1 - 0.5 bp")
print()
med=1e4*np.median(np.abs(r[i2]))
print("  move/spread ratio   : %.2fx  (crypto NEO was ~35bp move vs 12.8bp spread = 2.7x)"%(med/0.3))
print()
print("VERDICT LOGIC:")
print("  crypto: big edge, no capacity")
print("  forex : huge capacity, and the question is whether ANY edge survives")
