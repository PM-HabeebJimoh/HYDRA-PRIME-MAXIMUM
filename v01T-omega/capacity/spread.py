"""MEASURE the real effective spread per asset from executions with aggressor
flags. iter42 ASSUMED 8bp flat. Assumption is the blocker - measure it."""
import numpy as np, zipfile, csv, io, glob
def load_day(path):
    z=zipfile.ZipFile(path); name=z.namelist()[0]
    px=[];sa=[];qty=[]
    with z.open(name) as fh:
        rd=csv.reader(io.TextIOWrapper(fh,'utf-8')); next(rd,None)
        for row in rd:
            if len(row)<5: continue
            try: px.append(float(row[2])); qty.append(float(row[3]))
            except ValueError: continue
            sa.append(row[4].strip().lower()=='true')
    return np.array(px),np.array(qty),np.array(sa,dtype=bool)
print("%-9s %8s %14s %16s %14s"%("asset","days","half-spread bp","round-trip bp","med $/min"))
for sym in ('BTCUSDT','BNBUSDT','NEOUSDT','QTUMUSDT','LTCBTC','ETHBTC'):
    files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/%s/*.zip'%sym))[:60]
    hs=[];notional=[]
    for f in files:
        try: px,qty,sa=load_day(f)
        except Exception: continue
        b=px[~sa]; s=px[sa]
        if len(b)<200 or len(s)<200: continue
        mid=0.5*(b.mean()+s.mean())
        hs.append((b.mean()-s.mean())/mid*1e4/2)
        notional.append(px.mean()*qty.sum()/1440.0)
    if not hs: continue
    h=np.median(hs)
    print("%-9s %8d %13.3f %15.3f %14s"%(sym,len(hs),h,2*h,"${:,.0f}".format(np.median(notional))))
