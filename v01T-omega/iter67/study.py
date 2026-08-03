"""
iter67b: STUDY every collectable field, one at a time, for next-candle direction.
Before building anything, measure WHAT ACTUALLY PREDICTS. No model, no fitting -
just univariate predictive power of each real, easily-collected field.

Real Binance tick tape -> 17-column 1m OHLC+microstructure panels.
Target: sign of NEXT minute's close-to-close return.
Split: first 60% train / last 40% OOS. All numbers reported OOS.
"""
import numpy as np, sys, os

C=dict(ts=0,o=1,h=2,l=3,c=4,vol=5,ntr=6,ofi=7,bvol=8,svol=9,vwap=10,
       maxtr=11,top10=12,upt=13,rev=14,tfi=15,spr=16)

def roll(x,k):
    o=np.full(len(x),np.nan); v=np.nan_to_num(x)
    cs=np.cumsum(np.insert(v,0,0.0)); o[k-1:]=(cs[k:]-cs[:-k])/k; return o
def rstd(x,k):
    v=np.nan_to_num(x); o=np.full(len(x),np.nan)
    cs=np.cumsum(np.insert(v,0,0.0)); c2=np.cumsum(np.insert(v*v,0,0.0))
    m=(cs[k:]-cs[:-k])/k; var=(c2[k:]-c2[:-k])/k-m*m
    o[k-1:]=np.sqrt(np.maximum(var,0)); return o
def z(x,k): return (x-roll(x,k))/np.maximum(rstd(x,k),1e-12)

def build(sym):
    A=np.load('/tmp/ticks/ohlc_%s.npy'%sym)
    ts=A[:,C['ts']].astype(np.int64)
    o,h,l,c=A[:,1],A[:,2],A[:,3],A[:,4]
    vol,ntr,ofi=A[:,5],A[:,6],A[:,7]
    vwap,maxtr,top10=A[:,10],A[:,11],A[:,12]
    upt,rev,tfi,spr=A[:,13],A[:,14],A[:,15],A[:,16]
    lc=np.log(np.maximum(c,1e-12))
    ret=np.zeros(len(c)); ret[1:]=np.diff(lc)
    F={}
    F['ofi']              = ofi
    F['ofi_z60']          = z(ofi,60)
    F['tfi']              = tfi                       # late-minute flow
    F['tfi_z60']          = z(tfi,60)
    F['close_loc']        = np.where(h>l,(c-l)/np.maximum(h-l,1e-12)-0.5,0.0)
    F['body']             = (c-o)/np.maximum(vwap,1e-12)
    F['upper_wick']       = (h-np.maximum(c,o))/np.maximum(h-l,1e-12)
    F['lower_wick']       = (np.minimum(c,o)-l)/np.maximum(h-l,1e-12)
    F['c_vs_vwap']        = (c-vwap)/np.maximum(vwap,1e-12)
    F['ret1']             = ret
    F['ret3']             = roll(ret,3)
    F['range_z']          = z(spr,60)
    F['vol_z']            = z(np.log(np.maximum(vol,1e-9)),60)
    F['ntr_z']            = z(np.log(np.maximum(ntr,1)),60)
    F['whale']            = maxtr/np.maximum(vol,1e-12)
    F['top10']            = top10
    F['upt']              = upt-0.5
    F['rev_z']            = z(rev,60)
    F['ofi_x_vol']        = z(ofi,60)*z(np.log(np.maximum(vol,1e-9)),60)
    F['ofi_persist']      = roll(ofi,5)
    F['tfi_minus_ofi']    = tfi-ofi                   # late vs whole-minute pressure
    y=np.zeros(len(c)); y[:-1]=ret[1:]
    good=np.zeros(len(c),bool)
    good[:-1]=(ts[1:]-ts[:-1]==60)
    return F,y,good,ts

print("="*94)
print("UNIVARIATE STUDY: which real, easily-collected field predicts the NEXT candle?")
print("ERA 2018-19 | real Binance tick tape | OOS = last 40% | no fitting")
print("="*94)
for sym in ('BTCUSDT','NEOUSDT','LTCBTC'):
    p='/tmp/ticks/ohlc_%s.npy'%sym
    if not os.path.exists(p): continue
    F,y,good,ts=build(sym)
    n=len(y); cut=int(n*0.6)
    print()
    print(f"--- {sym}  n={n:,} ---")
    print(f"{'field':<18}{'|corr|':>9}{'acc@|z|>2':>12}{'n fired':>10}{'mean bp':>10}")
    rows=[]
    for k,v in F.items():
        m=good&np.isfinite(v)&np.isfinite(y)
        m[:cut]=False
        if m.sum()<500: continue
        cc=np.corrcoef(v[m],y[m])[0,1]
        zz=z(v,240)
        mm=m&np.isfinite(zz)&(np.abs(zz)>2)
        if mm.sum()<100: 
            rows.append((abs(cc),k,cc,np.nan,0,np.nan)); continue
        sgn=np.sign(cc) if cc==cc else 1
        acc=100*(np.sign(zz[mm])*sgn==np.sign(y[mm])).mean()
        bp=1e4*(np.sign(zz[mm])*sgn*y[mm]).mean()
        rows.append((abs(cc),k,cc,acc,int(mm.sum()),bp))
    rows.sort(reverse=True)
    for a,k,cc,acc,nn,bp in rows[:14]:
        astr=f"{acc:>11.2f}%" if acc==acc else f"{'--':>12}"
        bstr=f"{bp:>+9.3f}" if bp==bp else f"{'--':>10}"
        print(f"{k:<18}{cc:>+9.4f}{astr}{nn:>10}{bstr}")
