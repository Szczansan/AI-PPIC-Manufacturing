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
    response = supabase.table("MASTER").select(
        "machine_id, PART_NAME, part_no, target_hour"
    ).execute()
    if response.data:
        return pd.DataFrame(response.data)
    return pd.DataFrame()

df_master = get_master_data()

# --- HEADER ---
st.title("🏭 Input Actual Produksi")
st.caption("Mode: Slider Input (Mobile Friendly)")

if df_master.empty:
    st.error("Gagal memuat data Master Part.")
    st.stop()

# =========================================================================
# BAGIAN 1: INTERACTIVE SELECTION (FILTERING)
# =========================================================================

# A. PILIH MESIN
list_mesin = sorted(df_master['machine_id'].unique())
selected_machine = st.selectbox("Pilih Mesin", options=list_mesin)

# B. PILIH PART
df_filtered = df_master[df_master['machine_id'] == selected_machine]
part_options = df_filtered['PART_NAME'].unique()
selected_part_name = st.selectbox("Pilih Part Name", options=part_options)

# C. INFO DETAIL (Ambil Target buat Batas Slider)
if not df_filtered.empty:
    detail_part = df_filtered[df_filtered['PART_NAME'] == selected_part_name].iloc[0]
    target_val = int(detail_part['target_hour'])
    
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Part No:**\n{detail_part['part_no']}")
    with c2:
        st.info(f"**Target/Jam:**\n{target_val} Pcs")
else:
    st.warning("Part tidak ditemukan.")
    st.stop()

# =========================================================================
# BAGIAN 2: FORM INPUT DENGAN SLIDER
# =========================================================================

with st.form("input_form", clear_on_submit=True):
    st.markdown("---") 

    # D. LOGIC JAM (WIB FIX)
    now_wib = datetime.utcnow() + timedelta(hours=7)
    current_hour = now_wib.hour 

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

    # E. SLIDER INPUT (SMART RANGE)
    st.write("### Actual Qty (Geser)")
    
    # Logic Max Slider: 
    # Kita kasih napas 2x lipat dari target. 
    # Misal target 100, slider mentok di 200. Biar operator gampang ngepasinnya.
    # Tapi minimal slider mentok di 100 biar gak kekecilan.
    max_slider_val = max(target_val * 2, 100)
    
    actual_qty = st.slider(
        label="Geser tombol ini sesuai hasil produksi",
        min_value=0,
        max_value=max_slider_val,
        value=0, # Default 0
        step=1,  # Kelipatan 1
        help=f"Max slider diset ke {max_slider_val} berdasarkan target mesin."
    )

    # --- TOMBOL SUBMIT ---
    st.write("")
    submitted = st.form_submit_button("💾 SIMPAN DATA", type="primary")

    if submitted:
        if actual_qty == 0:
            st.warning("⚠️ Qty 0. Pastikan ini benar (Breakdown/Stop).")
        
        data_insert = {
            "machine_id": selected_machine,
            "part_no": detail_part['part_no'],
            "hour_index": selected_hour,
            "actual_qty": actual_qty,
            "snapshot_target": float(target_val)
        }

        try:
            supabase.table("monitor_per_hour").insert(data_insert).execute()
            st.success(f"✅ Data {selected_machine} Jam {selected_hour} = {actual_qty} Pcs Disimpan!")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Terjadi Kesalahan: {e}")

# --- 3. HISTORY ---
st.markdown("### 🕒 5 Input Terakhir")
last_data = supabase.table("monitor_per_hour").select("*").order("id", desc=True).limit(5).execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )
# --- TOMBOL SUBMIT ---
st.write("") # Spacer
submitted = st.button("💾 SIMPAN DATA", type="primary", use_container_width=True)

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
        
        # RESET INPUT MANUAL SETELAH SIMPAN
        st.session_state.qty_input = 0 
        
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ Terjadi Kesalahan: {e}")

# --- 5. HISTORY ---
st.markdown("### 🕒 5 Input Terakhir")
last_data = supabase.table("monitor_per_hour").select("*").order("id", desc=True).limit(5).execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )

