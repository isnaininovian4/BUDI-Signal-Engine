"""
Historical OHLCV adapter for educational backtesting.
Uses yfinance/Yahoo Finance, not an official IDX feed.
Check Yahoo's terms and data rights before any reuse or redistribution.
"""
from datetime import datetime, timezone
import pandas as pd

DEFAULT_TICKERS = ["PTRO", "BULL", "BMRI", "SOCI", "SAMI"]

class MarketDataError(RuntimeError):
    pass

def fetch_yahoo_daily(tickers=None, period="6mo"):
    try:
        import yfinance as yf
    except ImportError as exc:
        raise MarketDataError("Library yfinance belum terpasang. Jalankan pip install -r requirements.txt.") from exc

    tickers = tickers or DEFAULT_TICKERS
    frames, errors = [], []
    for ticker in tickers:
        symbol = f"{ticker.upper().strip()}.JK"
        try:
            data = yf.download(
                symbol, period=period, interval="1d",
                auto_adjust=False, actions=False, progress=False,
                threads=False, timeout=20, multi_level_index=False
            )
            if data is None or data.empty:
                errors.append(f"{ticker}: tidak ada data yang dikembalikan")
                continue
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            needed = ["Open", "High", "Low", "Close", "Volume"]
            missing = [c for c in needed if c not in data.columns]
            if missing:
                errors.append(f"{ticker}: kolom hilang {missing}")
                continue
            part = data[needed].copy().reset_index()
            date_col = "Date" if "Date" in part.columns else part.columns[0]
            part = part.rename(columns={date_col: "Date"})
            part["Ticker"] = ticker.upper()
            frames.append(part[["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]])
        except Exception as exc:
            errors.append(f"{ticker}: {type(exc).__name__}: {exc}")

    if not frames:
        raise MarketDataError("Tidak ada data berhasil diunduh. " + " | ".join(errors))
    result = pd.concat(frames, ignore_index=True)
    result["Date"] = pd.to_datetime(result["Date"], errors="coerce")
    result = result.dropna(subset=["Date"]).sort_values(["Ticker", "Date"]).reset_index(drop=True)
    result.attrs["source"] = "Yahoo Finance via yfinance (bukan feed resmi BEI)"
    result.attrs["retrieved_utc"] = datetime.now(timezone.utc).isoformat()
    result.attrs["provider_errors"] = errors
    return result
