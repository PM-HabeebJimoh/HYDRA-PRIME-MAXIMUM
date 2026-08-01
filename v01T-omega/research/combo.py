"""Stack every INDEPENDENT lever found, measured jointly.
L1 tail-cap (-1.5R, real: guaranteed stop / hedged leg)
L2 add breakout stream (2nd uncorrelated signal on same symbols)
L3 parallel concurrent capital (already in)
L4 per-stream risk parity (weight by inverse vol of that stream)
"""
import numpy as np
A=np.load('/tmp/v82/events.npy')
t0=A[:,0].min(); mo=(A[:,1].max()-t0)/86400000/30.44

def build(use_streams=(0,), clip=1.5, parity=False):
    S=A[np.isin(A[:,4],use_streams)]
    S=S[np.argsort(S[:,0])]
    R=np.maximum(S[:,2],-clip)
    key=S[:,3]*10+S[:,4]
    w=np.ones(len(S))
    if parity:
        for k in np.unique(key):
            m=key==k
            sd=R[m].std(ddof=1)
            w[m]=1.0/max(sd,1e-6)
        w/=w.mean()
    return S,R,w

def sim(S,R,w,f):
    n=len(S)
    ev=np.concatenate([np.stack([S[:,0],np.zeros(n),np.arange(n)],1),
                       np.stack([S[:,1],np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ev)):
        ty=ev[k,1];i=int(ev[k,2])
        if ty==0: st[i]=cap*f*w[i]; lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*R[i]; lv[i]=False
                if cap<=0: return 0.0,1.0
                peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd

def solve(S,R,w,target=0.04):
    lo,hi=1e-8,1.0
    for _ in range(48):
        m=(lo+hi)/2; c,d=sim(S,R,w,m)
        if c<=0 or d>target: hi=m
        else: lo=m
    c,d=sim(S,R,w,lo); return lo,d,c**(1/mo)-1,len(S)

print("%-52s %8s %10s %8s %14s"%("configuration","n","risk%","maxDD%","ROI/mo @DD4"))
cfgs=[("baseline: pullback, no cap",(0,),99.0,False),
      ("+ tail cap -1.5R",(0,),1.5,False),
      ("+ breakout stream",(0,1),1.5,False),
      ("+ risk parity per stream",(0,1),1.5,True),
      ("breakout only",(1,),1.5,False)]
for lbl,st,cl,pa in cfgs:
    S,R,w=build(st,cl,pa)
    f,d,roi,n=solve(S,R,w)
    print("%-52s %8d %9.4f%% %8.3f %+13.2f%%"%(lbl,n,100*f,100*d,100*roi))
