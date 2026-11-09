import numpy as np
import pandas as pd

REQUIRED = ["Date", "Ticker", "Open", "High", "Low", "Close", "Volume"]
PRICE_COLS = ["Open", "High", "Low", "Close"]

def load_ohlcv(source):
    """Read and audit daily OHLCV CSV. Returns (clean_dataframe, audit_dict)."""
    df = source.copy() if isinstance(source, pd.DataFrame) else pd.read_csv(source)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {', '.join(missing)}")

    df = df[REQUIRED].copy()
    original_rows = len(df)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Ticker"] = df["Ticker"].astype("string").str.upper().str.strip()
    for col in PRICE_COLS + ["Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    numeric = df[PRICE_COLS + ["Volume"]].to_numpy(dtype=float)
    finite = pd.Series(np.isfinite(numeric).all(axis=1), index=df.index)
    bad_null = df[REQUIRED].isna().any(axis=1)
    bad_ticker = df["Ticker"].eq("") | df["Ticker"].isna()
    bad_ohlc = (
        (df["High"] < df[PRICE_COLS].max(axis=1)) |
        (df["Low"] > df[PRICE_COLS].min(axis=1)) |
        (df["High"] < df["Low"]) |
        (df[PRICE_COLS] <= 0).any(axis=1) |
        (df["Volume"] < 0)
    )
    bad = bad_null | bad_ticker | bad_ohlc | ~finite
    rejected = int(bad.sum())
    df = df.loc[~bad].copy()
    if df.empty:
        raise ValueError("Tidak ada baris OHLCV valid setelah validasi.")

    duplicate_count = int(df.duplicated(["Date", "Ticker"]).sum())
    df = df.drop_duplicates(["Date", "Ticker"], keep="last")
    df = df.sort_values(["Ticker", "Date"]).reset_index(drop=True)

    audit = {
        "rows": len(df), "original_rows": original_rows,
        "rejected_rows": rejected, "duplicates_removed": duplicate_count,
        "tickers": sorted(df["Ticker"].unique().tolist()),
        "first_date": df["Date"].min(), "last_date": df["Date"].max(),
        "data_label": "USER_UPLOADED_CSV",
    }
    return df, audit
