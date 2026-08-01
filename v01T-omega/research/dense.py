"""72,030 trades/month required; 113,967 5m bars/month exist across 13 symbols.
So it is NOT ruled out by bar count. Test the maximum-density configuration:
shortest hold (barrier resolves fast), loosest gate, all 13 symbols, 5m."""
from load import *
import numpy as np, sys
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
    bp=((C-O)>0).astype(float); m20,m50=rm(C,20),rm(C,50)
    tu=(C>m20)&(m20>m50); td=(C<m20)&(m20<m50)
    p=np.zeros(len(C)); p[1:]=np.diff(C)/C[:-1]
    return tu,td,rm(p,3)*3,rm(bp,3)*3
def harvest(bb_lo,tm,sm,hold,allow_overlap):
    rec=[]
    for si,nm in enumerate(SYMS):
        raw=load_1m(nm)
        if raw is None or len(raw)<50000: continue
        f=resample(raw,5); h=resample(raw,60)
        tu,td,r3,st=forecast(h)
        A=atr_causal(f); C=f[:,2];O=f[:,1];H=f[:,3];L=f[:,4]
        bb=bb_percent(C); ht=h[:,0]
        ks=np.searchsorted(ht,f[:,0]-HB,side='right')-1
        idx=np.arange(len(f)); kk=np.clip(ks,0,len(h)-1)
        d=np.where(tu[kk]&(st[kk]>=2)&(r3[kk]>0),1,np.where(td[kk]&(st[kk]<=1)&(r3[kk]<0),-1,0))
        good=(ks>=60)&np.isfinite(A)&np.isfinite(bb)&(d!=0)&(idx>=60)&(idx<len(f)-hold-2)
        good&=np.where(d==1,bb<bb_lo,bb>100-bb_lo)
        sel=idx[good]
        if len(sel)==0: continue
        if not allow_overlap:
            busy=-1; keep=[]
            for i in sel:
                if i<busy: continue
                keep.append(i); busy=i+hold+1
            sel=np.array(keep)
        if len(sel)==0: continue
        dd=d[sel].astype(float); a=A[sel]; e=sel+1; S=O[e]; s0=dd*S
        off=np.arange(0,hold); wi=np.clip(e[:,None]+off[None,:],0,len(f)-1)
        sO=dd[:,None]*O[wi]; sH=np.where(dd[:,None]==1,H[wi],-L[wi]); sL=np.where(dd[:,None]==1,L[wi],-H[wi])
        stop=(s0-sm*a)[:,None]; targ=(s0+tm*a)[:,None]
        hS=(sO<=stop)|(sL<=stop); hT=(sO>=targ)|(sH>=targ)
        jS=np.where(hS.any(1),hS.argmax(1),10**6); jT=np.where(hT.any(1),hT.argmax(1),10**6)
        first=np.minimum(jS,jT); stopw=jS<=jT
        ar=np.arange(len(sel)); jc=np.clip(first,0,hold-1); opn=sO[ar,jc]
        fill=np.where(stopw,np.minimum(opn,stop[:,0]),np.maximum(opn,targ[:,0]))
        none=first>=10**6
        fill=np.where(none,dd*C[np.clip(e+hold-1,0,len(f)-1)],fill)
        R=(fill-s0)/a
        t1=f[np.clip(e+np.where(none,hold-1,jc),0,len(f)-1),0]
        for q in range(len(sel)): rec.append((f[e[q],0],t1[q],R[q],si))
    return np.array(rec,dtype=float)
def stats(E,lbl):
    R=E[:,2]; n=len(R); mo=(E[:,1].max()-E[:,0].min())/86400000/30.44
    se=R.std(ddof=1)/np.sqrt(n); t=R.mean()/se; S=t/np.sqrt(mo)
    need=np.sqrt(np.log(11)/0.08)
    print("%-42s n=%7d  %5.0f tr/mo  meanR %+.5f  t=%+6.2f  Smo=%.4f  need %.2fx"%(
        lbl,n,n/mo,R.mean(),t,S,need/S))
    return S
print("MAXIMUM DENSITY SEARCH — can trade count close the 91x gap?")
print("(overlap ALLOWED = every signal taken, multiple concurrent per symbol)")
for bb_lo,tm,sm,hold,ov in [(40,3,1,12,False),(40,3,1,12,True),(50,3,1,6,True),
                             (60,3,1,6,True),(100,3,1,6,True),(100,2,1,3,True),(100,1,1,2,True)]:
    E=harvest(bb_lo,tm,sm,hold,ov)
    if len(E)<300: continue
    stats(E,"bb<%d T%g S%g H%d %s"%(bb_lo,tm,sm,hold,"OVERLAP" if ov else "seq"))
