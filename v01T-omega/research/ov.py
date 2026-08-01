"""Overlap gave Sharpe 3.96 (need 5.47). BUT: overlapping trades on ONE capital
pool are NOT independent bets - concurrent positions in the same symbol are
nearly the same trade. The t-stat above treats them as independent. Test the
TRUTH by direct equity simulation, which cannot be fooled."""
from load import *
import numpy as np, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
exec(open('/tmp/v82/dense.py').read().split("print(\"MAXIMUM")[0])
E=harvest(100,3,1,6,True)
np.save('/tmp/v82/dense_best.npy',E)
E=E[np.argsort(E[:,0])]
R=E[:,2]; n=len(E); mo=(E[:,1].max()-E[:,0].min())/86400000/30.44
print("config bb<100 T3 S1 H6 OVERLAP: n=%d %.0f tr/mo meanR %+.5f"%(n,n/mo,R.mean()))
print("naive t=%.2f -> naive monthly Sharpe %.3f"%(R.mean()/(R.std(ddof=1)/np.sqrt(n)),
      (R.mean()/(R.std(ddof=1)/np.sqrt(n)))/np.sqrt(mo)))
ev=np.concatenate([np.stack([E[:,0],np.zeros(n),np.arange(n)],1),
                   np.stack([E[:,1],np.ones(n),np.arange(n)],1)])
ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)
def sim(f,ret_curve=False):
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    conc=0;pk=0; curve=[]
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0:
            st[i]=cap*f;lv[i]=True;conc+=1;pk=max(pk,conc)
        else:
            if lv[i]:
                cap+=st[i]*R[i];lv[i]=False;conc-=1
                if cap<=0: return (0.0,1.0,-1.0,pk,curve)
                if cap>peak: peak=cap
                d=(peak-cap)/peak
                if d>dd: dd=d
                if ret_curve: curve.append((ev[k,0],cap))
    return cap,dd,(cap**(1/mo)-1),pk,curve
def solve(t):
    lo,hi=1e-9,3.0
    for _ in range(46):
        m=(lo+hi)/2;c,d,_,_,_=sim(m)
        if c<=0 or d>t: hi=m
        else: lo=m
    return (lo,)+sim(lo)[:4]
print("\nDIRECT EQUITY SIMULATION (the number that cannot be faked)")
print("%-9s %12s %9s %16s %8s"%("DD cap","risk/trade","real DD","ROI/mo","peak conc"))
for t in (0.04,0.10,0.15,0.20,0.30,0.40,0.50):
    f,c,d,r,pk=solve(t)
    print("%-9s %11.5f%% %8.2f%% %+15.2f%% %8d"%(f"{100*t:.0f}%",100*f,100*d,100*r,pk))
# TRUE monthly Sharpe from the equity curve
f,c,d,r,pk=solve(0.15)
_,_,_,_,curve=sim(f,True)
cv=np.array(curve)
t0=cv[0,0]; mb=((cv[:,0]-t0)/86400000/30.44).astype(int)
marks=[]
for m in range(mb.max()+1):
    w=cv[mb==m]
    if len(w): marks.append(w[-1,1])
marks=np.array(marks); lr=np.diff(np.log(marks))
lr=lr[np.isfinite(lr)]
print("\nTRUE monthly Sharpe from realised equity: %.4f  (naive claimed 3.96)"%(lr.mean()/lr.std(ddof=1)))
print("required 5.4748 -> shortfall %.2fx"%(5.4748/(lr.mean()/lr.std(ddof=1))))
