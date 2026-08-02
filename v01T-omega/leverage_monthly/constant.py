"""THE EXACT QUESTION: is >500% CONSTANT, every month?
Count months >=500% for each config. No blending, no CAGR, no excuses."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
def months(nm,lev,per_month_rank=False):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    if per_month_rank:
        sel=[]
        for m in sorted(set(lab)):
            idx=np.flatnonzero(lab==m)
            k=max(1,int(len(idx)*0.005))
            sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
        sel=np.concatenate(sel)
    else:
        k=int(len(p)*0.005); sel=np.argsort(-np.abs(p))[:k]
    sel=sel[np.argsort(t[sel])]
    r=np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4
    L=lab[sel]
    out=[]
    for m in sorted(set(L)):
        rr=r[L==m]
        if len(rr)<3: continue
        cap=1.0
        for x in rr:
            cap*=(1.0+lev*x)
            if cap<=0: cap=0.0;break
        out.append((m,len(rr),cap-1.0))
    return out
print("IS >500%/MONTH CONSTANT? (>=500% every single month)")
print("%-12s %8s %10s %12s %14s"%("config","months",">=500%","<500%","worst month"))
for nm,lev in (('NEO',25),('NEO',50),('LTC',25),('LTC',50)):
    o=months(nm,lev)
    v=np.array([x[2] for x in o])
    hit=(v>=5.0).sum()
    print("%-12s %8d %10d %12d %+13.2f%%"%("%s %dx"%(nm,lev),len(v),hit,len(v)-hit,100*v.min()))
print()
print("SAME, with HONEST per-month ranking (no global look-ahead in allocation):")
print("%-12s %8s %10s %12s %14s"%("config","months",">=500%","<500%","worst month"))
for nm,lev in (('NEO',25),('NEO',50),('LTC',25),('LTC',50)):
    o=months(nm,lev,per_month_rank=True)
    v=np.array([x[2] for x in o])
    hit=(v>=5.0).sum()
    print("%-12s %8d %10d %12d %+13.2f%%"%("%s %dx"%(nm,lev),len(v),hit,len(v)-hit,100*v.min()))
print()
print("WHAT LEVERAGE MAKES *EVERY* MONTH >=500%? (solve on the worst month)")
print("%-8s %14s %12s %16s"%("asset","lev needed","worst mo","liq @ 1/lev"))
for nm in ('NEO','LTC'):
    for L in range(5,401,5):
        o=months(nm,L,per_month_rank=True)
        v=np.array([x[2] for x in o])
        if len(v) and (v>=5.0).all():
            print("%-8s %13dx %+11.2f%% %15.3f%%"%(nm,L,100*v.min(),100.0/L))
            break
    else:
        print("%-8s %14s"%(nm,"none <=400x"))
