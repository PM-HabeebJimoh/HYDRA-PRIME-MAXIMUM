"""V82.LOWDD ported EXACTLY as specified in the doc. No additions."""
import numpy as np, bisect

RISK_PER_TRADE=0.001; STOP_ATR_MULT=1.0; TARGET_ATR_MULT=2.0
MAX_HOLD_BARS=12; MIN_STREAK=2; INITIAL_CAPITAL=10_000.0
MA_FAST=20; MA_SLOW=50; ATR_PERIOD=20; STREAK_PERIOD=3; RET_PERIOD=3

def _rm(x,n):
    c=np.cumsum(np.insert(x,0,0.0)); o=np.full(len(x),np.nan)
    o[n-1:]=(c[n:]-c[:-n])/n; return o

def compute_1h_forecast(h):
    O,C,H,L=h[:,1],h[:,2],h[:,3],h[:,4]
    body=C-O; body_pos=(body>0).astype(float)
    ma20=_rm(C,MA_FAST); ma50=_rm(C,MA_SLOW)
    trend_up=(C>ma20)&(ma20>ma50); trend_down=(C<ma20)&(ma20<ma50)
    pct=np.zeros(len(C)); pct[1:]=np.diff(C)/C[:-1]
    ret3=_rm(pct,RET_PERIOD)*RET_PERIOD
    streak=_rm(body_pos,STREAK_PERIOD)*STREAK_PERIOD
    return trend_up,trend_down,ret3,streak

def atr(f,n=ATR_PERIOD):
    H,L,C=f[:,3],f[:,4],f[:,2]
    tr=np.empty(len(f)); tr[0]=H[0]-L[0]
    tr[1:]=np.maximum(H[1:]-L[1:],np.maximum(np.abs(H[1:]-C[:-1]),np.abs(L[1:]-C[:-1])))
    return _rm(tr,n)

def run(f,h,cost_frac_of_stop=0.0,capital=INITIAL_CAPITAL,causal_atr=True,allow_overlap=True):
    """cost_frac_of_stop: round-trip cost as fraction of the stop distance."""
    tu,td,r3,st=compute_1h_forecast(h)
    A=atr(f)
    if causal_atr: A=np.concatenate([[np.nan],A[:-1]])   # ATR known BEFORE bar i
    ht=list(h[:,0])
    C,H,L=f[:,2],f[:,3],f[:,4]
    peak=capital; maxdd=0.0; trades=[]; eq=[]
    busy_until=-1
    for i in range(60,len(f)-MAX_HOLD_BARS):
        if not allow_overlap and i<busy_until: continue
        k=bisect.bisect_right(ht,f[i,0])-1
        if k<60: continue
        a=A[i]
        if not np.isfinite(a) or a<=0: continue
        if tu[k] and st[k]>=MIN_STREAK and r3[k]>0: d=1
        elif td[k] and st[k]<=(STREAK_PERIOD-MIN_STREAK) and r3[k]<0: d=-1
        else: continue
        S=C[i]; stop=S-d*STOP_ATR_MULT*a; targ=S+d*TARGET_ATR_MULT*a
        dist=abs(S-stop)
        if dist<=0: continue
        risk=capital*RISK_PER_TRADE
        n=max(1,int(risk/dist))
        ex=None
        for j in range(i+1,min(i+MAX_HOLD_BARS,len(f))):
            if d==1:
                if L[j]<=stop: ex=stop; break
                if H[j]>=targ: ex=targ; break
            else:
                if H[j]>=stop: ex=stop; break
                if L[j]<=targ: ex=targ; break
        if ex is None: ex=C[min(i+MAX_HOLD_BARS,len(f)-1)]
        pnl=(ex-S)*d*n - cost_frac_of_stop*dist*n
        capital+=pnl
        if capital<=0: return dict(bust=True,trades=len(trades),capital=capital,maxdd=1.0)
        peak=max(peak,capital); maxdd=max(maxdd,(peak-capital)/peak)
        trades.append(pnl/ (risk if risk>0 else 1))
        eq.append(capital)
        busy_until=i+MAX_HOLD_BARS
    t=np.array(trades)
    return dict(bust=False,trades=len(t),capital=capital,maxdd=maxdd,
                wr=100*(t>0).mean() if len(t) else 0.0,
                meanR=t.mean() if len(t) else 0.0, eq=eq)
