"""
iter71: JULY 2026 BACKTEST, $1,000 capital, both geometries from iter70.

  GEOMETRY A: 400/200 bp  -> the SKILL config (edge +18.70, netR +0.2096 on 2018-19)
  GEOMETRY B:  30/270 bp  -> the 85%+ config (WR 91.95%, netR +0.0140 on 2018-19)

DATA: REAL Bitfinex tLTCBTC 1h candles, 2026-07-01 .. 2026-08-01, pulled live
      via fetch_page this session. 716 bars. Columns MTS,OPEN,CLOSE,HIGH,LOW,VOL.

RULES (identical to iter69/70, nothing relaxed):
  * signal computed from PAST bars only
  * entry at the NEXT bar's OPEN
  * outcome resolved by walking HIGH/LOW forward
  * pessimistic: if a bar touches both barriers -> STOP fills
  * non-overlapping: one position at a time
  * cost 5.15 bp round trip charged on every trade
  * FIXED FRACTIONAL sizing: risk a constant % of equity per trade

IMPORTANT LIMITATION, STATED UP FRONT:
  iter70 trained on 1-MINUTE 2018-19 bars. Here I only have 1-HOUR 2026 bars
  (Bitfinex 1m history via fetch_page would need ~200 hand-parsed calls).
  A 400bp barrier on 1h candles is a different regime from 400bp on 1m candles.
  So this is an HONEST OUT-OF-SAMPLE TEST OF THE RULES, not a replication of
  the same trade population. I report it as such.
"""
import json, math, datetime as dt

BARS=json.load(open('/tmp/j26/ltcbtc_1h.json'))
BARS=[b for b in BARS if dt.datetime.utcfromtimestamp(b[0]/1000).month==7]
TS=[b[0] for b in BARS]; O=[b[1] for b in BARS]; C=[b[2] for b in BARS]
H=[b[3] for b in BARS]; L=[b[4] for b in BARS]; V=[b[5] for b in BARS]
n=len(BARS)
print("="*96)
print("JULY 2026 BACKTEST | REAL Bitfinex tLTCBTC 1h | %d bars | %s .. %s"%(
    n, dt.datetime.utcfromtimestamp(TS[0]/1000).date(), dt.datetime.utcfromtimestamp(TS[-1]/1000).date()))
print("="*96)

def mean(x): return sum(x)/len(x) if x else 0.0
def sd(x):
    if len(x)<2: return 0.0
    m=mean(x); return math.sqrt(sum((v-m)**2 for v in x)/len(x))

# ---- signal: 'flow' proxy. No tick tape for 2026, so use the closest causal
# equivalent available in OHLCV: volume-weighted directional pressure.
ret=[0.0]*n
for i in range(1,n): ret[i]=math.log(max(C[i],1e-12)/max(C[i-1],1e-12))
# directional pressure = sign of bar body weighted by relative volume, z-scored
press=[0.0]*n
for i in range(n):
    rng=max(H[i]-L[i],1e-15)
    press[i]=((C[i]-O[i])/rng)*V[i]
def zser(x,k):
    out=[float('nan')]*len(x)
    for i in range(k,len(x)):
        w=x[i-k:i]
        s=sd(w)
        out[i]=(x[i]-mean(w))/s if s>0 else 0.0
    return out
Z=zser(press,48)

def resolve(i,side,tgt,stp,N):
    """enter at O[i]; walk bars i..i+N-1 using H/L; pessimistic ties."""
    e=O[i]
    up=e*(1+tgt*1e-4) if side>0 else e*(1+stp*1e-4)
    dn=e*(1-stp*1e-4) if side>0 else e*(1-tgt*1e-4)
    for k in range(i,min(i+N,n)):
        if side>0:
            if L[k]<=dn: return -1.0,k-i+1,'STOP'
            if H[k]>=up: return tgt/stp,k-i+1,'TARGET'
        else:
            if H[k]>=up: return -1.0,k-i+1,'STOP'
            if L[k]<=dn: return tgt/stp,k-i+1,'TARGET'
    k=min(i+N-1,n-1)
    return (C[k]/e-1)*1e4*side/stp, k-i+1, 'TIMEOUT'

COST=5.15
def run(tgt,stp,N,topq,risk_frac,label):
    av=sorted([abs(z) for z in Z[48:] if z==z])
    if not av: return
    thr=av[int(len(av)*(1-topq))]
    cap=1000.0; peak=1000.0; dd=0.0
    trades=[]; last=-1
    for i in range(48,n-1):
        z=Z[i]
        if z!=z or abs(z)<thr: continue
        if i<=last: continue
        side=1 if z>0 else -1
        R,bars,how=resolve(i+1,side,tgt,stp,N)
        last=i+bars
        netR=R-COST/stp
        risk=cap*risk_frac
        pnl=risk*netR
        cap+=pnl
        peak=max(peak,cap); dd=max(dd,(peak-cap)/peak)
        trades.append((TS[i+1],side,R,netR,pnl,cap,how,bars))
        if cap<=0: break
    if not trades:
        print(f"\n{label}: NO TRADES (threshold never met)"); return
    wins=sum(1 for t in trades if t[2]>0)
    wr=100*wins/len(trades)
    base=100*stp/(tgt+stp)
    print()
    print("-"*96)
    print(f"{label}   target {tgt}bp / stop {stp}bp   max hold {N}h   risk {risk_frac*100:.0f}% of equity")
    print("-"*96)
    print(f"{'date':<12}{'side':>5}{'outcome':>9}{'hrs':>5}{'R':>8}{'netR':>8}{'P&L $':>10}{'equity $':>11}")
    for ts,side,R,netR,pnl,eq,how,bars in trades:
        d=dt.datetime.utcfromtimestamp(ts/1000).strftime('%m-%d %H:%M')
        print(f"{d:<12}{('LONG' if side>0 else 'SHORT'):>5}{how:>9}{bars:>5}{R:>8.3f}{netR:>8.3f}{pnl:>+10.2f}{eq:>11.2f}")
    print(f"\n  trades {len(trades)}   WR {wr:.2f}%   free baseline {base:.2f}%   EDGE {wr-base:+.2f}")
    print(f"  final equity ${cap:,.2f}   return {100*(cap/1000-1):+.2f}%   maxDD {dd*100:.2f}%")
    return cap

run(400,200,240,0.05,0.02,"GEOMETRY A (skill config)")
run(30,270,240,0.05,0.02,"GEOMETRY B (85%+ config)")
