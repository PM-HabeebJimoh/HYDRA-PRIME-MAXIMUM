"""
iter70b: VECTORISED exhaustive search. Same rules as grid.py but the barrier
resolution is precomputed once per (barrier,horizon) with numpy instead of a
Python loop per config, so hundreds of configs finish in minutes.

Trick: for a given (tgt,stp,N) compute, for EVERY bar i, the outcome of a LONG
entered at open[i+1]. A SHORT's outcome is obtained from the mirrored barriers.
Then each signal/selectivity config is just a boolean mask over precomputed
outcomes + a non-overlap sweep.
"""
import numpy as np, os, math, json
def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

def outcomes(o,h,l,c,ts,tgt,stp,N,side):
    """R multiple and bars-held for a position opened at o[i+1], vectorised-ish.
       Uses running max/min over the window via a chunked scan."""
    n=len(c)
    R=np.full(n,np.nan); BH=np.full(n,np.nan)
    e=np.full(n,np.nan); e[:-1]=o[1:]
    valid=np.zeros(n,bool); valid[:-1]=(ts[1:]-ts[:-1]==60)
    up=np.where(side>0,e*(1+tgt*1e-4),e*(1+stp*1e-4))
    dn=np.where(side>0,e*(1-stp*1e-4),e*(1-tgt*1e-4))
    hitU=np.full(n,np.iinfo(np.int32).max,dtype=np.int64)
    hitD=np.full(n,np.iinfo(np.int32).max,dtype=np.int64)
    # scan forward N bars
    for k in range(0,N):
        idx=np.arange(n-1-k)
        if len(idx)==0: break
        j=idx+1+k
        okc=valid[idx]
        hu=(h[j]>=up[idx])&okc&(hitU[idx]==np.iinfo(np.int32).max)
        hd=(l[j]<=dn[idx])&okc&(hitD[idx]==np.iinfo(np.int32).max)
        hitU[idx[hu]]=k
        hitD[idx[hd]]=k
    BIG=np.iinfo(np.int32).max
    both=(hitU<BIG)|(hitD<BIG)
    if side>0:
        win=(hitU<hitD)&(hitU<BIG)
        lose=(hitD<=hitU)&(hitD<BIG)
    else:
        win=(hitD<hitU)&(hitD<BIG)
        lose=(hitU<=hitD)&(hitU<BIG)
    R[win]=tgt/stp
    R[lose]=-1.0
    # timeout
    to=(~win)&(~lose)&valid
    j=np.minimum(np.arange(n)+N,n-1)
    R[to]=((c[j[to]]/e[to]-1)*1e4*side)/stp
    BH[win]=np.minimum(hitU[win],hitD[win])+1
    BH[lose]=np.minimum(hitU[lose],hitD[lose])+1
    BH[to]=N
    R[~valid]=np.nan
    return R,BH

def sweep(mask,R,BH):
    """non-overlapping selection, first-come"""
    idx=np.flatnonzero(mask&np.isfinite(R)&np.isfinite(BH))
    out=[];last=-1
    for i in idx:
        if i<=last: continue
        out.append(i); last=i+int(BH[i])
    return np.array(out,dtype=int)

def load(sym):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    return dict(ts=A[:,0].astype(np.int64),o=A[:,1],h=A[:,2],l=A[:,3],c=A[:,4],
                vol=A[:,5],ntr=A[:,6],ofi=A[:,7],vwap=A[:,10],maxtr=A[:,11],
                top10=A[:,12],upt=A[:,13],rev=A[:,14],tfi=A[:,15],spr=A[:,16])

def build_signals(D,hub=None):
    c,vol,ntr,ofi=D['c'],D['vol'],D['ntr'],D['ofi']
    vwap,maxtr,top10=D['vwap'],D['maxtr'],D['top10']
    tfi,spr,rev=D['tfi'],D['spr'],D['rev']
    S={}
    S['flow']=z(ofi,240); S['flow_fast']=z(ofi,60); S['tfi']=z(tfi,240)
    S['flow_tfi']=z(ofi,240)+z(tfi,240)
    S['flow_pers']=z(roll(ofi,5),240)
    S['multiscale']=z(ofi,60)+z(ofi,240)+z(ofi,960)
    sgn=np.sign(np.nan_to_num(ofi))
    S['whale']=z(maxtr/np.maximum(vol,1e-12),240)*sgn
    S['conc']=z(top10,240)*sgn
    S['absence']=(-z(np.log(np.maximum(ntr,1)),240))*sgn
    S['rangeexp']=z(spr,240)*sgn
    S['vwapdev']=z((c-vwap)/np.maximum(vwap,1e-12),240)
    S['flow_x_act']=z(ofi,240)*np.maximum(z(np.log(np.maximum(vol,1e-9)),240),0)
    fam=[np.nan_to_num(z(ofi,240)),np.nan_to_num(z(tfi,240)),
         np.nan_to_num(z(maxtr/np.maximum(vol,1e-12),240)),
         np.nan_to_num(z(np.log(np.maximum(ntr,1)),240))]
    V=np.zeros(len(c))
    for f in fam: V+=np.sign(f)*(np.abs(f)>=1.5)
    S['css_vote']=V
    if hub is not None:
        S['hub']=hub; S['flow_hub']=z(ofi,240)+hub
    return S

COST={'BTCUSDT':5.65,'LTCBTC':5.15,'NEOUSDT':16.80,'ETHBTC':5.0,'BNBUSDT':6.0,
      'QTUMUSDT':10.0,'BCCUSDT':8.0}
BARRIERS=[(60,60),(120,60),(60,120),(180,60),(60,180),(240,120),(120,240),
          (300,100),(100,300),(400,200),(200,400),(50,200),(150,150),(90,270)]
TOPS=[0.05,0.02,0.01,0.005,0.002]
HOR=[240,720,1440]

res=[];ntest=0
syms=[s for s in ('BTCUSDT','LTCBTC','ETHBTC','BNBUSDT','NEOUSDT','QTUMUSDT','BCCUSDT')
      if os.path.exists('/tmp/ticks/ohlc_%s.npy'%s)]
HUB=load('BTCUSDT')
hubz=np.nan_to_num(z(HUB['ofi'],240))
for sym in syms:
    D=load(sym); n=len(D['c']); cut=int(n*0.6)
    hub=None
    if sym!='BTCUSDT':
        _,ia,ib=np.intersect1d(D['ts'],HUB['ts'],return_indices=True)
        hh=np.zeros(n); hh[ia]=hubz[ib]; hub=hh
    S=build_signals(D,hub)
    for (t,s) in BARRIERS:
        for N in HOR:
            RL,BL=outcomes(D['o'],D['h'],D['l'],D['c'],D['ts'],t,s,N,+1)
            RS,BS=outcomes(D['o'],D['h'],D['l'],D['c'],D['ts'],t,s,N,-1)
            for nm,sv in S.items():
                sg0=np.nan_to_num(sv)
                for flip in (1,-1):
                    sg=sg0*flip; av=np.abs(sg)
                    trv=av[:cut]; trv=trv[np.isfinite(trv)&(trv>0)]
                    if len(trv)<1000: continue
                    for tf in TOPS:
                        ntest+=1
                        thr=np.quantile(trv,1-tf)
                        if not np.isfinite(thr) or thr<=0: continue
                        mask=(av>=thr); mask[:1000]=False
                        Ruse=np.where(sg>0,RL,RS); Buse=np.where(sg>0,BL,BS)
                        sel=sweep(mask,Ruse,Buse)
                        sel=sel[sel>=cut]
                        if len(sel)<200: continue
                        R=Ruse[sel]; net=R-COST[sym]/s
                        wr=100*(R>0).mean(); base=100*s/(t+s)
                        res.append(dict(sym=sym,sig=nm,flip=flip,tgt=t,stp=s,N=N,
                            top=tf,n=int(len(sel)),wr=wr,base=base,edge=wr-base,
                            netR=float(net.mean()),totR=float(net.sum())))
print("configs tested:",ntest,"kept:",len(res))
json.dump(res,open('/tmp/grid.json','w'))
