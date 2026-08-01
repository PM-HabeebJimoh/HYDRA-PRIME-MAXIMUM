"""The frontier above is IN-SAMPLE: risk was solved knowing the whole path.
Real trading picks risk BEFORE seeing the future. Test that honestly."""
import numpy as np, datetime as dt
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]; P=P[np.argsort(P[:,0])]
SPLIT=dt.datetime(2020,1,1).timestamp()*1000
TR=P[P[:,1]<SPLIT]; TE=P[P[:,0]>=SPLIT]
def mk(S):
    n=len(S); R=S[:,2]
    ev=np.concatenate([np.stack([S[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([S[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    mo=(S[:,1].max()-S[:,0].min())/86400000/30.44
    return n,R,ev[:,1].astype(np.int8),ev[:,2].astype(np.int64),mo
def sim(pack,f):
    n,R,ET,EI,mo=pack
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
def solve(pack,target):
    lo,hi=1e-9,3.0
    for _ in range(50):
        m=(lo+hi)/2; c,d,_=sim(pack,m)
        if c<=0 or d>target: hi=m
        else: lo=m
    return lo
ptr=mk(TR); pte=mk(TE)
print("TRAIN 2018-2019 n=%d (%.1f mo)   TEST 2020-2021 n=%d (%.1f mo)"%(ptr[0],ptr[4],pte[0],pte[4]))
print()
print("Risk chosen on TRAIN ONLY, then applied unchanged to TEST:")
print("%-10s %12s %12s %12s %14s %12s"%("DD target","risk","train DD","train ROI","TEST DD","TEST ROI"))
for t in (0.04,0.06,0.10,0.15,0.20,0.25,0.30):
    f=solve(ptr,t)
    c1,d1,r1=sim(ptr,f); c2,d2,r2=sim(pte,f)
    print("%-10s %11.4f%% %11.2f%% %+11.2f%% %13.2f%% %+11.2f%%"%(
        f"{100*t:.0f}%",100*f,100*d1,100*r1,100*d2,100*r2))
print()
print("KEY: does the DD budget HOLD out of sample, or is it breached?")
