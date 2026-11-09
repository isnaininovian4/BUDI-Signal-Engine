import pandas as pd

def run_long_only_backtest(df: pd.DataFrame, fee_pct: float = 0.0015,
                           atr_multiple: float = 1.5, reward_multiple: float = 2.0):
    """
    Conservative long-only bar backtest.
    Entry: next bar open after BUY. Exit: SELL signal at next bar open,
    or stop/target intrabar. If stop and target both touched, stop wins.
    Gap-through stops are filled at bar open (worse price), not stop price.
    """
    trades = []
    for ticker, group in df.groupby("Ticker"):
        g = group.sort_values("Date").reset_index(drop=True)
        in_pos = False
        entry = stop = target = None
        entry_date = None

        for i in range(1, len(g)):
            prev, bar = g.iloc[i-1], g.iloc[i]
            if in_pos:
                exit_price, reason = None, None
                if prev.get("Signal") == "SELL":
                    exit_price, reason = float(bar["Open"]), "SELL_SIGNAL_NEXT_OPEN"
                elif float(bar["Open"]) <= stop:
                    exit_price, reason = float(bar["Open"]), "GAP_STOP"
                elif float(bar["Open"]) >= target:
                    exit_price, reason = target, "GAP_TARGET"
                elif float(bar["Low"]) <= stop:
                    exit_price, reason = stop, "STOP"
                elif float(bar["High"]) >= target:
                    exit_price, reason = target, "TARGET"

                if exit_price is not None:
                    net = ((exit_price-entry)/entry) - (2*fee_pct)
                    trades.append({
                        "Ticker":ticker, "Entry_Date":entry_date, "Exit_Date":bar["Date"],
                        "Entry":entry, "Exit":exit_price, "Exit_Reason":reason,
                        "Return_Pct":net*100
                    })
                    in_pos = False

            if not in_pos and prev.get("Signal") == "BUY":
                atr = prev.get("ATR14")
                if pd.notna(atr) and float(atr) > 0:
                    entry = float(bar["Open"])
                    stop = entry - atr_multiple*float(atr)
                    target = entry + reward_multiple*atr_multiple*float(atr)
                    entry_date = bar["Date"]
                    in_pos = True

        if in_pos:
            bar = g.iloc[-1]
            net = ((float(bar["Close"])-entry)/entry) - (2*fee_pct)
            trades.append({
                "Ticker":ticker, "Entry_Date":entry_date, "Exit_Date":bar["Date"],
                "Entry":entry, "Exit":float(bar["Close"]), "Exit_Reason":"END_OF_DATA",
                "Return_Pct":net*100
            })

    result = pd.DataFrame(trades)
    if result.empty:
        summary = {"Trades":0,"Win_Rate_Pct":0.0,"Average_Return_Pct":0.0,"Total_Return_Pct":0.0}
    else:
        summary = {
            "Trades":int(len(result)),
            "Win_Rate_Pct":round(float((result["Return_Pct"]>0).mean()*100),2),
            "Average_Return_Pct":round(float(result["Return_Pct"].mean()),3),
            "Total_Return_Pct":round(float(((1+result["Return_Pct"]/100).prod()-1)*100),3)
        }
    return result, summary
