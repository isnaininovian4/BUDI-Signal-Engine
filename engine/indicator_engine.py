import numpy as np
import pandas as pd

def add_indicators(group: pd.DataFrame) -> pd.DataFrame:
    g = group.sort_values("Date").copy()
    close, high, low, volume = g["Close"], g["High"], g["Low"], g["Volume"]

    g["MA20"] = close.rolling(20, min_periods=20).mean()
    g["MA50"] = close.rolling(50, min_periods=50).mean()
    # Donchian levels use only the 20 completed bars before the current bar.
    g["Donchian_Upper"] = high.shift(1).rolling(20, min_periods=20).max()
    g["Donchian_Lower"] = low.shift(1).rolling(20, min_periods=20).min()
    g["Volume_Avg20_Prev"] = volume.shift(1).rolling(20, min_periods=20).mean()
    g["Volume_Ratio"] = volume / g["Volume_Avg20_Prev"].replace(0, np.nan)

    prev_close = close.shift(1)
    tr = pd.concat([(high-low), (high-prev_close).abs(), (low-prev_close).abs()], axis=1).max(axis=1)
    g["ATR14"] = tr.rolling(14, min_periods=14).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, np.nan)
    g["RSI14"] = 100 - 100/(1+rs)
    g.loc[(loss == 0) & (gain > 0), "RSI14"] = 100
    g.loc[(loss == 0) & (gain == 0), "RSI14"] = 50

    g["Golden_Cross"] = (g["MA20"] > g["MA50"]) & (g["MA20"].shift(1) <= g["MA50"].shift(1))
    g["Death_Cross"] = (g["MA20"] < g["MA50"]) & (g["MA20"].shift(1) >= g["MA50"].shift(1))
    g["Breakout"] = close > g["Donchian_Upper"]
    g["Breakdown"] = close < g["Donchian_Lower"]
    g["Volume_Confirmed"] = g["Volume_Ratio"] >= 1.2

    # ICT-inspired mechanical proxies only; not discretionary ICT/SMT.
    prior_low = low.shift(1).rolling(5, min_periods=5).min()
    prior_high = high.shift(1).rolling(5, min_periods=5).max()
    g["Liquidity_Sweep_Low_Proxy"] = (low < prior_low) & (close > prior_low)
    g["Liquidity_Sweep_High_Proxy"] = (high > prior_high) & (close < prior_high)
    g["BOS_Bullish_Proxy"] = close > prior_high
    g["BOS_Bearish_Proxy"] = close < prior_low
    g["FVG_Bullish_Proxy"] = low > high.shift(2)
    g["FVG_Bearish_Proxy"] = high < low.shift(2)
    g["Displacement_Proxy"] = (close - g["Open"]).abs() > (0.8 * g["ATR14"])
    return g

def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    parts = [add_indicators(g) for _, g in df.groupby("Ticker", sort=False)]
    if not parts:
        raise ValueError("Data kosong.")
    return pd.concat(parts, ignore_index=True).sort_values(["Ticker", "Date"]).reset_index(drop=True)
