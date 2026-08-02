"""LTC 38x: does EVERY complete month clear 500%? Run the real paths."""
import numpy as np, datetime as dt
SPREAD={'BTC':1.649,'NEO':12.802,'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}
def build(nm):
    p=np.load('/tmp/ticks/xex_%s.npy'%nm); y=np.load('/tmp/ticks/xexy_%s.npy'%nm); t=np.load('/tmp/ticks/xext_%s.npy'%nm)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
    sel=[]
    for m in sorted(set(lab)):
        if m in DROP: continue
        idx=np.flatnonzero(lab==m)
        k=max(1,int(len(idx)*0.005))
        sel.append(idx[np.argsort(-np.abs(p[idx]))[:k]])
    sel=np.concatenate(sel); sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel]-(SPREAD[nm]+FEE)*1e-4, lab[sel]
for nm,levs in (('LTC',(38,50,84)),('NEO',(214,)) ):
    r,L=build(nm)
    for lev in levs:
        print("=== %s at %dx : liquidation @ %.3f%% ==="%(nm,lev,100.0/lev))
        print("%-9s %7s %14s %10s %9s"%("month","trades","MONTH RETURN","maxDD","WR%"))
        vals=[];bust=0
        for m in sorted(set(L)):
            rr=r[L==m]
            cap=1.0;peak=1.0;dd=0.0;b=False
            for x in rr:
                cap*=(1.0+lev*x)
                if cap<=0: b=True;cap=0.0;break
                peak=max(peak,cap);dd=max(dd,(peak-cap)/peak)
            if b: bust+=1
            vals.append(cap-1.0)
            print("%-9s %7d %+13.2f%% %9.2f%% %8.1f%%%s"%(m,len(rr),100*(cap-1),100*dd,100*(rr>0).mean()," BUST" if b else ""))
        v=np.array(vals)
        print("  months %d | >=500%%: %d | >=5000%%: %d | worst %+.2f%% | busts %d"%(
            len(v),(v>=5.0).sum(),(v>=50.0).sum(),100*v.min(),bust))
        print("  worst single trade at %dx: %.1f%%  (liq threshold %.3f%%)"%(lev,100*lev*r.min(),100.0/lev))
        print()
