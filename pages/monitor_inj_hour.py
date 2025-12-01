import streamlit as st
import pandas as pd
from datetime import datetime
import time
from supabase_client import get_supabase

# --- 1. IMPORT NAVBAR DARI FOLDER COMPONENTS ---
from components.navbar import show_navbar  # <--- TAMBAHAN 1

# --- 2. SETUP ---
st.set_page_config(page_title="Input Produksi", layout="centered")

# --- 3. PANGGIL NAVBAR DISINI ---
show_navbar()  # <--- TAMBAHAN 2 (Wajib ditaruh setelah set_page_config)

supabase = get_supabase()

@st.cache_data(ttl=300)
def get_master_data():
    # Pastikan nama kolom sesuai sama database loe (case sensitive)
    response = supabase.table("MASTER").select(
        "machine_id, PART_NAME, part_no, target_hour"
    ).execute()
    
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

df_master = get_master_data()

# --- 2. HEADER ---
st.title("🏭 Input Actual Produksi")
st.caption("Pastikan data yang diinput sesuai dengan kondisi mesin saat ini.")

if df_master.empty:
    st.error("Gagal memuat data Master Part. Cek koneksi database.")
    st.stop()

# =========================================================================
# BAGIAN 1: INTERACTIVE SELECTION (DILUAR FORM BIAR AUTO-UPDATE)
# =========================================================================

# A. PILIH MESIN
list_mesin = sorted(df_master['machine_id'].unique())
selected_machine = st.selectbox("Pilih Mesin", options=list_mesin)

# B. PILIH PART (Otomatis ke-filter & Langsung Reload karena diluar Form)
df_filtered = df_master[df_master['machine_id'] == selected_machine]
part_options = df_filtered['PART_NAME'].unique()
selected_part_name = st.selectbox("Pilih Part Name", options=part_options)

# C. INFO DETAIL (Langsung muncul real-time)
if not df_filtered.empty:
    # Ambil detail dari part yang dipilih
    detail_part = df_filtered[df_filtered['PART_NAME'] == selected_part_name].iloc[0]
    
    # Tampilkan Info dalam kotak biru
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Part No:**\n{detail_part['part_no']}")
    with c2:
        st.info(f"**Target/Jam:**\n{detail_part['target_hour']} Pcs")
else:
    st.warning("Part tidak ditemukan untuk mesin ini.")
    st.stop()

# =========================================================================
# BAGIAN 2: TRANSACTION FORM (SUBMIT BARU KIRIM)
# =========================================================================

with st.form("input_form", clear_on_submit=True):
    st.markdown("---") # Garis pemisah biar rapi
    
    # D. LOGIC JAM (Smart Default)
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
        
        # Payload Data
        data_insert = {
            "machine_id": selected_machine,
            "part_no": detail_part['part_no'],
            "hour_index": selected_hour,
            "actual_qty": actual_qty,
            "snapshot_target": float(detail_part['target_hour'])
        }

        try:
            supabase.table("monitor_per_hour").insert(data_insert).execute()
            st.success(f"✅ Data {selected_machine} Jam {selected_hour} berhasil disimpan!")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Terjadi Kesalahan: {e}")

# --- 5. HISTORY ---
st.markdown("### 🕒 5 Input Terakhir")
# Tambahin machine_id di query biar history-nya relevan
last_data = supabase.table("monitor_per_hour").select("*").order("id", desc=True).limit(5).execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )