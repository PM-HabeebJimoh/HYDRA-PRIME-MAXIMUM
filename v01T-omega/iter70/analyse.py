"""
iter70c: analyse the exhaustive grid.
Guard against the obvious trap: with ~7,840 configs, the best WR is almost
certainly a multiple-comparisons artifact. Apply Bonferroni and separate
GEOMETRY (b/(a+b)) from SKILL (edge).
"""
import json,math,sys
R=json.load(open(sys.argv[1] if len(sys.argv)>1 else '/tmp/grid_btc.json'))
M=len(R)
print("="*104)
print(f"EXHAUSTIVE GRID: {M:,} configurations tested (rules: next-open entry, path-resolved,")
print("pessimistic ties, non-overlapping, costs charged, thresholds frozen on train)")
print("="*104)

hi=[r for r in R if r['wr']>=85]
print(f"\nconfigs reaching WR >= 85%: {len(hi)}")
if hi:
    print(f"{'sym':<9}{'signal':<12}{'f':>3}{'tgt':>5}{'stp':>5}{'N':>6}{'top':>7}{'n':>7}{'WR%':>8}{'base%':>8}{'EDGE':>8}{'netR':>9}")
    for r in sorted(hi,key=lambda x:-x['wr'])[:15]:
        print(f"{r['sym']:<9}{r['sig']:<12}{r['flip']:>3}{r['tgt']:>5}{r['stp']:>5}{r['N']:>6}"
              f"{r['top']:>7.3f}{r['n']:>7}{r['wr']:>7.2f}%{r['base']:>7.2f}%{r['edge']:>+8.2f}{r['netR']:>+9.4f}")
    pos=[r for r in hi if r['edge']>0]
    print(f"\n  of those, with POSITIVE skill (WR > baseline): {len(pos)}")
    posn=[r for r in hi if r['netR']>0]
    print(f"  of those, PROFITABLE after costs           : {len(posn)}")
    if posn:
        print(f"\n  >>> WR>=85% AND net-positive:")
        for r in sorted(posn,key=lambda x:-x['netR'])[:10]:
            print(f"      {r['sym']} {r['sig']} flip{r['flip']} {r['tgt']}/{r['stp']} N{r['N']} "
                  f"top{r['top']} n={r['n']} WR={r['wr']:.2f}% base={r['base']:.2f}% "
                  f"edge={r['edge']:+.2f} netR={r['netR']:+.4f}")

print()
print("="*104)
print("RANKED BY GENUINE SKILL (edge = WR - b/(a+b)), Bonferroni-corrected")
print("="*104)
print(f"{'sym':<9}{'signal':<12}{'f':>3}{'tgt':>5}{'stp':>5}{'N':>6}{'top':>7}{'n':>7}{'WR%':>8}{'base%':>8}{'EDGE':>8}{'netR':>9}{'p_bonf':>10}")
def pval(r):
    p=r['base']/100.0; n=r['n']; k=r['wr']/100.0*n
    se=math.sqrt(p*(1-p)*n)
    if se<=0: return 1.0
    zsc=(k-p*n)/se
    return 0.5*math.erfc(zsc/math.sqrt(2))
scored=[]
for r in R:
    if r['n']<200: continue
    r['p']=pval(r); r['pb']=min(1.0,r['p']*M)
    scored.append(r)
for r in sorted(scored,key=lambda x:-x['edge'])[:15]:
    print(f"{r['sym']:<9}{r['sig']:<12}{r['flip']:>3}{r['tgt']:>5}{r['stp']:>5}{r['N']:>6}"
          f"{r['top']:>7.3f}{r['n']:>7}{r['wr']:>7.2f}%{r['base']:>7.2f}%{r['edge']:>+8.2f}"
          f"{r['netR']:>+9.4f}{r['pb']:>10.4f}")

print()
print("="*104)
print("RANKED BY NET PROFIT AFTER COSTS (the only thing that is real)")
print("="*104)
print(f"{'sym':<9}{'signal':<12}{'f':>3}{'tgt':>5}{'stp':>5}{'N':>6}{'top':>7}{'n':>7}{'WR%':>8}{'EDGE':>8}{'netR':>9}{'totR':>9}{'p_bonf':>9}")
for r in sorted(scored,key=lambda x:-x['netR'])[:15]:
    print(f"{r['sym']:<9}{r['sig']:<12}{r['flip']:>3}{r['tgt']:>5}{r['stp']:>5}{r['N']:>6}"
          f"{r['top']:>7.3f}{r['n']:>7}{r['wr']:>7.2f}%{r['edge']:>+8.2f}{r['netR']:>+9.4f}"
          f"{r['totR']:>+9.1f}{r['pb']:>9.4f}")
sig=[r for r in scored if r['pb']<0.05 and r['edge']>0]
print(f"\nconfigs with POSITIVE skill surviving Bonferroni (p_bonf<0.05): {len(sig)}")
sign=[r for r in sig if r['netR']>0]
print(f"  ...and net-positive after costs: {len(sign)}")
for r in sorted(sign,key=lambda x:-x['netR'])[:10]:
    print(f"   {r['sym']} {r['sig']} flip{r['flip']} {r['tgt']}/{r['stp']} N{r['N']} top{r['top']} "
          f"n={r['n']} WR={r['wr']:.2f}% edge={r['edge']:+.2f} netR={r['netR']:+.4f} p={r['pb']:.5f}")
