"""The discovery: v01T's band gate is only useful when read as a PULLBACK,
i.e. buy the LOWER band in an UPTREND. Tune the threshold + target."""
from load import *; from v82 import *
from hybrid import ddsolve
import numpy as np, bisect, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega')
from omega.indicators import bb_percent, hv_ratio

def harvest(f,h,bb_lo,hv_max,tmult,cost=0.02,use_hv=True):
    tu,td,r3,st=compute_1h_forecast(h); A=np.concatenate([[np.nan],atr(f)[:-1]])
    C=f[:,2]; bb=bb_percent(C); hv=hv_ratio(C)
    ht=list(h[:,0]); O,H,L=f[:,1],f[:,3],f[:,4]
    out=[];busy=-1
    for i in range(60,len(f)-12):
        if i<busy: continue
        k=bisect.bisect_right(ht,f[i,0])-1
        if k<60: continue
        a=A[i]
        if not np.isfinite(a) or a<=0: continue
        b=bb[i]; v=hv[i]
        if not np.isfinite(b): continue
        if use_hv and not (np.isfinite(v) and v<hv_max): continue
        if tu[k] and st[k]>=2 and r3[k]>0:
            d=1
            if not (b<bb_lo): continue
        elif td[k] and st[k]<=1 and r3[k]<0:
            d=-1
            if not (b>100-bb_lo): continue
        else: continue
        S=C[i]; stop=S-d*a; targ=S+d*tmult*a; ex=None; jj=i+12
        for j in range(i+1,i+12):
            op=O[j]
            if d==1:
                if op<=stop or op>=targ: ex=op;jj=j;break
                if L[j]<=stop: ex=stop;jj=j;break
                if H[j]>=targ: ex=targ;jj=j;break
            else:
                if op>=stop or op<=targ: ex=op;jj=j;break
                if H[j]>=stop: ex=stop;jj=j;break
                if L[j]<=targ: ex=targ;jj=j;break
        if ex is None: ex=C[i+12]
        out.append((f[i,0],f[jj,0],(ex-S)*d/a-cost))
        busy=jj
    return out

if __name__=='__main__':
    syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
    D={}
    for s in syms:
        a=load_1m(s)
        if a is None or len(a)<50000: continue
        D[s]=(resample(a,5),resample(a,60))
    print('%-28s %8s %7s %7s %8s %7s %11s'%('config','n','tr/mo','WR%','meanR','t','ROI/mo@DD4'))
    best=[]
    for bb_lo in (10,20,30,40):
        for hvm,uh in ((0.8,True),(1.0,True),(9.9,False)):
            for tm in (2.0,3.0):
                ev=[]
                for s,(f,h) in D.items(): ev+=harvest(f,h,bb_lo,hvm,tm,use_hv=uh)
                ev.sort(); r=ddsolve(ev)
                if r is None: continue
                lbl='bb<%d hv%s T%.0f'%(bb_lo,('<%.1f'%hvm) if uh else 'off',tm)
                print('%-28s %8d %7.0f %7.2f %+8.4f %7.1f %+10.2f%%'%(lbl,r['n'],r['permo'],r['wr'],r['meanR'],r['t'],100*r['roi']))
                best.append((r['roi'],lbl,r))
    best.sort(reverse=True)
    print('\nBEST: %s  ROI %+.2f%%/mo  n=%d  WR %.2f%%  t=%.1f'%(best[0][1],100*best[0][0],best[0][2]['n'],best[0][2]['wr'],best[0][2]['t']))
