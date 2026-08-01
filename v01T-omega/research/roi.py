"""Take every harvested config and ask ONE question: what ROI/mo at what DD?
Parallel event-queue simulation, honest, no per-trade sequential fiction."""
import numpy as np, glob, os, json
def simpack(E):
    E=E[np.argsort(E[:,0])]; n=len(E); R=E[:,2]
    ev=np.concatenate([np.stack([E[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([E[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    mo=(E[:,1].max()-E[:,0].min())/86400000/30.44
    return n,R,ev[:,1].astype(np.int8),ev[:,2].astype(np.int64),mo
def sim(pk,f):
    n,R,ET,EI,mo=pk
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f;lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*R[i];lv[i]=False
                if cap<=0: return 0.0,1.0,-1.0
                if cap>peak: peak=cap
                d=(peak-cap)/peak
                if d>dd: dd=d
    return cap,dd,(cap**(1/mo)-1)
def solve(pk,t):
    lo,hi=1e-9,3.0
    for _ in range(46):
        m=(lo+hi)/2;c,d,_=sim(pk,m)
        if c<=0 or d>t: hi=m
        else: lo=m
    return (lo,)+sim(pk,lo)
rows=[]
for fn in sorted(glob.glob('/tmp/v82/grid_*.npy')):
    key=os.path.basename(fn)[5:-4]
    E=np.load(fn)
    if len(E)<300: continue
    R=E[:,2]; se=R.std(ddof=1)/np.sqrt(len(R)); t=R.mean()/se
    if R.mean()<=0: continue
    pk=simpack(E)
    out={}
    for cap_dd in (0.04,0.15,0.30):
        f,c,d,r=solve(pk,cap_dd)
        out[cap_dd]=(f,d,r)
    rows.append((key,len(R),R.mean(),t,100*(R>0).mean(),out))
    print("%-34s n=%6d meanR %+.4f t=%+5.2f | DD4 %+8.2f%% | DD15 %+9.2f%% | DD30 %+10.2f%%"%(
        key,len(R),R.mean(),t,100*out[0.04][2],100*out[0.15][2],100*out[0.30][2]),flush=True)
rows.sort(key=lambda x:-x[5][0.15][2])
print("\nTOP by ROI at DD15:")
for r in rows[:8]:
    print("  %-34s t=%+5.2f DD4 %+8.2f%%  DD15 %+9.2f%%"%(r[0],r[3],100*r[5][0.04][2],100*r[5][0.15][2]))
