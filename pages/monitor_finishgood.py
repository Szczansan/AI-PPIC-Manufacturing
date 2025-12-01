import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from io import BytesIO
# Pastikan file components/navbar.py ada
from components.navbar import show_navbar 

# --- PAGE CONFIG ---
st.set_page_config(page_title="🏭 Monitor Integrated Stock", layout="wide")

# --- CONNECT SUPABASE ---
# st.secrets harus tersedia saat deployment
url = st.secrets.get("SUPABASE_URL", "URL_NOT_FOUND")
key = st.secrets.get("SUPABASE_KEY", "KEY_NOT_HING")
supabase = create_client(url, key)

# --- NAVBAR (Diaktifkan) ---
show_navbar()

# --- FUNGSI STATUS OTOMATIS ---
def status_label(balance):
    """Fungsi untuk menentukan status stok berdasarkan BALANCE (BAL)"""
    try:
        val = float(balance)
        if val < 0:
            return "🟥 STOCK MINUS"
        elif val >= 0:
            return "🟩 READY DELIVERY"
        else:
            return "⚪ UNKNOWN"
    except:
        return "⚪ UNKNOWN"

# --- FUNGSI AMBIL & GABUNG DATA (Menggunakan View v_stock_balance) ---
# Menggunakan cache_data karena transaksi IN/OUT dilakukan di halaman lain.
@st.cache_data(ttl=60)
def load_integrated_data(date_str):
    """Mengambil data dari forcast, MASTER, dan Saldo Berjalan dari View v_stock_balance."""
    try:
        # 1. LOAD FORCAST data (MENJADI BASE TABLE)
        # Asumsi kolom di forcast: part_no, part_name, delivery_date (huruf kecil)
        res_fc = supabase.table("forcast").select("part_no, part_name, delivery_date").execute()
        df_fc = pd.DataFrame(res_fc.data)

        # Cari nama kolom yang benar (case-insensitive)
        part_name_col = next((col for col in df_fc.columns if col.lower() == 'part_name'), 'PART_NAME')
        part_no_col = next((col for col in df_fc.columns if col.lower() == 'part_no'), 'PART_NO')
        forecast_date_col = next((col for col in df_fc.columns if col.lower() == 'delivery_date'), 'DELIVERY_DATE')

        if part_name_col and part_no_col:
            df_fc = df_fc.rename(columns={part_name_col: 'PART_NAME', part_no_col: 'PART_NO', forecast_date_col: 'FORCAST_DATE_REF'})
            # Base table dari forcast (PART_NO harus unik untuk join)
            df_base = df_fc[['PART_NO', 'PART_NAME', 'FORCAST_DATE_REF']].drop_duplicates(subset=['PART_NO'], keep='first')
        else:
            raise ValueError(f"Kolom Part tidak ditemukan di tabel 'forcast'.")

        # 2. LOAD MASTER data (Untuk SPQ)
        res_master = supabase.table("MASTER").select("part_no, SPQ").execute()
        df_master = pd.DataFrame(res_master.data).rename(columns={'part_no': 'PART_NO'})
        
        # Merge 1: Forecast Base + Master (LEFT JOIN)
        df_merged = pd.merge(df_base, df_master, on="PART_NO", how="left")
        
        # 3. LOAD SALDO BERJALAN dari VIEW (v_stock_balance)
        # Ambil semua saldo dari View HINGGA tanggal yang dipilih.
        # Kolom di view: date, part_no, qty_in_harian, qty_out_harian, balance
        res_view_history = supabase.table("v_stock_balance").select("*").lte("date", date_str).execute()
        df_history = pd.DataFrame(res_view_history.data)
        
        df_final = df_merged.copy() 
        
        if not df_history.empty:
            
            # Ubah nama kolom agar mudah diolah dan dipadankan dengan part_no
            df_history = df_history.rename(columns={'part_no': 'PART_NO', 'date': 'LAST_UPDATE_DATE'})
            
            # --- SOLUSI V23: Konversi Paksa ke DateTime ---
            # Mengatasi error ".dt accessor"
            df_history['LAST_UPDATE_DATE'] = pd.to_datetime(df_history['LAST_UPDATE_DATE'], errors='coerce')
            
            # --- 3.1. Tentukan SALDO TERAKHIR (Latest Running Balance) ---
            # Sort DESCENDING berdasarkan tanggal (untuk mendapatkan baris saldo terbaru)
            df_stock_sorted = df_history.sort_values(
                by=['LAST_UPDATE_DATE'], 
                ascending=False
            )
            
            # Simpan hanya baris PERTAMA per PART_NO untuk mendapatkan 'BALANCE' (BAL) terbaru
            df_stock_latest = df_stock_sorted[['PART_NO', 'balance']].drop_duplicates(subset=['PART_NO'], keep='first')
            df_stock_latest = df_stock_latest.rename(columns={'balance': 'BAL'})
            
            # --- 3.2. Ambil QTY_IN dan QTY_OUT Harian (Hanya di TANGGAL YANG DIPILIH) ---
            # Cari transaksi yang tanggalnya SAMA PERSIS dengan tanggal snapshot
            # Gunakan .strftime('%Y-%m-%d') pada kolom yang sudah menjadi datetime
            df_daily_transactions = df_history[df_history['LAST_UPDATE_DATE'].dt.strftime('%Y-%m-%d') == date_str]
            
            if not df_daily_transactions.empty:
                # Ambil QTY_IN dan QTY_OUT harian
                df_daily_agg = df_daily_transactions.groupby('PART_NO').agg(
                    QTY_IN=('qty_in_harian', 'sum'),
                    QTY_OUT=('qty_out_harian', 'sum')
                ).reset_index()
            else:
                df_daily_agg = pd.DataFrame({'PART_NO': [], 'QTY_IN': [], 'QTY_OUT': []})

            # --- 3.3. Merge Semua Data ---
            
            # Merge 2: Result + Latest Stock Staxte (LEFT JOIN untuk BAL)
            df_final = pd.merge(df_merged, df_stock_latest, on="PART_NO", how="left")
            
            # Merge 3: Result + Daily Transaction (LEFT JOIN untuk QTY IN/OUT)
            df_final = pd.merge(df_final, df_daily_agg, on="PART_NO", how="left")
            
            # Tambahkan kolom LAST_UPDATE (Tanggal Snapshot yang dipilih user)
            df_final['LAST_UPDATE'] = date_str
            
        else:
            # Jika tidak ada riwayat stok sama sekali
            df_final['QTY_IN'] = None
            df_final['QTY_OUT'] = None
            df_final['BAL'] = None
            df_final['LAST_UPDATE'] = None
            
        # --- Post-Merge Cleaning and Column Management ---

        if 'PART_NAME' in df_final.columns:
            df_final = df_final.rename(columns={'PART_NAME': 'PART NAME'})
        if 'PART_NO' in df_final.columns:
            df_final = df_final.rename(columns={'PART_NO': 'PART NO'})
        if 'FORCAST_DATE_REF' in df_final.columns:
            df_final = df_final.rename(columns={'FORCAST_DATE_REF': 'FORCAST DATE'})

        # Terapkan STATUS
        df_final["STATUS"] = df_final["BAL"].apply(status_label)
        
        # Handle MODEL (Set to Empty)
        df_final['MODEL'] = df_final.get('MODEL', '') 
        
        # Fill NaN/Null values for numeric columns after merge 
        numeric_cols = ["QTY_IN", "BAL", "SPQ", "QTY_OUT"]
        for col in numeric_cols:
             if col in df_final.columns:
                 df_final[col] = pd.to_numeric(df_final[col], errors='coerce').fillna(0)
                 
        # Format FORCAST DATE to YYYY:mm (Tahun:Bulan)
        if 'FORCAST DATE' in df_final.columns:
            df_final['FORCAST DATE'] = pd.to_datetime(df_final['FORCAST DATE'], errors='coerce')
            df_final['FORCAST DATE'] = df_final['FORCAST DATE'].dt.strftime('%Y:%m').fillna('N/A')

        # Drop duplicates berdasarkan PART NO (untuk melihat status part unik)
        # Jika forcast date berbeda, kita biarkan saja (seperti sebelumnya)
        df_final = df_final.drop_duplicates(subset=['PART NO', 'FORCAST DATE'], keep='first') 
        
        # Sort by FORCAST DATE and PART NO
        df_final = df_final.sort_values(['FORCAST DATE', 'PART NO'], ascending=[False, True])

        return df_final
        
    except Exception as e:
        st.error(f"Gagal mengambil atau menggabungkan data dari Supabase. Pastikan View 'v_stock_balance' dan tabel 'forcast', 'MASTER' ada. Detail Error: {e}")
        st.stop()
        return pd.DataFrame()

# --- HEADER SECTION ---
st.markdown("""
<div style="background: linear-gradient(90deg,#0f172a,#1e293b);
padding: 12px 16px; border-radius:8px; color:#fff;">
    <h3 style="margin:0;">📊 Integrated Stock & Forecast Monitor</h3>
    <p style="margin:0;font-size:13px;color:#94a3b8;">
        Menggabungkan data perencanaan (Forecast), master, dan stok aktual (fg_in/fg_out).
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")

# --- FILTER CONTROLS ---
col_date, col_status = st.columns([1, 1.5])

with col_date:
    # Filter Tanggal (Tanggal Snapshot)
    today = date.today()
    selected_date = st.date_input("📅 Pilih tanggal snapshot stok", value=today, help="Saldo (BAL) dihitung berdasarkan semua transaksi hingga tanggal ini.")
    selected_date_str = selected_date.strftime("%Y-%m-%d") 
    
# --- LOAD DATA ---
df_integrated = load_integrated_data(selected_date_str)

# --- CEK DATA KOSONG ---
if df_integrated.empty:
    with col_date:
        st.warning(f"📦 Data Part dari Forecast kosong atau View 'v_stock_balance' belum terisi.")
    st.stop()

# --- FILTER STATUS STOK ---
with col_status:
    status_options = ["Semua Status", "🟩 READY DELIVERY", "🟥 STOCK MINUS"]
    selected_status = st.selectbox("🚦 Filter berdasarkan Status Stok", status_options)

# --- SEARCH FILTER ---
search_query = st.text_input("🔍 Cari berdasarkan Part No atau Part Name", value="", help="Ketik Part No atau Part Name untuk memfilter tabel.")


# --- APLIKASIKAN SEMUA FILTER ---
df_filtered = df_integrated.copy()

# 1. Filter Status
if selected_status != "Semua Status":
    df_filtered = df_filtered[df_filtered["STATUS"] == selected_status]

# 2. Filter Search
if search_query:
    df_filtered = df_filtered[
        # Menggunakan kolom dengan spasi: 'PART NO' dan 'PART NAME'
        df_filtered["PART NO"].astype(str).str.contains(search_query, case=False, na=False) |
        df_filtered["PART NAME"].astype(str).str.contains(search_query, case=False, na=False)
    ]

# --- CEK DATA SETELAH FILTER ---
if df_filtered.empty:
    st.warning("Tidak ditemukan data yang cocok dengan kriteria filter.")
    st.stop()
    
# --- FORMAT ANGKA UNTUK TAMPILAN ---
df_display = df_filtered.copy()
# Format QTY dan BAL dengan separator ribuan
for col in ["QTY_IN", "QTY_OUT", "BAL", "SPQ"]:
    if col in df_display.columns:
        # Gunakan '{:,.0f}' untuk menghilangkan desimal dan menambahkan koma
        df_display[col] = df_display[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) and isinstance(x, (int, float)) else x)

# --- RINGKASAN TOTAL ---
# Hitungan total Part unik
total_part = len(df_filtered.drop_duplicates(subset=['PART NO'])) 

# Hitungan Part berdasarkan Status
# 🟥 STOCK MINUS
count_minus = len(df_filtered[df_filtered["STATUS"] == "🟥 STOCK MINUS"].drop_duplicates(subset=['PART NO']))
# 🟩 READY DELIVERY
count_ready = len(df_filtered[df_filtered["STATUS"] == "🟩 READY DELIVERY"].drop_duplicates(subset=['PART NO']))


st.markdown("### 📊 Ringkasan Stok Integrated")
# Menggunakan 3 kolom: Total Part, Count Ready, Count Minus
c1, c2, c3 = st.columns(3) 

with c1:
    st.metric("Total Part", f"{total_part:,}")  
with c2:
    st.metric("Total Ready Delivery", f"🟩 {count_ready:,}")
with c3:
    st.metric("Total Stock Minus", f"🟥 {count_minus:,}")

# --- TAMPILKAN DATA ---
st.markdown("### 📦 Data Integrated STOCK")
# Urutan kolom sesuai permintaan
# LAST_UPDATE sekarang adalah Tanggal Snapshot
display_cols = ["FORCAST DATE", "MODEL", "PART NAME", "PART NO", "SPQ", "QTY_IN", "QTY_OUT", "BAL", "STATUS", "LAST_UPDATE"]
st.dataframe(
    df_display[display_cols],
    use_container_width=True,
    height=500
)

# --- FUNGSI EKSPOR KE EXCEL ---
def convert_df_to_excel(df):
    df_export = df.copy()
    
    # Hapus kolom yang tidak perlu (jika ada) dan pastikan urutan
    export_cols = [col for col in display_cols if col in df_export.columns]
    df_export = df_export[export_cols]

    # Pastikan kolom angka tetap numerik untuk Excel
    numeric_cols = ["QTY_IN", "BAL", "SPQ", "QTY_OUT"]
    for col in numeric_cols:
        if col in df_export.columns:
            # Hilangkan format string untuk eksport ke Excel
            df_export[col] = pd.to_numeric(df_export[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')


    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export.to_excel(writer, index=False, sheet_name="Integrated_Stock")
        workbook = writer.book
        worksheet = writer.sheets["Integrated_Stock"]

        # Atur lebar kolom otomatis
        for i, col in enumerate(df_export.columns):
            max_len = max([len(str(s)) for s in df_export[col].astype(str)]) + 2
            worksheet.set_column(i, i, max_len)
    return output.getvalue()

excel_data = convert_df_to_excel(df_filtered) # Ekspor data yang sudah difilter

# --- DOWNLOAD BUTTON ---
st.download_button(
    label="📤 Export ke Excel",
    data=excel_data,
    file_name=f"Integrated_Stock_{selected_date_str.replace('-', '_')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# --- REFRESH BUTTON ---
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()