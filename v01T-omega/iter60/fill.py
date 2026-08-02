"""
iter60: THE LAST BLOCKER, MEASURED.

Claim to test: to hit 500%/mo at 1x with 80% WR and zero fees you must fill
63.4% of posted 1-minute maker orders.

Data: REAL Binance tick tape with IsBuyerMaker flag (Nucs/cryptocurrency-ticks-data).
Simulation rule (conservative, no lookahead):
  - at the start of each 1m bar, post a passive limit order at the best price
    implied by the FIRST trade of that bar (buy at that price - 1 tick).
  - it FILLS during the bar iff a later trade in that bar prints at or below
    the posted price (for a buy). This is the standard price-touch fill test,
    and it is OPTIMISTIC (ignores queue position).
  - measure: fill rate, and the realised open->close move conditional on filling.
"""
import csv, io, zipfile, os, statistics as st, glob

def load_day(sym, day):
    p = f'/tmp/ticks/cryptocurrency-ticks-data-master/data/{sym}/{sym}.{day}.csv.zip'
    if not os.path.exists(p): return None
    z = zipfile.ZipFile(p)
    n = z.namelist()[0]
    out=[]
    with z.open(n) as fh:
        r = csv.reader(io.TextIOWrapper(fh, 'utf-8'))
        next(r)
        for row in r:
            try: out.append((float(row[1]), float(row[2]), row[4]=='True'))
            except: pass
    return out

def analyse(sym, days):
    fills=0; posts=0; moves=[]; touch_moves=[]
    allmoves=[]
    for day in days:
        t = load_day(sym, day)
        if not t: continue
        bars={}
        for ts,px,ibm in t:
            b=int(ts//60)
            bars.setdefault(b,[]).append((ts,px,ibm))
        for b in sorted(bars):
            tr=bars[b]
            if len(tr)<3: continue
            posts+=1
            p0=tr[0][1]; pend=tr[-1][1]
            allmoves.append(abs(pend/p0-1)*1e4)
            # post a passive BUY 1 tick below first print; tick ~ 0.01 for BTCUSDT
            tick=0.01 if p0>1000 else p0*1e-6
            post=p0-tick
            lo=min(x[1] for x in tr[1:])
            if lo<=post:
                fills+=1
                touch_moves.append((pend/post-1)*1e4)
    return posts, fills, allmoves, touch_moves

days=[f'2019-06-{d:02d}' for d in range(1,15)]
print("="*78)
print("REAL MAKER FILL RATE | Binance tick tape w/ IsBuyerMaker | BTCUSDT 2019-06-01..14")
print("(era 2018-19 tape - the ONLY tape I have with true aggressor flags)")
print("="*78)
for sym in ('BTCUSDT','NEOUSDT'):
    posts, fills, allm, tm = analyse(sym, days)
    if not posts: print(f"{sym}: no data"); continue
    fr = fills/posts*100
    print()
    print(f"{sym}:  1m bars posted = {posts:,}   filled = {fills:,}   FILL RATE = {fr:.1f}%")
    if allm: print(f"   median |open->close| move       = {st.median(allm):.3f} bp")
    if tm:
        print(f"   median post->close move ON FILLS = {st.median(tm):+.3f} bp")
        wr = 100*sum(1 for x in tm if x>0)/len(tm)
        print(f"   WR of a filled passive buy       = {wr:.2f}%   <- ADVERSE SELECTION CHECK")
    print(f"   required fill rate for 500%/mo   = 63.4%")
    print(f"   VERDICT: {'fill rate SUFFICIENT' if fr>=63.4 else 'fill rate TOO LOW'}")
