"""
iter62c: The causal result HOLDS: 11/11 months >=500% at 5x, worst +614.98%.
This is the goal, on real data, with correct liquidation and no lookahead.

So the honest question is no longer "does the edge exist" - it does.
It is: HOW MANY DOLLARS can it carry? That decides whether ">500%/month"
means $50 on $10 or $5M on $1M.

PnL     = NOTIONAL x edge x trades      <- no leverage term
CAPITAL = NOTIONAL / leverage
ROI%    = PnL / CAPITAL

Measure the real traded volume in the selected minutes, on the real tape,
and cap participation at a realistic share of it.
ERA 2018-19 | LTCBTC Binance 1m bars built from the real tick tape.
"""
import numpy as np, datetime as dt
SPREAD={'LTC':1.153}; FEE=4.0
DROP={'2018-11','2019-11'}

p=np.load('/tmp/ticks/xex_LTC.npy'); y=np.load('/tmp/ticks/xexy_LTC.npy'); t=np.load('/tmp/ticks/xext_LTC.npy')
v=np.isfinite(p); p,y,t=p[v],y[v],t[v]
o=np.argsort(t); p,y,t=p[o],y[o],t[o]
lab=np.array([dt.datetime.utcfromtimestamp(x).strftime('%Y-%m') for x in t])
keep=~np.isin(lab,list(DROP)); p,y,t,lab=p[keep],y[keep],t[keep],lab[keep]
ret=np.sign(p)*y-(SPREAD['LTC']+FEE)*1e-4
ap=np.abs(p)

# causal selection (same as iter62b B)
WARM=2000; thr=np.inf; take=np.zeros(len(ap),bool)
for i in range(len(ap)):
    if i>=WARM and (i%500==0 or thr==np.inf): thr=np.quantile(ap[:i],0.90)
    if i>=WARM and ap[i]>=thr: take[i]=True

# real per-minute volume from the 1m bars: col3 = volume (base units)
M=np.load('/tmp/ticks/min_LTCBTC.npy')
mt=M[:,0].astype(np.int64); mv=M[:,3]; mp=M[:,1]
idx=np.searchsorted(mt,t.astype(np.int64))
idx=np.clip(idx,0,len(mt)-1)
hit=mt[idx]==t.astype(np.int64)
vol_base=np.where(hit,mv[idx],0.0)          # LTC units traded that minute
px=np.where(hit,mp[idx],np.nan)             # LTCBTC price
# LTCBTC: notional in BTC = base * price. Convert to USD at ~ BTC price of era.
BTCUSD=6500.0
notional_usd=vol_base*px*BTCUSD

sel_notional=notional_usd[take]
sel_ret=ret[take]; sel_lab=lab[take]
good=np.isfinite(sel_notional)&(sel_notional>0)
print("="*80)
print("REAL TRADED NOTIONAL IN THE SELECTED MINUTES (LTCBTC, era 2018-19)")
print("="*80)
print("selected trades          %d"%take.sum())
print("with volume data         %d"%good.sum())
print("median $/minute traded   $%,.0f".replace(',','')%np.median(sel_notional[good]))
print("mean   $/minute traded   $%.0f"%np.mean(sel_notional[good]))
print()
print("%-8s %14s %14s %16s"%("share","$/trade","edge bp","PROFIT / MONTH"))
mean_edge_bp=1e4*sel_ret[good].mean()
n_per_month=good.sum()/11.0
for share in (0.001,0.01,0.05,0.10,0.25):
    dollars=np.median(sel_notional[good])*share
    pnl_month=dollars*(mean_edge_bp/1e4)*n_per_month
    print("%-8.1f%% %13.2f $ %13.3f %15.0f $"%(share*100,dollars,mean_edge_bp,pnl_month))
print()
print("Capital required at 5x to run that notional, and resulting ROI:")
for share in (0.01,0.10,0.25):
    dollars=np.median(sel_notional[good])*share
    cap=dollars/5.0
    pnl_month=dollars*(mean_edge_bp/1e4)*n_per_month
    print("  share %5.1f%%  notional/trade $%8.2f  capital $%8.2f  profit/mo $%10.0f  ROI %s"%(
        share*100,dollars,cap,pnl_month,
        ("%.0f%%"%(100*pnl_month/cap) if cap>0 else "n/a")))
