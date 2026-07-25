"""
Signal helpers — common computations
"""
import pandas as pd
import numpy as np
import logging
logger = logging.getLogger(__name__)

def compute_bollinger_bands(close: pd.Series, window=20, std=2):
    sma = close.rolling(window).mean()
    std_dev = close.rolling(window).std()
    upper = sma + std*std_dev
    lower = sma - std*std_dev
    width = (upper - lower) / sma
    return sma, upper, lower, width

def compute_rsi(close: pd.Series, period=14):
    delta = close.diff()
    gain = delta.where(delta>0,0).rolling(period).mean()
    loss = -delta.where(delta<0,0).rolling(period).mean()
    rs = gain / (loss+1e-10)
    return 100 - (100/(1+rs))

def compute_zscore(series: pd.Series, window=90):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / (std+1e-10)

def detect_divergence(price_a: pd.Series, price_b: pd.Series, window=21):
    # correlation divergence
    corr = price_a.rolling(window).corr(price_b)
    # current corr vs historical mean
    mean_corr = corr.rolling(90).mean()
    z = (corr - mean_corr) / (corr.rolling(90).std()+1e-10)
    return corr, z

def safe_last(series):
    try:
        if series.empty:
            return None
        val = series.iloc[-1]
        if pd.isna(val):
            return None
        return float(val)
    except:
        return None
