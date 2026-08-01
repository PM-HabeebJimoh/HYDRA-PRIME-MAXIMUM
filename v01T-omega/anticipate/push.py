"""Spread works. Now maximise INDEPENDENT bets: tighter quantile, and critically
NON-OVERLAPPING clocks. Overlapping 4h options every hour = 4x redundancy."""
import numpy as np, math
d=np.load('feat.npz',allow_pickle=True)
y=d['y'];t0=d['t0'];t1=d['t1'];sym=d['sym']
oof=np.load('oof.npy'); v=np.isfinite(oof)
y=y[v];t0=t0[v];t1=t1[v];sym=sym[v];p=oof[v]
mo=(t1.max()-t0.min())/86400000/30.44
hr=(t0//3600000).astype(np.int64)
order=np.lexsort((p,hr))
hr_s=hr[order];p_s=p[order];y_s=y[order];a_s=t0[order];b_s=t1[order]
bounds=np.flatnonzero(np.diff(hr_s))+1
grp=np.split(np.arange(len(hr_s)),bounds)
def build(qfrac,stride):
    L=[];A=[];B=[]
    for g in grp:
        if len(g)<4: continue
        h=hr_s[g[0]]
        if stride>1 and (h%stride)!=0: continue     # non-overlapping clock
        k=max(1,int(len(g)*qfrac))
        lo=g[:k];hi=g[-k:]
        m=min(len(lo),len(hi))
        L.append((y_s[hi][:m]-y_s[lo][:m])/2.0)
        A.append(a_s[hi][:m]);B.append(b_s[hi][:m])
    if not L: return None
    return np.concatenate(L),np.concatenate(A),np.concatenate(B)
def sim(ret,A,B,f):
    n=len(ret)
    ev=np.concatenate([np.stack([A,np.zeros(n),np.arange(n)],1),
                       np.stack([B,np.ones(n),np.arange(n)],1)])
    ev=ev[np.lexsort((ev[:,1],ev[:,0]))]
    ET=ev[:,1].astype(np.int8);EI=ev[:,2].astype(np.int64)
    cap=1.0;peak=1.0;dd=0.0;st=np.zeros(n);lv=np.zeros(n,bool)
    for k in range(len(ET)):
        i=EI[k]
        if ET[k]==0: st[i]=cap*f;lv[i]=True
        else:
            if lv[i]:
                cap+=st[i]*ret[i];lv[i]=False
                if cap<=0: return 0.0,1.0
                if cap>peak:peak=cap
                dd=max(dd,(peak-cap)/peak)
    return cap,dd
def solve(ret,A,B,cd):
    lo,hi=1e-8,3.0
    for _ in range(46):
        m=(lo+hi)/2;c,dd=sim(ret,A,B,m)
        if c<=0 or dd>cd: hi=m
        else: lo=m
    c,dd=sim(ret,A,B,lo);return lo,dd,(c**(1/mo)-1) if c>0 else -1
print("%-22s %8s %7s %9s %13s %13s"%("config","n","WR%","mean","ROI@DD4","ROI@DD10"))
best=None
for qf in (0.25,0.15,0.10):
    for stride in (1,2,4):
        r=build(qf,stride)
        if r is None: continue
        net,A,B=r
        if len(net)<500: continue
        f4,d4,roi4=solve(net,A,B,0.04)
        f10,d10,roi10=solve(net,A,B,0.10)
        print("q%-5s stride%-2d %8d %6.2f%% %+8.2f%% %+12.2f%% %+12.2f%%"%(
            qf,stride,len(net),100*(net>0).mean(),100*net.mean(),100*roi4,100*roi10))
        if best is None or roi4>best[0]: best=(roi4,qf,stride,net,A,B)
print()
roi4,qf,stride,net,A,B=best
print("BEST @DD4: q=%.2f stride=%d -> %+.2f%%/mo"%(qf,stride,100*roi4))
print()
print("full DD curve for the best config:")
print("%-10s %11s %9s %14s"%("DD cap","size","real DD","MONTHLY ROI"))
for cd in (0.02,0.04,0.06,0.08,0.10,0.15,0.20,0.25):
    f,dd,roi=solve(net,A,B,cd)
    flag=" <== >700%" if roi>7.0 else ""
    print("%-10s %10.4f%% %8.2f%% %+13.2f%%%s"%("%.0f%%"%(100*cd),100*f,100*dd,100*roi,flag))
