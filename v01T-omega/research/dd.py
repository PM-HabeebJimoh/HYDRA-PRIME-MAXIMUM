"""What ACTUALLY creates the 4% drawdown? Anatomy of the worst episode."""
import numpy as np
A=np.load('/tmp/v82/events.npy'); P=A[A[:,4]==0]
P=P[np.argsort(P[:,0])]; R=P[:,2]; n=len(P); t0=P[:,0].min()
f=0.0008739
ev=np.concatenate([np.stack([P[:,0],np.zeros(n),np.arange(n)],1),
                   np.stack([P[:,1],np.ones(n),np.arange(n)],1)])
ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
cap=1.0;peak=1.0;dd=0.0;staked=np.zeros(n);live=np.zeros(n,bool)
curve=[]; worst=(0,None,None)
for k in range(len(ev)):
    ts=ev[k,0];ty=ev[k,1];i=int(ev[k,2])
    if ty==0: staked[i]=cap*f; live[i]=True
    else:
        if live[i]:
            cap+=staked[i]*R[i]; live[i]=False
            peak=max(peak,cap); d=(peak-cap)/peak
            if d>worst[0]: worst=(d,ts,cap)
            dd=max(dd,d); curve.append((ts,cap,d))
curve=np.array(curve)
print("final %.4f  maxDD %.3f%%"%(cap,100*dd))
wt=worst[1]
print("worst DD %.3f%% at t=%s"%(100*worst[0],wt))
# what happened in the 7 days before the DD trough?
w=(P[:,1]>wt-7*86400000)&(P[:,1]<=wt)
v=R[w]
print("\ntrades closing in the 7 days into the trough: n=%d meanR %+.3f sumR %+.1f"%(len(v),v.mean(),v.sum()))
print("  worst 10 R in that window:",np.sort(v)[:10].round(2))
print("\nOVERALL tail of R:")
print("  R < -5 : %d trades (%.3f%%), total %.0f R"%((R<-5).sum(),100*(R<-5).mean(),R[R<-5].sum()))
print("  R < -10: %d trades (%.3f%%), total %.0f R"%((R<-10).sum(),100*(R<-10).mean(),R[R<-10].sum()))
print("  R < -20: %d trades (%.3f%%), total %.0f R"%((R<-20).sum(),100*(R<-20).mean(),R[R<-20].sum()))
print("  most negative single trade: %.2f R"%R.min())
print("\nA -44R trade at 0.0874%% risk = -%.2f%% of equity in ONE trade."%(44*0.08739))
print("THAT is what sets the DD, not the count noise.")
print("\nThese are GAP-THROUGH fills (honest). Cap them and DD collapses.")
# what if we cap loss per trade at -kR (i.e. guaranteed-stop / options-like protection)
mo=(P[:,1].max()-t0)/86400000/30.44
def sim(f,clip):
    Rc=np.maximum(R,-clip)
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ev)):
        ty=ev[k,1];i=int(ev[k,2])
        if ty==0: st[i]=cap*f; lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*Rc[i]; lv[i]=False
                if cap<=0: return 0,1
                peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(clip,target=0.04):
    lo,hi=1e-7,1.0
    for _ in range(46):
        m=(lo+hi)/2; c,d=sim(m,clip)
        if c<=0 or d>target: hi=m
        else: lo=m
    c,d=sim(lo,clip); return lo,d,c**(1/mo)-1
print("\n%-22s %11s %9s %14s"%("max loss per trade","risk/trade","maxDD%","ROI/mo @DD4"))
for clip in (99,10,5,3,2,1.5):
    fr,d,roi=solve(clip)
    lbl=("none" if clip==99 else "-%.1fR"%clip)
    print("%-22s %10.4f%% %9.3f %+13.2f%%"%(lbl,100*fr,100*d,100*roi))
