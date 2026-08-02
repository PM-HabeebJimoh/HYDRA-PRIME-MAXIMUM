"""HONEST SCOPE STATEMENT for the 2026 re-verification.

The volatility-magnitude system (iter35/36) was built and validated on:
  - 13 Bitfinex SPOT instruments, 1-minute bars, 2018-2021 (95.3 months)
  - 24 features, 6-fold walk-forward, OOS corr 0.2150
  - market-neutral cross-sectional vol spread
  - result: WR 63.17%, DD 4.00%, +49.65%/month

To re-verify on 2026 I need the SAME 13-instrument cross-section in 2026.
What is actually reachable from this sandbox:
  - bash egress to exchange APIs: BLOCKED (TLS EOF on every attempt)
  - fetch_page to Bitfinex API:   WORKS, but returns ~1500 bars per call
  - 2026 PERP data exists:        XLM/BTC confirmed, Jan-Aug 2026

The cross-sectional spread REQUIRES many instruments quoted at the same
timestamp. Pulling 13 instruments x 2026 at 6h = 13 x ~7 chunks = 91 fetches.
That is feasible but each chunk must be manually parsed from markdown.

I have pulled XLM and BTC fully. I will state plainly what that can and
cannot verify rather than pretending a 2-instrument sample re-validates a
13-instrument cross-sectional strategy.
"""
print(__doc__)
