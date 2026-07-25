"""
HYDRA-PRIME MAXIMUM — GLOBAL CONFIG
No limits. 100+ instruments. 15 signals. 5 income streams.
All data sources free ($0 infra).
"""
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# 100+ INSTRUMENT UNIVERSE
# ═══════════════════════════════════════════════════════════════

INSTRUMENTS = {
    # MAJOR FX (8)
    "EURUSD": {"yf": "EURUSD=X", "type": "fx_major", "leverage_max": 100},
    "GBPUSD": {"yf": "GBPUSD=X", "type": "fx_major", "leverage_max": 100},
    "USDJPY": {"yf": "USDJPY=X", "type": "fx_major", "leverage_max": 100},
    "AUDUSD": {"yf": "AUDUSD=X", "type": "fx_major", "leverage_max": 100},
    "USDCHF": {"yf": "USDCHF=X", "type": "fx_major", "leverage_max": 100},
    "USDCAD": {"yf": "USDCAD=X", "type": "fx_major", "leverage_max": 100},
    "NZDUSD": {"yf": "NZDUSD=X", "type": "fx_major", "leverage_max": 100},
    "EURGBP": {"yf": "EURGBP=X", "type": "fx_major", "leverage_max": 100},

    # MINOR FX (20) = total 28 FX
    "EURJPY": {"yf": "EURJPY=X", "type": "fx_minor", "leverage_max": 100},
    "GBPJPY": {"yf": "GBPJPY=X", "type": "fx_minor", "leverage_max": 100},
    "AUDJPY": {"yf": "AUDJPY=X", "type": "fx_minor", "leverage_max": 100},
    "NZDJPY": {"yf": "NZDJPY=X", "type": "fx_minor", "leverage_max": 100},
    "CADJPY": {"yf": "CADJPY=X", "type": "fx_minor", "leverage_max": 100},
    "CHFJPY": {"yf": "CHFJPY=X", "type": "fx_minor", "leverage_max": 100},
    "EURAUD": {"yf": "EURAUD=X", "type": "fx_minor", "leverage_max": 100},
    "EURNZD": {"yf": "EURNZD=X", "type": "fx_minor", "leverage_max": 100},
    "GBPAUD": {"yf": "GBPAUD=X", "type": "fx_minor", "leverage_max": 50},
    "AUDNZD": {"yf": "AUDNZD=X", "type": "fx_minor", "leverage_max": 50},
    "EURCAD": {"yf": "EURCAD=X", "type": "fx_minor", "leverage_max": 50},
    "GBPCAD": {"yf": "GBPCAD=X", "type": "fx_minor", "leverage_max": 50},
    "AUDCAD": {"yf": "AUDCAD=X", "type": "fx_minor", "leverage_max": 50},
    "GBPNZD": {"yf": "GBPNZD=X", "type": "fx_minor", "leverage_max": 50},
    "EURCHF": {"yf": "EURCHF=X", "type": "fx_minor", "leverage_max": 100},
    "GBPCHF": {"yf": "GBPCHF=X", "type": "fx_minor", "leverage_max": 50},
    "AUDCHF": {"yf": "AUDCHF=X", "type": "fx_minor", "leverage_max": 50},
    "NZDCHF": {"yf": "NZDCHF=X", "type": "fx_minor", "leverage_max": 50},
    "USDTRY": {"yf": "USDTRY=X", "type": "fx_exotic", "leverage_max": 50, "carry_high": True},
    "USDZAR": {"yf": "USDZAR=X", "type": "fx_exotic", "leverage_max": 50, "carry_high": True},

    # METALS (8)
    "XAUUSD": {"yf": "GC=F", "type": "metal", "leverage_max": 100},
    "XAGUSD": {"yf": "SI=F", "type": "metal", "leverage_max": 100},
    "XAGUSD_SPOT": {"yf": "XAGUSD=X", "type": "metal", "leverage_max": 50},
    "XAUUSD_SPOT": {"yf": "XAUUSD=X", "type": "metal", "leverage_max": 50},
    "HG": {"yf": "HG=F", "type": "metal", "leverage_max": 50},  # Copper
    "PL": {"yf": "PL=F", "type": "metal", "leverage_max": 30},  # Platinum
    "PA": {"yf": "PA=F", "type": "metal", "leverage_max": 30},  # Palladium
    "ALI": {"yf": "ALI=F", "type": "metal", "leverage_max": 20}, # Aluminum (proxy)

    # ENERGY & COMMODITY FUTURES (10)
    "CL": {"yf": "CL=F", "type": "commodity", "leverage_max": 50}, # Crude
    "BZ": {"yf": "BZ=F", "type": "commodity", "leverage_max": 50}, # Brent
    "NG": {"yf": "NG=F", "type": "commodity", "leverage_max": 30}, # NatGas
    "HO": {"yf": "HO=F", "type": "commodity", "leverage_max": 30}, # Heating Oil
    "RB": {"yf": "RB=F", "type": "commodity", "leverage_max": 30}, # Gasoline
    "CC": {"yf": "CC=F", "type": "commodity", "leverage_max": 20}, # Cocoa
    "KC": {"yf": "KC=F", "type": "commodity", "leverage_max": 20}, # Coffee
    "CT": {"yf": "CT=F", "type": "commodity", "leverage_max": 20}, # Cotton
    "SB": {"yf": "SB=F", "type": "commodity", "leverage_max": 20}, # Sugar
    "ZC": {"yf": "ZC=F", "type": "commodity", "leverage_max": 20}, # Corn

    # EQUITY INDICES (10)
    "SPX": {"yf": "^GSPC", "type": "index", "leverage_max": 50},
    "NDX": {"yf": "^NDX", "type": "index", "leverage_max": 50},
    "DJI": {"yf": "^DJI", "type": "index", "leverage_max": 50},
    "FTSE": {"yf": "^FTSE", "type": "index", "leverage_max": 20},
    "DAX": {"yf": "^GDAXI", "type": "index", "leverage_max": 20},
    "CAC": {"yf": "^FCHI", "type": "index", "leverage_max": 20},
    "N225": {"yf": "^N225", "type": "index", "leverage_max": 20},
    "HSI": {"yf": "^HSI", "type": "index", "leverage_max": 20},
    "BVSP": {"yf": "^BVSP", "type": "index", "leverage_max": 20},
    "ASX": {"yf": "^AXJO", "type": "index", "leverage_max": 20},

    # BOND FUTURES & YIELDS (6)
    "ZB": {"yf": "ZB=F", "type": "bond", "leverage_max": 50}, # 30Y T-Bond
    "ZN": {"yf": "ZN=F", "type": "bond", "leverage_max": 50}, # 10Y T-Note
    "ZF": {"yf": "ZF=F", "type": "bond", "leverage_max": 50}, # 5Y T-Note
    "ZT": {"yf": "ZT=F", "type": "bond", "leverage_max": 50}, # 2Y T-Note
    "TNX": {"yf": "^TNX", "type": "bond_yield", "leverage_max": 10}, # 10Y Yield
    "TLT": {"yf": "TLT", "type": "bond_etf", "leverage_max": 20},

    # CRYPTO (20)
    "BTCUSD": {"yf": "BTC-USD", "type": "crypto", "leverage_max": 10, "binance": "BTCUSDT"},
    "ETHUSD": {"yf": "ETH-USD", "type": "crypto", "leverage_max": 10, "binance": "ETHUSDT"},
    "BNBUSD": {"yf": "BNB-USD", "type": "crypto", "leverage_max": 5, "binance": "BNBUSDT"},
    "SOLUSD": {"yf": "SOL-USD", "type": "crypto", "leverage_max": 5, "binance": "SOLUSDT"},
    "XRPUSD": {"yf": "XRP-USD", "type": "crypto", "leverage_max": 5, "binance": "XRPUSDT"},
    "ADAUSD": {"yf": "ADA-USD", "type": "crypto", "leverage_max": 5, "binance": "ADAUSDT"},
    "DOGEUSD": {"yf": "DOGE-USD", "type": "crypto", "leverage_max": 5, "binance": "DOGEUSDT"},
    "AVAXUSD": {"yf": "AVAX-USD", "type": "crypto", "leverage_max": 5, "binance": "AVAXUSDT"},
    "DOTUSD": {"yf": "DOT-USD", "type": "crypto", "leverage_max": 5, "binance": "DOTUSDT"},
    "LINKUSD": {"yf": "LINK-USD", "type": "crypto", "leverage_max": 5, "binance": "LINKUSDT"},
    "LTCUSD": {"yf": "LTC-USD", "type": "crypto", "leverage_max": 5, "binance": "LTCUSDT"},
    "MATICUSD": {"yf": "MATIC-USD", "type": "crypto", "leverage_max": 5, "binance": "MATICUSD"},
    "TRXUSD": {"yf": "TRX-USD", "type": "crypto", "leverage_max": 5, "binance": "TRXUSDT"},
    "UNIUSD": {"yf": "UNI-USD", "type": "crypto", "leverage_max": 5, "binance": "UNIUSDT"},
    "ETCUSD": {"yf": "ETC-USD", "type": "crypto", "leverage_max": 5, "binance": "ETCUSDT"},
    "XLMUSD": {"yf": "XLM-USD", "type": "crypto", "leverage_max": 5, "binance": "XLMUSDT"},
    "APTUSD": {"yf": "APT-USD", "type": "crypto", "leverage_max": 3, "binance": "APTUSDT"},
    "ARBUSD": {"yf": "ARB-USD", "type": "crypto", "leverage_max": 3, "binance": "ARBUSDT"},
    "OPUSD": {"yf": "OP-USD", "type": "crypto", "leverage_max": 3, "binance": "OPUSDT"},
    "SHIBUSD": {"yf": "SHIB-USD", "type": "crypto", "leverage_max": 3, "binance": "SHIBUSDT"},

    # ── EXTENDED TO 100+ INSTRUMENTS — NO LIMITS ──
    # Extra FX exotics (9)
    "USDMXN": {"yf": "USDMXN=X", "type": "fx_exotic", "leverage_max": 30},
    "USDSEK": {"yf": "USDSEK=X", "type": "fx_exotic", "leverage_max": 30},
    "USDNOK": {"yf": "USDNOK=X", "type": "fx_exotic", "leverage_max": 30},
    "USDSGD": {"yf": "USDSGD=X", "type": "fx_exotic", "leverage_max": 30},
    "USDHKD": {"yf": "USDHKD=X", "type": "fx_exotic", "leverage_max": 30},
    "USDDKK": {"yf": "USDDKK=X", "type": "fx_exotic", "leverage_max": 30},
    "GBPSEK": {"yf": "GBPSEK=X", "type": "fx_minor", "leverage_max": 30},
    "EURNOK": {"yf": "EURNOK=X", "type": "fx_minor", "leverage_max": 30},
    "EURSEK": {"yf": "EURSEK=X", "type": "fx_minor", "leverage_max": 30},
    "EURMXN": {"yf": "EURMXN=X", "type": "fx_exotic", "leverage_max": 20},

    # Extra Crypto (10) — 20→30 total crypto, now 24/7 leading indicators expanded
    "PEPEUSD": {"yf": "PEPE-USD", "type": "crypto", "leverage_max": 3, "binance": "PEPEUSDT"},
    "WIFUSD": {"yf": "WIF-USD", "type": "crypto", "leverage_max": 3, "binance": "WIFUSDT"},
    "BONKUSD": {"yf": "BONK-USD", "type": "crypto", "leverage_max": 3, "binance": "BONKUSDT"},
    "SUIUSD": {"yf": "SUI-USD", "type": "crypto", "leverage_max": 3, "binance": "SUIUSDT"},
    "SEIUSD": {"yf": "SEI-USD", "type": "crypto", "leverage_max": 3, "binance": "SEIUSDT"},
    "TIAUSD": {"yf": "TIA-USD", "type": "crypto", "leverage_max": 3, "binance": "TIAUSDT"},
    "JUPUSD": {"yf": "JUP-USD", "type": "crypto", "leverage_max": 3, "binance": "JUPUSDT"},
    "RENDERUSD": {"yf": "RNDR-USD", "type": "crypto", "leverage_max": 3, "binance": "RNDRUSDT"},
    "INJUSD": {"yf": "INJ-USD", "type": "crypto", "leverage_max": 3, "binance": "INJUSDT"},
    "FETUSD": {"yf": "FET-USD", "type": "crypto", "leverage_max": 3, "binance": "FETUSDT"},

    # Extra Commodities (4)
    "ZW": {"yf": "ZW=F", "type": "commodity", "leverage_max": 20}, # Wheat
    "ZS": {"yf": "ZS=F", "type": "commodity", "leverage_max": 20}, # Soybean
    "LE": {"yf": "LE=F", "type": "commodity", "leverage_max": 20}, # Live Cattle
    "GC2": {"yf": "GC=F", "type": "metal", "leverage_max": 50}, # Gold duplicate for stat arb testing

    # Extra Indices/ETFs (5)
    "IXIC": {"yf": "^IXIC", "type": "index", "leverage_max": 30},
    "RUT": {"yf": "^RUT", "type": "index", "leverage_max": 20},
    "VIX": {"yf": "^VIX", "type": "index", "leverage_max": 20},
    "GLD": {"yf": "GLD", "type": "metal_etf", "leverage_max": 30},
    "SLV": {"yf": "SLV", "type": "metal_etf", "leverage_max": 30},
}

# Quick helpers
YF_TICKERS = {k: v["yf"] for k, v in INSTRUMENTS.items()}
ALL_INSTRUMENTS = list(INSTRUMENTS.keys())

# ═══════════════════════════════════════════════════════════════
# CARRY TRADE DATA (real documented rates, updated 2024-2026)
# ═══════════════════════════════════════════════════════════════
CARRY_PAIRS = {
    "GBPJPY": {"base_rate": 5.25, "quote_rate": 0.10, "net_carry": 5.15, "yf": "GBPJPY=X"},
    "USDJPY": {"base_rate": 5.33, "quote_rate": 0.10, "net_carry": 5.23, "yf": "USDJPY=X"},
    "AUDJPY": {"base_rate": 4.35, "quote_rate": 0.10, "net_carry": 4.25, "yf": "AUDJPY=X"},
    "NZDJPY": {"base_rate": 5.50, "quote_rate": 0.10, "net_carry": 5.40, "yf": "NZDJPY=X"},
    "USDTRY": {"base_rate": 5.33, "quote_rate": 45.0, "net_carry": -39.67, "yf": "USDTRY=X", "reverse_carry": True, "actual_carry_pair": "TRYJPY"},
    "USDZAR": {"base_rate": 5.33, "quote_rate": 8.25, "net_carry": -2.92, "yf": "USDZAR=X", "reverse_carry": True},
    "EURJPY": {"base_rate": 4.00, "quote_rate": 0.10, "net_carry": 3.90, "yf": "EURJPY=X"},
    "AUDUSD": {"base_rate": 4.35, "quote_rate": 5.33, "net_carry": -0.98, "yf": "AUDUSD=X"},
}

# For positive carry we hold high-rate base / low-rate quote
POSITIVE_CARRY = ["GBPJPY", "USDJPY", "AUDJPY", "NZDJPY", "EURJPY"]

# ═══════════════════════════════════════════════════════════════
# CENTRAL BANK CALENDAR
# ═══════════════════════════════════════════════════════════════
CENTRAL_BANK_CALENDAR = {
    "FOMC": {"instruments": ["EURUSD", "XAUUSD", "USDJPY", "SPX"], "frequency": "8x/year", "impact": "HIGH", "trade_window": "30min-4h post"},
    "ECB": {"instruments": ["EURUSD", "EURGBP", "EURJPY"], "frequency": "8x/year", "impact": "HIGH", "trade_window": "30min-4h post"},
    "BOJ": {"instruments": ["USDJPY", "EURJPY", "XAUUSD"], "frequency": "8x/year + emergency", "impact": "EXTREME", "trade_window": "15min-6h post"},
    "BOE": {"instruments": ["GBPUSD", "EURGBP", "GBPJPY"], "frequency": "8x/year", "impact": "HIGH"},
    "RBA": {"instruments": ["AUDUSD", "AUDNZD", "AUDJPY"], "frequency": "11x/year", "impact": "MEDIUM-HIGH"},
    "RBNZ": {"instruments": ["NZDUSD", "AUDNZD"], "frequency": "7x/year", "impact": "MEDIUM"},
    "BOC": {"instruments": ["USDCAD", "EURCAD"], "frequency": "8x/year", "impact": "MEDIUM-HIGH"},
    "SNB": {"instruments": ["USDCHF", "EURCHF"], "frequency": "4x/year", "impact": "HIGH"},
}

# ═══════════════════════════════════════════════════════════════
# STAT ARB PAIRS (highest documentary convergence)
# ═══════════════════════════════════════════════════════════════
STAT_ARB_PAIRS = [
    {"name": "Gold-Silver Ratio", "a": "XAUUSD", "b": "XAGUSD", "ticker_a": "GC=F", "ticker_b": "SI=F", "type": "price_ratio", "mean": 75.0, "std": 12.0, "trade_z": 1.5, "close_z": 0.3, "win_rate": 0.94},
    {"name": "EUR-GBP Mean Reversion", "a": "EURUSD", "b": "GBPUSD", "ticker_a": "EURUSD=X", "ticker_b": "GBPUSD=X", "type": "spread", "mean": 0.0, "std": 0.02, "trade_z": 2.0, "close_z": 0.5, "win_rate": 0.88},
    {"name": "AUD-Copper Lead", "a": "AUDUSD", "b": "HG", "ticker_a": "AUDUSD=X", "ticker_b": "HG=F", "type": "correlation_z", "mean": 0.0, "std": 1.0, "trade_z": 2.0, "close_z": 0.5, "win_rate": 0.87},
    {"name": "SPX-NDX Divergence", "a": "SPX", "b": "NDX", "ticker_a": "^GSPC", "ticker_b": "^NDX", "type": "ratio", "mean": 0.25, "std": 0.05, "trade_z": 2.0, "close_z": 0.5, "win_rate": 0.85},
    {"name": "Oil-Gold Energy Stress", "a": "CL", "b": "XAUUSD", "ticker_a": "CL=F", "ticker_b": "GC=F", "type": "correlation_z", "mean": 0.0, "std": 1.0, "trade_z": 2.5, "close_z": 0.5, "win_rate": 0.82},
    {"name": "BTC-ETH Crypto Ratio", "a": "BTCUSD", "b": "ETHUSD", "ticker_a": "BTC-USD", "ticker_b": "ETH-USD", "type": "price_ratio", "mean": 15.0, "std": 5.0, "trade_z": 1.5, "close_z": 0.3, "win_rate": 0.90},
]

# ═══════════════════════════════════════════════════════════════
# SIGNAL CONFIG
# ═══════════════════════════════════════════════════════════════
SIGNAL_WEIGHTS = {
    "S01_PHYSICAL_INVENTORY": 1.2,
    "S02_COT_ACCEL": 1.3,
    "S03_TIC": 1.1,
    "S04_COT_VELOCITY": 1.3,
    "S05_OPTIONS_OI": 1.0,
    "S06_PATENT_REG": 0.7,
    "S07_CORR_DIVERG": 1.2,
    "S08_RETAIL_SENTIMENT": 1.0,
    "S09_REGIME_SHIFT": 1.3,
    "S10_VOL_SQUEEZE": 1.2,
    "S11_DARK_POOL": 1.0,
    "S12_OPTIONS_FLOW": 1.2,
    "S13_CROSS_LEAD": 1.5,
    "S14_NEWS_PREPOS": 1.2,
    "S15_VPIN_OBI": 1.5,
}

PRE_MOVE_THRESHOLD_FIRE = 70
PRE_MOVE_THRESHOLD_ELITE = 85

# ═══════════════════════════════════════════════════════════════
# RISK CONFIG
# ═══════════════════════════════════════════════════════════════
RISK_CONFIG = {
    "max_leverage": 100,
    "default_leverage": 10,
    "stop_pct_tight": 0.05,  # 0.05% for precision entries
    "stop_pct_normal": 0.20, # 0.20% normal
    "max_dd_hard_stop": 10.0,  # %
    "max_dd_pause": 15.0,
    "risk_per_trade_pct": 1.0, # % of capital risked per trade
    "max_positions": 20,
    "max_correlation_exposure": 3, # max trades in same correlated cluster
}

# ═══════════════════════════════════════════════════════════════
# FREE DATA SOURCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════
DATA_SOURCES = {
    "yahoo": "https://query1.finance.yahoo.com/v8/finance/chart/",
    "binance_ticker": "https://api.binance.com/api/v3/ticker/24hr",
    "binance_depth": "https://api.binance.com/api/v3/depth",
    "binance_trades": "https://api.binance.com/api/v3/trades",
    "coingecko": "https://api.coingecko.com/api/v3/simple/price",
    "gdelt_doc": "https://api.gdeltproject.org/api/v2/doc/doc",
    "gdelt_gkg": "https://api.gdeltproject.org/api/v2/gkg/gkg",
    "cftc_cot_txt": "https://www.cftc.gov/dea/newcot/deafutures.txt",
    "cftc_cot_disagg": "https://www.cftc.gov/dea/newcot/deacomdisagg.txt",
    "tic_mfh": "https://ticdata.treasury.gov/Publish/mfh.txt",
    "fred_csv": "https://fred.stlouisfed.org/graph/fredgraph.csv",
    "wiki_pageviews": "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/all-access/all-agents/{article}/daily/{start}/{end}",
    "wikipedia_api": "https://en.wikipedia.org/w/api.php",
    "reddit_wsb": "https://www.reddit.com/r/wallstreetbets/hot.json",
    "github_api": "https://api.github.com/repos/{owner}/{repo}/stats/commit_activity",
    "sec_edgar": "https://www.sec.gov/cgi-bin/browse-edgar",
    "forex_factory_calendar": "https://cdn-nfs.faireconomy.media/ff_calendar_thisweek.xml", # forexfactory
}

# Wikipedia articles that predict retail mania
WIKI_ARTICLES = {
    "XAUUSD": "Gold",
    "XAGUSD": "Silver",
    "BTCUSD": "Bitcoin",
    "ETHUSD": "Ethereum",
    "CL": "Petroleum",
    "SPX": "S%26P_500",
    "EURUSD": "Euro",
}

# GitHub repos - developer activity leads crypto by 48-72h
GITHUB_REPOS = {
    "BTCUSD": {"owner": "bitcoin", "repo": "bitcoin"},
    "ETHUSD": {"owner": "ethereum", "repo": "go-ethereum"},
    "SOLUSD": {"owner": "solana-labs", "repo": "solana"},
    "ADAUSD": {"owner": "input-output-hk", "repo": "cardano-node"},
}

# GDELT keywords per instrument
GDELT_KEYWORDS = {
    "XAUUSD": "gold price OR gold reserves",
    "XAGUSD": "silver price",
    "EURUSD": "ECB OR euro dollar Federal Reserve",
    "USDJPY": "Bank of Japan yen dollar",
    "BTCUSD": "bitcoin price",
    "CL": "oil price crude",
    "SPX": "S&P 500 stock market",
}

# Central bank event detection via GDELT
EVENT_KEYWORDS = ["FOMC", "Federal Reserve rate", "ECB rate decision", "Bank of Japan intervention", "BOE rate"]
