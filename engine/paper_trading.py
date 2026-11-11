import uuid
from pathlib import Path
import pandas as pd

LEDGER_PATH = Path("data/paper_trades.csv")
COLUMNS = [
    "Trade_ID", "Ticker", "Entry_Date", "Entry_Price", "Stop_Loss",
    "Take_Profit", "Lots", "Shares", "Status", "Exit_Date",
    "Exit_Price", "Exit_Reason", "Last_Price", "Unrealized_PnL_Rp",
    "Realized_PnL_Rp"
]

def load_ledger(path=LEDGER_PATH):
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(
    path,
    dtype={
        "Trade_ID": "string",
        "Ticker": "string",
        "Entry_Date": "string",
        "Status": "string",
        "Exit_Date": "string",
        "Exit_Reason": "string",
    },
)
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[COLUMNS]

def save_ledger(df, path=LEDGER_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.reindex(columns=COLUMNS).to_csv(path, index=False)

def add_paper_trade(ticker, entry_date, entry_price, stop_loss, take_profit,
                    lots, lot_size=100, path=LEDGER_PATH):
    vals = [entry_price, stop_loss, take_profit]
    if any(float(x) <= 0 for x in vals):
        raise ValueError("Harga entry, stop loss, dan target harus lebih besar dari nol.")
    if not (float(stop_loss) < float(entry_price) < float(take_profit)):
        raise ValueError("Untuk simulasi posisi long, Stop Loss < Entry < Target.")
    if int(lots) < 1:
        raise ValueError("Jumlah lot minimal 1.")
    df = load_ledger(path)
    row = {
        "Trade_ID": uuid.uuid4().hex[:10].upper(),
        "Ticker": str(ticker).upper().strip(),
        "Entry_Date": pd.Timestamp(entry_date).isoformat(),
        "Entry_Price": float(entry_price),
        "Stop_Loss": float(stop_loss),
        "Take_Profit": float(take_profit),
        "Lots": int(lots),
        "Shares": int(lots) * int(lot_size),
        "Status": "OPEN",
        "Exit_Date": "",
        "Exit_Price": pd.NA,
        "Exit_Reason": "",
        "Last_Price": float(entry_price),
        "Unrealized_PnL_Rp": 0.0,
        "Realized_PnL_Rp": pd.NA,
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_ledger(df, path)
    return row["Trade_ID"]

def update_marks(prices, path=LEDGER_PATH):
    df = load_ledger(path)
    if df.empty:
        return df
    for idx, row in df[df["Status"] == "OPEN"].iterrows():
        px = prices.get(str(row["Ticker"]).upper())
        if px is not None and pd.notna(px) and float(px) > 0:
            df.at[idx, "Last_Price"] = float(px)
            df.at[idx, "Unrealized_PnL_Rp"] = (
                (float(px) - float(row["Entry_Price"])) * int(row["Shares"])
            )
    save_ledger(df, path)
    return df

def close_paper_trade(trade_id, exit_price, exit_date=None, reason="MANUAL",
                      path=LEDGER_PATH):
    if float(exit_price) <= 0:
        raise ValueError("Harga keluar harus lebih besar dari nol.")
    df = load_ledger(path)
    mask = (df["Trade_ID"].astype(str) == str(trade_id)) & (df["Status"] == "OPEN")
    if not mask.any():
        raise ValueError("Transaksi OPEN tidak ditemukan.")
    idx = df.index[mask][0]
    pnl = (float(exit_price) - float(df.at[idx, "Entry_Price"])) * int(df.at[idx, "Shares"])
    df.at[idx, "Status"] = "CLOSED"
    df.at[idx, "Exit_Date"] = pd.Timestamp(exit_date or pd.Timestamp.now()).isoformat()
    df.at[idx, "Exit_Price"] = float(exit_price)
    df.at[idx, "Exit_Reason"] = str(reason)
    df.at[idx, "Last_Price"] = float(exit_price)
    df.at[idx, "Unrealized_PnL_Rp"] = 0.0
    df.at[idx, "Realized_PnL_Rp"] = pnl
    save_ledger(df, path)
    return pnl
