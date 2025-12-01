import streamlit as st
import pandas as pd
from supabase_client import get_supabase

# -----------------------------------------------------------------------------
# 1. KONFIGURASI HALAMAN
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Monitor WIP Stock",
    page_icon="🏭",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. STYLING & NAVBAR
# -----------------------------------------------------------------------------
def show_navbar():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 6rem !important; padding-bottom: 2rem !important; }
        .navbar {
            background: linear-gradient(90deg, #0f172a, #1e293b);
            padding: 0.8rem 1.5rem;
            border-radius: 12px;
            display: flex; justify-content: space-between; align-items: center;
            color: white; margin-bottom: 2rem; border: 1px solid #334155;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .navbar-title { font-size: 1.1rem; font-weight: 700; color: #f8fafc; display: flex; align-items: center; gap: 10px; }
        .navbar-links a { color: #94a3b8; margin-left: 1.5rem; text-decoration: none; font-size: 0.9rem; font-weight: 500; transition: color 0.3s ease; }
        .navbar-links a:hover { color: #38bdf8; }
        .kpi-container {
            background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px;
            display: flex; flex-direction: column; align-items: flex-start;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); height: 100%;
        }
        .kpi-label { font-size: 0.85rem; color: #94a3b8; margin-bottom: 5px; font-weight: 600; text-transform: uppercase; }
        .kpi-value { font-size: 2.2rem; font-weight: 700; color: #f1f5f9; line-height: 1.2; }
        .kpi-delta { font-size: 0.85rem; margin-top: 8px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
        .delta-pos { background-color: rgba(16, 185, 129, 0.1); color: #34d399; }
        .delta-neg { background-color: rgba(239, 68, 68, 0.1); color: #f87171; }
        .delta-neutral { background-color: rgba(59, 130, 246, 0.1); color: #60a5fa; }
        .filter-box { background-color: #162032; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 2rem; }
        .stDataFrame { border: 1px solid #334155; border-radius: 8px; overflow: hidden; }
        </style>
        <div class="navbar">
            <div class="navbar-title"><span>🏭</span> Ecosystem Production</div>
            <div class="navbar-links">
                <a href="/" target="_self">Home</a>
                <a href="/Production_Control" target="_self">Production</a>
                <a href="/ppc" target="_self">PPC</a>
                <a href="/warehouse" target="_self">Warehouse</a>
            </div>
        </div>
    """, unsafe_allow_html=True)
show_navbar()

# -----------------------------------------------------------------------------
# 3. FUNGSI LOAD DATA
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def load_data():
    supabase = get_supabase()
    try:
        # 1. Ambil Data WIP (Semua History)
        response = supabase.table('v_wip_stock_balance').select('*').execute()
        data = response.data
        if not data: return pd.DataFrame()
        df = pd.DataFrame(data)

        # 2. Ambil Data MASTER
        response_master = supabase.table('MASTER').select('part_no, PART_NAME').execute()
        data_master = response_master.data
        
        if data_master:
            df_master = pd.DataFrame(data_master)
            if 'part_no' in df_master.columns and 'PART_NAME' in df_master.columns:
                df_master['part_no'] = df_master['part_no'].astype(str)
                df_master['PART_NAME'] = df_master['PART_NAME'].astype(str)
                # Logic Master: Nama Terpanjang
                df_master['name_len'] = df_master['PART_NAME'].str.len()
                df_master = df_master.sort_values(by='name_len', ascending=False)
                df_master = df_master.drop_duplicates(subset=['part_no'], keep='first')
                df_master = df_master.drop(columns=['name_len'])
            
            if 'part_no' in df.columns:
                df['part_no'] = df['part_no'].astype(str)
                df = pd.merge(df, df_master[['part_no', 'PART_NAME']], on='part_no', how='left')
                if 'part_name' in df.columns:
                    df['PART_NAME'] = df['PART_NAME'].fillna(df['part_name'])
        
        # 3. Mapping Nama Kolom
        column_mapping = {
            'date': 'Date',
            'forecast_date': 'FORECAST DATE',
            'model': 'MODEL',
            'PART_NAME': 'PART NAME', 
            'part_name': 'PART NAME OLD', 
            'part_no': 'PART NO',
            'spq': 'SPQ',
            'qty_in_harian': 'QTY IN',
            'qty_out_harian': 'QTY OUT',
            'balance': 'BAL',
            'status': 'STATUS',
            'last_update': 'LAST_UPDATE',
            'created_at': 'created_at' # Keep created_at for sorting
        }
        
        existing_cols = {k: v for k, v in column_mapping.items() if k in df.columns}
        df = df.rename(columns=existing_cols)
        
        numeric_cols = ['QTY IN', 'QTY OUT', 'BAL', 'SPQ']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        if 'PART NAME' in df.columns:
             df['PART NAME'] = df['PART NAME'].fillna("-")

        # NOTE: Jangan drop duplicate di sini, karena kita butuh history buat snapshot
        return df

    except Exception as e:
        st.error(f"Terjadi kesalahan koneksi atau data: {e}")
        return pd.DataFrame()

df_merged = load_data()

# -----------------------------------------------------------------------------
# 4. MAIN LAYOUT & TITLE
# -----------------------------------------------------------------------------
col_title, col_refresh = st.columns([6, 1])
with col_title:
    st.markdown("## 📊 Monitor WIP Stock")
    st.markdown("<p style='color: #94a3b8; margin-top: -10px;'>Real-time monitoring for In, Out, and Balance stocks.</p>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 5. FILTER SECTION
# -----------------------------------------------------------------------------
with st.container():
    st.markdown('<div class="filter-box">', unsafe_allow_html=True)
    f_col1, f_col2, f_col3 = st.columns([1.5, 2, 2.5])
    
    with f_col1:
        st.caption("📅 Pilih Tanggal")
        selected_date = st.date_input("Tanggal Snapshot", value=pd.to_datetime("today"), label_visibility="collapsed")
    
    with f_col2:
        st.caption("🏷️ Status Stock")
        # Filter status ambil dari data yang ada
        status_opts = ["Semua Status"]
        if not df_merged.empty and 'STATUS' in df_merged.columns:
             status_opts += sorted(df_merged['STATUS'].dropna().unique().tolist())
        selected_status = st.selectbox("Status", status_opts, label_visibility="collapsed")
            
    with f_col3:
        st.caption("🔍 Search Part")
        search_query = st.text_input("Search", placeholder="Ketik Part No / Name...", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. SNAPSHOT LOGIC (THIS IS THE FIX) 🛠️
# -----------------------------------------------------------------------------
final_display = pd.DataFrame()

if not df_merged.empty:
    # Pastikan kolom tanggal dikenali sebagai datetime
    if 'Date' in df_merged.columns:
        df_merged['Date'] = pd.to_datetime(df_merged['Date'])
    if 'created_at' in df_merged.columns:
        df_merged['created_at'] = pd.to_datetime(df_merged['created_at'])

    # A. AMBIL HISTORY SAMPAI TANGGAL TERPILIH (Inclusive)
    # Gunanya buat cari SALDO TERAKHIR (BAL)
    mask_history = df_merged['Date'].dt.date <= selected_date
    df_history = df_merged[mask_history].copy()

    if not df_history.empty:
        # Urutkan berdasarkan waktu paling baru ke lama
        # Supaya baris paling atas adalah kondisi stok terakhir
        sort_cols = ['PART NO', 'created_at'] if 'created_at' in df_history.columns else ['PART NO', 'Date']
        df_history = df_history.sort_values(by=sort_cols, ascending=[True, False])

        # Ambil 1 baris per Part No (Baris paling atas = Saldo Terakhir)
        # Kita simpan kolom-kolom master juga (Part Name, Model, dll)
        keep_cols = ['PART NO', 'BAL', 'PART NAME', 'STATUS', 'MODEL', 'SPQ', 'PART NAME OLD']
        keep_cols = [c for c in keep_cols if c in df_history.columns]
        
        df_snapshot = df_history.drop_duplicates(subset=['PART NO'], keep='first')[keep_cols]

        # B. HITUNG TRANSAKSI HARI INI (IN & OUT)
        # Kalau hari ini gak ada transaksi, nanti hasilnya 0.
        mask_today = df_merged['Date'].dt.date == selected_date
        df_today = df_merged[mask_today].copy()
        
        # Agregasi (Jumlahkan) In & Out hari ini per Part No
        if not df_today.empty:
            today_agg = df_today.groupby('PART NO')[['QTY IN', 'QTY OUT']].sum().reset_index()
        else:
            today_agg = pd.DataFrame(columns=['PART NO', 'QTY IN', 'QTY OUT'])

        # C. GABUNGKAN SNAPSHOT + HARI INI
        # Kita join ke df_snapshot (Saldo) karena itu master list barang yg punya stok
        final_display = pd.merge(df_snapshot, today_agg, on='PART NO', how='left')

        # Isi NaN dengan 0 (Artinya hari ini gak ada transaksi in/out)
        final_display['QTY IN'] = final_display['QTY IN'].fillna(0)
        final_display['QTY OUT'] = final_display['QTY OUT'].fillna(0)
        
        # Tambahkan kolom Tanggal buat display
        final_display['Date'] = selected_date.strftime('%Y-%m-%d')

    else:
        # Kasus langka: Tanggal dipilih SEBELUM transaksi pertama kali ada
        final_display = pd.DataFrame()

# --- FILTER TAMBAHAN (Status & Search) ---
if not final_display.empty:
    # 1. Filter Status
    if selected_status != "Semua Status" and 'STATUS' in final_display.columns:
        final_display = final_display[final_display['STATUS'] == selected_status]
    
    # 2. Filter Search
    if search_query:
        query = search_query.lower()
        p_no = final_display['PART NO'] if 'PART NO' in final_display.columns else pd.Series(dtype='object')
        p_name = final_display['PART NAME'] if 'PART NAME' in final_display.columns else pd.Series(dtype='object')
        
        final_display = final_display[
            p_no.astype(str).str.lower().str.contains(query, na=False) | 
            p_name.astype(str).str.lower().str.contains(query, na=False)
        ]

# -----------------------------------------------------------------------------
# 7. KPI & TABLE RENDER
# -----------------------------------------------------------------------------
if not final_display.empty:
    total_part = len(final_display)
    bal_col = final_display['BAL'] if 'BAL' in final_display.columns else pd.Series([0]*len(final_display))
    
    total_ready = len(final_display[bal_col > 0])
    total_minus = len(final_display[bal_col < 0])
    
    pct_ready = round((total_ready / total_part * 100), 1) if total_part > 0 else 0
    pct_minus = round((total_minus / total_part * 100), 1) if total_part > 0 else 0

    k_col1, k_col2, k_col3 = st.columns(3)
    with k_col1:
        st.markdown(f"""<div class="kpi-container" style="border-left: 4px solid #3b82f6;"><div class="kpi-label">Total Items</div><div class="kpi-value">{total_part}</div><div class="kpi-delta delta-neutral">Snapshot Date: {selected_date}</div></div>""", unsafe_allow_html=True)
    with k_col2:
        st.markdown(f"""<div class="kpi-container" style="border-left: 4px solid #10b981;"><div class="kpi-label">Ready Stock</div><div class="kpi-value">{total_ready}</div><div class="kpi-delta delta-pos">Safe ({pct_ready}%)</div></div>""", unsafe_allow_html=True)
    with k_col3:
        st.markdown(f"""<div class="kpi-container" style="border-left: 4px solid #ef4444;"><div class="kpi-label">Stock Critical/Minus</div><div class="kpi-value">{total_minus}</div><div class="kpi-delta delta-neg">Attention ({pct_minus}%)</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 

    bal_max = final_display['BAL'].max() if 'BAL' in final_display.columns and final_display['BAL'].max() > 0 else 100

    # Kolom Display
    desired_order = ['Date', 'PART NO', 'PART NAME', 'QTY IN', 'QTY OUT', 'BAL', 'STATUS']
    available_cols = [c for c in desired_order if c in final_display.columns]
    remaining_cols = [c for c in final_display.columns if c not in available_cols and c not in ['created_at', 'PART NAME OLD']]
    
    df_show = final_display[available_cols + remaining_cols]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.TextColumn("Date"),
            "PART NO": st.column_config.TextColumn("Part Number", help="Nomor Identifikasi Part", width="medium"),
            "PART NAME": st.column_config.TextColumn("Part Name", help="Nama Barang", width="large"),
            "STATUS": st.column_config.TextColumn("Status", width="small"),
            "QTY IN": st.column_config.NumberColumn("In (Today)", format="%d"),
            "QTY OUT": st.column_config.NumberColumn("Out (Today)", format="%d"),
            "BAL": st.column_config.ProgressColumn("Ending Balance", help="Stock Balance Akhir Hari Terpilih", format="%d", min_value=0, max_value=int(bal_max)),
        }
    )
    st.caption(f"Menampilkan {len(df_show)} SKU yang memiliki history stok sampai tanggal {selected_date}.")
else:
    st.info(f"Tidak ada history stok ditemukan sampai tanggal {selected_date}.")