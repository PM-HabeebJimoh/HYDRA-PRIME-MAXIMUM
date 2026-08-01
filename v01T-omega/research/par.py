"""THE CORRECTION: 26 streams trade CONCURRENTLY, not one-after-another.

Sequential compounding pretends trade #2 waits for trade #1 to close.
It does not. XLM and BTC fire at the same instant on separate capital slots.

Consequence, exactly:
  sequential -> equity path is a product of N terms, drawdown = worst RUN of losses
  parallel   -> k positions share one equity, drawdown = worst SUM of simultaneous losses
If streams are imperfectly correlated, k simultaneous losses of size f partially
cancel: DD grows ~ f*sqrt(k), while return grows ~ f*k. Return/DD improves by sqrt(k).
That is the diversification lever, and it is the whole game.
"""
import numpy as np
A=np.load('/tmp/v82/events.npy')   # t0,t1,R,sym,stream
def sim(A,f,dd_cap=None,maxconc=None):
    """Calendar-ordered, concurrent positions, risk f of CURRENT equity per slot.
    Equity updates when a trade CLOSES. Returns (final, maxdd_closed, n_used, peakconc)."""
    n=len(A)
    order=np.argsort(A[:,0])
    t0=A[order,0]; t1=A[order,1]; R=A[order,2]
    # event queue: (time, type, idx) type 0=open 1=close
    ev=np.concatenate([np.stack([t0,np.zeros(n),np.arange(n)],1),
                       np.stack([t1,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]   # closes before opens at same ts
    cap=1.0; peak=1.0; dd=0.0
    staked=np.zeros(n); live=np.zeros(n,bool); used=0; conc=0; peakc=0
    for k in range(len(ev)):
        ty=ev[k,1]; i=int(ev[k,2])
        if ty==0:
            if maxconc and conc>=maxconc: continue
            staked[i]=cap*f; live[i]=True; conc+=1; used+=1
            peakc=max(peakc,conc)
        else:
            if not live[i]: continue
            cap+=staked[i]*R[i]; live[i]=False; conc-=1
            if cap<=0: return 0.0,1.0,used,peakc
            peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd,used,peakc

t0=A[:,0].min(); t1=A[:,1].max(); mo=(t1-t0)/86400000/30.44
print("PARALLEL vs SEQUENTIAL — same 78,417 pullback trades, %.1f months"%mo)
P=A[A[:,4]==0]
def seq(R,f):
    cap=1.0;peak=1.0;dd=0.0
    for r in R:
        cap*=(1+f*r)
        if cap<=0: return 0.0,1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(fn,cap_dd=0.04):
    lo,hi=1e-7,2.0
    for _ in range(50):
        m=(lo+hi)/2
        c,dd=fn(m)[:2]
        if c<=0 or dd>cap_dd: hi=m
        else: lo=m
    return lo,fn(lo)
print("%-42s %10s %9s %14s"%("mode","risk/trade","maxDD%","ROI/mo"))
f,(c,dd)=solve(lambda x: seq(P[:,2],x))
print("%-42s %10.5f%% %9.3f %+13.2f%%"%("SEQUENTIAL (what I reported: iter27)",100*f,100*dd,100*(c**(1/mo)-1)))
f,(c,dd,u,pc)=solve(lambda x: sim(P,x))
print("%-42s %10.5f%% %9.3f %+13.2f%%   peak concurrent=%d"%("PARALLEL, pullback only",100*f,100*dd,100*(c**(1/mo)-1),pc))
f,(c,dd,u,pc)=solve(lambda x: sim(A,x))
print("%-42s %10.5f%% %9.3f %+13.2f%%   peak concurrent=%d"%("PARALLEL, pullback+breakout (26 streams)",100*f,100*dd,100*(c**(1/mo)-1),pc))
