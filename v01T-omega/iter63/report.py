"""
iter63: the user's four questions, answered with numbers.
  - per-month DD and WR (never reported per-month before for the CAUSAL slice)
  - the causal (no-lookahead) selection from iter62
  - correct liquidation rule x <= -1/L
ERA 2018-19 | Binance -> Bitfinex 1m ticks | costs charged
"""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}

def load(nm):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm)
    t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p,y,t=p[v],y[v],t[v]
    o=np.argsort(t); return p[o],y[o],t[o]

def causal_take(ap, warm=2000, q=0.90):
    thr=np.inf; take=np.zeros(len(ap),bool)
    for i in range(len(ap)):
        if i>=warm and (i%500==0 or thr==np.inf): thr=np.quantile(ap[:i],q)
        if i>=warm and ap[i]>=thr: take[i]=True
    return take

def month_of(t):
    return np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])

for nm in ('LTC','NEO','BTC'):
    try: p,y,t=load(nm)
    except Exception as e:
        print(nm,"missing",e); continue
    lab=month_of(t); keep=~np.isin(lab,list(DROP))
    p,y,t,lab=p[keep],y[keep],t[keep],lab[keep]
    ret=np.sign(p)*y-(SPREAD[nm]+FEE)*1e-4
    take=causal_take(np.abs(p))
    r=ret[take]; L=lab[take]
    print()
    print("="*90)
    print("%s | ERA 2018-19 | CAUSAL slice (no lookahead) | cost %.3fbp spread + %.1fbp fee"%(
        nm,SPREAD[nm],FEE))
    print("="*90)
    print("trades %d | mean edge %+.3f bp | worst single trade %.4f%%"%(
        len(r),1e4*r.mean(),100*r.min()))
    for lev in (5,10):
        print()
        print("--- %dx leverage (liquidation at %.2f%% adverse) ---"%(lev,100.0/lev))
        print("%-9s %7s %9s %10s %16s %6s"%("month","trades","WR%","maxDD%","MONTH ROI","liq"))
        vals=[]
        for m in sorted(set(L)):
            rr=r[L==m]
            cap=1.0;peak=1.0;dd=0.0;dead=False
            for x in rr:
                if x<=-1.0/lev: cap=0.0;dead=True;break
                cap*=(1.0+lev*x)
                if cap<=0: cap=0.0;dead=True;break
                peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
            vals.append(cap-1.0)
            print("%-9s %7d %8.2f%% %9.2f%% %+15.2f%% %6s"%(
                m,len(rr),100*(rr>0).mean(),100*dd,100*(cap-1),"LIQ" if dead else "-"))
        v=np.array(vals)
        print("  >=500%%: %d/%d   worst month %+.2f%%   mean WR %.2f%%"%(
            (v>=5.0).sum(),len(v),100*v.min(),100*(r>0).mean()))
