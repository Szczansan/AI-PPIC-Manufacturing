import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from supabase_client import get_supabase

# --- 1. IMPORT NAVBAR DARI FOLDER COMPONENTS ---
from components.navbar import show_navbar 

# --- 2. SETUP ---
st.set_page_config(page_title="Input Produksi", layout="centered")

# --- 3. PANGGIL NAVBAR DISINI ---
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
# BAGIAN 2: NUMPAD LOGIC (Input Angka Ala ATM)
# =========================================================================

# Inisialisasi State Angka
if "qty_input" not in st.session_state:
    st.session_state.qty_input = 0

# Fungsi Callback
def add_digit(digit):
    current_val = str(st.session_state.qty_input)
    if current_val == "0":
        st.session_state.qty_input = int(digit)
    else:
        st.session_state.qty_input = int(current_val + str(digit))

def backspace():
    current_val = str(st.session_state.qty_input)
    if len(current_val) > 1:
        st.session_state.qty_input = int(current_val[:-1])
    else:
        st.session_state.qty_input = 0

def clear_input():
    st.session_state.qty_input = 0

# =========================================================================
# BAGIAN 3: INPUT & SUBMIT (TANPA FORM BIAR NUMPAD JALAN)
# =========================================================================

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

# E. INPUT ACTUAL (Terhubung ke Numpad)
st.write("Actual Qty (Pcs)")
actual_qty = st.number_input(
    label="qty_hidden", 
    label_visibility="collapsed",
    min_value=0, 
    step=1, 
    key="qty_input" # <--- Kuncinya: nyambung ke session_state
)

# F. TAMPILAN TOMBOL NUMPAD
with st.expander("🔢 Buka Numpad (Input Cepat)", expanded=True):
    # Grid 3 Kolom
    col_n1, col_n2, col_n3 = st.columns(3)
    
    with col_n1: st.button("1", use_container_width=True, on_click=add_digit, args=(1,))
    with col_n2: st.button("2", use_container_width=True, on_click=add_digit, args=(2,))
    with col_n3: st.button("3", use_container_width=True, on_click=add_digit, args=(3,))
    
    with col_n1: st.button("4", use_container_width=True, on_click=add_digit, args=(4,))
    with col_n2: st.button("5", use_container_width=True, on_click=add_digit, args=(5,))
    with col_n3: st.button("6", use_container_width=True, on_click=add_digit, args=(6,))
    
    with col_n1: st.button("7", use_container_width=True, on_click=add_digit, args=(7,))
    with col_n2: st.button("8", use_container_width=True, on_click=add_digit, args=(8,))
    with col_n3: st.button("9", use_container_width=True, on_click=add_digit, args=(9,))
    
    with col_n1: st.button("🗑️ C", use_container_width=True, on_click=clear_input, type="primary")
    with col_n2: st.button("0", use_container_width=True, on_click=add_digit, args=(0,))
    with col_n3: st.button("⌫", use_container_width=True, on_click=backspace)

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
