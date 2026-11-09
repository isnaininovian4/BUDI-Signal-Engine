import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

from engine.data_engine import load_ohlcv
from engine.indicator_engine import calculate_all
from engine.signal_engine import build_signals, add_historical_signals
from engine.backtest_engine import run_long_only_backtest
from engine.live_feed import fetch_latest_ohlcv, LiveFeedNotConfigured
from engine.yahoo_history import fetch_yahoo_daily, MarketDataError, DEFAULT_TICKERS
from engine.paper_trading import load_ledger, add_paper_trade, update_marks, close_paper_trade

st.set_page_config(page_title="BUDI Signal Engine V3.1", layout="wide")
st.title("BUDI SIGNAL ENGINE V3.3 – Historical Data Lab")
st.caption("CSV + impor historis edukasional + jurnal paper trading lokal. Tidak mengirim order ke broker.")

with st.sidebar:
    st.header("Pengaturan")
    mode = st.radio("Mode", ["Simulator CSV", "Data Historis (Yahoo Finance)"])
    capital = st.number_input("Modal simulasi (Rp)", min_value=100_000, value=5_000_000, step=500_000)
    risk_pct = st.slider("Risiko maksimum per transaksi (%)", 0.25, 2.0, 2.0, 0.25) / 100
    fee_pct = st.number_input("Biaya per sisi (%)", min_value=0.0, max_value=1.0, value=0.15, step=0.01) / 100

if mode == "Data Historis (Yahoo Finance)":
    st.subheader("1. Ambil data historis harian")
    st.warning(
        "Sumber ini adalah Yahoo Finance melalui yfinance, BUKAN feed resmi BEI. "
        "Data dapat tertunda/tidak lengkap dan ditujukan untuk pembelajaran serta backtesting, "
        "bukan sinyal transaksi langsung. Periksa ketentuan penggunaan dan hak data provider."
    )
    selected_tickers = st.multiselect("Pilih saham", DEFAULT_TICKERS, default=DEFAULT_TICKERS)
    period = st.selectbox("Periode historis", ["3mo", "6mo", "1y", "2y"], index=1)
    if st.button("Ambil data historis", type="primary"):
        if not selected_tickers:
            st.error("Pilih minimal satu ticker.")
        else:
            with st.spinner("Mengambil data historis..."):
                try:
                    fetched = fetch_yahoo_daily(selected_tickers, period=period)
                    st.session_state["budi_market_history"] = fetched
                    st.session_state["budi_market_meta"] = {
                        "source": fetched.attrs.get("source", "Yahoo Finance"),
                        "retrieved_utc": fetched.attrs.get("retrieved_utc", ""),
                        "errors": fetched.attrs.get("provider_errors", []),
                    }
                except MarketDataError as exc:
                    st.error(str(exc))
    raw_online = st.session_state.get("budi_market_history")
    if raw_online is None:
        st.info("Klik Ambil data historis untuk memuat data. Koneksi internet diperlukan.")
        st.stop()
    raw, audit = load_ohlcv(raw_online)
    meta = st.session_state.get("budi_market_meta", {})
    st.caption(f"Sumber: {meta.get('source','Yahoo Finance')} | Diambil (UTC): {meta.get('retrieved_utc','')}")
    if meta.get("errors"):
        st.warning("Sebagian ticker tidak berhasil: " + " | ".join(meta["errors"]))
    st.download_button("Unduh data historis CSV", raw.to_csv(index=False).encode("utf-8"),
                       "BUDI_market_history_yahoo.csv", "text/csv")
else:
    st.subheader("1. Unggah data CSV")
    uploaded = st.file_uploader("CSV wajib berisi Date,Ticker,Open,High,Low,Close,Volume", type=["csv"])
    if uploaded is None:
        st.info("Unggah CSV historis. Contoh sintetis tersedia di folder data proyek.")
        st.stop()
    try:
        raw, audit = load_ohlcv(uploaded)
    except Exception as exc:
        st.error(f"Data gagal diproses: {exc}")
        st.stop()

try:
    calc = calculate_all(raw)
    signals = build_signals(calc, capital=capital, risk_pct=risk_pct, fee_pct=fee_pct)
except Exception as exc:
    st.error(f"Data gagal diproses oleh mesin indikator/sinyal: {exc}")
    st.stop()

st.subheader("2. Audit data")
c1,c2,c3,c4 = st.columns(4)
c1.metric("Baris valid", audit["rows"])
c2.metric("Baris ditolak", audit["rejected_rows"])
c3.metric("Duplikat dihapus", audit["duplicates_removed"])
c4.metric("Ticker", len(audit["tickers"]))
st.caption(f"Periode: {audit['first_date'].date()} s.d. {audit['last_date'].date()} | {', '.join(audit['tickers'])}")

st.subheader("3. Sinyal terbaru")
st.dataframe(signals, use_container_width=True, hide_index=True)
st.caption("BUY/SELL adalah label riset. SELL berarti keluar/menghindari posisi long, bukan short selling. ICT masih proxy mekanis; SMT dan foreign flow belum aktif.")

ticker = st.selectbox("Pilih ticker untuk grafik", audit["tickers"])
g = calc[calc["Ticker"] == ticker].sort_values("Date")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=g["Date"], open=g["Open"], high=g["High"], low=g["Low"], close=g["Close"], name="OHLC"))
for col in ["MA20","MA50","Donchian_Upper","Donchian_Lower"]:
    fig.add_trace(go.Scatter(x=g["Date"], y=g[col], name=col))
fig.update_layout(height=560, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

st.subheader("4. Paper Trading – Jurnal Simulasi")
st.warning("Paper trading saja: transaksi dicatat secara lokal dan tidak dikirim ke Stockbit, sekuritas, atau broker.")
ledger = load_ledger()
latest_prices = calc.sort_values("Date").groupby("Ticker").tail(1).set_index("Ticker")["Close"].to_dict()
ledger = update_marks(latest_prices)
with st.expander("Catat posisi simulasi baru", expanded=True):
    choices = audit["tickers"]
    with st.form("paper_trade_form"):
        p1, p2, p3 = st.columns(3)
        pticker = p1.selectbox("Ticker", choices)
        pentry = p2.number_input("Harga entry simulasi", min_value=0.01, value=float(latest_prices.get(choices[0], 100.0)), step=1.0)
        plots = p3.number_input("Jumlah lot", min_value=1, value=1, step=1)
        p4, p5 = st.columns(2)
        pstop = p4.number_input("Stop loss", min_value=0.01, value=max(0.01, float(pentry)*0.97), step=1.0)
        ptarget = p5.number_input("Target", min_value=0.02, value=float(pentry)*1.05, step=1.0)
        pdate = st.date_input("Tanggal entry")
        submitted = st.form_submit_button("Simpan paper trade")
        if submitted:
            try:
                trade_id = add_paper_trade(pticker, pdate, pentry, pstop, ptarget, plots)
                st.success(f"Paper trade tersimpan. ID: {trade_id}")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

ledger = load_ledger()
if not ledger.empty:
    st.dataframe(ledger, use_container_width=True, hide_index=True)
    open_trades = ledger[ledger["Status"] == "OPEN"]
    if not open_trades.empty:
        st.markdown("**Tutup posisi simulasi secara manual**")
        with st.form("close_paper_trade_form"):
            selected_id = st.selectbox("Pilih ID transaksi", open_trades["Trade_ID"].astype(str).tolist())
            selected_row = open_trades[open_trades["Trade_ID"].astype(str) == selected_id].iloc[0]
            exit_px = st.number_input("Harga keluar simulasi", min_value=0.01,
                                      value=float(latest_prices.get(str(selected_row["Ticker"]), selected_row["Last_Price"])),
                                      step=1.0)
            exit_reason = st.selectbox("Alasan keluar", ["MANUAL", "STOP_LOSS", "TAKE_PROFIT", "ATURAN_STRATEGI"])
            close_submit = st.form_submit_button("Tutup paper trade")
            if close_submit:
                try:
                    pnl = close_paper_trade(selected_id, exit_px, reason=exit_reason)
                    st.success(f"Posisi simulasi ditutup. P/L kotor: Rp {pnl:,.0f}")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    st.download_button("Unduh jurnal paper trading CSV", ledger.to_csv(index=False).encode("utf-8"),
                       "BUDI_paper_trading_ledger.csv", "text/csv")
else:
    st.info("Belum ada paper trade. Catat posisi simulasi untuk mulai menguji disiplin entry dan exit.")

st.subheader("5. Backtest long-only")
st.caption("Entry pada open bar berikutnya. Stop/target intrabar; jika keduanya tersentuh dalam satu candle, stop diasumsikan lebih dahulu. Biaya dua sisi dihitung sederhana; pajak, slippage, antrean, fraksi harga dan corporate action belum dimodelkan.")
history = add_historical_signals(calc)
trades, summary = run_long_only_backtest(history, fee_pct=fee_pct)
b1,b2,b3,b4 = st.columns(4)
b1.metric("Transaksi", summary["Trades"])
b2.metric("Win rate", f'{summary["Win_Rate_Pct"]:.2f}%')
b3.metric("Rata-rata return", f'{summary["Average_Return_Pct"]:.3f}%')
b4.metric("Compounded return", f'{summary["Total_Return_Pct"]:.3f}%')
if not trades.empty:
    st.dataframe(trades, use_container_width=True, hide_index=True)
else:
    st.info("Belum ada transaksi berdasarkan aturan saat ini.")

st.download_button("Unduh indikator CSV", calc.to_csv(index=False).encode("utf-8"), f"BUDI_indicators_{ticker}.csv", "text/csv")
st.download_button("Unduh sinyal CSV", signals.to_csv(index=False).encode("utf-8"), "BUDI_signals.csv", "text/csv")
st.download_button("Unduh backtest CSV", trades.to_csv(index=False).encode("utf-8"), "BUDI_backtest.csv", "text/csv")
st.error("Data contoh sintetis bukan harga BEI. Jangan gunakan untuk keputusan transaksi riil.")
