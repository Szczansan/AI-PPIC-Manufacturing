import streamlit as st
import pandas as pd
from PIL import Image
import io
from streamlit_cropper import st_cropper
from modules import (
    inject_premium_theme, protect_page, get_master_products, manage_product,
    upload_part_image, delete_part_image
)

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="Master Part", layout="wide")
inject_premium_theme()
protect_page('master_data')

st.title("⚙️ Master Finish Good (Part)")

# --- HELPER FUNCTIONS ---
def safe_int(val):
    try: return int(float(val)) if pd.notna(val) and val != '' else 0
    except: return 0

def safe_float(val):
    try: return float(val) if pd.notna(val) and val != '' else 0.0
    except: return 0.0

def safe_str(val):
    return str(val) if pd.notna(val) else ""

def process_image(cropped_img):
    """Resize dan Compress gambar di memori jadi WebP biar irit storage"""
    img = cropped_img.resize((400, 400), Image.Resampling.LANCZOS)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='WEBP', quality=80)
    img_byte_arr.seek(0)
    return img_byte_arr.read()

# ==========================================
# 2. LOAD DATA
# ==========================================
df = get_master_products()

# ==========================================
# 3. TABS UI
# ==========================================
tab_view, tab_add = st.tabs(["📋 Database & Edit (Excel Mode)", "➕ Tambah Part Baru"])

# ==========================================
# TAB 1: VIEW & EDIT (EXCEL MODE & IMAGE ISOLATED)
# ==========================================
with tab_view:
    if df.empty:
        st.info("Belum ada data part di database.")
    else:
        # 1. Mapping Nama Kolom (Sudah ditambah Mat. Mixing & % Mix)
        col_mapping = {
            "id": "ID_DB", 
            "customer": "Customer", "model": "Model", "part_name": "Part Name",
            "part_no": "Part No", "mc_id": "M/C ID", "inventory_id": "Inventory ID", 
            "cav": "Cav", "material_type": "Mat. Type", "material_grade": "Mat. Grade",
            "material_color": "Mat. Color", "material_mix": "Mat. Mixing", 
            "composition_percentage": "% Mix", "spq": "SPQ", 
            "std_cycle_time": "Cycle Time (s)", "part_weight": "Part Weight (g)", 
            "runner_weight": "Runner Weight (g)", "status": "Status", 
            "created_at": "Update AT", "image_url": "Image URL"
        }
        
        reverse_mapping = {v: k for k, v in col_mapping.items()}
        available_cols = [c for c in col_mapping.keys() if c in df.columns]
        df_display = df[available_cols].rename(columns=col_mapping)

        # --- 2. FILTER ALA EXCEL ---
        with st.expander("🔍 PANEL FILTER", expanded=False):
            filter_data = {}
            columns_to_filter = [c for c in df_display.columns if c not in ["ID_DB", "Update AT", "Image URL"]]
            cols_per_row = 5 
            
            for i in range(0, len(columns_to_filter), cols_per_row):
                cols_ui = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    if i + j < len(columns_to_filter):
                        col_name = columns_to_filter[i + j]
                        unique_options = sorted(df_display[col_name].astype(str).unique().tolist())
                        with cols_ui[j]:
                            selected = st.multiselect(
                                f"{col_name}", unique_options,
                                placeholder="All", key=f"filter_{col_name}"
                            )
                            if selected: filter_data[col_name] = selected

        # Logic Filtering
        df_final_view = df_display.copy()
        if filter_data:
            for col_name, selected_items in filter_data.items():
                df_final_view = df_final_view[df_final_view[col_name].astype(str).isin(selected_items)]
        
        df_final_view = df_final_view.reset_index(drop=True)

        # --- 3. TOGGLE SAFETY LOCK ---
        st.markdown("<br>", unsafe_allow_html=True)
        c_tog1, c_tog2 = st.columns([1, 3])
        with c_tog1:
            edit_mode = st.toggle("🛠️ Aktifkan Mode Edit", value=False)
        
        with c_tog2:
            if edit_mode:
                st.info("💡 **Mode Edit Aktif:** Double-click pada cell untuk mengubah data (Termasuk Mat. Mix & %).")
            else:
                st.caption("🔒 **Mode View:** Tabel terkunci dari perubahan tidak disengaja.")

        disabled_setting = ["ID_DB", "Update AT", "Image URL"] if edit_mode else True

        # --- 4. EXCEL-LIKE DATA EDITOR ---
        edited_data = st.data_editor(
            df_final_view,
            key="part_editor",
            use_container_width=True,
            hide_index=True,
            height=400,
            disabled=disabled_setting,
            column_config={
                "ID_DB": None, 
                "Update AT": st.column_config.DatetimeColumn(format="D MMM YYYY, HH:mm"),
                "M/C ID": st.column_config.TextColumn(help="Preferred Machine"),
                "Image URL": st.column_config.LinkColumn("Foto Part (Edit di bawah)")
            }
        )

        # --- 5. LOGIC SAVE PERUBAHAN TEKS/ANGKA ---
        if edit_mode and "part_editor" in st.session_state and st.session_state["part_editor"]["edited_rows"]:
            st.warning("⚠️ Ada perubahan data yang belum disimpan!")
            if st.button("💾 Simpan Perubahan Tabel", type="primary"):
                changes = st.session_state["part_editor"]["edited_rows"]
                success_count = 0
                error_msgs = []
                
                for row_idx, col_changes in changes.items():
                    target_id = df_final_view.loc[int(row_idx), 'ID_DB']
                    payload = {}
                    
                    for ui_col, new_val in col_changes.items():
                        db_col = reverse_mapping[ui_col]
                        payload[db_col] = new_val
                    
                    if payload:
                        success, msg = manage_product('UPDATE', payload, target_id)
                        if success: 
                            success_count += 1
                        else:
                            error_msgs.append(msg)
                
                if success_count > 0:
                    st.success(f"✅ {success_count} Part berhasil di-update!")
                    st.rerun()
                if error_msgs:
                    for e in error_msgs: st.error(e)

        # ==========================================
        # 6. ISOLATED IMAGE EDITOR & DELETE PART
        # ==========================================
        st.markdown("---")
        st.subheader("📷 Update Foto Part Khusus")
        
        c_img1, c_img2 = st.columns([1, 2])
        with c_img1:
            part_options = df['part_name'].tolist()
            selected_img_part = st.selectbox("Pilih Part:", part_options, index=None, placeholder="Cari nama part untuk ubah foto...")
            
            if selected_img_part:
                curr_data = df[df['part_name'] == selected_img_part].iloc[0]
                
                st.markdown("**Foto Saat Ini:**")
                old_img_url = curr_data.get('image_url')
                if pd.notna(old_img_url) and old_img_url not in ['-', 'None', '']:
                    st.image(old_img_url, width=150)
                else:
                    st.info("Belum ada foto.")

                with st.expander("🗑️ Hapus Part (Danger Zone)"):
                    st.warning("Tindakan ini akan menghapus data part beserta fotonya secara permanen.")
                    if st.button(f"Hapus Permanen {curr_data['part_no']}", type="primary"):
                        success, msg = manage_product('DELETE', target_id=curr_data['id'])
                        if success: st.success(msg); st.rerun()
                        else: st.error(msg)

        with c_img2:
            if selected_img_part:
                edit_img_file = st.file_uploader("Upload Foto Baru", type=['png', 'jpg', 'jpeg'], key="upd_img")
                cropped_edit_img = None
                
                if edit_img_file:
                    img_edit = Image.open(edit_img_file)
                    st.markdown("**Sesuaikan Potongan Foto (1:1):**")
                    cropped_edit_img = st_cropper(img_edit, aspect_ratio=(1, 1), box_color='#00FF00', key="crop_edit")
                    
                    if st.button("💾 Simpan Foto Baru", type="primary"):
                        img_bytes = process_image(cropped_edit_img)
                        success_up, result_up = upload_part_image(img_bytes, curr_data['part_no'])
                        
                        if success_up:
                            delete_part_image(old_img_url)
                            success_db, msg_db = manage_product('UPDATE', {"image_url": result_up}, curr_data['id'])
                            
                            if success_db:
                                st.success("✅ Foto berhasil diperbarui!")
                                st.rerun()
                            else:
                                st.error(f"❌ Gagal simpan URL ke database: {msg_db}")
                        else:
                            st.error(f"❌ Gagal upload foto: {result_up}")


# ==========================================
# TAB 2: TAMBAH BARU
# ==========================================
with tab_add:
    st.subheader("📝 Registrasi Part Baru")
    
    add_img_file = st.file_uploader("Upload Foto Part", type=['png', 'jpg', 'jpeg'], key="add_img")
    cropped_add_img = None
    if add_img_file:
        img_add = Image.open(add_img_file)
        cropped_add_img = st_cropper(img_add, aspect_ratio=(1, 1), box_color='#00FF00', key="crop_add")

    with st.form("form_add_part"):
        c1, c2, c3 = st.columns(3)
        add_name = c1.text_input("Part Name *")
        add_no = c2.text_input("Part No *")
        add_model = c3.text_input("Model / Project")
        
        c4, c5, c6 = st.columns(3)
        add_cust = c4.text_input("Customer")
        add_inv_id = c5.text_input("Inventory ID (Client Code)") 
        add_mc_id = c6.text_input("Machine ID (M/C)", placeholder="Ex: M-01")
        
        st.markdown("##### 🧪 Material & Packaging")
        # --- PERUBAHAN: Form Material dipecah jadi 2 baris ---
        m1, m2, m3 = st.columns(3)
        add_mat_type = m1.text_input("Mat. Type")
        add_mat_grade = m2.text_input("Mat. Grade")
        add_mat_col = m3.text_input("Mat. Color")
        
        m4, m5, m6 = st.columns(3)
        add_mat_mix = m4.text_input("Material Mix (MB)") # <--- NEW
        add_comp_perc = m5.text_input("% Mix", placeholder="Ex: 5% atau 1:25") # <--- NEW
        add_spq = m6.number_input("SPQ", min_value=1, value=1)

        st.markdown("##### 🏭 Production Specs")
        p1, p2, p3, p4 = st.columns(4)
        add_ct = p1.number_input("Cycle Time", min_value=0.0)
        add_pw = p2.number_input("Part Weight", min_value=0.0)
        add_rw = p3.number_input("Runner Weight", min_value=0.0)
        add_cav = p4.number_input("Cavity", min_value=1, value=1)
        
        if st.form_submit_button("🚀 SIMPAN PART BARU", type="primary"):
            if not add_name or not add_no:
                st.error("Nama Part dan Part No Wajib Diisi!")
            else:
                image_url = None
                if cropped_add_img:
                    img_bytes = process_image(cropped_add_img)
                    success_up, result_up = upload_part_image(img_bytes, add_no)
                    if success_up: image_url = result_up

                payload = {
                    "part_name": add_name, "part_no": add_no, "model": add_model,
                    "customer": add_cust, "inventory_id": add_inv_id, "mc_id": add_mc_id,
                    "spq": add_spq, "cav": add_cav, "material_type": add_mat_type, 
                    "material_grade": add_mat_grade, "material_color": add_mat_col,
                    "material_mix": add_mat_mix, "composition_percentage": add_comp_perc, # <--- NEW DI PAYLOAD
                    "std_cycle_time": add_ct, "part_weight": add_pw, "runner_weight": add_rw,
                    "image_url": image_url
                }
                success, msg = manage_product('INSERT', payload)
                if success: st.success(msg); st.rerun()
                else: st.error(msg)