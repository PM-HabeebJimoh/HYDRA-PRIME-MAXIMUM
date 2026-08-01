"""WR/DD/MONTHLY ROI with tape features, market-neutral spread (iter35 fix)."""
import numpy as np, math
d=np.load('/tmp/ticks/micro.npz',allow_pickle=True)
y=d['y'];t0=d['t0'];t1=d['t1'];sym=d['sym']
for tag,fn in (('CHART only','/tmp/ticks/oof_chart.npy'),('CHART+TAPE','/tmp/ticks/oof_both.npy')):
    p=np.load(fn); v=np.isfinite(p)
    Y=y[v];A=t0[v];B=t1[v];P=p[v];S=sym[v]
    mo=(B.max()-A.min())/86400.0/30.44
    hr=(A//3600).astype(np.int64)
    o=np.lexsort((P,hr)); hs=hr[o];ys=Y[o];as_=A[o];bs=B[o]
    bnd=np.flatnonzero(np.diff(hs))+1
    L=[];TA=[];TB=[]
    for g in np.split(np.arange(len(hs)),bnd):
        if len(g)<4: continue
        k=max(1,len(g)//4); lo=g[:k];hi=g[-k:]; m=min(len(lo),len(hi))
        L.append((ys[hi][:m]-ys[lo][:m])/2.0); TA.append(as_[hi][:m]); TB.append(bs[hi][:m])
    net=np.concatenate(L);TA=np.concatenate(TA);TB=np.concatenate(TB)
    def sim(r,a,b,f):
        n=len(r)
        ev=np.concatenate([np.stack([a,np.zeros(n),np.arange(n)],1),
                           np.stack([b,np.ones(n),np.arange(n)],1)])
        ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
        ET=ev[:,1].astype(np.int8);EI=ev[:,2].astype(np.int64)
        cap=1.0;pk=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
        for i2 in range(len(ET)):
            i=EI[i2]
            if ET[i2]==0: st[i]=cap*f;lv[i]=True
            else:
                if lv[i]:
                    cap+=st[i]*r[i];lv[i]=False
                    if cap<=0: return 0.0,1.0
                    if cap>pk: pk=cap
                    dd=max(dd,(pk-cap)/pk)
        return cap,dd
    def solve(r,a,b,cd):
        lo,hi=1e-8,3.0
        for _ in range(46):
            m=(lo+hi)/2;c,dd=sim(r,a,b,m)
            if c<=0 or dd>cd: hi=m
            else: lo=m
        c,dd=sim(r,a,b,lo);return lo,dd,(c**(1/mo)-1) if c>0 else -1
    mb=((TA-TA.min())/86400.0/30.44).astype(int)
    ms=[net[mb==m].sum() for m in range(mb.max()+1) if (mb==m).sum()>=10]
    ms=np.array(ms); Sh=ms.mean()/ms.std(ddof=1)
    print()
    print("=== %s ===  n=%d  %.1f months  WR %.2f%%  mean %+.2f%%  monthlySharpe %.3f"%(
        tag,len(net),mo,100*(net>0).mean(),100*net.mean(),Sh))
    print("%-9s %10s %9s %14s"%("DD cap","size","real DD","MONTHLY ROI"))
    for cd in (0.04,0.10,0.20,0.25):
        f,dd,roi=solve(net,TA,TB,cd)
        print("%-9s %9.4f%% %8.2f%% %+13.2f%%"%("%.0f%%"%(100*cd),100*f,100*dd,100*roi))
