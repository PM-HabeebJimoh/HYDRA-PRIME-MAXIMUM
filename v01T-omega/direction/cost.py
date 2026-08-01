"""Directional edge exists at 15s-60s (corr +0.06 to +0.07, t=+13 to +15).
Can it be TRADED? Measure the real spread from executions and compare."""
import numpy as np, zipfile, csv, io, glob
def load_day(path):
    z=zipfile.ZipFile(path);name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try: ts.append(float(row[1]));px.append(float(row[2]));qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    a=np.argsort(np.array(ts))
    return np.array(ts)[a],np.array(px)[a],np.array(qty)[a],np.array(sa)[a]
for SYM in ('BTCUSDT','BNBUSDT','NEOUSDT'):
    files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%SYM))[:40]
    B=30
    grosses=[];spreads=[]
    for f in files:
        try: ts,px,qty,sa=load_day(f)
        except Exception: continue
        unit=1000.0 if ts.max()>2e10 else 1.0
        T=ts/unit; sign=np.where(sa,-1.0,1.0); sv=sign*qty
        # measured effective spread from real prints
        pb=px[sign>0]; ps=px[sign<0]
        if len(pb)>100 and len(ps)>100:
            mid=0.5*(pb.mean()+ps.mean())
            spreads.append((pb.mean()-ps.mean())/mid*1e4)
        b=np.floor(T/B).astype(np.int64)
        ub,first=np.unique(b,return_index=True)
        if len(ub)<50: continue
        idx=np.split(np.arange(len(T)),first[1:])
        ofi=np.array([sv[g].sum()/max(qty[g].sum(),1e-12) for g in idx])
        close=np.array([px[g][-1] for g in idx])
        cont=np.diff(ub)==1
        r=np.zeros(len(ub)); r[1:]=np.log(np.maximum(close[1:],1e-12)/np.maximum(close[:-1],1e-12))
        o=ofi[:-1][cont]; fwd=r[1:][cont]
        m=np.isfinite(o)&np.isfinite(fwd)
        if m.sum()<50: continue
        # trade the top/bottom quintile of |OFI|
        oo=o[m]; ff=fwd[m]
        q=np.quantile(oo,[0.2,0.8])
        pos=np.where(oo>=q[1],1.0,np.where(oo<=q[0],-1.0,0.0))
        act=pos!=0
        if act.sum()<10: continue
        grosses.append((pos[act]*ff[act]).mean()*1e4)   # bp per trade
    g=np.array(grosses); s=np.array(spreads)
    print("%-9s gross %+7.3f bp/trade (n=%d days)  |  measured half-spread %.3f bp  |  round trip %.3f bp"%(
        SYM,g.mean(),len(g),s.mean()/2,s.mean()))
    print("           NET after crossing spread both ways: %+7.3f bp   %s"%(
        g.mean()-s.mean(), "PROFIT" if g.mean()>s.mean() else "LOSS"))
