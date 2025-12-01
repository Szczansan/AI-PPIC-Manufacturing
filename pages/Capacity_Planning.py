import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
from postgrest.exceptions import APIError 

# --- KONSTANTA & CONFIG ---
HOURS_PER_WORKDAY = 8.0 
MACHINES = ['250T','850T','1500T']

# Mapping Kolom Table Baru (forecast_monthly)
FC_TABLE = 'forecast_monthly'
FC_COL_ID = 'id'
FC_COL_MONTH = 'forecast_month'
FC_COL_PART = 'part_no'
FC_COL_QTY = 'forecast_qty_monthly'
FC_COL_REV = 'revision_no' # Penting buat filtering
FC_COL_CUST = 'customer_name'

# Mapping Master Data (DB Lama)
MST_TABLE = 'MASTER' # Asumsi nama table master masih sama
MST_COL_PART = 'part_no'
MST_COL_CT = 'CYCLE_TIME'
MST_COL_TONAGE = 'TONAGE'

# =======================================================
# 1. SETUP & SUPABASE
# =======================================================
@st.cache_resource
def get_supabase_client():
    SUPABASE_URL = "https://laxagfijnbcpzxjvwutq.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxheGFnZmlqbmJjcHp4anZ3dXRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDE1ODIsImV4cCI6MjA3Njk3NzU4Mn0.VkYg-4zu1SjNzv1RqzccHnKCMY0NDHsDrd6Il3paC6U"
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# --- Fetcher Helper ---
@st.cache_data(ttl=3600)
def fetch_master_rules():
    """Fetch Master Data & Rules sekali jalan."""
    try:
        # 1. Fetch Rules
        res_rules = supabase.table('rules').select("*").execute()
        df_rules = pd.DataFrame(res_rules.data)
        
        # 2. Fetch Master Part
        res_master = supabase.table(MST_TABLE).select("*").execute()
        df_master = pd.DataFrame(res_master.data)
        
        return df_rules, df_master
    except APIError as e:
        st.error(f"❌ Gagal ambil data Master/Rules: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60) # Cache sebentar aja biar kalau ada upload baru cepet update
def get_available_months():
    """Ambil list bulan unik yang ada di table forecast_monthly"""
    try:
        # Kita cuma ambil kolom bulan biar ringan
        response = supabase.table(FC_TABLE).select(FC_COL_MONTH).execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            # Ambil unik dan sort desc (bulan terbaru paling atas)
            return sorted(df[FC_COL_MONTH].unique(), reverse=True)
        return []
    except Exception as e:
        st.error(f"❌ Gagal ambil list bulan: {e}")
        return []

@st.cache_data(ttl=300)
def get_forecast_data(selected_month):
    """Ambil data forecast KHUSUS bulan yang dipilih"""
    try:
        response = supabase.table(FC_TABLE)\
            .select("*")\
            .eq(FC_COL_MONTH, selected_month)\
            .execute() # Filter di level database (Server-side filtering)
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"❌ Gagal ambil data forecast bulan {selected_month}: {e}")
        return pd.DataFrame()

# =======================================================
# 2. CORE LOGIC (CALCULATION)
# =======================================================

def process_latest_revision(df_raw):
    """
    LOGIC PENTING:
    Ambil hanya revision_no TERTINGGI untuk setiap part_no + customer + month.
    """
    if df_raw.empty:
        return df_raw
        
    # 1. Pastikan Part No uppercase & bersih
    df_raw[FC_COL_PART] = df_raw[FC_COL_PART].astype(str).str.strip().str.upper()
    
    # 2. Sorting: Part ASC, Revision DESC (biar revisi paling gede ada di atas)
    # Kita group by Part No (dan Customer kalau perlu)
    df_sorted = df_raw.sort_values(by=[FC_COL_PART, FC_COL_REV], ascending=[True, False])
    
    # 3. Drop Duplicates: Keep 'first' (karena yg first itu revisi tertinggi)
    # Unique key-nya adalah Part No. (Kalau satu part bisa beda customer, tambahin customer di subset)
    df_clean = df_sorted.drop_duplicates(subset=[FC_COL_PART], keep='first')
    
    return df_clean

def calculate_naoh_monthly(rules_series, num_days=30):
    """Hitung Kapasitas (Sama kayak sebelumnya)"""
    MST_Hours = 24.0 * num_days
    efficiency = rules_series['efficiency'] # Asumsi 0.9 (90%)
    
    NAOH_Hours = MST_Hours * efficiency
    NAOH_Days = NAOH_Hours / HOURS_PER_WORKDAY
    
    return pd.DataFrame({
        'machine': MACHINES,
        'Kapasitas (Hari)': [NAOH_Days] * len(MACHINES)
    })

def calculate_machine_load(df_fc_clean, df_mst, rules_series):
    """Hitung Load Mesin"""
    # Cleanup Master
    df_mst[MST_COL_PART] = df_mst[MST_COL_PART].astype(str).str.strip().str.upper()
    
    # Merge Forecast (yang udah bersih revisinya) dengan Master
    df_merged = pd.merge(
        df_fc_clean,
        df_mst[[MST_COL_PART, MST_COL_CT, MST_COL_TONAGE]],
        left_on=FC_COL_PART,
        right_on=MST_COL_PART,
        how='left'
    )
    
    # Cek yang gak match (Opsional: Tampilkan di expander biar gak menuhin layar)
    unmatched = df_merged[df_merged[MST_COL_TONAGE].isnull()]
    if not unmatched.empty:
        with st.expander(f"⚠️ {len(unmatched)} Part Tidak Ada di Master (Klik untuk lihat)"):
            st.dataframe(unmatched[[FC_COL_PART, FC_COL_QTY]])

    # Filter data valid
    df_valid = df_merged.dropna(subset=[MST_COL_TONAGE, MST_COL_CT])
    
    # Konversi Tipe Data
    df_valid[MST_COL_CT] = pd.to_numeric(df_valid[MST_COL_CT], errors='coerce').fillna(0)
    df_valid[FC_COL_QTY] = pd.to_numeric(df_valid[FC_COL_QTY], errors='coerce').fillna(0)
    
    # --- LOGIC BEBAN ---
    dandory_min = rules_series['dandory_min']
    startup_min = rules_series['startup_min']
    
    # Group by Mesin
    df_load = df_valid.groupby(MST_COL_TONAGE).agg(
        total_prod_sec = (FC_COL_QTY, lambda x: (x * df_valid.loc[x.index, MST_COL_CT]).sum()),
        num_parts = (FC_COL_PART, 'nunique')
    ).reset_index()
    
    # Kalkulasi Jam -> Hari
    df_load['prod_hours'] = df_load['total_prod_sec'] / 3600
    df_load['dandory_hours'] = (df_load['num_parts'] - 1) * (dandory_min / 60)
    df_load['dandory_hours'] = df_load['dandory_hours'].clip(lower=0) # Gak boleh minus
    df_load['setup_hours'] = startup_min / 60
    
    df_load['total_hours'] = df_load['prod_hours'] + df_load['dandory_hours'] + df_load['setup_hours']
    df_load['Beban (Hari)'] = df_load['total_hours'] / HOURS_PER_WORKDAY
    
    # Filter cuma mesin yang kita punya
    df_final = df_load[df_load[MST_COL_TONAGE].isin(MACHINES)].copy()
    df_final = df_final.rename(columns={MST_COL_TONAGE: 'machine'})
    
    return df_final[['machine', 'Beban (Hari)']]

# =======================================================
# 3. MAIN UI
# =======================================================
st.title("🏭 Capacity Planning (New Table Structure)")

# 1. Load Master Data & Rules
df_rules_raw, df_master = fetch_master_rules()

if df_rules_raw.empty or df_master.empty:
    st.warning("Menunggu data Rules/Master...")
    st.stop()

rules = df_rules_raw.iloc[0]

# 2. Select Month (Fetching Ringan)
available_months = get_available_months()

if not available_months:
    st.info("Belum ada data di table 'forecast_monthly'. Silakan upload data dulu.")
    st.stop()

col1, col2 = st.columns([1, 3])
with col1:
    selected_month = st.selectbox("Pilih Bulan Forecast:", available_months)

# 3. Fetch Forecast Data (Fetching Berat - Cuma bulan yg dipilih)
with st.spinner(f"Mengambil data forecast bulan {selected_month}..."):
    df_fc_raw = get_forecast_data(selected_month)

if df_fc_raw.empty:
    st.warning(f"Data forecast bulan {selected_month} kosong.")
    st.stop()

# 4. Process Revision (Ambil Revisi Tertinggi)
df_fc_clean = process_latest_revision(df_fc_raw)

# Tampilkan Statistik Data
st.markdown(f"**Status Data {selected_month}:**")
col_a, col_b, col_c = st.columns(3)
col_a.metric("Total Rows (DB)", len(df_fc_raw))
col_b.metric("Part Unik (Max Rev)", len(df_fc_clean))
col_c.metric("Total Qty", f"{df_fc_clean[FC_COL_QTY].sum():,}")

# 5. Calculate & Visualize
# Hitung NAOH (default 30 hari, bisa dibikin dinamis kalau mau)
df_naoh = calculate_naoh_monthly(rules)
# Hitung Load
df_load = calculate_machine_load(df_fc_clean, df_master, rules)

# Merge
df_result = pd.merge(df_naoh, df_load, on='machine', how='left').fillna(0)
df_result['Utilisasi (%)'] = (df_result['Beban (Hari)'] / df_result['Kapasitas (Hari)']) * 100

# Tampilan Table
st.subheader("📊 Hasil Analisis")
st.dataframe(
    df_result.style.format({
        'Kapasitas (Hari)': "{:.2f}",
        'Beban (Hari)': "{:.2f}",
        'Utilisasi (%)': "{:.2f}%"
    }).background_gradient(subset=['Utilisasi (%)'], cmap='Reds'),
    use_container_width=True
)

# 6. Save Button (Opsional)
if st.button("💾 Simpan Summary ke Database"):
    # Logic save sama kayak sebelumnya, sesuaikan nama table tujuan
    st.toast("Fitur simpan belum diaktifkan di kode ini.", icon="ℹ️")