import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from supabase_client import get_supabase

# --- 1. IMPORT NAVBAR ---
from components.navbar import show_navbar 

# --- 2. SETUP ---
st.set_page_config(page_title="Input Produksi", layout="centered")

# --- 3. NAVBAR ---
show_navbar() 

supabase = get_supabase()

@st.cache_data(ttl=300)
def get_master_data():
    # Ambil data Master Part
    response = supabase.table("MASTER").select(
        "machine_id, PART_NAME, part_no, target_hour"
    ).execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

df_master = get_master_data()

# --- HEADER ---
st.title("🏭 Input Actual Produksi")
st.caption("Input data hasil produksi per jam.")

if df_master.empty:
    st.error("Gagal memuat data Master Part. Cek koneksi database.")
    st.stop()

# =========================================================================
# BAGIAN 1: FILTERING (DILUAR FORM BIAR AUTO-RELOAD)
# =========================================================================

# A. PILIH MESIN
list_mesin = sorted(df_master['machine_id'].unique())
selected_machine = st.selectbox("Pilih Mesin", options=list_mesin)

# B. PILIH PART (Filter based on Machine)
df_filtered = df_master[df_master['machine_id'] == selected_machine]
part_options = df_filtered['PART_NAME'].unique()
selected_part_name = st.selectbox("Pilih Part Name", options=part_options)

# C. INFO DETAIL
if not df_filtered.empty:
    detail_part = df_filtered[df_filtered['PART_NAME'] == selected_part_name].iloc[0]
    target_val = int(detail_part['target_hour'])
    
    # Tampilkan Info Target biar operator tau
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Part No:**\n{detail_part['part_no']}")
    with c2:
        st.info(f"**Target/Jam:**\n{target_val} Pcs")
else:
    st.warning("Part tidak ditemukan untuk mesin ini.")
    st.stop()

# =========================================================================
# BAGIAN 2: FORM INPUT STANDARD (STABIL & CEPAT)
# =========================================================================

with st.form("input_form", clear_on_submit=True):
    st.markdown("---") 

    # D. LOGIC JAM (FIX WIB UTC+7)
    now_wib = datetime.utcnow() + timedelta(hours=7)
    current_hour = now_wib.hour 

    hours_list = list(range(0, 24))
    try:
        # Smart Default: Pilih jam sekarang otomatis
        default_index = hours_list.index(current_hour)
    except ValueError:
        default_index = 0

    selected_hour = st.selectbox(
        "Jam Ke- (Jam Produksi)", 
        options=hours_list, 
        index=default_index
    )

    # E. INPUT ACTUAL (STANDARD KETIK)
    # Pake number_input biasa, paling robust & anti error
    actual_qty = st.number_input(
        "Actual Qty (Pcs)", 
        min_value=0, 
        step=1,
        help="Masukkan jumlah barang OK yang dihasilkan."
    )

    # --- TOMBOL SUBMIT ---
    st.write("")
    submitted = st.form_submit_button("💾 SIMPAN DATA", type="primary")

    if submitted:
        if actual_qty == 0:
            st.warning("⚠️ Qty 0. Pastikan ini benar (Breakdown/Stop).")
        
        # Payload Data
        data_insert = {
            "machine_id": selected_machine,
            "part_no": detail_part['part_no'],
            "hour_index": selected_hour,
            "actual_qty": actual_qty,
            "snapshot_target": float(target_val)
        }

        try:
            # Kirim ke Database
            supabase.table("monitor_per_hour").insert(data_insert).execute()
            
            # Feedback Sukses
            st.success(f"✅ Data {selected_machine} Jam {selected_hour} = {actual_qty} Pcs berhasil disimpan!")
            
            # Delay dikit biar notif kebaca, lalu refresh
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Terjadi Kesalahan: {e}")

# --- 3. HISTORY TABLE ---
st.markdown("### 🕒 5 Input Terakhir")
# Query 5 data terakhir buat konfirmasi visual
last_data = supabase.table("monitor_per_hour").select("*").order("id", desc=True).limit(5).execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    # Tampilkan tabel history sederhana
    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )
