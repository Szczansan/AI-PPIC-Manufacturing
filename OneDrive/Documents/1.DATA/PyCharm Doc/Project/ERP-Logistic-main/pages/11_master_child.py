import streamlit as st
import pandas as pd
import time
from modules import (
    inject_premium_theme, protect_page, 
    add_new_child_part, get_child_parts, 
    update_child_part, delete_child_part # <--- Import fungsi baru
)

st.set_page_config(page_title="Master Child Part", layout="wide")
inject_premium_theme()
protect_page("master_data")

# --- HEADER ---
st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("🔩 Master Data: Child Parts")
st.caption("Database Komponen / Sub-Material (Baut, Mur, Dus, dll).")

# ==========================================
# 1. INPUT CHILD PART BARU
# ==========================================
with st.expander("➕ Tambah Child Part Baru", expanded=False):
    with st.form("add_child"):
        c1, c2 = st.columns(2)
        with c1:
            part_name = st.text_input("Part Name", placeholder="Contoh: Baut M6 x 10")
            part_no = st.text_input("Part Number", placeholder="Contoh: CP-BT-M6")
        with c2:
            # Dropdown UOM disamakan opsinya
            uom_opts = ["Pcs", "Set", "Kg", "Meter", "ML", "Roll", "Lembar", "Box"]
            uom = st.selectbox("Satuan (UOM)", uom_opts)
            min_stk = st.number_input("Min. Stock Alert", min_value=0, value=100)
            
        if st.form_submit_button("Simpan Database"):
            if part_name and part_no:
                # Panggil fungsi add yg baru (4 parameter)
                success, msg = add_new_child_part(part_name, part_no, uom, min_stk)
                if success:
                    st.success(msg)
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else: st.error(msg)
            else:
                st.error("Nama & Nomor Part wajib diisi!")

# ==========================================
# 2. TABEL CHILD PART (SAFE MODE)
# ==========================================
st.divider()

# Load Data
df_child = get_child_parts()

if not df_child.empty:
    # --- PRE-PROCESSING ---
    # 1. Format Tanggal
    if 'created_at' in df_child.columns:
        df_child['created_at'] = pd.to_datetime(df_child['created_at']).dt.strftime('%d %B %Y')
    
    # 2. Tambah Kolom Delete
    if 'delete' not in df_child.columns:
        df_child['delete'] = False

    # --- SAFETY TOGGLE ---
    col_t1, col_t2 = st.columns([1, 4])
    with col_t1:
        is_editing = st.toggle("🔓 Buka Kunci Edit / Hapus", value=False)
    with col_t2:
        if is_editing:
            st.warning("⚠️ Mode Edit Aktif! Harap berhati-hati mengubah data.")
        else:
            st.info("🔒 Mode Lihat (Read-Only). Geser tombol di kiri untuk mengubah data.")

    # --- DATA EDITOR ---
    edited_df = st.data_editor(
        df_child,
        key="editor_child",
        disabled=not is_editing, # Logic Kunci
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.NumberColumn("System ID", disabled=True, width="small"),
            "part_name": st.column_config.TextColumn("Part Name", required=True, width="medium"),
            "part_no": st.column_config.TextColumn("Part Number", required=True, width="medium"),
            "uom": st.column_config.SelectboxColumn("UOM", options=["Pcs", "Set", "Kg", "Meter", "ML", "Roll", "Lembar", "Box"], required=True, width="small"),
            "min_stock": st.column_config.NumberColumn("Min. Stock", required=True, width="small"),
            "created_at": st.column_config.TextColumn("Created Date", disabled=True),
            "delete": st.column_config.CheckboxColumn("Hapus?", default=False)
        },
        column_order=["delete", "part_name", "part_no", "uom", "min_stock", "created_at"]
    )

    # --- ACTION BUTTONS ---
    if is_editing:
        st.write("")
        col_act1, col_act2 = st.columns(2)
        
        # 1. LOGIC SIMPAN
        with col_act1:
            if st.button("💾 Simpan Perubahan", use_container_width=True):
                st.session_state['confirm_save_child'] = True
            
            if st.session_state.get('confirm_save_child'):
                with st.container(border=True):
                    st.warning("❓ Anda yakin ingin menyimpan perubahan data ini?")
                    c_yes, c_no = st.columns(2)
                    if c_yes.button("✅ Ya, Simpan", key="yes_save_c"):
                        changes = 0
                        for index, row in edited_df.iterrows():
                            # Update ke DB
                            update_child_part(row['id'], row['part_name'], row['part_no'], row['uom'], row['min_stock'])
                            changes += 1
                        
                        st.success(f"✅ {changes} Data Berhasil Diupdate!")
                        st.session_state['confirm_save_child'] = False
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
                    
                    if c_no.button("❌ Batal", key="no_save_c"):
                        st.session_state['confirm_save_child'] = False
                        st.rerun()

        # 2. LOGIC HAPUS
        with col_act2:
            to_delete = edited_df[edited_df['delete'] == True]
            count_del = len(to_delete)
            
            btn_lbl = f"🗑️ Hapus ({count_del}) Item" if count_del > 0 else "🗑️ Hapus (Pilih Dulu)"
            if st.button(btn_lbl, type="primary", disabled=(count_del==0), use_container_width=True):
                st.session_state['confirm_del_child'] = True
            
            if st.session_state.get('confirm_del_child'):
                with st.container(border=True):
                    st.error(f"🚨 Yakin Hapus {count_del} Child Part secara PERMANEN? Data tidak bisa kembali.")
                    d_yes, d_no = st.columns(2)
                    if d_yes.button("💀 Ya, Hapus Permanen", key="yes_del_c"):
                        for index, row in to_delete.iterrows():
                            delete_child_part(row['id'])
                        
                        st.success(f"✅ {count_del} Data Telah Dihapus.")
                        st.session_state['confirm_del_child'] = False
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
                        
                    if d_no.button("❌ Batalkan", key="no_del_c"):
                        st.session_state['confirm_del_child'] = False
                        st.rerun()

else:
    st.info("Belum ada data Child Parts.")