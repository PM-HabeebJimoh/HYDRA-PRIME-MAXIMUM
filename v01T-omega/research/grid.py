"""WIDEST HONEST SEARCH. All fills EXECUTABLE (enter at O[i+1]).
Sweeps: timeframe x entry rule x barrier geometry x hold. Records everything.
No config is chosen here - this only harvests. Selection happens later with
OOS + multiple-testing correction."""
from load import *
import numpy as np, itertools, sys, json
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent

SYMS=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
HB=3600000.0

def rm(x,n):
    c=np.cumsum(np.insert(x,0,0.0)); o=np.full(len(x),np.nan); o[n-1:]=(c[n:]-c[:-n])/n; return o

def atr_causal(f,n=20):
    H,L,C=f[:,3],f[:,4],f[:,2]
    tr=np.empty(len(f)); tr[0]=H[0]-L[0]
    tr[1:]=np.maximum(H[1:]-L[1:],np.maximum(np.abs(H[1:]-C[:-1]),np.abs(L[1:]-C[:-1])))
    return np.concatenate([[np.nan],rm(tr,n)[:-1]])

def forecast(h):
    O,C=h[:,1],h[:,2]
    bp=((C-O)>0).astype(float)
    m20,m50=rm(C,20),rm(C,50)
    tu=(C>m20)&(m20>m50); td=(C<m20)&(m20<m50)
    p=np.zeros(len(C)); p[1:]=np.diff(C)/C[:-1]
    return tu,td,rm(p,3)*3,rm(bp,3)*3

def harvest(tf_min, bb_lo, tmult, smult, hold, mode):
    """Returns array (t0,t1,R,sym). EXECUTABLE: signal at bar i, enter at O[i+1]."""
    rec=[]
    for si,nm in enumerate(SYMS):
        raw=load_1m(nm)
        if raw is None or len(raw)<50000: continue
        f=resample(raw,tf_min); h=resample(raw,60)
        if len(f)<500: continue
        tu,td,r3,st=forecast(h)
        A=atr_causal(f); C=f[:,2]; O=f[:,1]; H=f[:,3]; L=f[:,4]
        bb=bb_percent(C); ht=h[:,0]
        ks=np.searchsorted(ht,f[:,0]-HB,side='right')-1
        idx=np.arange(len(f)); kk=np.clip(ks,0,len(h)-1)
        d=np.where(tu[kk]&(st[kk]>=2)&(r3[kk]>0),1,np.where(td[kk]&(st[kk]<=1)&(r3[kk]<0),-1,0))
        good=(ks>=60)&np.isfinite(A)&np.isfinite(bb)&(d!=0)&(idx>=60)&(idx<len(f)-hold-2)
        if mode=='pull': good&=np.where(d==1,bb<bb_lo,bb>100-bb_lo)
        elif mode=='brk': good&=np.where(d==1,bb>100-bb_lo,bb<bb_lo)
        sel=idx[good]
        if len(sel)==0: continue
        busy=-1; keep=[]
        for i in sel:
            if i<busy: continue
            keep.append(i); busy=i+hold+1
        if not keep: continue
        sel=np.array(keep)
        dd=d[sel].astype(float); a=A[sel]
        e=sel+1                       # EXECUTABLE ENTRY: next bar open
        S=O[e]
        s0=dd*S
        off=np.arange(0,hold)
        wi=e[:,None]+off[None,:]
        wi=np.clip(wi,0,len(f)-1)
        sO=dd[:,None]*O[wi]
        sH=np.where(dd[:,None]==1,H[wi],-L[wi]); sL=np.where(dd[:,None]==1,L[wi],-H[wi])
        stop=(s0-smult*a)[:,None]; targ=(s0+tmult*a)[:,None]
        hS=(sO<=stop)|(sL<=stop); hT=(sO>=targ)|(sH>=targ)
        jS=np.where(hS.any(1),hS.argmax(1),10**6); jT=np.where(hT.any(1),hT.argmax(1),10**6)
        first=np.minimum(jS,jT); stopw=jS<=jT
        ar=np.arange(len(sel)); jc=np.clip(first,0,hold-1)
        opn=sO[ar,jc]
        fill=np.where(stopw,np.minimum(opn,stop[:,0]),np.maximum(opn,targ[:,0]))
        none=first>=10**6
        fill=np.where(none,dd*C[np.clip(e+hold-1,0,len(f)-1)],fill)
        R=(fill-s0)/a
        t1=f[np.clip(e+np.where(none,hold-1,jc),0,len(f)-1),0]
        for q in range(len(sel)):
            rec.append((f[e[q],0],t1[q],R[q],si))
    return np.array(rec,dtype=float) if rec else None

if __name__=='__main__':
    grid=[]
    for tf in (5,15,30,60):
        for mode in ('pull','brk','all'):
            for bb_lo in (30,40):
                if mode=='all' and bb_lo!=30: continue
                for (tm,sm) in ((3,1),(2,1),(1,1),(4,2),(6,3),(8,3)):
                    for hold in (12,24,48):
                        grid.append((tf,bb_lo,tm,sm,hold,mode))
    print("configs:",len(grid),flush=True)
    res={}
    for gi,(tf,bl,tm,sm,hd,md) in enumerate(grid):
        key="tf%d_%s_bb%d_T%g_S%g_H%d"%(tf,md,bl,tm,sm,hd)
        try: E=harvest(tf,bl,tm,sm,hd,md)
        except Exception as ex: print("ERR",key,ex,flush=True); continue
        if E is None or len(E)<300: continue
        np.save('/tmp/v82/grid_%s.npy'%key,E)
        R=E[:,2]; se=R.std(ddof=1)/np.sqrt(len(R))
        res[key]=dict(n=int(len(R)),meanR=float(R.mean()),t=float(R.mean()/se),wr=float(100*(R>0).mean()))
        print("%-34s n=%6d meanR %+.4f t=%+6.2f WR %.1f%%"%(key,len(R),R.mean(),R.mean()/se,100*(R>0).mean()),flush=True)
    json.dump(res,open('/tmp/v82/grid.json','w'),indent=1)
    print("done",len(res))
