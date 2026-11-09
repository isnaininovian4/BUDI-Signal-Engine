# BUDI SIGNAL ENGINE V3.3 – Historical Data Lab

Mempertahankan fondasi V3.2 dan menambahkan impor data historis harian melalui `yfinance`.

## Perubahan V3.3
- Mode CSV tetap tersedia.
- Mode Data Historis (Yahoo Finance) untuk mencoba mengunduh candle harian ticker IDX dengan akhiran `.JK`.
- Default watchlist: PTRO, BULL, BMRI, SOCI, SAMI.
- Pilihan periode 3 bulan, 6 bulan, 1 tahun, atau 2 tahun.
- Validasi OHLCV menggunakan data engine yang sudah ada.
- Unduh hasil data menjadi CSV.
- Jurnal paper trading tetap lokal; tidak ada order broker.

## Peringatan sumber data
Data diambil dari Yahoo Finance melalui library yfinance. Ini BUKAN data feed resmi BEI dan bukan jaminan real-time. Ketersediaan tiap ticker, kelengkapan, penyesuaian corporate action, dan keterlambatan dapat berbeda. Library yfinance menyatakan tidak berafiliasi dengan Yahoo dan ditujukan untuk riset/edukasi; pengguna harus memeriksa ketentuan Yahoo dan hak penggunaan data. Jangan mengandalkan data ini untuk keputusan transaksi atau mendistribusikannya ulang.

Untuk produksi atau penggunaan pasar aktual, gunakan vendor data yang memiliki hak distribusi dan layanan sesuai kebutuhan, misalnya IDX Data Services atau vendor berlisensi. Update halaman 60 detik tidak menjadikan data historis sebagai feed real-time.

## Cara menjalankan Windows
Ekstrak ZIP, buka CMD di folder `BUDI_SIGNAL_ENGINE_V3_3`, lalu:

```cmd
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Buka `http://localhost:8501`.

## Cara mengambil data historis
1. Pilih mode `Data Historis (Yahoo Finance)` di sidebar.
2. Pilih ticker dan periode.
3. Klik `Ambil data historis`.
4. Periksa daftar data, audit, tanggal terakhir, dan peringatan ticker yang gagal.
5. Unduh CSV untuk arsip bila diperlukan.

Jika koneksi gagal, periksa internet dan coba lagi nanti. Ticker yang tidak tersedia tidak boleh diganti dengan data sintetis seolah-olah aktual.

## Format data
`Date,Ticker,Open,High,Low,Close,Volume`

## Uji dan batasan
- Data yang diambil adalah candle harian, bukan streaming 1-menit.
- Tidak ada koneksi Stockbit atau broker.
- Sinyal hanya untuk pembelajaran/simulasi; tidak menjamin hasil.
- P/L paper trading belum memasukkan semua pajak, slippage, antrean, fraksi harga, dan corporate action.
- Jangan memasukkan API key atau password ke kode.
