"""87% survives continuity. But accuracy is HIGHER in LOW-volume minutes
(93.02% vs 81.40%). That is the signature of a CAPACITY-CONSTRAINED edge:
it works best exactly where there is least liquidity to trade against.

Measure the real capacity: how much notional can actually be executed at the
prices I assumed, before my own order moves the market past the edge?"""
import numpy as np, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from load import load_1m
p=np.load('/tmp/ticks/xex_NEO.npy'); y=np.load('/tmp/ticks/xexy_NEO.npy'); t=np.load('/tmp/ticks/xext_NEO.npy')
v=np.isfinite(p); p=p[v];y=y[v];t=t[v].astype(np.int64)
a=load_1m('NEO')
bt=(a[:,0]/1000.0).astype(np.int64); bv=a[:,5]; bc=a[:,2]
VOL={int(x):float(z) for x,z in zip(bt,bv)}
PX={int(x):float(z) for x,z in zip(bt,bc)}
k=int(len(p)*0.005)
sel=np.argsort(-np.abs(p))[:k]
vol=np.array([VOL.get(int(t[i]+60),0.0) for i in sel])
px=np.array([PX.get(int(t[i]),0.0) for i in sel])
notional=vol*px
print("TOP 0.5%% TRADES (n=%d), the ones earning +34bp"%len(sel))
print("  next-minute VOLUME (NEO units): median %.1f  p25 %.1f  p10 %.1f"%(
    np.median(vol),np.percentile(vol,25),np.percentile(vol,10)))
print("  next-minute NOTIONAL (USD)    : median ${:,.0f}  p25 ${:,.0f}  p10 ${:,.0f}".format(
    np.median(notional),np.percentile(notional,25),np.percentile(notional,10)))
print()
print("A trader can realistically capture a small share of one minute's volume")
print("without moving price. At 10%% participation:")
for share in (0.02,0.05,0.10,0.20):
    cap=np.median(notional)*share
    print("   %3.0f%% participation -> $%8.0f per trade"%(100*share,cap))
print()
print("MONTHLY DOLLAR PnL CEILING (148 trades/mo, +20.93bp net, 10.8x lev):")
for share in (0.02,0.05,0.10,0.20):
    capital=np.median(notional)*share/10.8   # notional = capital x leverage
    monthly=capital*10.8*0.002093*148
    print("   %3.0f%% participation -> capital $%8.0f -> PnL $%9.0f/month"%(
        100*share,capital,monthly))
