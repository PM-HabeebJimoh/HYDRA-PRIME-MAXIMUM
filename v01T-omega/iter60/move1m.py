"""
iter60: measure the REAL 2026 1-minute move for BTC on Bitfinex.
ERA 2026 | venue Bitfinex | tBTCUSD | 1m real candles via fetch_page
This corrects iter54's 0.0315bp figure, which was Kraken-specific and
measured on a tiny, unusually quiet window.
"""
import json, statistics as st
d = json.load(open('/tmp/bfx.json'))
# bitfinex candle order: [mts, open, close, high, low, volume]
C = [r[2] for r in d]
O = [r[1] for r in d]
rets = [abs(C[i]/C[i-1]-1)*1e4 for i in range(1,len(C))]      # bp, close-to-close
oc   = [abs(C[i]/O[i]-1)*1e4 for i in range(len(C))]          # bp, open-to-close (tradable)
rs = sorted(rets); q=lambda p: rs[int(p*(len(rs)-1))]
os_=sorted(oc);    qo=lambda p: os_[int(p*(len(os_)-1))]
print("ERA 2026 | Bitfinex tBTCUSD | 1-MINUTE real candles | n =", len(d))
print(f"  window: {d[0][0]} .. {d[-1][0]} (ms)")
print()
print("close-to-close |move|, bp:")
for p in (.25,.50,.75,.90,.99): print(f"   p{int(p*100):<3} {q(p):>8.3f} bp")
print(f"   mean {st.mean(rets):>7.3f} bp")
print()
print("open-to-close |move| (what you can actually capture in the bar), bp:")
for p in (.25,.50,.75,.90,.99): print(f"   p{int(p*100):<3} {qo(p):>8.3f} bp")
print(f"   mean {st.mean(oc):>7.3f} bp")
print()
REQ = 0.69
print("="*70)
print(f"REQUIREMENT at 1m / WR80% / L=1 for 500%/mo:  {REQ} bp NET per trade")
print("="*70)
med = st.median(oc)
print(f"real median open-close move (2026 BTC 1m):   {med:.3f} bp GROSS")
print(f"  ratio to requirement, BEFORE cost:         {med/REQ:.2f}x")
for name,c in [('Bitfinex taker 2026 (~2bp+spread)',2.0+1.649),
               ('maker/maker, spread only',1.649),
               ('perfect zero cost',0.0)]:
    net = med - c
    print(f"  net of {name:<34} {net:>8.3f} bp -> {net/REQ:>6.2f}x  "
          f"{'PASS' if net>REQ else 'FAIL'}")
print()
print("At WR=80%, edge per trade = net_move * (2*0.8-1) = net_move * 0.6")
for name,c in [('Bitfinex taker',3.649),('maker only',1.649),('zero cost',0.0)]:
    e = (med-c)/1e4*0.6
    if e<=-1: mo=-100.0
    else:
        try: mo=((1+e)**43200-1)*100
        except OverflowError: mo=float('inf')
    print(f"  {name:<16} edge={e*1e4:>7.3f}bp/trade  ->  monthly ROI @1x = "
          f"{mo:>14,.2f}%" if abs(mo)<1e12 else f"  {name:<16} edge={e*1e4:>7.3f}bp -> astronomically large")
