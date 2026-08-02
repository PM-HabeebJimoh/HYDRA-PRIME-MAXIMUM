# Cross-exchange direction model — 2026 re-test

The +1,234%/mo (NEO 50x) and +1,398%/mo (LTC 25x) results came from the
CROSS-EXCHANGE DIRECTION model, not the volatility straddle. Iterations 46-47
tested the straddle, which was the wrong system. This directory tests the
right one.

Model: venue A (leader) price/flow predicts venue B (follower) next minute.
Original: Binance -> Bitfinex, 2018-2019, 1-minute, aggressor flags.

2026 data access:
  Binance  api.binance.com  -> HTTP 451 geo-blocked ("restricted location")
  Bitfinex api-pub          -> WORKS via fetch_page
  Kraken   api.kraken.com   -> WORKS via fetch_page, 1m OHLC
  OKX      www.okx.com      -> WORKS via fetch_page, 1m OHLC

So Binance->Bitfinex cannot be reproduced. But the MECHANISM is
"venue A leads venue B", which is testable on any pair. Using
OKX/Kraken -> Bitfinex as the 2026 venue pair.
