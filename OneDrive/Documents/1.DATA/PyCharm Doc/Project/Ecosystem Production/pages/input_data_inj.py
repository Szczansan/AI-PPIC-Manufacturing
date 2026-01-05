import streamlit as st
from supabase import create_client
import datetime
from datetime import timedelta
import pandas as pd
import io # Wajib buat handling file Excel di memory
from components.navbar import show_navbar

# ==================== CONFIG & CSS (TRUE DARK MODE) ==================== #
st.set_page_config(page_title="Input Produksi", layout="wide") 

st.markdown("""
<style>
    /* 1. GLOBAL BACKGROUND */
    [data-testid="stAppViewContainer"] { 
        background-color: #0e1117; 
    }
    
    /* 2. HEADER BOX */
    .header-box {
        background: linear-gradient(90deg, #161b22, #21262d);
        padding: 20px; 
        border-radius: 10px; 
        color: white;
        border-left: 5px solid #238636; /* Aksen Hijau */
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

    /* 5. INPUT FIELDS */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"], .stTextArea textarea, .stTimeInput input, .stDateInput input {
        background-color: #0d1117 !important; 
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
    }
    
    /* 6. TOMBOL SUBMIT */
    .stButton button {
        background-color: #238636;
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
    
    h1, h2, h3, h4, h5, p, label, span { color: #e6edf3 !important; }
    
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
except Exception as e:
    st.error(f"Koneksi Database Gagal: {e}")
    st.stop()

# ==================== NAVBAR ==================== #
show_navbar() 

# ==================== PAGE HEADER ==================== #
st.markdown("""
<div class="header-box">
    <h3 style="margin:0; font-weight:700;">🏭 Input Hasil Produksi</h3>
    <p style="margin:5px 0 0 0; font-size:14px; color:#8b949e;">
        Pencatatan data harian Injection Molding (Auto Calc NG).
    </p>
</div>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ==================== #
@st.cache_data(ttl=60)
def get_all_parts():
    """Mengambil list part dari tabel MASTER"""
    try:
        # REVISI: Tambah kolom 'machine_id' di query
        res = supabase.table("MASTER").select("part_no, PART_NAME, machine_id").execute()
        return res.data
    except: return []

def get_production_data(selected_month=None, limit_rows=100):
    """Mengambil data history produksi dengan limit"""
    try:
        if selected_month is None:
            selected_month = datetime.datetime.now().strftime('%Y-%m')
        
        start_date = f"{selected_month}-01"
        next_month = (datetime.datetime.strptime(selected_month + '-01', '%Y-%m-%d') + timedelta(days=32)).replace(day=1)
        end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Base query
        query = supabase.table("hasil_produksi")\
            .select("*")\
            .gte('date', start_date)\
            .lte('date', end_date)\
            .order('date', desc=True)
            
        # Terapkan Limit jika bukan 'Semua'
        if limit_rows != "Semua":
            query = query.limit(int(limit_rows))
            
        res = query.execute()
        return res.data
    except Exception as e:
        st.error(f"Gagal load data: {e}")
        return []

def get_available_months():
    try:
        res = supabase.table("hasil_produksi").select("date").execute()
        months = set()
        for item in res.data:
            if item['date']: months.add(item['date'][:7])
        months.add(datetime.datetime.now().strftime('%Y-%m'))
        return sorted(list(months), reverse=True)
    except:
        return [datetime.datetime.now().strftime('%Y-%m')]

# Fungsi export Excel rapi
def convert_df_to_excel(df_in):
    output = io.BytesIO()
    # Menggunakan xlsxwriter sebagai engine agar bisa formatting
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_in.to_excel(writer, index=False, sheet_name='Data Produksi')
        
        # Ambil objects workbook dan worksheet
        workbook  = writer.book
        worksheet = writer.sheets['Data Produksi']
        
        # Definisi Format
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#238636', # Hijau header
            'font_color': 'white',
            'border': 1
        })
        
        body_format = workbook.add_format({
            'border': 1,
            'valign': 'top'
        })
        
        # Terapkan format header & atur lebar kolom otomatis
        for col_num, value in enumerate(df_in.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
            # Kira-kira lebar kolom berdasarkan panjang isi atau header
            max_len = max(
                df_in.iloc[:, col_num].astype(str).map(len).max(), # Panjang data
                len(str(value)) # Panjang header
            ) + 2
            worksheet.set_column(col_num, col_num, max_len, body_format)
            
    return output.getvalue()

# ==================== LOGIC INPUT ==================== #
all_parts = get_all_parts()
part_names = sorted(list(set([p['PART_NAME'] for p in all_parts]))) if all_parts else []

# --- BAGIAN 1: KONTEKS KERJA (Diluar Form) ---
st.markdown("##### 1️⃣ Identitas Kerja")
col_sel1, col_sel2, col_sel3, col_sel4 = st.columns([2, 1, 1, 1])

# Variabel Auto Fill
part_no_val = ""
machine_auto_val = ""

with col_sel1:
    selected_name = st.selectbox("Pilih Nama Part", options=[""] + part_names, index=0)

# Logic Auto Fill berdasarkan selection
if selected_name:
    match = next((p for p in all_parts if p['PART_NAME'] == selected_name), None)
    if match: 
        part_no_val = match.get('part_no', '')
        machine_auto_val = match.get('machine_id', '') # Ambil machine_id dari master

with col_sel2:
    st.text_input("Part Number (Auto)", value=part_no_val, disabled=True)

with col_sel3:
    date_val = st.date_input("Tanggal", value=datetime.datetime.now())

with col_sel4:
    waktu_val = st.time_input("Jam Input", value=datetime.datetime.now().time())

# --- BAGIAN 2: FORM UTAMA ---
with st.form("main_form", clear_on_submit=True):
    
    st.markdown("##### 2️⃣ Detail Shift & Mesin")
    c_shift, c_machine, c_plan = st.columns(3)
    
    with c_shift:
        shift_select = st.selectbox("Shift", options=["Shift 1", "Shift 2", "Shift 3", "Non-Shift"])
    with c_machine:
        # REVISI: Jadi Read-Only (Disabled) dan ngisi otomatis
        machine_input = st.text_input("No. Mesin (Auto)", value=machine_auto_val, disabled=True, help="Otomatis dari Master Part")
    with c_plan:
        plan = st.number_input("Target Plan (Pcs)", min_value=0, step=1)

    st.markdown("---")
    st.markdown("##### 3️⃣ Hasil Produksi (Auto Hitung NG)")
    
    c_shot, c_ok, c_ct = st.columns(3)
    with c_shot:
        total_shot = st.number_input("Total Shot (Counter Mesin)", min_value=0, step=1)
    with c_ok:
        total_ok = st.number_input("Total OK (Barang Bagus)", min_value=0, step=1)
    with c_ct:
        cycle_time = st.number_input("Cycle Time (Detik)", min_value=0.0, format="%.1f")

    st.caption(f"💡 *System akan otomatis menghitung NG = Total Shot - Total OK*")

    st.markdown("---")
    st.markdown("##### 4️⃣ Masalah & Remarks")
    
    d1, d2, d3 = st.columns(3)
    with d1:
        weight_part = st.number_input("Berat Part (Gr)", min_value=0.0, format="%.2f")
    with d2:
        loss_time = st.number_input("Loss Time (Menit)", min_value=0, step=1)
    with d3:
        problem_code = st.selectbox("Kode Masalah Utama", 
                                  options=["OK", "SETTING", "MATERIAL", "MOLD", "MESIN", "MANPOWER", "OTHER"], 
                                  index=0)
    
    st.markdown("<br>", unsafe_allow_html=True)
    remarks = st.text_area("Keterangan Detail (Jika ada reject/masalah)", height=80)

    st.markdown("<br>", unsafe_allow_html=True)
    
    submitted = st.form_submit_button("💾 SIMPAN & HITUNG NG", use_container_width=True)

    if submitted:
        if not selected_name:
            st.warning("⚠️ Mohon pilih Nama Part terlebih dahulu!")
        elif not machine_input:
            st.warning("⚠️ Data Mesin Kosong di Master Data! Hubungi Admin.")
        elif total_ok > total_shot:
            st.error("⛔ Logic Error: Total OK tidak boleh lebih besar dari Total Shot!")
        else:
            calc_ng = total_shot - total_ok
            dt_combined = datetime.datetime.combine(date_val, waktu_val)
            
            data_insert = {
                "date": dt_combined.isoformat(),
                "shift": shift_select,
                "machine": machine_input, # Menggunakan value yang auto-filled
                "part_name": selected_name,
                "part_no": part_no_val,
                "plan": plan,
                "total_shot": total_shot,
                "total_ok": total_ok,
                "total_ng": calc_ng,
                "cycle_time": cycle_time,
                "weight_part": weight_part,
                "losse_time": loss_time,
                "code_prob": problem_code,
                "remarks": remarks
            }

            try:
                response = supabase.table("hasil_produksi").insert(data_insert).execute()
                if response.data:
                    msg = f"✅ Data Masuk! NG terhitung: **{calc_ng} pcs**"
                    st.success(msg)
                    st.cache_data.clear()
                else:
                    st.error("❌ Gagal menyimpan (No Data Returned).")
            except Exception as e:
                st.error(f"❌ Error System: {e}")

# ==================== DASHBOARD MONITORING ==================== #
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("### 📊 Live Monitoring Harian")

# Filter Layout: Bulan | Limit Data
m_col1, m_col2 = st.columns([1, 1])
with m_col1:
    available_months = get_available_months()
    selected_month = st.selectbox("Filter Bulan", options=available_months, index=0)

with m_col2:
    # FITUR BARU: Limit Data
    limit_options = [50, 100, 200, 500, "Semua"]
    selected_limit = st.selectbox("Jumlah Data Ditampilkan (Terkini)", options=limit_options, index=1) # Default 100

# Ambil Data dengan Limit
raw_data = get_production_data(selected_month, limit_rows=selected_limit)

if raw_data:
    df = pd.DataFrame(raw_data)
    
    # ------------------ FITUR FILTERING ------------------ #
    with st.expander("🔍 Filter Analisis (Klik untuk buka)", expanded=False):
        st.caption("Pilih satu atau lebih opsi untuk memfilter data dan metrics.")
        f1, f2, f3, f4 = st.columns(4)
        
        # 1. Filter Tanggal (Diekstrak dari timestamp)
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        available_dates = sorted(df['date_only'].unique().tolist())
        sel_dates = f1.multiselect("Pilih Tanggal", available_dates)

        # 2. Filter Part Name
        available_parts = sorted(df['part_name'].unique().tolist())
        sel_parts = f2.multiselect("Pilih Part", available_parts)

        # 3. Filter Machine
        available_machines = sorted(df['machine'].unique().tolist())
        sel_machines = f3.multiselect("Pilih Mesin", available_machines)

        # 4. Filter Code Problem
        available_probs = sorted(df['code_prob'].unique().tolist())
        sel_probs = f4.multiselect("Pilih Problem", available_probs)

    # ------------------ TERAPKAN FILTER ------------------ #
    df_filtered = df.copy()

    if sel_dates:
        df_filtered = df_filtered[df_filtered['date_only'].isin(sel_dates)]
    if sel_parts:
        df_filtered = df_filtered[df_filtered['part_name'].isin(sel_parts)]
    if sel_machines:
        df_filtered = df_filtered[df_filtered['machine'].isin(sel_machines)]
    if sel_probs:
        df_filtered = df_filtered[df_filtered['code_prob'].isin(sel_probs)]
    
    # ------------------ HITUNG METRICS DARI DATA FILTERED ------------------ #
    total_plan = df_filtered['plan'].sum()
    total_shot_all = df_filtered['total_shot'].sum()
    total_ok_all = df_filtered['total_ok'].sum()
    total_ng_all = df_filtered['total_ng'].sum()
    
    achievement = (total_ok_all / total_plan * 100) if total_plan > 0 else 0
    reject_rate = (total_ng_all / total_shot_all * 100) if total_shot_all > 0 else 0

    met1, met2, met3, met4 = st.columns(4)
    
    # Update label metrics biar user sadar ini data ter-filter/ter-limit
    data_label = f"(Last {selected_limit})" if selected_limit != "Semua" else "(All)"
    
    met1.metric(f"Total Plan {data_label}", f"{total_plan:,}")
    met2.metric("Total OK", f"{total_ok_all:,}", delta=f"{achievement:.1f}% Achv")
    met3.metric("Total NG", f"{total_ng_all:,}", delta=f"{reject_rate:.1f}% Rate", delta_color="inverse")
    
    top_prob = df_filtered[df_filtered['code_prob'] != 'OK']['code_prob'].mode()
    prob_text = top_prob[0] if not top_prob.empty else "Clean"
    met4.metric("Top Issue", prob_text)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # ------------------ TAMPILKAN TABEL FILTERED ------------------ #
    
    # Layout Header Tabel & Tombol Export
    t_col1, t_col2 = st.columns([3, 1])
    with t_col1:
        st.markdown(f"**Menampilkan {len(df_filtered)} data produksi:**")
    with t_col2:
        # EXPORT LOGIC
        if not df_filtered.empty:
            # Siapkan Data Khusus Export (Rename Kolom biar Bagus di Excel)
            df_export = df_filtered[[
                'date', 'shift', 'machine', 'part_name', 
                'plan', 'total_shot', 'total_ok', 'total_ng', 
                'code_prob', 'remarks'
            ]].copy()
            
            # Formatting Tanggal
            df_export['date'] = pd.to_datetime(df_export['date']).dt.strftime('%d-%m-%Y %H:%M')
            
            # Rename Column Header Bahasa Indonesia
            df_export.columns = [
                'Waktu Input', 'Shift', 'No. Mesin', 'Nama Part', 
                'Target Plan', 'Total Shot', 'Total OK', 'Total NG', 
                'Problem Code', 'Keterangan'
            ]
            
            excel_data = convert_df_to_excel(df_export)
            
            st.download_button(
                label="📥 Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"Laporan_Produksi_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='download-excel'
            )
    
    df_display = df_filtered[[
        'date', 'shift', 'machine', 'part_name', 
        'plan', 'total_shot', 'total_ok', 'total_ng', 
        'code_prob', 'remarks'
    ]].copy()
    
    df_display['date'] = pd.to_datetime(df_display['date']).dt.strftime('%d/%m %H:%M')

    st.dataframe(
        df_display,
        use_container_width=True,
        column_config={
            "date": "Waktu",
            "shift": "Shift",
            "machine": "Msn",
            "part_name": "Part Name",
            "plan": st.column_config.NumberColumn("Plan", format="%d"),
            "total_shot": st.column_config.NumberColumn("Shot", format="%d"),
            "total_ok": st.column_config.NumberColumn("OK", format="%d"),
            "total_ng": st.column_config.NumberColumn("NG", format="%d"),
            "code_prob": "Code",
            "remarks": "Ket"
        },
        hide_index=True
    )
else:
    st.info(f"Belum ada data produksi untuk periode {selected_month}. Data kosong atau cek koneksi.")