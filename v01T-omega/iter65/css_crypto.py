"""
iter65: CSS v10.0 applied to CRYPTO. The user is right that this is the correct frame.

WHY IT IS DIFFERENT FROM EVERYTHING I TRIED BEFORE:
  iter1-64 predicted the NEXT MINUTE / NEXT BAR - a coin flip with an edge of
  basis points. CSS predicts a TERMINAL EVENT - an asset going to zero.
  You do not need 43,200 trades. You need THREE per month.

THE ARITHMETIC (this is the answer to "where's leverage?"):
     3 collapses/month at 95% capture = (1.95)^3 - 1 = +641%   AT 1x LEVERAGE
     4 collapses/month at 90% capture = (1.90)^4 - 1 = +1,203% AT 1x
  NO LEVERAGE NEEDED. This is the only structure I have found in 65 iterations
  that reaches >500%/mo without leverage.

CSS TIER 4 = MANDATORY ABSENCE. For crypto the mandatory flows are:
  L35  GitHub commits   - a live chain MUST ship code (security patches)
  L34  On-chain flow    - a live chain MUST produce blocks/transactions
  L26  Legal existence  - a live foundation MUST pay to exist
  L36  Team exodus      - devs leave before the public knows
  L29  Digital ghosting - website/docs decay

THE TEST THAT DECIDES IT (this is what I must not fake):
  Did the ABSENCE happen BEFORE the price collapse? If the code died after the
  price died, it is a lagging indicator and worthless.

DATA: GitHub REST API (live, real, free) + Bitfinex 1m history 2017-2021 (real).
"""
import json, subprocess, glob, datetime as dt, statistics as st

TOK=subprocess.run(['gh','auth','token'],capture_output=True,text=True).stdout.strip()

def gh(path):
    import urllib.request
    r=urllib.request.Request('https://api.github.com'+path,
        headers={'Authorization':'token '+TOK,'Accept':'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(r,timeout=20) as f: return json.load(f)
    except Exception as e: return None

# Map Bitfinex symbol -> its canonical repo
REPOS={'EOS':'EOSIO/eos','BSV':'bitcoin-sv/bitcoin-sv','IOT':'iotaledger/iri',
       'XTZ':'tezos/tezos','TRX':'tronprotocol/java-tron','NEO':'neo-project/neo',
       'XLM':'stellar/stellar-core','LTC':'litecoin-project/litecoin',
       'ETC':'ethereum/go-ethereum','XMR':'monero-project/monero',
       'BTC':'bitcoin/bitcoin','ETH':'ethereum/go-ethereum','XRP':'XRPLF/rippled'}

print("="*96)
print("SIGNAL LAYER 35 (GitHub abandonment) - LIVE, REAL, 2026")
print("="*96)
print(f"{'symbol':<7}{'repo':<30}{'last push':<13}{'days dead':>10}{'issues':>8}  {'L35 SCORE':>10}")
today=dt.datetime(2026,8,3)
live={}
for sym,repo in REPOS.items():
    d=gh('/repos/'+repo)
    if not d: print(f"{sym:<7}{repo:<30}{'ERR':<13}"); continue
    lp=dt.datetime.strptime(d['pushed_at'][:10],'%Y-%m-%d')
    dead=(today-lp).days
    iss=d['open_issues_count']
    # CSS L35 scoring
    if dead>90 and iss>50: s35=0.35
    elif dead>90: s35=0.20
    else: s35=0.0
    live[sym]=(repo,lp,dead,iss,s35)
    print(f"{sym:<7}{repo:<30}{d['pushed_at'][:10]:<13}{dead:>10}{iss:>8}  {s35:>10.2f}")

print()
print("="*96)
print("THE DECIDING TEST: did the ABSENCE lead the PRICE COLLAPSE?")
print("="*96)
print("EOSIO/eos last commit 2022-07-27. If CSS is real, EOS price should have")
print("kept falling AFTER that date - i.e. the signal was tradable in advance.")
print()

def load_daily(sym):
    rows={}
    for f in sorted(glob.glob(f'/tmp/v7/fromBitFinex/{sym}/*.csv')):
        with open(f) as fh:
            fh.readline()
            for line in fh:
                p=line.strip().split('\t')
                if len(p)<6: continue
                try:
                    t=int(p[0]); c=float(p[2])
                    rows[dt.datetime.utcfromtimestamp(t/1000).strftime('%Y-%m-%d')]=c
                except: pass
    return sorted(rows.items())

for sym in ('EOS','BSV','IOT','XTZ'):
    ser=load_daily(sym)
    if len(ser)<100: 
        print(f"  {sym}: no price history"); continue
    first,last=ser[0],ser[-1]
    peak=max(ser,key=lambda x:x[1])
    dd=(last[1]-peak[1])/peak[1]*100
    print(f"  {sym:<5} {first[0]} ${first[1]:<10.4f} -> {last[0]} ${last[1]:<10.4f}   "
          f"peak ${peak[1]:.4f} on {peak[0]}   from peak {dd:+.1f}%")
print()
print("NOTE: my Bitfinex history ENDS 2021-03. EOS's GitHub died 2022-07 - AFTER")
print("my price data ends. So I CANNOT test the lead/lag on EOS with this data.")
print("Stating that plainly instead of pretending. Need 2021-2026 prices.")
