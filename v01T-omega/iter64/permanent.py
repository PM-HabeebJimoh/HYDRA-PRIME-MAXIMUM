"""
iter64: PERMANENT vs TEMPORARY structural effects.

The user's critique: XEX-D is a latency arb = a temporary plumbing defect.
Test instead effects created by LAW / CONTRACT / MANDATE, which cannot be
arbitraged away and are knowable YEARS in advance from a calendar - no
market data needed to know WHEN they occur.

THE DISCRIMINATING TEST: a permanent effect must appear in BOTH eras.
  era A = 2017-2021 (Bitfinex 1m, 13 instruments)
  era B = 2026      (market-data-mirror real bars)
If it only appears in one, it is temporary and I must discard it.

Forced flows tested (all calendar-known in advance):
  1. FUNDING SETTLEMENT   - perpetual funding paid 00/08/16 UTC. Traders
                            close/flip to avoid or capture payment.
  2. MONTH-END REBALANCE  - pension/index mandates restore weights.
  3. QUARTER-END          - stronger version of the same mandate.
  4. UTC MIDNIGHT / DAY   - accounting boundary, settlement, VWAP resets.
  5. WEEKEND->MONDAY GAP  - crypto trades 24/7, TradFi collateral does not.
"""
import csv, glob, os, math, datetime as dt, statistics as st

def load_bfx_1m(sym, root='/tmp/v7/fromBitFinex'):
    rows=[]
    for f in sorted(glob.glob(f'{root}/{sym}/*.csv')):
        with open(f) as fh:
            fh.readline()
            for line in fh:
                p=line.strip().split('\t')
                if len(p)<6: continue
                try: rows.append((int(p[0]),float(p[2])))
                except: pass
    rows.sort()
    out=[];seen=set()
    for t,c in rows:
        if t in seen: continue
        seen.add(t); out.append((t,c))
    return out

def load_csv(path):
    r=list(csv.DictReader(open(path)))
    out=[]
    for x in r:
        d=x['date']
        try: out.append((d,float(x['close'])))
        except: pass
    return out

def tstat(xs):
    n=len(xs)
    if n<3: return 0.0,0.0
    m=st.mean(xs); s=st.pstdev(xs)
    if s==0: return m,0.0
    return m, m/(s/math.sqrt(n))

print("="*94)
print("TEST 1: FUNDING SETTLEMENT HOURS (00/08/16 UTC) - contractual, permanent")
print("="*94)
print("Hypothesis: the hour BEFORE settlement has systematically different returns")
print("because leveraged traders must close or flip to avoid/collect funding.")
print()
for sym in ('BTC','ETH','LTC','XLM'):
    d=load_bfx_1m(sym)
    if len(d)<100000: continue
    # hourly returns
    byh={}
    prev=None
    for t,c in d:
        h=dt.datetime.utcfromtimestamp(t/1000).hour
        mnt=dt.datetime.utcfromtimestamp(t/1000).minute
        if mnt!=0: continue
        if prev is not None and prev[1]>0:
            r=(c/prev[1]-1)*1e4
            byh.setdefault(h,[]).append(r)
        prev=(t,c)
    if not byh: continue
    pre=[]; oth=[]
    for h,v in byh.items():
        (pre if h in (23,7,15) else oth).extend(v)
    mp,tp=tstat(pre); mo,to=tstat(oth)
    print(f"  {sym:<5} ERA 2017-21  pre-funding hr mean {mp:+8.3f}bp (t={tp:+6.2f}, n={len(pre):,})   "
          f"other {mo:+7.3f}bp")

print()
print("="*94)
print("TEST 2: MONTH-END / QUARTER-END REBALANCE - mandate-driven, permanent")
print("="*94)
def monthend_test(series, label, datefmt):
    last=[]; rest=[]; qend=[]
    prev=None
    for d,c in series:
        if prev is None: prev=(d,c); continue
        r=(c/prev[1]-1)*100
        day=dt.datetime.strptime(d[:10],'%Y-%m-%d')
        nxt=day+dt.timedelta(days=1)
        is_me = nxt.month!=day.month
        is_qe = is_me and day.month in (3,6,9,12)
        if is_qe: qend.append(r)
        if is_me: last.append(r)
        else: rest.append(r)
        prev=(d,c)
    m1,t1=tstat(last); m2,t2=tstat(rest); m3,t3=tstat(qend)
    print(f"  {label:<22} month-end {m1:+7.3f}% (t={t1:+5.2f}, n={len(last)})   "
          f"other {m2:+6.3f}%   quarter-end {m3:+7.3f}% (n={len(qend)})")

for sym in ('BTC','ETH','LTC'):
    d=load_bfx_1m(sym)
    if not d: continue
    daily={}
    for t,c in d:
        k=dt.datetime.utcfromtimestamp(t/1000).strftime('%Y-%m-%d')
        daily[k]=c
    ser=sorted(daily.items())
    monthend_test(ser, f"{sym} ERA 2017-21", None)

MM='/tmp/market-data-mirror-main/data'
for f in ('BTC_1d.csv','SPX_1d.csv','SPY_1d.csv','QQQ_1d.csv','SOL_1d.csv'):
    p=os.path.join(MM,f)
    if not os.path.exists(p): continue
    ser=[(d,c) for d,c in load_csv(p) if d[:4] in ('2022','2023','2024','2025','2026')]
    if len(ser)<200: continue
    monthend_test(ser, f"{f.replace('_1d.csv','')} ERA 2022-26", None)

print()
print("="*94)
print("TEST 3: DAY-OF-WEEK (TradFi collateral cycle vs 24/7 crypto) - permanent")
print("="*94)
for f in ('BTC_1d.csv','SOL_1d.csv','SPX_1d.csv'):
    p=os.path.join(MM,f)
    if not os.path.exists(p): continue
    ser=load_csv(p)
    byd={}
    prev=None
    for d,c in ser:
        if prev is not None and prev[1]>0:
            wd=dt.datetime.strptime(d[:10],'%Y-%m-%d').weekday()
            byd.setdefault(wd,[]).append((c/prev[1]-1)*100)
        prev=(d,c)
    nm=['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
    out=[]
    for wd in range(7):
        if wd in byd:
            m,t=tstat(byd[wd]); out.append(f"{nm[wd]} {m:+.3f}%(t{t:+.1f})")
    print(f"  {f.replace('_1d.csv',''):<6} "+"  ".join(out))
