import streamlit as st
from supabase import create_client
import datetime
from datetime import timedelta
import pandas as pd
from components.navbar import show_navbar

# ==================== CONFIG & CSS (TRUE DARK MODE) ==================== #
# st.set_page_config(page_title="Input Produksi", layout="wide") # Uncomment jika ini page utama

st.markdown("""
<style>
    /* 1. GLOBAL BACKGROUND (Hampir Hitam) */
    [data-testid="stAppViewContainer"] { 
        background-color: #0e1117; 
    }
    
    /* 2. HEADER BOX (Abu-abu Gelap Netral) */
    .header-box {
        background: linear-gradient(90deg, #161b22, #21262d);
        padding: 20px; 
        border-radius: 10px; 
        color: white;
        border-left: 5px solid #238636; /* Aksen Hijau Github */
        border: 1px solid #30363d;
        margin-bottom: 25px;
    }

    /* 3. FORM CONTAINER */
    [data-testid="stForm"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 20px;
        border-radius: 12px;
    }

    /* 4. METRIC CARDS */
    [data-testid="stMetric"] {
        background-color: #161b22;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
        box-shadow: none;
    }
    [data-testid="stMetricLabel"] { color: #8b949e; }
    [data-testid="stMetricValue"] { color: #f0f6fc; }

    /* 5. INPUT FIELDS (Biar nyatu sama tema gelap) */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea {
        background-color: #0d1117 !important; 
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
    }
    
    /* 6. TOMBOL SUBMIT */
    .stButton button {
        background-color: #238636; /* Hijau Gelap */
        color: white;
        font-weight: 600;
        border-radius: 6px;
        height: 50px;
        border: 1px solid rgba(255,255,255,0.1);
        transition: all 0.2s;
    }
    .stButton button:hover {
        background-color: #2ea043;
        border-color: #8b949e;
    }
    
    /* Teks Global */
    h1, h2, h3, h4, h5, p, label, span {
        color: #e6edf3 !important;
    }
    
    /* Hapus border biru saat fokus */
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== INIT SUPABASE ==================== #
try:
    supabase = create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )
except Exception:
    st.error("Koneksi Database Gagal. Cek Secrets.")
    st.stop()

# ==================== NAVBAR ==================== #
show_navbar()

# ==================== PAGE HEADER ==================== #
st.markdown("""
<div class="header-box">
    <h3 style="margin:0; font-weight:700;">🏭 Input Hasil Produksi</h3>
    <p style="margin:5px 0 0 0; font-size:14px; color:#8b949e;">
        Pencatatan data harian Injection Molding secara real-time.
    </p>
</div>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ==================== #
@st.cache_data(ttl=60)
def get_all_parts():
    try:
        res = supabase.table("List_Part").select("PART_NO, PART_NAME").execute()
        return res.data
    except: return []

def get_production_data(selected_month=None):
    try:
        if selected_month is None:
            selected_month = datetime.datetime.now().strftime('%Y-%m')
        
        start_date = f"{selected_month}-01"
        next_month = (datetime.datetime.strptime(selected_month + '-01', '%Y-%m-%d') + timedelta(days=32)).replace(day=1)
        end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
        
        res = supabase.table("Hasil_Produksi")\
            .select("*")\
            .gte('DATE', start_date)\
            .lte('DATE', end_date)\
            .order('DATE', desc=True)\
            .execute()
        return res.data
    except: return []

def get_available_months():
    try:
        res = supabase.table("Hasil_Produksi").select("DATE").execute()
        months = set()
        for item in res.data:
            if item['DATE']: months.add(item['DATE'][:7])
        months.add(datetime.datetime.now().strftime('%Y-%m'))
        return sorted(list(months), reverse=True)
    except:
        return [datetime.datetime.now().strftime('%Y-%m')]

# ==================== LOGIC INPUT ==================== #
all_parts = get_all_parts()
part_names = sorted(list(set([p['PART_NAME'] for p in all_parts]))) if all_parts else []

# --- BAGIAN 1: PILIH PART (Diluar Form) ---
st.markdown("##### 1️⃣ Identitas Part & Waktu")
col_sel1, col_sel2, col_sel3 = st.columns([2, 2, 1])

with col_sel1:
    selected_name = st.selectbox("Pilih Nama Part", options=[""] + part_names, index=0)

with col_sel2:
    part_no_val = ""
    if selected_name:
        match = next((p for p in all_parts if p['PART_NAME'] == selected_name), None)
        if match: part_no_val = match['PART_NO']
    
    st.text_input("Part Number (Auto)", value=part_no_val, disabled=True)

with col_sel3:
    date_val = st.date_input("Tanggal", value=datetime.datetime.now())


# --- BAGIAN 2: FORM UTAMA ---
with st.form("main_form", clear_on_submit=True):
    
    st.markdown("##### 2️⃣ Data Produksi")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        waktu_val = st.time_input("Jam Input", value=datetime.datetime.now().time())
    with c2:
        plan = st.number_input("Plan (Pcs)", min_value=0, step=1)
    with c3:
        act = st.number_input("Actual (Pcs)", min_value=0, step=1)
    with c4:
        cycle_time = st.number_input("Cycle Time (Detik)", min_value=0.0, format="%.1f")

    st.markdown("---")
    st.markdown("##### 3️⃣ Kualitas & Problem")
    
    # Layout Kolom jadi 3 (Weight, Loss, Problem)
    d1, d2, d3 = st.columns(3)
    with d1:
        weight_part = st.number_input("Berat Part (Gr)", min_value=0.0, format="%.2f")
    with d2:
        loss_time = st.number_input("Loss Time (Menit)", min_value=0, step=1)
    with d3:
        problem_code = st.selectbox("Kode Masalah", options=["OK", "MACHINE", "MATERIAL", "MOLD", "START UP", "NG SETTING"], index=0)
    
    # REMARKS DITARUH DI BAWAH KOLOM (FULL WIDTH)
    st.markdown("<br>", unsafe_allow_html=True)
    remarks = st.text_area("Keterangan / Remarks (Opsional)", placeholder="Contoh: Mesin trouble heater no.2...", height=100)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tombol Submit
    submitted = st.form_submit_button("💾 SIMPAN DATA PRODUKSI", use_container_width=True)

    if submitted:
        if not selected_name:
            st.warning("⚠️ Mohon pilih Nama Part terlebih dahulu di bagian atas!")
        else:
            dt_combined = datetime.datetime.combine(date_val, waktu_val)
            
            data_insert = {
                "DATE": dt_combined.isoformat(),
                "PART_NO": part_no_val,
                "PART_NAME": selected_name,
                "PLAN": plan,
                "ACT": act,
                "CYCLE_TIME": cycle_time,
                "WEIGHT_PART": weight_part,
                "LOSSE_TIME": loss_time,
                "REMARKS": remarks,
                "CODE_PROB": problem_code
            }

            try:
                response = supabase.table("Hasil_Produksi").insert(data_insert).execute()
                if response.data:
                    st.success(f"✅ Berhasil input: {selected_name} ({act} pcs)")
                    st.cache_data.clear()
                else:
                    st.error("❌ Gagal menyimpan ke database.")
            except Exception as e:
                st.error(f"❌ Error System: {e}")

# ==================== DASHBOARD MONITORING ==================== #
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("### 📊 Monitoring Hasil Produksi")

# Filter Bulan
m_col1, m_col2 = st.columns([1, 3])
with m_col1:
    available_months = get_available_months()
    selected_month = st.selectbox("Filter Bulan", options=available_months, index=0)

# Ambil Data
raw_data = get_production_data(selected_month)

if raw_data:
    df = pd.DataFrame(raw_data)
    
    total_plan = df['PLAN'].sum()
    total_act = df['ACT'].sum()
    total_ng_time = df['LOSSE_TIME'].sum()
    achievement = (total_act / total_plan * 100) if total_plan > 0 else 0

    # Metrics
    met1, met2, met3, met4 = st.columns(4)
    met1.metric("Total Plan", f"{total_plan:,} pcs")
    met2.metric("Total Actual", f"{total_act:,} pcs", delta=f"{achievement:.1f}% Achieve")
    met3.metric("Total Loss Time", f"{total_ng_time} min", delta_color="inverse")
    
    top_prob = df[df['CODE_PROB'] != 'OK']['CODE_PROB'].mode()
    prob_text = top_prob[0] if not top_prob.empty else "No Issue"
    met4.metric("Top Issue", prob_text)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabel
    df_display = df[[
        'DATE', 'PART_NAME', 'PLAN', 'ACT', 'CYCLE_TIME', 'CODE_PROB', 'LOSSE_TIME', 'REMARKS'
    ]].copy()
    
    df_display['DATE'] = pd.to_datetime(df_display['DATE']).dt.strftime('%d-%m-%Y %H:%M')
    df_display['Achv (%)'] = df_display.apply(lambda x: (x['ACT']/x['PLAN']) if x['PLAN']>0 else 0, axis=1)

    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "DATE": "Waktu Input",
            "PART_NAME": "Nama Part",
            "PLAN": st.column_config.NumberColumn("Plan", format="%d"),
            "ACT": st.column_config.NumberColumn("Actual", format="%d"),
            "Achv (%)": st.column_config.ProgressColumn(
                "Achievement",
                format="%.1f%%",
                min_value=0,
                max_value=1.2,
            ),
            "CYCLE_TIME": st.column_config.NumberColumn("C/T (s)", format="%.1f"),
            "LOSSE_TIME": st.column_config.NumberColumn("Loss (m)", format="%d"),
            "CODE_PROB": "Status",
            "REMARKS": "Ket"
        },
        hide_index=True
    )

else:
    st.info(f"Belum ada data produksi untuk periode {selected_month}.")
    met1, met2 = st.columns(2)
    met1.metric("Total Plan", "0")
    met2.metric("Total Actual", "0")