import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
D=np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)),'opt_rows.npy'))
s20,s5,hv,atband,el,pay,sym=D.T
W=4
def Nd(x): return 0.5*(1+math.erf(x/math.sqrt(2)))
def prem(sig_T): return 2*(Nd(sig_T/2)-Nd(-sig_T/2))
print("="*76); print("WHAT IS THE BREAKEVEN VOL RISK PREMIUM?"); print("="*76)
for name,mask in (("v01T squeeze",el>0.5),("band only (no HV gate)",atband>0.5)):
    lo,hi=1.0,3.0
    for _ in range(60):
        m=(lo+hi)/2
        net=pay[mask]-np.array([prem(x) for x in s20[mask]*math.sqrt(W)*m])
        if net.mean()>0: lo=m
        else: hi=m
    print("  %-26s breakeven IV multiple = %.4fx"%(name,lo))
print()
print("  Real crypto short-dated options trade at IV/RV of roughly 1.1-1.4x.")
print("  Deribit BTC 1-day ATM bid/ask alone is ~2-5%% of premium.")
print()
print("="*76); print("HV<0.8 IS ACTIVELY HARMFUL"); print("="*76)
for name,mask in (("band AND HV<0.8 (v01T)",el>0.5),
                  ("band AND HV>=0.8",(atband>0.5)&(hv>=0.8)),
                  ("band only, any HV",atband>0.5)):
    net=pay[mask]-np.array([prem(x) for x in s20[mask]*math.sqrt(W)])
    se=net.std(ddof=1)/np.sqrt(len(net))
    print("  %-26s n=%6d  %+.4f%%  t=%+.2f"%(name,len(net),100*net.mean(),net.mean()/se))
print()
print("  => v01T's HV<0.8 filter REMOVES the better half of its own signal.")
print()
print("="*76); print("PER-INSTRUMENT ROBUSTNESS (band only, IV=1.00x)"); print("="*76)
SY=['XLM','TRX','BTC','ETH','XRP','EOS','LTC','NEO','XMR','ETC','IOT','BSV','XTZ']
pos=0
for i,s in enumerate(SY):
    m=(atband>0.5)&(sym==i)
    if m.sum()<200: continue
    net=pay[m]-np.array([prem(x) for x in s20[m]*math.sqrt(W)])
    se=net.std(ddof=1)/np.sqrt(len(net))
    if net.mean()>0: pos+=1
    print("  %-5s n=%6d  %+.4f%%  t=%+6.2f"%(s,m.sum(),100*net.mean(),net.mean()/se))
print("  positive on %d/13"%pos)
