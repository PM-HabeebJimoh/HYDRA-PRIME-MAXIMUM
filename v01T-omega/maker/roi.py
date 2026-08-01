"""Filter turns MM profitable. Now: WR / DD / MONTHLY ROI on capital,
with REAL maker fees. Binance maker was 0.10% then, but VIP/BNB -> 0.00-0.02%.
Report across the fee schedule so nothing is assumed."""
import numpy as np, glob, sys
sys.path.insert(0,'/home/user/HYDRA-PRIME-MAXIMUM/v01T-omega/maker')
from filt import simulate, SIG
files=sorted(glob.glob('/tmp/ticks/cryptocurrency-ticks-data-master/data/NEOUSDT/*.zip'))
print("total NEO days available: %d"%len(files))
HS=20.0; MODE='skew'; TH=0.5
for fee in (0.0,1.0,2.0,5.0,10.0):
    daily=[];p0=None
    for f in files:
        r=simulate(f,HS,MODE,TH,fee_bp=fee)
        if r is None: continue
        pnl,fl,px0,inv=r
        if p0 is None: p0=px0
        daily.append(pnl)
    d=np.array(daily)
    if len(d)<30: continue
    # capital required = max inventory (5 units) x price, plus buffer
    cap=5.0*p0*2.0
    dr=d/cap
    eq=np.cumsum(dr); peak=np.maximum.accumulate(np.concatenate([[0],eq]))[1:]
    dd=np.max(peak-eq)
    mo=len(d)/30.44
    roi=(1+dr).prod()**(1/mo)-1
    wr=100*(d>0).mean()
    sh=dr.mean()/dr.std(ddof=1)*np.sqrt(30.44)
    print("maker fee %4.1fbp | days %3d | WR %5.2f%% | maxDD %6.2f%% | monthly ROI %+8.2f%% | Sharpe_mo %5.2f"%(
        fee,len(d),wr,100*dd,100*roi,sh))
