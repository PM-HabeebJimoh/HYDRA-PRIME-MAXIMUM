"""
iter67c: THE TRAP CHECK before building anything.

Every top signal is NEGATIVE correlation (mean reversion):
  NEO close_loc -0.0793, c_vs_vwap -0.0678, body -0.0331, ret1 -0.0330
At 1-minute horizon that is the classic signature of BID-ASK BOUNCE:
trades alternate between bid and ask, so close-to-close returns are
mechanically negatively autocorrelated. It is NOT tradable - you cannot
buy at the bid print and sell at the ask print.

THE TEST that separates real mean-reversion from bounce:
  (a) predict close[i+1] vs close[i]      <- contaminated by bounce
  (b) predict close[i+1] vs OPEN[i+1]     <- tradable: enter at next open
If the edge exists in (a) but vanishes in (b), it was bounce. This is the
single most important check and I have been burned by its cousin before
(bug #2, iter30).
"""
import numpy as np, os
def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

print("="*96)
print("BID-ASK BOUNCE TEST: does the mean-reversion edge survive entering at the NEXT OPEN?")
print("="*96)
for sym in ('NEOUSDT','LTCBTC','BTCUSDT'):
    p='/tmp/ticks/ohlc_%s.npy'%sym
    if not os.path.exists(p): continue
    A=np.load(p); ts=A[:,0].astype(np.int64)
    o,h,l,c,vwap=A[:,1],A[:,2],A[:,3],A[:,4],A[:,10]
    good=np.zeros(len(c),bool); good[:-1]=(ts[1:]-ts[:-1]==60)
    lc=np.log(np.maximum(c,1e-12)); lo=np.log(np.maximum(o,1e-12))
    y_cc=np.zeros(len(c)); y_cc[:-1]=lc[1:]-lc[:-1]          # close->close
    y_oc=np.zeros(len(c)); y_oc[:-1]=lc[1:]-lo[1:]           # NEXT open -> next close (tradable)
    sigs={
      'close_loc': np.where(h>l,(c-l)/np.maximum(h-l,1e-12)-0.5,0.0),
      'c_vs_vwap': (c-vwap)/np.maximum(vwap,1e-12),
      'body':      (c-o)/np.maximum(vwap,1e-12),
    }
    n=len(c); cut=int(n*0.6)
    print()
    print(f"--- {sym} ---")
    print(f"{'signal':<12}{'corr(close-close)':>19}{'corr(open-close)':>19}{'acc CC':>9}{'acc OC':>9}{'verdict':>12}")
    for k,v in sigs.items():
        zz=z(v,240)
        m=good&np.isfinite(zz)&np.isfinite(y_cc)&np.isfinite(y_oc)&(np.abs(zz)>2)
        m[:cut]=False
        if m.sum()<200: 
            print(f"{k:<12}{'(never fires)':>19}"); continue
        c_cc=np.corrcoef(v[good&np.isfinite(v)][cut:] if False else v[m],y_cc[m])[0,1]
        c_oc=np.corrcoef(v[m],y_oc[m])[0,1]
        a_cc=100*(np.sign(zz[m])*-1==np.sign(y_cc[m])).mean()
        a_oc=100*(np.sign(zz[m])*-1==np.sign(y_oc[m])).mean()
        verdict="BOUNCE" if (a_cc-50)>2*(a_oc-50) and (a_oc-50)<3 else "REAL"
        print(f"{k:<12}{c_cc:>+19.4f}{c_oc:>+19.4f}{a_cc:>8.2f}%{a_oc:>8.2f}%{verdict:>12}")
