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
st.caption("Gunakan Slider untuk cepat, atau Ketik Manual untuk presisi.")

if df_master.empty:
    st.error("Gagal memuat data Master Part.")
    st.stop()

# =========================================================================
# BAGIAN 1: FILTERING MESIN & PART
# =========================================================================

list_mesin = sorted(df_master['machine_id'].unique())
selected_machine = st.selectbox("Pilih Mesin", options=list_mesin)

df_filtered = df_master[df_master['machine_id'] == selected_machine]
part_options = df_filtered['PART_NAME'].unique()
selected_part_name = st.selectbox("Pilih Part Name", options=part_options)

if not df_filtered.empty:
    detail_part = df_filtered[df_filtered['PART_NAME'] == selected_part_name].iloc[0]
    target_val = int(detail_part['target_hour'])
    
    c1, c2 = st.columns(2)
    with c1: st.info(f"**Part No:**\n{detail_part['part_no']}")
    with c2: st.info(f"**Target/Jam:**\n{target_val} Pcs")
else:
    st.warning("Part tidak ditemukan.")
    st.stop()

# =========================================================================
# BAGIAN 2: LOGIC DUAL INPUT (TANPA FORM BIAR REALTIME)
# =========================================================================

# Inisialisasi State Qty kalau belum ada
if "current_qty" not in st.session_state:
    st.session_state.current_qty = 0

# Callback: Slider Digeser -> Update Session State
def update_from_slider():
    st.session_state.current_qty = st.session_state.slider_val

# Callback: Kotak Diketik -> Update Session State
def update_from_input():
    st.session_state.current_qty = st.session_state.number_val

# Batas Max Slider
max_slider = max(int(target_val * 1.5), 100)

st.markdown("---") 

# --- LOGIC JAM (WIB FIX) ---
now_wib = datetime.utcnow() + timedelta(hours=7)
current_hour = now_wib.hour 
hours_list = list(range(0, 24))
try:
    default_idx = hours_list.index(current_hour)
except:
    default_idx = 0

selected_hour = st.selectbox("Jam Ke-", options=hours_list, index=default_idx)

st.write("### Actual Qty")

# --- A. SLIDER ---
safe_slider_value = min(st.session_state.current_qty, max_slider)

st.slider(
    label="Geser Cepat",
    min_value=0,
    max_value=max_slider,
    value=safe_slider_value,
    key="slider_val",    
    on_change=update_from_slider # Aman karena diluar st.form
)

# --- B. NUMBER INPUT ---
actual_qty = st.number_input(
    label="Ketik Manual (Jika Over Target)",
    min_value=0,
    step=1,
    value=st.session_state.current_qty,
    key="number_val",    
    on_change=update_from_input # Aman karena diluar st.form
)

# --- TOMBOL SUBMIT (Bukan form_submit_button) ---
st.write("")
submitted = st.button("💾 SIMPAN DATA", type="primary", use_container_width=True)

if submitted:
    if actual_qty == 0:
        st.warning("⚠️ Qty 0. Pastikan ini benar.")
    
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
        
        # Reset angka jadi 0 setelah sukses
        st.session_state.current_qty = 0
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.error(f"❌ Terjadi Kesalahan: {e}")

# --- HISTORY ---
st.markdown("### 🕒 5 Input Terakhir")
last_data = supabase.table("monitor_per_hour").select("*").order("id", desc=True).limit(5).execute()

if last_data.data:
    df_last = pd.DataFrame(last_data.data)
    st.dataframe(
        df_last[['machine_id', 'hour_index', 'actual_qty', 'created_at']], 
        hide_index=True,
        use_container_width=True
    )
