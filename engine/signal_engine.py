import math
import pandas as pd

LOT_SIZE = 100  # saham BEI: 1 lot = 100 saham

def build_signals(df: pd.DataFrame, capital: float = 5_000_000,
                  risk_pct: float = 0.02, fee_pct: float = 0.0015,
                  lot_size: int = LOT_SIZE) -> pd.DataFrame:
    """
    Rule-based long-only research signal.
    SELL means exit/avoid long exposure; it does not initiate a short position.
    """
    if capital <= 0 or not 0 < risk_pct <= 0.02:
        raise ValueError("Modal harus > 0 dan risiko harus > 0 sampai maksimum 2%.")
    if lot_size <= 0:
        raise ValueError("lot_size harus positif.")

    results = []
    for ticker, group in df.groupby("Ticker"):
        g = group.sort_values("Date")
        r = g.iloc[-1]
        required = ["MA20", "MA50", "Donchian_Upper", "Donchian_Lower", "RSI14", "ATR14"]
        if any(pd.isna(r.get(k)) for k in required):
            results.append({
                "Ticker": ticker, "Date": r["Date"], "Close": r["Close"],
                "Signal": "WAIT", "Confidence": "Belum cukup data",
                "Reason": "Histori belum cukup untuk indikator MA50/Donchian/ATR."
            })
            continue

        bullish = r["MA20"] > r["MA50"] and r["Close"] > r["MA20"]
        bearish = r["MA20"] < r["MA50"] and r["Close"] < r["MA20"]
        vol_ok = bool(r["Volume_Confirmed"]) if pd.notna(r["Volume_Confirmed"]) else False
        breakout, breakdown = bool(r["Breakout"]), bool(r["Breakdown"])
        sweep_low = bool(r.get("Liquidity_Sweep_Low_Proxy", False))
        sweep_high = bool(r.get("Liquidity_Sweep_High_Proxy", False))
        rsi = float(r["RSI14"])
        signal, confidence = "HOLD", "Rendah"
        reasons = ["Belum ada konfirmasi entry yang cukup."]

        if breakout and bullish and vol_ok and 50 <= rsi <= 70:
            signal, confidence = "BUY", "Menengah"
            reasons = ["Breakout Donchian", "MA20 di atas MA50", "volume >= 1,2x rata-rata 20 bar", "RSI 50–70"]
        elif breakdown and bearish and vol_ok and rsi < 50:
            signal, confidence = "SELL", "Menengah"
            reasons = ["Breakdown Donchian", "MA20 di bawah MA50", "volume >= 1,2x rata-rata 20 bar"]
        elif sweep_low and bullish and vol_ok:
            signal, confidence = "WATCH BUY", "Rendah"
            reasons = ["Sweep low proxy; tunggu konfirmasi struktur dan candle berikutnya"]
        elif sweep_high and bearish and vol_ok:
            signal, confidence = "WATCH SELL", "Rendah"
            reasons = ["Sweep high proxy; tunggu konfirmasi struktur dan candle berikutnya"]
        elif (breakout or breakdown) and not vol_ok:
            signal, confidence = "WAIT", "Rendah"
            reasons = ["Break level belum didukung volume relatif"]

        close, atr = float(r["Close"]), float(r["ATR14"])
        entry = stop = target = rr = shares = lots = risk_cash = value = None
        if signal == "BUY" and atr > 0:
            entry = close  # reference only; execution assumed at next valid price
            stop = entry - 1.5 * atr
            target = entry + 3.0 * atr
            rr = (target-entry)/(entry-stop)
            risk_cash = capital * risk_pct
            risk_per_share = (entry-stop) + (entry * fee_pct * 2)
            raw_shares = min(risk_cash/risk_per_share, capital/(entry*(1+fee_pct)))
            lots = max(0, math.floor(raw_shares/lot_size))
            shares = lots * lot_size
            value = shares * close

        results.append({
            "Ticker": ticker, "Date": r["Date"], "Close": close,
            "Signal": signal, "Confidence": confidence, "Reason": "; ".join(reasons),
            "Entry_Reference": entry, "Stop_Loss": stop, "Take_Profit": target,
            "Risk_Reward": rr, "Risk_Budget_Rp": risk_cash,
            "Estimated_Lots": lots, "Estimated_Shares": shares,
            "Estimated_Value_Rp": value, "Volume_Ratio": r.get("Volume_Ratio"),
            "RSI14": rsi, "MA20": r["MA20"], "MA50": r["MA50"],
            "ICT_Sweep_Low_Proxy": sweep_low, "ICT_Sweep_High_Proxy": sweep_high,
            "SMT_Status": "BELUM DIHITUNG - butuh data benchmark sinkron",
            "Execution_Status": "REFERENSI SIMULASI, BUKAN ORDER"
        })
    return pd.DataFrame(results)

def add_historical_signals(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    valid = out[["MA20","MA50","Donchian_Upper","Donchian_Lower","RSI14","ATR14"]].notna().all(axis=1)
    bullish = (out["MA20"] > out["MA50"]) & (out["Close"] > out["MA20"])
    bearish = (out["MA20"] < out["MA50"]) & (out["Close"] < out["MA20"])
    buy = valid & out["Breakout"].fillna(False) & bullish & out["Volume_Confirmed"].fillna(False) & out["RSI14"].between(50,70)
    sell = valid & out["Breakdown"].fillna(False) & bearish & out["Volume_Confirmed"].fillna(False) & (out["RSI14"] < 50)
    out["Signal"] = "HOLD"
    out.loc[~valid, "Signal"] = "WAIT"
    out.loc[buy, "Signal"] = "BUY"
    out.loc[sell, "Signal"] = "SELL"
    return out
