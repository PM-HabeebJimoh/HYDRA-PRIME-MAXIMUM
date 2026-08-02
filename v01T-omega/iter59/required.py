"""
iter59 / Q1: "If you achieve 80% direction and magnitude accuracy, then where's leverage?"

The user is right that this is a closed-form question, not a research question.
Solve it, then measure the answer against REAL 2026 data.

DATA: real 2026 bars, github.com/pantlinardatos/market-data-mirror (codeload tarball,
reachable from bash). BTC/SOL/HYPE 4h 2026-04-04..2026-08-02; BTC/SPX/QQQ/TSLA 1d 2026.
NO synthetic, no assumed, no dummy.
"""
import csv, glob, os, math, statistics as st

DIR = '/tmp/market-data-mirror-main/data'

def load(f):
    rows = list(csv.DictReader(open(f)))
    return [(r['date'], float(r['open']), float(r['high']), float(r['low']), float(r['close'])) for r in rows]

# ---------------------------------------------------------------- part 1
# Required per-trade edge for 5000%/mo at 1x, as a function of trade count.
print("="*74)
print("Q1 SOLVED IN CLOSED FORM: what does '80% accuracy' have to deliver")
print("="*74)
print("Target: x51 per month (5000% ROI), NO leverage (L=1).")
print("Compounding: (1+e)^N = 51  ->  e = 51^(1/N) - 1")
print("With win rate w and symmetric move m net of cost: e = m*(2w-1)")
print()
print(f"{'trades/mo':>10} {'req edge e':>12} {'req move m @ WR80%':>20} {'@WR90%':>10} {'@WR100%':>10}")
for N in (20, 100, 250, 500, 1000, 5000, 20000, 43200):
    e = 51**(1.0/N) - 1
    print(f"{N:>10} {e*100:>11.4f}% {e/0.6*100:>19.4f}% {e/0.8*100:>9.4f}% {e/1.0*100:>9.4f}%")
print()
print("So the user's question has a precise answer: at 80% accuracy leverage is")
print("unnecessary ONLY IF the per-trade move exceeds the number in column 3.")
print("That column is the whole problem. Now measure it on real 2026 data.")

# ---------------------------------------------------------------- part 2
print()
print("="*74)
print("REAL 2026 MOVE SIZES (era=2026, source=market-data-mirror, real bars)")
print("="*74)
print(f"{'series':<14} {'tf':<4} {'n':>5} {'period':<26} {'med |ret|':>10} {'p75':>8} {'p90':>8}")
rows_out = {}
for f in sorted(glob.glob(f'{DIR}/*_4h.csv')) + sorted(glob.glob(f'{DIR}/*_1d.csv')):
    name = os.path.basename(f).replace('.csv','')
    d = load(f)
    d = [x for x in d if x[0][:4] == '2026']
    if len(d) < 40: continue
    rets = [abs(d[i+1][4]/d[i][4]-1)*100 for i in range(len(d)-1)]
    rets_s = sorted(rets)
    q = lambda p: rets_s[int(p*(len(rets_s)-1))]
    tf = '4h' if '_4h' in name else '1d'
    print(f"{name:<14} {tf:<4} {len(d):>5} {d[0][0][:10]}..{d[-1][0][:10]:<12} "
          f"{q(.50):>9.4f}% {q(.75):>7.4f}% {q(.90):>7.4f}%")
    rows_out[name] = (len(d), q(.50), tf)

# ---------------------------------------------------------------- part 3
print()
print("="*74)
print("THE ANSWER TO Q1, PER REAL 2026 SERIES")
print("="*74)
print("bars/month = bars in sample / months in sample. Take EVERY bar as a trade")
print("(the most trades physically available at that timeframe). Cost = 0 (best case).")
print()
print(f"{'series':<14} {'trades/mo':>9} {'med move':>9} {'req move@WR80':>14} {'shortfall':>10} {'ROI@WR80,1x':>13}")
for name,(n, med, tf) in rows_out.items():
    months = n/ (180.0 if tf=='4h' else 30.4)   # 4h: 6 bars/day
    tpm = n/months
    e_req = 51**(1.0/tpm) - 1
    m_req = e_req/0.6*100
    e_act = med/100*0.6              # if WR were 80% on the MEDIAN move
    roi = ((1+e_act)**tpm - 1)*100
    print(f"{name:<14} {tpm:>9.0f} {med:>8.4f}% {m_req:>13.4f}% {med/m_req:>9.2f}x "
          f"{roi:>12,.0f}%")
