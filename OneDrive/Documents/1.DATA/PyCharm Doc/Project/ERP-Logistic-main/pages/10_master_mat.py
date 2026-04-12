import streamlit as st
import pandas as pd
import time
from modules import (
    inject_premium_theme, protect_page, 
    # Import Material Functions
    add_new_material, get_master_materials, 
    update_raw_material, delete_raw_material,
    # Import Child Part Functions
    add_new_child_part, get_child_parts, 
    update_child_part, delete_child_part
)

st.set_page_config(page_title="Master Materials & Parts", layout="wide")
inject_premium_theme()
protect_page("master_data") 

# --- HEADER ---
st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📦 Master Data: Materials & Components")
st.caption("Database Terpusat: Raw Material (Resin) & Komponen Pendukung (Child Parts)")

# --- TABS NAVIGASI ---
tab_resin, tab_part = st.tabs(["🛢️ Raw Materials (Resin)", "🔩 Components (Child Parts)"])

# ==========================================
# TAB 1: RAW MATERIALS (RESIN)
# ==========================================
with tab_resin:
    st.subheader("Database Resin & Bahan Baku Utama")
    
    # 1. INPUT MATERIAL BARU
    with st.expander("➕ Tambah Resin Baru", expanded=False):
        with st.form("add_mat"):
            c1, c2 = st.columns(2)
            with c1:
                type_g = st.selectbox("Type Resin", ["ABS", "PP", "PC", "PA6", "POM", "PS","LDPE","Masterbatch","HPR", "Others"])
                mat_g = st.text_input("Material Grade", placeholder="Contoh: Toyolac 700")
            with c2:
                col_g = st.text_input("Color Grade", placeholder="Contoh: Black / Natural")
                
            if st.form_submit_button("Simpan Database Resin"):
                if mat_g and col_g:
                    success, msg = add_new_material(type_g, mat_g, col_g)
                    if success: 
                        st.success(msg)
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else: st.error(msg)
                else: 
                    st.error("Grade & Color wajib diisi!")

    # 2. TABEL MATERIAL (SAFE MODE)
    st.divider()
    
    # Load Data
    df_mat = get_master_materials()

    if not df_mat.empty:
        # Pre-processing
        if 'created_at' in df_mat.columns:
            df_mat['created_at'] = pd.to_datetime(df_mat['created_at']).dt.strftime('%d %B %Y')
        
        if 'delete' not in df_mat.columns:
            df_mat['delete'] = False

        # Safety Toggle Resin
        col_t1, col_t2 = st.columns([1, 4])
        with col_t1:
            is_editing_mat = st.toggle("🔓 Edit Resin", value=False, key="toggle_mat")
        with col_t2:
            if is_editing_mat:
                st.warning("⚠️ Mode Edit Aktif! Harap berhati-hati.")
            else:
                st.info("🔒 Mode Lihat (Read-Only).")

        # Editor Resin
        edited_df_mat = st.data_editor(
            df_mat,
            key="editor_material",
            disabled=not is_editing_mat,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("System ID", disabled=True, width="small"),
                "type_grade": st.column_config.SelectboxColumn("Type", options=["ABS", "PP", "PC", "PA6", "POM", "PS","LDPE","Masterbatch","HPR", "Others"], required=True),
                "material_grade": st.column_config.TextColumn("Grade Name", required=True),
                "color_grade": st.column_config.TextColumn("Color", required=True),
                "full_name": st.column_config.TextColumn("Display Name (Preview)", disabled=True, width="large"),
                "created_at": st.column_config.TextColumn("Created Date", disabled=True),
                "delete": st.column_config.CheckboxColumn("Hapus?", default=False)
            },
            column_order=["delete", "type_grade", "material_grade", "color_grade", "full_name", "created_at"]
        )

        # Action Buttons Resin
        if is_editing_mat:
            st.write("")
            col_act1, col_act2 = st.columns(2)
            
            # SAVE UPDATE
            with col_act1:
                if st.button("💾 Simpan Perubahan Resin", use_container_width=True):
                    st.session_state['confirm_save_mat'] = True
                
                if st.session_state.get('confirm_save_mat'):
                    with st.container(border=True):
                        st.warning("❓ Update data Resin?")
                        c_yes, c_no = st.columns(2)
                        if c_yes.button("✅ Ya, Simpan", key="yes_save_mat"):
                            changes = 0
                            for index, row in edited_df_mat.iterrows():
                                update_raw_material(row['id'], row['type_grade'], row['material_grade'], row['color_grade'])
                                changes += 1
                            st.success("✅ Data Resin Diupdate!")
                            st.session_state['confirm_save_mat'] = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        if c_no.button("❌ Batal", key="no_save_mat"):
                            st.session_state['confirm_save_mat'] = False
                            st.rerun()

            # DELETE
            with col_act2:
                items_del = edited_df_mat[edited_df_mat['delete'] == True]
                count_del = len(items_del)
                if st.button(f"🗑️ Hapus ({count_del}) Resin", type="primary", disabled=(count_del==0), use_container_width=True):
                    st.session_state['confirm_del_mat'] = True
                
                if st.session_state.get('confirm_del_mat'):
                    with st.container(border=True):
                        st.error(f"🚨 Hapus {count_del} Resin Permanen?")
                        d_yes, d_no = st.columns(2)
                        if d_yes.button("💀 Hapus", key="yes_del_mat"):
                            for index, row in items_del.iterrows():
                                delete_raw_material(row['id'])
                            st.success("✅ Resin Dihapus.")
                            st.session_state['confirm_del_mat'] = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        if d_no.button("❌ Batal", key="no_del_mat"):
                            st.session_state['confirm_del_mat'] = False
                            st.rerun()
    else:
        st.info("Belum ada data resin.")


# ==========================================
# TAB 2: CHILD PARTS (KOMPONEN)
# ==========================================
with tab_part:
    st.subheader("Database Komponen & Sub-Material")
    
    # 1. INPUT CHILD PART BARU
    with st.expander("➕ Tambah Komponen Baru", expanded=False):
        with st.form("add_child"):
            c1, c2 = st.columns(2)
            with c1:
                part_name = st.text_input("Part Name", placeholder="Contoh: Baut M6 x 10")
                part_no = st.text_input("Part Number", placeholder="Contoh: CP-BT-M6")
            with c2:
                uom_opts = ["Pcs", "Set", "Kg", "Meter", "ML", "Roll", "Lembar", "Box"]
                uom = st.selectbox("Satuan (UOM)", uom_opts)
                min_stk = st.number_input("Min. Stock Alert", min_value=0, value=100)
                
            if st.form_submit_button("Simpan Database Komponen"):
                if part_name and part_no:
                    success, msg = add_new_child_part(part_name, part_no, uom, min_stk)
                    if success:
                        st.success(msg)
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                    else: st.error(msg)
                else:
                    st.error("Nama & Nomor Part wajib diisi!")

    # 2. TABEL CHILD PART (SAFE MODE)
    st.divider()

    # Load Data
    df_child = get_child_parts()

    if not df_child.empty:
        if 'created_at' in df_child.columns:
            df_child['created_at'] = pd.to_datetime(df_child['created_at']).dt.strftime('%d %B %Y')
        
        if 'delete' not in df_child.columns:
            df_child['delete'] = False

        # Safety Toggle Child
        col_t1, col_t2 = st.columns([1, 4])
        with col_t1:
            is_editing_child = st.toggle("🔓 Edit Komponen", value=False, key="toggle_child")
        with col_t2:
            if is_editing_child:
                st.warning("⚠️ Mode Edit Aktif! Harap berhati-hati.")
            else:
                st.info("🔒 Mode Lihat (Read-Only).")

        # Editor Child
        edited_df_child = st.data_editor(
            df_child,
            key="editor_child",
            disabled=not is_editing_child,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "id": st.column_config.NumberColumn("System ID", disabled=True),
                "part_name": st.column_config.TextColumn("Part Name", required=True, width="medium"),
                "part_no": st.column_config.TextColumn("Part Number", required=True, width="medium"),
                "uom": st.column_config.SelectboxColumn("UOM", options=["Pcs", "Set", "Kg", "Meter", "ML", "Roll", "Lembar", "Box"], required=True, width="small"),
                # min_stock sengaja gak dimasukin ke config biar hidden
                "created_at": st.column_config.TextColumn("Created Date", disabled=True),
                "delete": st.column_config.CheckboxColumn("Hapus?", default=False)
            },
            # Urutan kolom disesuaikan sama request loe (min_stock dihilangkan dari view)
            column_order=["delete", "part_name", "part_no", "uom", "created_at"]
        )

        # Action Buttons Child
        if is_editing_child:
            st.write("")
            col_act1, col_act2 = st.columns(2)
            
            # SAVE UPDATE
            with col_act1:
                if st.button("💾 Simpan Perubahan Komponen", use_container_width=True):
                    st.session_state['confirm_save_child'] = True
                
                if st.session_state.get('confirm_save_child'):
                    with st.container(border=True):
                        st.warning("❓ Update data Komponen?")
                        c_yes, c_no = st.columns(2)
                        if c_yes.button("✅ Ya, Simpan", key="yes_save_c"):
                            changes = 0
                            for index, row in edited_df_child.iterrows():
                                update_child_part(row['id'], row['part_name'], row['part_no'], row['uom'], row['min_stock'])
                                changes += 1
                            st.success("✅ Data Komponen Diupdate!")
                            st.session_state['confirm_save_child'] = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        if c_no.button("❌ Batal", key="no_save_c"):
                            st.session_state['confirm_save_child'] = False
                            st.rerun()

            # DELETE
            with col_act2:
                items_del_c = edited_df_child[edited_df_child['delete'] == True]
                count_del_c = len(items_del_c)
                if st.button(f"🗑️ Hapus ({count_del_c}) Komponen", type="primary", disabled=(count_del_c==0), use_container_width=True):
                    st.session_state['confirm_del_child'] = True
                
                if st.session_state.get('confirm_del_child'):
                    with st.container(border=True):
                        st.error(f"🚨 Hapus {count_del_c} Komponen Permanen?")
                        d_yes, d_no = st.columns(2)
                        if d_yes.button("💀 Hapus", key="yes_del_c"):
                            for index, row in items_del_c.iterrows():
                                delete_child_part(row['id'])
                            st.success("✅ Komponen Dihapus.")
                            st.session_state['confirm_del_child'] = False
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        if d_no.button("❌ Batal", key="no_del_c"):
                            st.session_state['confirm_del_child'] = False
                            st.rerun()
    else:
        st.info("Belum ada data komponen.")