"""THE FACTOR PROBLEM. Every long straddle is exposed to ONE common factor:
market-wide volatility. When crypto vol expands, ALL win together; when it
compresses, ALL lose. 730 trades/month behave like ~1 bet. That is why
independence predicts Sharpe 5.80 but reality delivers 1.42.

FIX: trade RELATIVE volatility. Long straddles on predicted-high, SHORT
straddles on predicted-low, matched in premium at the same timestamp. The
common vol factor cancels; what remains is the model's ranking skill.
Bonus: the short leg EARNS the vol risk premium instead of paying it."""
import numpy as np, math
d=np.load('feat.npz',allow_pickle=True)
y=d['y'];t0=d['t0'];t1=d['t1'];sym=d['sym']
oof=np.load('oof.npy'); v=np.isfinite(oof)
y=y[v];t0=t0[v];t1=t1[v];sym=sym[v];p=oof[v]
mo=(t1.max()-t0.min())/86400000/30.44

# bucket by hour; within each hour rank cross-sectionally across instruments
hr=(t0//3600000).astype(np.int64)
order=np.lexsort((p,hr))
hr_s=hr[order]; p_s=p[order]; y_s=y[order]; t0_s=t0[order]; t1_s=t1[order]
bounds=np.flatnonzero(np.diff(hr_s))+1
grp=np.split(np.arange(len(hr_s)),bounds)
L=[];S=[];TL=[];TR=[]
for g in grp:
    if len(g)<4: continue          # need enough instruments to rank
    k=max(1,len(g)//4)             # top/bottom quartile within the hour
    lo=g[:k]; hi=g[-k:]
    L.append(y_s[hi]); S.append(y_s[lo])
    TL.append(t0_s[hi]); TR.append(t1_s[hi])
Ly=np.concatenate(L); Sy=np.concatenate(S)
T0=np.concatenate(TL); T1=np.concatenate(TR)
print("cross-sectional hourly buckets: %d usable hours"%len(grp))
print("LONG  leg (predicted high vol): n=%d mean %+.2f%%"%(len(Ly),100*Ly.mean()))
print("SHORT leg (predicted low  vol): n=%d mean %+.2f%%"%(len(Sy),100*Sy.mean()))
# market-neutral: long the high, short the low, equal premium
net=(Ly-Sy)/2.0
print("SPREAD (long-short)/2         : n=%d mean %+.2f%%  t=%+.2f"%(
    len(net),100*net.mean(),net.mean()/(net.std(ddof=1)/np.sqrt(len(net)))))
print()
mb=((T0-T0.min())/86400000/30.44).astype(int)
for nm,r in (("LONG only",Ly),("SPREAD",net)):
    ms=[]
    for m in range(mb.max()+1):
        s=r[mb==m]
        if len(s)>=10: ms.append(s.mean()*len(s))
    ms=np.array(ms); Sh=ms.mean()/ms.std(ddof=1)
    print("%-10s monthly Sharpe %.3f -> implied ROI@DD4 %+.1f%%"%(nm,Sh,100*(math.exp(2*0.04*Sh*Sh)-1)))
print()
def sim(ret,A,B,f):
    n=len(ret)
    ev=np.concatenate([np.stack([A,np.zeros(n),np.arange(n)],1),
                       np.stack([B,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    ET=ev[:,1].astype(np.int8); EI=ev[:,2].astype(np.int64)
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f;lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*ret[i];lv[i]=False
                if cap<=0: return 0.0,1.0
                if cap>peak: peak=cap
                dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(ret,A,B,cd):
    lo,hi=1e-8,3.0
    for _ in range(46):
        m=(lo+hi)/2;c,dd=sim(ret,A,B,m)
        if c<=0 or dd>cd: hi=m
        else: lo=m
    c,dd=sim(ret,A,B,lo); return lo,dd,(c**(1/mo)-1) if c>0 else -1
print("MARKET-NEUTRAL VOL SPREAD — WR/DD/MONTHLY ROI")
print("  WIN RATE = %.2f%%"%(100*(net>0).mean()))
print("%-10s %11s %9s %14s"%("DD cap","size/trade","real DD","MONTHLY ROI"))
for cd in (0.02,0.04,0.06,0.10,0.20):
    f,dd,roi=solve(net,T0,T1,cd)
    print("%-10s %10.4f%% %8.2f%% %+13.2f%%"%("%.0f%%"%(100*cd),100*f,100*dd,100*roi))
