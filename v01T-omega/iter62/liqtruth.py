"""
iter62: best.py prints 11/11 months >=5000% AND "SAFE".
But its own output line says:

    worst trade at 10x = -37.49%  vs liq 10.000%  -> SAFE

A -37.49% position move when liquidation is at -10% is NOT safe. It is a
blown account. The string "SAFE" comes from this expression in best.py:

    "SAFE" if abs(100*lev*r.min())<100.0/lev*100 else "check"

  abs(100*10*r.min()) = 37.49        (a PERCENT)
  100.0/lev*100       = 10/1*100 = 1000   (a percent times 100 - WRONG UNITS)

  37.49 < 1000 -> always True -> always prints SAFE.

This is bug #8 from my own log ("broken SAFE liquidation check"), and it is
STILL in the file producing the headline number. The correct test for a
position at leverage L with per-trade return x is:  x <= -1/L  => liquidated.

Re-run the exact same trades with the CORRECT liquidation rule.
ERA 2018-19 | real Binance->Bitfinex 1m ticks | LTC 10% slice
"""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}

def build(nm,sf):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    sel=[]
    for m in sorted(set(lab)):
        if m in DROP: continue
        idx=np.flatnonzero(lab==m)
        k=max(1,int(len(idx)*sf))
        sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
    sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4, lab[sel]

r,L=build('LTC',0.10)
print("="*84)
print("LTC 10%% slice | ERA 2018-19 | n=%d trades"%len(r))
print("="*84)
print("worst single trade return = %.4f%%"%(100*r.min()))
print()
print("LIQUIDATION THRESHOLD: a trade with return x wipes the account when x <= -1/L")
print()
print("%-5s %14s %14s %10s"%("lev","liq at","worst trade","breaches"))
for lev in (2,3,5,10,15,25,50):
    thr=-1.0/lev
    nb=int((r<=thr).sum())
    print("%-5d %13.4f%% %13.4f%% %10d"%(lev,100*thr,100*r.min(),nb))
print()
print("="*84)
print("MONTHLY ROI WITH CORRECT LIQUIDATION (account dies on first breach)")
print("="*84)
for lev in (2,3,5,10,15):
    print()
    print("--- %dx  (liquidation at %.3f%% adverse) ---"%(lev,100.0/lev))
    print("%-9s %8s %16s %8s"%("month","trades","MONTH RETURN","liq?"))
    vals=[]
    for m in sorted(set(L)):
        rr=r[L==m]
        cap=1.0; dead=False
        for x in rr:
            if x <= -1.0/lev:          # CORRECT liquidation test
                cap=0.0; dead=True; break
            cap*=(1.0+lev*x)
            if cap<=0: cap=0.0; dead=True; break
        vals.append(cap-1.0)
        print("%-9s %8d %+15.2f%% %8s"%(m,len(rr),100*(cap-1),"LIQ" if dead else ""))
    v=np.array(vals)
    print("  >=500%%: %d/11   >=5000%%: %d/11   worst month %+.2f%%"%(
        (v>=5.0).sum(),(v>=50.0).sum(),100*v.min()))
