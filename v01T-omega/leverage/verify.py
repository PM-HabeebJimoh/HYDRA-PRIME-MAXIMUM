"""Before claiming >500%: does leverage chosen on EARLY data survive on LATE data?
This is the test that has killed every prior result."""
import numpy as np
def load(bf,sf):
    p=np.load('/tmp/ticks/xex_%s.npy'%bf); y=np.load('/tmp/ticks/xexy_%s.npy'%bf); t=np.load('/tmp/ticks/xext_%s.npy'%bf)
    v=np.isfinite(p); p=p[v];y=y[v];t=t[v]
    k=max(50,int(len(p)*sf)); sel=np.argsort(-np.abs(p))[:k]; sel=sel[np.argsort(t[sel])]
    return np.sign(p[sel])*y[sel], t[sel]
def sim(r,mo,fee,lev):
    cap=1.0;peak=1.0;dd=0.0
    for x in r-fee*1e-4:
        cap*=(1.0+lev*x)
        if cap<=0: return 0.0,1.0,-1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd,cap**(1/mo)-1
def solve(r,mo,fee,cd):
    lo,hi=0.01,200.0
    for _ in range(50):
        m=(lo+hi)/2;c,dd,roi=sim(r,mo,fee,m)
        if c<=0 or dd>cd: hi=m
        else: lo=m
    return lo
FEE=8.0
for sf in (0.005,0.02,0.05):
    r,t=load('NEO',sf)
    half=t.min()+(t.max()-t.min())/2
    tr=t<half; te=t>=half
    if tr.sum()<40 or te.sum()<40: continue
    mo_tr=(t[tr].max()-t[tr].min())/86400.0/30.44
    mo_te=(t[te].max()-t[te].min())/86400.0/30.44
    L=solve(r[tr],mo_tr,FEE,0.20)
    c1,d1,r1=sim(r[tr],mo_tr,FEE,L)
    c2,d2,r2=sim(r[te],mo_te,FEE,L)
    print("top %-5s n=%5d | lev %5.1fx chosen on FIRST half"%("%.1f%%"%(100*sf),len(r),L))
    print("   TRAIN  DD %6.2f%%  ROI %+10.2f%%/mo"%(100*d1,100*r1))
    print("   TEST   DD %6.2f%%  ROI %+10.2f%%/mo   %s"%(100*d2,100*r2,"HOLDS" if r2>0 else "FAILS"))
    # per-month
    mb=((t-t.min())/86400.0/30.44).astype(int)
    accs=[]
    for m in range(mb.max()+1):
        z=mb==m
        if z.sum()<10: continue
        c,d,_=sim(r[z],1.0,FEE,L)
        accs.append(c-1)
    a=np.array(accs)
    print("   monthly returns: n=%d  mean %+.1f%%  min %+.1f%%  neg months %d/%d"%(
        len(a),100*a.mean(),100*a.min(),(a<0).sum(),len(a)))
    print()
