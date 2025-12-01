import streamlit as st
import pandas as pd
from supabase_client import get_supabase
import time

# --- 1. IMPORT NAVBAR ---
from components.navbar import show_navbar 

# --- 2. CONFIG & PAGE SETUP ---
st.set_page_config(page_title="Dashboard Produksi", layout="wide")

# =============================
# CSS (MODERN DASHBOARD THEME)
# =============================
st.markdown("""
<style>
    .stApp { background-color: #0f172a; }
    div[data-testid="stDataFrame"] {
        background-color: #1e293b; padding: 1rem; border-radius: 12px; border: 1px solid #334155;
    }
    .stat-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155; padding: 20px; border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); text-align: center;
        transition: transform 0.2s;
    }
    .stat-card:hover { border-color: #60a5fa; transform: translateY(-2px); }
    .stat-value { font-size: 2rem; font-weight: 700; color: #f8fafc; margin: 5px 0; }
    .stat-label { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .stat-icon { font-size: 1.5rem; margin-bottom: 10px; display: inline-block; padding: 10px; border-radius: 50%; background: rgba(255, 255, 255, 0.05); }
    .dash-title { font-size: 1.8rem; font-weight: 800; background: -webkit-linear-gradient(45deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .dash-subtitle { color: #94a3b8; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- 3. PANGGIL NAVBAR ---
show_navbar() 
supabase = get_supabase()

# --- 4. LOAD DATA FUNCTIONS ---

# A. Ambil Data Transaksi Harian
@st.cache_data(ttl=60) 
def get_production_data():
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    response = supabase.table("monitor_per_hour")\
        .select("*")\
        .eq("production_date", today)\
        .execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

# B. Ambil Data Master (Buat Translate Part No -> Part Name)
@st.cache_data(ttl=300) # Cache lamaan dikit aman
def get_master_mapping():
    # Kita cuma butuh Part No & Part Name aja
    response = supabase.table("MASTER").select("part_no, PART_NAME").execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

# Load Data
df = get_production_data()
df_master = get_master_mapping()

# =============================
# HEADER SECTION
# =============================
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown("<div class='dash-title'>📊 Production Control Board</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='dash-subtitle'>Monitoring real-time activity • {pd.Timestamp.now().strftime('%d %B %Y')}</div>", unsafe_allow_html=True)
with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
        st.rerun()

st.divider()

# =============================
# METRICS SECTION
# =============================
if not df.empty:
    total_pcs = df['actual_qty'].sum()
    total_input = len(df)
    active_machines = df['machine_id'].nunique()
    avg_target = df['snapshot_target'].sum() if 'snapshot_target' in df.columns else 0
    achievement = (total_pcs / avg_target * 100) if avg_target > 0 else 0
else:
    total_pcs, total_input, active_machines, achievement = 0, 0, 0, 0

def metric_card(icon, label, value, color_hex="#3b82f6"):
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon" style="color: {color_hex};">{icon}</div>
        <div class="stat-value">{value}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
with m1: metric_card("📦", "Total Output", f"{total_pcs:,}", "#34d399")
with m2: metric_card("⚙️", "Mesin Aktif", f"{active_machines}", "#60a5fa")
with m3: metric_card("📝", "Total Input", f"{total_input}", "#fbbf24")
with m4: metric_card("📈", "Avg Achievement", f"{achievement:.1f}%", "#f472b6")

st.markdown("<br>", unsafe_allow_html=True)

# =============================
# MAIN CONTENT (PIVOT TABLE)
# =============================

if df.empty:
    st.info("👋 Belum ada data produksi hari ini. Silakan input data di menu 'Hourly Input'.")
    st.stop()

# --- STEP 1: GABUNGKAN DATA (JOIN) ---
# Kita tempel PART_NAME dari df_master ke df transaksi berdasarkan 'part_no'
if not df_master.empty:
    # Merge: left join (biar kalau ada part baru yg belum ada di master, data gak ilang)
    df = pd.merge(df, df_master, on='part_no', how='left')
    # Kalau ada yang NULL (gak ketemu di master), isi strip
    df['PART_NAME'] = df['PART_NAME'].fillna('-')
else:
    # Fallback kalau master gagal load, pake part_no aja
    df['PART_NAME'] = df['part_no']

# --- STEP 2: PIVOT LOGIC ---
# Sekarang index-nya pake 'PART_NAME' bukan 'part_no'
pivot_df = df.pivot_table(
    index=["machine_id", "PART_NAME", "snapshot_target"], # <--- INI YG DIRUBAH
    columns="hour_index",
    values="actual_qty",
    aggfunc='sum',
    fill_value=0
)

pivot_df.reset_index(inplace=True)
pivot_df.rename(columns={'snapshot_target': 'Target/Jam'}, inplace=True)
pivot_df.sort_values(by="machine_id", inplace=True)

st.markdown("### 📋 Detail Per Jam")

# --- TABLE DISPLAY ---
st.dataframe(
    pivot_df,
    use_container_width=True,
    height=(len(pivot_df) * 35) + 38,
    hide_index=True,
    column_config={
        "machine_id": st.column_config.TextColumn("Nama Mesin", width="medium"),
        
        # Kolom ini sekarang isinya Nama Part
        "PART_NAME": st.column_config.TextColumn("Part Name", width="large"), 
        
        "Target/Jam": st.column_config.NumberColumn("Target (CT)", format="%d"),
        **{str(h): st.column_config.NumberColumn(f"Jam {h}", format="%d", width="small") for h in range(24)}
    }
)