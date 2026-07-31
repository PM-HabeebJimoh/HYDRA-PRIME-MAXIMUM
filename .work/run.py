import json,statistics,datetime as dt,sys
KEY=sys.argv[1]; STEP=int(sys.argv[2]); LABEL=sys.argv[3]
BARS_PER_DAY=int(86400/STEP)
W=BARS_PER_DAY            # 24h window in bars of this timeframe
TP,SL=0.005,0.0005
d=json.load(open(f"raw/{KEY}.json"))
TS=sorted(int(k) for k in d)
def mon(t): return dt.datetime.utcfromtimestamp(t).strftime("%Y-%m")
def bbp(w):
    if len(w)<20: return 50.0
    l=w[-20:]; sma=sum(l)/20
    sd=(sum((x-sma)**2 for x in l)/20)**0.5
    return 50.0 if sd==0 else round((w[-1]-(sma-2*sd))/(4*sd)*100,2)
def hvr(w):
    if len(w)<30: return 1.0
    r=[(w[k]/w[k-1]-1) for k in range(1,len(w))]
    if len(r)<20: return 1.0
    s5,s20=statistics.stdev(r[-5:]),statistics.stdev(r[-20:])
    return 1.0 if s20==0 else round(s5/s20,3)

C=[d[str(t)][3] for t in TS]; H=[d[str(t)][1] for t in TS]; L=[d[str(t)][0] for t in TS]

def straddle(i):
    """0.05% stop enforced against REAL intrabar high/low. Stopped leg is dead."""
    e=C[i]; lt,ls=e*(1+TP),e*(1-SL); st,ss=e*(1-TP),e*(1+SL)
    lo=sh=True
    for k in range(1,W+1):
        if i+k>=len(C): break
        hi,low=H[i+k],L[i+k]
        if sh and hi>=ss: sh=False
        if lo and low<=ls: lo=False
        if lo and hi>=lt: return 'win'
        if sh and low<=st: return 'win'
        if not lo and not sh: return 'double_stop'
    return 'time_exit'

def gate4(i):
    e=C[i]
    for k in range(1,W+1):
        if i+k>=len(C): break
        if abs((C[i+k]-e)/e)>=TP: return True
    return False

print("="*78); print(f"{LABEL} — v01T — REAL intrabar OHLC (Bitstamp BTC/USD)"); print("="*78)
print(f"total bars {len(C)}  {dt.datetime.utcfromtimestamp(TS[0]):%Y-%m-%d %H:%M} -> {dt.datetime.utcfromtimestamp(TS[-1]):%Y-%m-%d %H:%M}")
print(f"window = {W} bars = 24h\n")

rows=[]
for M,name in (("2026-03","MARCH"),("2026-04","APRIL"),("2026-05","MAY")):
    idx=[i for i in range(20,len(C)-W) if mon(TS[i])==M]
    if not idx: continue
    sig=[]
    for i in idx:
        w=C[:i+1]; bb=bbp(w); hv=hvr(w)
        sc=92 if bb<10 else (85 if bb>90 else 72)
        if (bb<10 or bb>90) and hv<0.8 and sc>=85: sig.append(i)
    mi=[i for i in range(len(TS)) if mon(TS[i])==M]
    move=(C[mi[-1]]-C[mi[0]])/C[mi[0]]*100
    n=len(sig)
    if n==0:
        print(f"{name}: 0 squeezes"); continue
    # A: spec (stop ignored)
    cap=1e4;pk=cap;dd=0;w1=0
    for i in sig:
        if gate4(i): cap*=1.225; w1+=1
        else: cap*=0.975
        pk=max(pk,cap); dd=max(dd,(pk-cap)/pk*100)
    wrA,roiA,ddA=w1/n*100,(cap-1e4)/100,dd
    # B: stop enforced on real OHLC
    cap=1e4;pk=cap;dd=0;w2=0;ds=0;te=0
    for i in sig:
        o=straddle(i)
        if o=='win': cap*=1.225; w2+=1
        elif o=='double_stop': cap*=0.95; ds+=1
        else: cap*=0.975; te+=1
        pk=max(pk,cap); dd=max(dd,(pk-cap)/pk*100)
    wrB,roiB,ddB=w2/n*100,(cap-1e4)/100,dd
    rng=[(H[i]-L[i])/C[i]*100 for i in mi]
    print(f"--- {name} 2026 --- bars {len(mi)}  BTC {move:+.2f}%  squeezes {n}  (selectivity {n/len(idx)*100:.1f}%)")
    print(f"  [A] spec, stop NOT checked : WR {wrA:6.2f}%  ROI {roiA:>12,.2f}%  DD {ddA:6.2f}%")
    print(f"  [B] STOP ENFORCED real OHLC: WR {wrB:6.2f}%  ROI {roiB:>12,.2f}%  DD {ddB:6.2f}%   (wins {w2}, double_stops {ds}, time {te})")
    print(f"      median bar range {statistics.median(rng):.3f}%  = {statistics.median(rng)/0.10:.1f}x the 0.10% stop corridor")
    print(f"  GOALS [A]: WR>80 {'PASS' if wrA>80 else 'FAIL'} | ROI>1000 {'PASS' if roiA>1000 else 'FAIL'} | DD<4 {'PASS' if ddA<4 else 'FAIL'}")
    print(f"  GOALS [B]: WR>80 {'PASS' if wrB>80 else 'FAIL'} | ROI>1000 {'PASS' if roiB>1000 else 'FAIL'} | DD<4 {'PASS' if ddB<4 else 'FAIL'}\n")
    rows.append((name,n,wrA,roiA,ddA,wrB,roiB,ddB))
print("SUMMARY",LABEL)
print(f"{'month':<8} {'n':>4} | {'A_WR%':>7} {'A_ROI%':>13} {'A_DD%':>7} | {'B_WR%':>7} {'B_ROI%':>11} {'B_DD%':>7}")
for r in rows:
    print(f"{r[0]:<8} {r[1]:>4} | {r[2]:>7.2f} {r[3]:>13,.2f} {r[4]:>7.2f} | {r[5]:>7.2f} {r[6]:>11,.2f} {r[7]:>7.2f}")
