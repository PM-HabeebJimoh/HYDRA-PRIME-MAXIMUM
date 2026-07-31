from load import *; from v82 import *
from port import signals,resolve
import numpy as np
syms=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
ev=[]
for s in syms:
    a=load_1m(s)
    if a is None or len(a)<50000: continue
    f=resample(a,5); h=resample(a,60); busy=-1
    for (i,d,at) in signals(f,h):
        if i<busy: continue
        R,jx=resolve(f,i,d,at,0.02)
        ev.append((f[i,0],f[jx,0],s,R)); busy=jx
ev.sort()
np.save('/tmp/v82/ev_R.npy',np.array([e[3] for e in ev]))
np.save('/tmp/v82/ev_t.npy',np.array([[e[0],e[1]] for e in ev]))
R=np.array([e[3] for e in ev])
t0=ev[0][0]; t1=max(e[1] for e in ev); mo=(t1-t0)/86400000/30.44
print('events %d over %.1f months = %.0f/month'%(len(R),mo,len(R)/mo))
print('meanR %+.4f  SE %.4f  t=%.1f'%(R.mean(),R.std(ddof=1)/np.sqrt(len(R)),R.mean()/(R.std(ddof=1)/np.sqrt(len(R)))))

def sim(f):
    cap=1.0;peak=1.0;dd=0.0
    for r in R:
        cap*= (1+f*r)
        if cap<=0: return None,1.0
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
    return cap,dd

print('\nDD-CONSTRAINED LEVERAGE SOLVE (target max DD < 4%)')
print('%-10s %10s %10s'%('risk/trade','maxDD%','ROI/mo'))
best=None
for f in (0.0001,0.0002,0.0003,0.0005,0.001,0.002,0.005):
    c,dd=sim(f)
    if c is None: print('%-10.4f%%   BUST'%(100*f)); continue
    roi=c**(1/mo)-1
    flag=' <= DD OK' if dd<0.04 else ''
    print('%-10s %10.2f %+10.2f%%%s'%(f'{100*f:.2f}%',100*dd,100*roi,flag))
    if dd<0.04: best=(f,dd,roi)
# bisect for exact DD=4%
lo,hi=0.00001,0.01
for _ in range(40):
    m=(lo+hi)/2; c,dd=sim(m)
    if c is None or dd>0.04: hi=m
    else: lo=m
c,dd=sim(lo); roi=c**(1/mo)-1
print('\nEXACT solve: risk=%.5f%% -> DD %.3f%%  ROI %+.2f%%/mo'%(100*lo,100*dd,100*roi))
print('required for 1000%%/mo: need ROI >= 1000%%. Achieved: %.2f%%'%(100*roi))
