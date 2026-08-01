"""Flow impact is contemporaneous (+0.2263) but forward is ~0.
WHERE exactly does it die? Go INSIDE the hour using raw ticks - sub-minute.
If there is a directional edge, it lives at seconds-to-minutes, not hours."""
import numpy as np, zipfile, csv, io, glob, os
def load_day(path):
    z=zipfile.ZipFile(path);name=z.namelist()[0]
    ts=[];px=[];qty=[];sa=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try:
                ts.append(float(row[1]));px.append(float(row[2]));qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    if not ts: return None
    a=np.argsort(np.array(ts))
    return np.array(ts)[a],np.array(px)[a],np.array(qty)[a],np.array(sa)[a]
SYM='BTCUSDT'
files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%SYM))[:60]
BUCK=[5,15,30,60,300,900,1800,3600]
res={b:[] for b in BUCK}
for f in files:
    d=load_day(f)
    if d is None: continue
    ts,px,qty,sa=d
    unit=1000.0 if ts.max()>2e10 else 1.0
    T=ts/unit
    sign=np.where(sa,-1.0,1.0); sv=sign*qty
    for B in BUCK:
        b=np.floor(T/B).astype(np.int64)
        ub,first=np.unique(b,return_index=True)
        if len(ub)<20: continue
        # bucket OFI and bucket close
        ofi=np.zeros(len(ub)); close=np.zeros(len(ub))
        idx=np.split(np.arange(len(T)),first[1:])
        for i,g in enumerate(idx):
            q=qty[g].sum()
            ofi[i]=sv[g].sum()/max(q,1e-12); close[i]=px[g][-1]
        cont=np.diff(ub)==1
        r=np.zeros(len(ub)); r[1:]=np.log(np.maximum(close[1:],1e-12)/np.maximum(close[:-1],1e-12))
        # forward return over NEXT bucket
        if len(ub)<5: continue
        o=ofi[:-1][cont]; fwd=r[1:][cont]
        m=np.isfinite(o)&np.isfinite(fwd)
        if m.sum()>30 and o[m].std()>0:
            res[B].append(np.corrcoef(o[m],fwd[m])[0,1])
print("BTCUSDT, %d days — corr(OFI in bucket, return in NEXT bucket)"%len(files))
print("%-10s %10s %10s %8s"%("bucket","mean corr","t-stat","n_days"))
for B in BUCK:
    v=np.array(res[B]); v=v[np.isfinite(v)]
    if len(v)<5: continue
    t=v.mean()/(v.std(ddof=1)/np.sqrt(len(v)))
    lbl="%ds"%B if B<60 else "%dm"%(B//60) if B<3600 else "1h"
    print("%-10s %+10.4f %+10.2f %8d"%(lbl,v.mean(),t,len(v)))
