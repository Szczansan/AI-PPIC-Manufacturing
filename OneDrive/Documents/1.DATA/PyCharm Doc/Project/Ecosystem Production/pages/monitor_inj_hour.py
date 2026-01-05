import streamlit as st
import pandas as pd
from datetime import datetime
import time
from supabase_client import get_supabase

# --- 1. IMPORT NAVBAR DARI FOLDER COMPONENTS ---
from components.navbar import show_navbar

# --- 2. SETUP ---
st.set_page_config(page_title="Input Produksi", layout="centered")

# --- 3. PANGGIL NAVBAR ---
show_navbar()

# --- [BARU] 4. SECURITY CHECK & AMBIL USER ---
# Cek apakah user sudah login dari halaman Home?
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("⚠️ Akses Ditolak! Anda harus login terlebih dahulu.")
    st.stop() # Stop eksekusi program di sini

# Ambil username dari session
current_user = st.session_state['username']

# --- 5. KONEKSI DATABASE ---
supabase = get_supabase()

@st.cache_data(ttl=300)
def get_master_data():
    response = supabase.table("MASTER").select(
        "machine_id, PART_NAME, part_no, target_hour"
    ).execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

df_master = get_master_data()

# --- 6. HEADER ---
st.title("🏭 Input Actual Produksi")
# [BARU] Tampilkan siapa yang sedang login
st.markdown(f"👤 Operator: **{current_user}**") 
st.caption("Pastikan data yang diinput sesuai dengan kondisi mesin saat ini.")

if df_master.empty:
    st.error("Gagal memuat data Master Part. Cek koneksi database.")
    st.stop()

# =========================================================================
# BAGIAN 1: INTERACTIVE SELECTION
# =========================================================================

# A. PILIH MESIN
list_mesin = sorted(df_master['machine_id'].unique())
selected_machine = st.selectbox("Pilih Mesin", options=list_mesin)

# B. PILIH PART
df_filtered = df_master[df_master['machine_id'] == selected_machine]
part_options = df_filtered['PART_NAME'].unique()
selected_part_name = st.selectbox("Pilih Part Name", options=part_options)

# C. INFO DETAIL
if not df_filtered.empty:
    detail_part = df_filtered[df_filtered['PART_NAME'] == selected_part_name].iloc[0]
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Part No:**\n{detail_part['part_no']}")
    with c2:
        st.info(f"**Target/Jam:**\n{detail_part['target_hour']} Pcs")
else:
    st.warning("Part tidak ditemukan untuk mesin ini.")
    st.stop()

# =========================================================================
# BAGIAN 2: TRANSACTION FORM
# =========================================================================

with st.form("input_form", clear_on_submit=True):
    st.markdown("---") 
    
    # D. LOGIC JAM
    current_hour = datetime.now().hour
    hours_list = list(range(0, 24))
    try:
        default_index = hours_list.index(current_hour)
    except ValueError:
        default_index = 0

    selected_hour = st.selectbox(
        "Jam Ke- (Jam Produksi)", 
        options=hours_list, 
        index=default_index
    )

    # E. INPUT ACTUAL
    actual_qty = st.number_input(
        "Actual Qty (Pcs)", 
        min_value=0, 
        step=1
    )

    # --- TOMBOL SUBMIT ---
    submitted = st.form_submit_button("💾 SIMPAN DATA", type="primary")

    if submitted:
        if actual_qty == 0:
            st.warning("⚠️ Qty 0. Pastikan ini benar (Breakdown/Stop).")
        
        # [BARU] Payload Data sekarang ada 'created_by'
        data_insert = {
            "machine_id": selected_machine,
            "part_no": detail_part['part_no'],
            "hour_index": selected_hour,
            "actual_qty": actual_qty,
            "snapshot_target": float(detail_part['target_hour']),
            "created_by": current_user  # <--- INI DIA LOGICNYA
        }

        try:
            supabase.table("monitor_per_hour").insert(data_insert).execute()
            st.success(f"✅ Data {selected_machine} Jam {selected_hour} berhasil disimpan oleh {current_user}!")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Terjadi Kesalahan: {e}")

# --- 7. HISTORY ---
st.markdown("### 🕒 5 Input Terakhir")
# [BARU] Nambahin created_by di select biar kelihatan di tabel history
last_data = supabase.table("monitor_per_hour")\
    .select("machine_id, hour_index, actual_qty, created_at, created_by")\
    .order("id", desc=True)\
    .limit(5)\
    .execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    
    # Format jam biar enak dilihat (Opsional)
    df_last['created_at'] = pd.to_datetime(df_last['created_at']).dt.strftime('%H:%M:%S')

    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_by', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )