"""
Provider adapter placeholder.
The UI refresh interval does not create live market data.
Configure a licensed/authorized BEI data vendor before enabling live quotes.
"""
class LiveFeedNotConfigured(RuntimeError):
    pass

def fetch_latest_ohlcv(tickers):
    raise LiveFeedNotConfigured(
        "Feed online belum aktif. Pilih provider data BEI berizin dan siapkan "
        "API endpoint/kredensial sebelum BUDI mengambil harga aktual."
    )
