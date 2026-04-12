import streamlit as st
import pandas as pd
from modules import inject_premium_theme, protect_page, get_master_boxes, manage_master_box
import time

st.set_page_config(page_title="Master Box", layout="wide")
inject_premium_theme()
protect_page("master") # Butuh akses master

st.title("📦 Master Database Box & Packaging")

# Ambil data master
df_box = get_master_boxes()

# --- TAMPILAN DATA ---
st.subheader("📋 List Box Terdaftar")
if not df_box.empty:
    st.dataframe(df_box[['box_name', 'specification', 'model', 'customer']], use_container_width=True, hide_index=True)
else:
    st.info("Belum ada data Box.")

st.divider()

# --- MODE INPUT / EDIT ---
edit_mode = st.toggle("🛠️ Aktifkan Mode Edit / Hapus Data")

if not edit_mode:
    st.subheader("➕ Tambah Box Baru")
    with st.form("form_add_box", clear_on_submit=True):
        col1, col2 = st.columns(2)
        b_name = col1.text_input("Nama Box (Wajib)*")
        b_spec = col2.text_input("Spesifikasi / Ukuran")
        b_model = col1.text_input("Model Part")
        b_cust = col2.text_input("Customer")
        
        if st.form_submit_button("Simpan Box", use_container_width=True, type="primary"):
            if not b_name:
                st.error("Nama Box wajib diisi, Bre!")
            else:
                payload = {"box_name": b_name.upper(), "specification": b_spec, "model": b_model, "customer": b_cust}
                sukses, pesan = manage_master_box('INSERT', payload)
                
                # --- UBAH BAGIAN INI ---
                if sukses: 
                    st.toast(pesan, icon="✅") # Muncul popup kecil
                    time.sleep(1)             # Jeda 1 detik biar kebaca
                    st.rerun()                # Refresh page full
                else: 
                    st.error(pesan)
else:
    st.subheader("✏️ Edit / Hapus Box")
    if df_box.empty:
        st.warning("Data kosong, tidak ada yang bisa diedit.")
    else:
        # Bikin dictionary buat mapping nama ke ID
        box_dict = {row['box_name']: row for _, row in df_box.iterrows()}
        selected_box_name = st.selectbox("Pilih Box yang mau diedit:", list(box_dict.keys()))
        
        if selected_box_name:
            curr_data = box_dict[selected_box_name]
            
            with st.form("form_edit_box"):
                e_name = st.text_input("Nama Box", value=curr_data['box_name'])
                e_spec = st.text_input("Spesifikasi", value=curr_data.get('specification', ''))
                e_model = st.text_input("Model Part", value=curr_data.get('model', ''))
                e_cust = st.text_input("Customer", value=curr_data.get('customer', ''))
                
                c1, c2 = st.columns(2)
                btn_update = c1.form_submit_button("💾 Update Data", type="primary", use_container_width=True)
                btn_delete = c2.form_submit_button("🗑️ Hapus Box", use_container_width=True)
                
                if btn_update:
                    payload = {"box_name": e_name.upper(), "specification": e_spec, "model": e_model, "customer": e_cust}
                    sukses, pesan = manage_master_box('UPDATE', payload, curr_data['id'])
                    if sukses: st.success(pesan); st.rerun()
                    else: st.error(pesan)
                    
                if btn_delete:
                    sukses, pesan = manage_master_box('DELETE', None, curr_data['id'])
                    if sukses: st.success(pesan); st.rerun()
                    else: st.error(pesan)