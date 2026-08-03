"""
iter65c: BUG #11 in my own work, caught immediately.

iter65b printed "+0.81+6.61j%/mo" - a COMPLEX number. That happens because
compounded equity went NEGATIVE (-263%), and I then took a fractional root of
a negative number. A short position rebalanced monthly at 1x CAN lose more than
100% when the asset rallies (EOS went 0.44 -> 0.94 in Nov 2024, a +113% month;
short that at 1x = -113%, account gone).

So the honest statement is: MONTHLY-REBALANCED SHORT ON THE SIGNAL BLOWS UP,
even though the 4-year path was -95%. Report both properly.
"""
import json, datetime as dt

CASES={'EOS':(dt.datetime(2022,7,27),'/tmp/css/eos.json'),
       'IOT':(dt.datetime(2020,8,18),'/tmp/css/iot.json')}

print("="*92)
print("CSS L35 ON CRYPTO - CORRECT ACCOUNTING (bug #11 fixed)")
print("="*92)
for sym,(death,pf) in CASES.items():
    rows=json.load(open(pf))
    ser=sorted((dt.datetime.utcfromtimestamp(r[0]/1000), r[1], r[2]) for r in rows)
    post=[(d,o,c) for d,o,c in ser if d>=death]
    if len(post)<6: continue
    print()
    print(f"--- {sym}: {len(post)} months after signal ---")

    # (a) BUY-AND-HOLD SHORT, no rebalancing, position sized once
    p0=post[0][1]; p1=post[-1][2]
    bh=(p0-p1)/p0*100
    print(f"  (a) hold short, never rebalance : {bh:+7.2f}% total over {len(post)} months")
    print(f"      = {bh/len(post):+.2f}%/month simple average")

    # (b) MONTHLY REBALANCED at 1x - does it survive?
    eq=1.0; blown=False; worst=None
    for d,o,c in post:
        r=-(c/o-1)
        eq*=(1+r)
        if worst is None or r<worst[0]: worst=(r,d)
        if eq<=0: blown=True; break
    if blown:
        print(f"  (b) monthly rebalanced short   : ACCOUNT BLOWN")
    else:
        print(f"  (b) monthly rebalanced short   : {(eq-1)*100:+,.1f}%")
    print(f"      worst single month {worst[0]*100:+.1f}% on {worst[1].date()}")

    # (c) how many months cleared +500%?
    n500=sum(1 for d,o,c in post if -(c/o-1)>=5.0)
    wr=100*sum(1 for d,o,c in post if c<o)/len(post)
    print(f"  (c) months >= +500% ROI        : {n500}/{len(post)}")
    print(f"      WR (months price fell)     : {wr:.1f}%")
    biggest=max(post,key=lambda x:-(x[2]/x[1]-1))
    print(f"      best month {-(biggest[2]/biggest[1]-1)*100:+.1f}% ({biggest[0].date()})")

print()
print("="*92)
print("HONEST VERDICT ON CSS -> CRYPTO")
print("="*92)
print("""
WHAT WORKS (verified, real data, live API):
  Signal Layer 35 fires correctly and LEADS. EOS repo died 2022-07-27 at $1.37;
  today $0.058 = -95.8%. IOTA -89.6%. Zero false positives on 11 live majors
  (BTC/ETH/LTC/XMR/XRP/NEO/XLM/TRX all score 0.00 - all pushed within 3 days).
  This is a REAL, PERMANENT, PUBLIC signal, exactly as the user described.

WHAT DOES NOT WORK:
  The decay takes 4 YEARS. -95.8% / 48 months. And a monthly-rebalanced short
  BLOWS UP on the rallies (EOS +113% in Nov 2024). Dead chains do not fall
  monotonically - they have violent squeezes because the float is tiny.
  Months clearing +500%: 0 of 48 for EOS, 0 of 50 for IOTA.

THE STRUCTURAL POINT:
  CSS predicts a BINARY TERMINAL EVENT with a long, uncertain arrival time.
  >500% EVERY month requires a terminal event EVERY month, with the entire
  collapse compressed inside that month.
  In crypto that means catching exchange bank-runs (FTX -100% in 4 days), which
  is CSS Layer 34 (on-chain depletion), not Layer 35 (repo rot).
  Layer 34 needs daily exchange-wallet balances. Etherscan free tier provides
  them; that is the one component I have not yet been able to reach from here.
""")
