"""HEAD TO HEAD on identical 2026 minutes, same venue (Kraken):
  EURUSD (deep, efficient)  vs  BTCUSD (the untested middle)
Same clock, same exchange, same measurement -> no apples/oranges."""
import json, numpy as np
def load(p):
    d=json.load(open(p))
    ts=np.array(sorted(int(k) for k in d)); px=np.array([d[str(t)] for t in ts])
    return ts,px
def stats(ts,px,spread_bp,name):
    r=np.zeros(len(px)); r[1:]=np.log(px[1:]/px[:-1])
    i=np.arange(1,len(ts)-1)
    g=(ts[i+1]-ts[i]==60)&(ts[i]-ts[i-1]==60)
    i2=i[g]
    med=1e4*np.median(np.abs(r[i2])); mean=1e4*np.abs(r[i2]).mean()
    ac=np.corrcoef(r[i2],r[i2+1])[0,1]
    n=len(i2); t=ac*np.sqrt((n-2)/max(1-ac*ac,1e-12))
    acv=np.corrcoef(np.abs(r[i2]),np.abs(r[i2+1]))[0,1]
    zero=100*(np.abs(r[i2])<1e-12).mean()
    return dict(name=name,n=n,med=med,mean=mean,ac=ac,t=t,acv=acv,
                sp=spread_bp,ratio=med/spread_bp,mratio=mean/spread_bp,zero=zero)
e=stats(*load('/tmp/krk_eurusd.json'),0.30,'EURUSD')
b=stats(*load('/tmp/krk_btc.json'),1.649,'BTCUSD')
print("="*78)
print("IDENTICAL WINDOW, IDENTICAL VENUE (Kraken), 2026-08-02")
print("="*78)
print("%-26s %14s %14s"%("metric","EURUSD","BTCUSD"))
print("%-26s %14d %14d"%("usable minutes",e['n'],b['n']))
print("%-26s %13.4f %13.4f"%("median |1m move| bp",e['med'],b['med']))
print("%-26s %13.4f %13.4f"%("mean   |1m move| bp",e['mean'],b['mean']))
print("%-26s %13.3f %13.3f"%("round-trip spread bp",e['sp'],b['sp']))
print("%-26s %13.2fx %12.2fx"%("MEDIAN move/spread",e['ratio'],b['ratio']))
print("%-26s %13.2fx %12.2fx"%("MEAN   move/spread",e['mratio'],b['mratio']))
print("%-26s %+13.4f %+13.4f"%("1m autocorrelation",e['ac'],b['ac']))
print("%-26s %+13.2f %+13.2f"%("   t-stat",e['t'],b['t']))
print("%-26s %+13.4f %+13.4f"%("|r| autocorr (vol clust)",e['acv'],b['acv']))
print("%-26s %12.1f%% %13.1f%%"%("zero-move minutes",e['zero'],b['zero']))
print()
print("BENCHMARK from iter44 (2018-19 Binance, measured):")
print("  NEO median move ~35bp vs 12.802bp spread = 2.73x  <- the profitable case")
print()
for x in (e,b):
    v="TRADEABLE" if x['ratio']>1.5 else ("MARGINAL" if x['ratio']>1.0 else "BELOW COST")
    print("  %-8s median move/spread %5.2fx  ->  %s"%(x['name'],x['ratio'],v))
