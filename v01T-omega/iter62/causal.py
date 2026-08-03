"""
iter62b: LOOKAHEAD IN THE SLICE SELECTION - bug #10 in my own work.

best.py / build() does, for each month:
    idx = trades in month m
    k   = 10% of len(idx)
    sel = idx[ argsort(-|pred|)[:k] ]        <-- ranks within the WHOLE month

To know that a given minute is in the top 10% of |prediction| for October,
you must have seen all of October. On 2019-10-01 you cannot. This selects
trades using future information, and |pred| correlates with realised move,
so it preferentially keeps the minutes that worked.

CORRECT: threshold must come only from the PAST. Use an EXPANDING quantile
computed on data strictly before each trade.

Same data, same model, same costs. Only the selection is made causal.
ERA 2018-19 | Binance->Bitfinex 1m ticks | LTC
"""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}

def load(nm):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p,y,t=p[v],y[v],t[v]
    o=np.argsort(t); return p[o],y[o],t[o]

def month_of(t):
    return np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])

def report(tag,r,L,levs=(5,10,15)):
    print("  "+tag+"  n=%d"%len(r))
    for lev in levs:
        vals=[];dead_any=0
        for m in sorted(set(L)):
            rr=r[L==m]; cap=1.0; dead=False
            for x in rr:
                if x<=-1.0/lev: cap=0.0;dead=True;break
                cap*=(1.0+lev*x)
                if cap<=0: cap=0.0;dead=True;break
            if dead: dead_any+=1
            vals.append(cap-1.0)
        v=np.array(vals)
        print("     %2dx  >=500%%: %2d/%d  >=5000%%: %2d/%d  worst %+14.2f%%  liq-months %d"%(
            lev,(v>=5.0).sum(),len(v),(v>=50.0).sum(),len(v),100*v.min(),dead_any))
    return

nm='LTC'
p,y,t=load(nm); lab=month_of(t)
keep=~np.isin(lab,list(DROP))
p,y,t,lab=p[keep],y[keep],t[keep],lab[keep]
ret_all=np.sign(p)*y-(SPREAD[nm]+FEE)*1e-4
ap=np.abs(p)

print("="*86)
print("LTC | ERA 2018-19 | identical model, identical costs - ONLY the slice rule changes")
print("="*86)
print()
print("A) ORIGINAL (per-month top 10% ranking = LOOKAHEAD):")
sel=[]
for m in sorted(set(lab)):
    idx=np.flatnonzero(lab==m); k=max(1,int(len(idx)*0.10))
    sel.append(idx[np.argsort(-ap[idx])[:k]])
sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
report("lookahead slice",ret_all[sel],lab[sel])

print()
print("B) CAUSAL (expanding quantile from strictly PAST data only):")
# threshold at time i = 90th pct of |pred| over all trades before i (min 2000 warmup)
order=np.argsort(t)
apo=ap[order]; ro=ret_all[order]; lo=lab[order]
WARM=2000
take=np.zeros(len(apo),dtype=bool)
# running 90th percentile via periodic recompute (every 500) on the past window
thr=np.inf
for i in range(len(apo)):
    if i>=WARM and (i%500==0 or thr==np.inf):
        thr=np.quantile(apo[:i],0.90)
    if i>=WARM and apo[i]>=thr: take[i]=True
report("causal slice",ro[take],lo[take])

print()
print("C) CAUSAL, threshold frozen from FIRST 3 MONTHS only (strictest):")
first3=set(sorted(set(lab))[:3])
mask3=np.isin(lo,list(first3))
thr3=np.quantile(apo[mask3],0.90)
take3=(~mask3)&(apo>=thr3)
report("frozen-threshold slice",ro[take3],lo[take3])
print()
print("If B and C collapse versus A, the headline came from the lookahead.")
