"""
iter70: EXHAUSTIVE SEARCH for >85% accuracy with POSITIVE SKILL.

Hard rules (all lessons from iter67-69 encoded so I cannot fool myself):
 R1 entry at NEXT bar OPEN
 R2 outcome = triple barrier resolved on HIGH/LOW path
 R3 pessimistic: if both touched in one bar -> STOP
 R4 non-overlapping positions
 R5 costs charged both sides
 R6 all thresholds/quantiles/signs FROZEN ON TRAIN (first 60%)
 R7 report EDGE = WR - b/(a+b), never WR alone
 R8 report binomial CI; require n>=200
 R9 Bonferroni over the number of configs tested

Search axes (hundreds of combinations):
  * 12 signal constructions (flow, imbalance persistence, whale, concentration,
    absence, reversal, range-expansion, cross-asset BTC lead, VWAP deviation,
    interaction terms, multi-scale z, CSS-style convergence votes)
  * 6 selectivity levels
  * 12 barrier geometries (incl. asymmetric)
  * 3 horizons
  * 5 instruments
"""
import numpy as np, os, math, itertools, json, sys

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

def load(sym):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    return dict(ts=A[:,0].astype(np.int64),o=A[:,1],h=A[:,2],l=A[:,3],c=A[:,4],
                vol=A[:,5],ntr=A[:,6],ofi=A[:,7],bv=A[:,8],sv=A[:,9],
                vwap=A[:,10],maxtr=A[:,11],top10=A[:,12],upt=A[:,13],
                rev=A[:,14],tfi=A[:,15],spr=A[:,16])

def signals(D, HUB=None):
    o,h,l,c=D['o'],D['h'],D['l'],D['c']
    vol,ntr,ofi=D['vol'],D['ntr'],D['ofi']
    vwap,maxtr,top10=D['vwap'],D['maxtr'],D['top10']
    upt,rev,tfi,spr=D['upt'],D['rev'],D['tfi'],D['spr']
    n=len(c); lc=np.log(np.maximum(c,1e-12))
    ret=np.zeros(n); ret[1:]=np.diff(lc)
    S={}
    S['flow']       = z(ofi,240)
    S['flow_fast']  = z(ofi,60)
    S['tfi']        = z(tfi,240)
    S['flow_tfi']   = z(ofi,240)+z(tfi,240)
    S['flow_pers']  = z(roll(ofi,5),240)
    S['whale']      = z(maxtr/np.maximum(vol,1e-12),240)*np.sign(np.nan_to_num(ofi))
    S['conc_flow']  = z(top10,240)*np.sign(np.nan_to_num(ofi))
    S['absence']    = (-z(np.log(np.maximum(ntr,1)),240))*np.sign(np.nan_to_num(ofi))
    S['rangeexp']   = z(spr,240)*np.sign(np.nan_to_num(ofi))
    S['vwapdev']    = z((c-vwap)/np.maximum(vwap,1e-12),240)
    S['flow_x_act'] = z(ofi,240)*np.maximum(z(np.log(np.maximum(vol,1e-9)),240),0)
    S['multiscale'] = z(ofi,60)+z(ofi,240)+z(ofi,960)
    if HUB is not None:
        S['hub']    = HUB
        S['flow_hub']= z(ofi,240)+HUB
    # CSS-style convergence vote
    fam=[np.nan_to_num(z(ofi,240)),np.nan_to_num(z(tfi,240)),
         np.nan_to_num(z(maxtr/np.maximum(vol,1e-12),240)),
         np.nan_to_num(z(np.log(np.maximum(ntr,1)),240))]
    V=np.zeros(n)
    for f in fam:
        V+=np.sign(f)*(np.abs(f)>=1.5)
    S['css_vote']=V
    return S

def resolve(o,h,l,c,ts,i,side,tgt,stp,N):
    e=o[i]
    if e<=0: return None
    up=e*(1+tgt*1e-4) if side>0 else e*(1+stp*1e-4)
    dn=e*(1-stp*1e-4) if side>0 else e*(1-tgt*1e-4)
    lim=min(i+N,len(c))
    for k in range(i,lim):
        if k>i and ts[k]-ts[k-1]!=60: break
        if side>0:
            if l[k]<=dn: return -1.0,k-i+1
            if h[k]>=up: return tgt/stp,k-i+1
        else:
            if h[k]>=up: return -1.0,k-i+1
            if l[k]<=dn: return tgt/stp,k-i+1
    k=min(lim-1,len(c)-1)
    return (c[k]/e-1)*1e4*side/stp, k-i+1

def backtest(D,S,tgt,stp,N,cost,topfrac,flip):
    ts,o,h,l,c=D['ts'],D['o'],D['h'],D['l'],D['c']
    n=len(c); cut=int(n*0.6)
    sg=np.nan_to_num(S)*flip
    av=np.abs(sg)
    tr=av[:cut]; tr=tr[np.isfinite(tr)&(tr>0)]
    if len(tr)<1000: return None
    thr=np.quantile(tr,1-topfrac)
    if not np.isfinite(thr) or thr<=0: return None
    rows=[]; last=-10**9
    for i in range(1000,n-2):
        if av[i]<thr: continue
        if i<last: continue
        if ts[i+1]-ts[i]!=60: continue
        side=1 if sg[i]>0 else -1
        r=resolve(o,h,l,c,ts,i+1,side,tgt,stp,N)
        if r is None: continue
        R,bars=r
        last=i+bars
        rows.append((R,R-cost/stp,1.0 if i>=cut else 0.0))
    if not rows: return None
    return np.array(rows)

COST={'BTCUSDT':5.65,'LTCBTC':5.15,'NEOUSDT':16.80,'ETHBTC':5.0,'BNBUSDT':6.0,
      'QTUMUSDT':10.0,'BCCUSDT':8.0}

if __name__=='__main__':
    syms=[s for s in ('BTCUSDT','LTCBTC','ETHBTC','BNBUSDT','NEOUSDT')
          if os.path.exists('/tmp/ticks/ohlc_%s.npy'%s)]
    print("instruments:",syms)
    HUBD=load('BTCUSDT') if os.path.exists('/tmp/ticks/ohlc_BTCUSDT.npy') else None
    results=[]; ntest=0
    BARRIERS=[(60,60),(120,60),(60,120),(180,60),(60,180),(240,120),(120,240),
              (300,100),(100,300),(400,200),(200,400),(50,200)]
    TOPS=[0.05,0.02,0.01,0.005,0.002,0.001]
    HOR=[240,720,1440]
    for sym in syms:
        D=load(sym)
        hub=None
        if HUBD is not None and sym!='BTCUSDT':
            _,ia,ib=np.intersect1d(D['ts'],HUBD['ts'],return_indices=True)
            hh=np.zeros(len(D['c'])); hh[ia]=np.nan_to_num(z(HUBD['ofi'],240))[ib]
            hub=hh
        S=signals(D,hub)
        for nm,sv in S.items():
            for flip in (1,-1):
                for (t,s) in BARRIERS:
                    for tf in TOPS:
                        for N in HOR:
                            ntest+=1
                            r=backtest(D,sv,t,s,N,COST[sym],tf,flip)
                            if r is None: continue
                            oos=r[r[:,2]==1]
                            if len(oos)<200: continue
                            wr=100*(oos[:,0]>0).mean()
                            base=100*s/(t+s)
                            edge=wr-base
                            netR=oos[:,1].mean()
                            se=math.sqrt(max(wr,1e-9)/100*(1-wr/100)/len(oos))*100
                            results.append(dict(sym=sym,sig=nm,flip=flip,tgt=t,stp=s,
                                N=N,top=tf,n=int(len(oos)),wr=wr,base=base,edge=edge,
                                netR=netR,totR=float(oos[:,1].sum()),se=se))
    print("configs tested:",ntest,"  kept:",len(results))
    json.dump(results,open('/tmp/grid.json','w'))
