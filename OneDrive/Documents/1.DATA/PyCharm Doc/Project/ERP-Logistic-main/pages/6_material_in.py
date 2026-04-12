import streamlit as st
import pandas as pd
import time
from datetime import date, timedelta
from modules import (
    inject_premium_theme, protect_page, 
    get_master_materials, get_material_in_history, submit_incoming_material_cart,
    get_child_parts, get_child_in_history, submit_incoming_child_cart,
    get_open_vendor_pos, update_log_bulk, get_incoming_history_filtered # <--- Pastikan import fungsi baru ini
)

st.set_page_config(page_title="Incoming Material", page_icon="📥", layout="wide")
inject_premium_theme()
protect_page("material")

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📥 Incoming Material & Parts")

# --- SESSION STATE (KERANJANG) ---
if 'cart_resin_in' not in st.session_state: st.session_state.cart_resin_in = []
if 'cart_child_in' not in st.session_state: st.session_state.cart_child_in = []

# Tab Navigasi
tab1, tab2, tab3 = st.tabs(["🛢️ Resin", "🔩 Child Part", "📜 Riwayat & Edit"])

# ==========================================
# TAB 1: RESIN (Input Only)
# ==========================================
with tab1:
    df_mat = get_master_materials()
    df_vpo = get_open_vendor_pos()
    po_list = df_vpo['po_number'].tolist() if not df_vpo.empty else []

    if df_mat.empty:
        st.warning("Master Material Kosong.")
    else:
        # Header Resin
        with st.container():
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.subheader("1. Informasi Surat Jalan (Header)")
            c1, c2, c3, c4, c5 = st.columns(5)
            trx_date = c1.date_input("Tanggal Datang", value=date.today(), key="d_res")
            sel_po = c2.selectbox("No. PO (Opsional)", po_list, index=None, placeholder="Pilih / Kosongkan", key="po_res")
            doc_no = c3.text_input("No. SJ / DO Supplier", key="sj_res")
            supp_name = c4.text_input("Nama Supplier", key="sup_res")
            checker = c5.text_input("Diterima Oleh", key="chk_res")
            st.markdown('</div>', unsafe_allow_html=True)

        # Input Item Resin
        col_input, col_cart = st.columns([1, 1.5])
        with col_input:
            st.markdown("### 2. Input Barang")
            mat_list = df_mat['full_name'].tolist()
            selected_name = st.selectbox("Pilih Material", mat_list, key="sel_mat_res")
            mat_obj = df_mat[df_mat['full_name'] == selected_name].iloc[0]
            mat_id = mat_obj['id']
            qty_input = st.number_input("Qty (Kg)", min_value=0.0, step=25.0, key="qty_res")
            item_note = st.text_input("Catatan Item", key="note_res")
            
            if st.button("➕ Tambah List", key="add_res"):
                if qty_input > 0:
                    st.session_state.cart_resin_in.append({
                        "id": mat_id, "name": selected_name, "qty": qty_input, "notes": item_note
                    })
                    st.rerun()

        # Cart Resin
        with col_cart:
            st.markdown("### 3. List Barang")
            if st.session_state.cart_resin_in:
                st.dataframe(pd.DataFrame(st.session_state.cart_resin_in)[['name', 'qty', 'notes']], hide_index=True)
                if st.button("🗑️ Reset List", key="clr_res"):
                    st.session_state.cart_resin_in = []
                    st.rerun()
                
                st.divider()
                if st.button("💾 SIMPAN DATA", type="primary", use_container_width=True, key="save_res"):
                    if not doc_no or not supp_name:
                        st.error("Header Wajib Diisi!")
                    else:
                        header_data = {"date": trx_date, "doc_no": doc_no, "supplier": supp_name, "input_by": checker, "po_no": sel_po}
                        ok, msg = submit_incoming_material_cart(header_data, st.session_state.cart_resin_in)
                        if ok:
                            st.success(msg)
                            st.session_state.cart_resin_in = []
                            time.sleep(1)
                            st.rerun()
                        else: st.error(msg)
            else: st.info("List Kosong")

# ==========================================
# TAB 2: CHILD PART (Sudah Dibalikin Full Code-nya)
# ==========================================
with tab2:
    df_child = get_child_parts()
    po_list_cp = po_list # Pakai list PO yang sama
    
    if df_child.empty:
        st.warning("Master Child Part Kosong.")
    else:
        # Header Child Part
        with st.container():
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.subheader("1. Informasi Surat Jalan (Header)")
            c1, c2, c3, c4, c5 = st.columns(5)
            trx_date_cp = c1.date_input("Tanggal Datang", value=date.today(), key="d_cp")
            sel_po_cp = c2.selectbox("No. PO (Opsional)", po_list_cp, index=None, placeholder="Pilih / Kosongkan", key="po_cp")
            doc_no_cp = c3.text_input("No. SJ / DO Supplier", key="sj_cp")
            supp_cp = c4.text_input("Nama Supplier", key="sup_cp")
            checker_cp = c5.text_input("Diterima Oleh", key="chk_cp")
            st.markdown('</div>', unsafe_allow_html=True)

        # Input Item Child Part
        col_input_cp, col_cart_cp = st.columns([1, 1.5])
        with col_input_cp:
            st.markdown("### 2. Input Komponen")
            cp_list = df_child['part_name'].tolist()
            sel_cp = st.selectbox("Pilih Komponen", cp_list, key="sel_cp_nm")
            cp_obj = df_child[df_child['part_name'] == sel_cp].iloc[0]
            cp_id = cp_obj['id']
            qty_cp = st.number_input("Qty (Pcs)", min_value=0, step=1, key="q_cp_in")
            item_note_cp = st.text_input("Catatan", key="n_cp_in")
            
            if st.button("➕ Tambah ke List", key="add_cp"):
                if qty_cp > 0:
                    st.session_state.cart_child_in.append({
                        "id": cp_id, "name": sel_cp, "qty": qty_cp, "notes": item_note_cp
                    })
                    st.rerun()

        # Cart Child Part
        with col_cart_cp:
            st.markdown("### 3. List Komponen")
            if st.session_state.cart_child_in:
                st.dataframe(pd.DataFrame(st.session_state.cart_child_in)[['name', 'qty', 'notes']], hide_index=True)
                if st.button("🗑️ Reset List", key="clr_cp"):
                    st.session_state.cart_child_in = []
                    st.rerun()

                st.divider()
                if st.button("💾 SIMPAN DATA", type="primary", use_container_width=True, key="save_cp"):
                    if not doc_no_cp or not supp_cp:
                        st.error("Header Wajib Diisi!")
                    else:
                        header_data_cp = {"date": trx_date_cp, "doc_no": doc_no_cp, "supplier": supp_cp, "input_by": checker_cp, "po_no": sel_po_cp}
                        ok, msg = submit_incoming_child_cart(header_data_cp, st.session_state.cart_child_in)
                        if ok:
                            st.success(msg)
                            st.session_state.cart_child_in = []
                            time.sleep(1)
                            st.rerun()
                        else: st.error(msg)
            else: st.info("List Kosong")

# ==========================================
# TAB 3: RIWAYAT & EDIT (EXCEL STYLE + FILTER)
# ==========================================
with tab3:
    st.subheader("📜 Riwayat Kedatangan")
    
    # --- 1. FILTERING AREA ---
    with st.container():
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        c_head1, c_head2 = st.columns([2, 1])
        cat_option = c_head1.radio("Pilih Kategori:", ["Resin", "Child Part"], horizontal=True)
        is_edit_mode = c_head2.toggle("✏️ Mode Edit", value=False)
        
        st.divider()
        c_f1, c_f2, c_f3 = st.columns([1, 1, 2])
        filter_start = c_f1.date_input("Mulai Tanggal", value=date.today() - timedelta(days=7))
        filter_end = c_f2.date_input("Sampai Tanggal", value=date.today())
        search_txt = c_f3.text_input("🔍 Cari PO / Surat Jalan / Supplier / Barang", placeholder="Ketik kata kunci di sini...")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- 2. PULL DATA & SETUP MASTER DROPDOWN ---
    category_code = 'RESIN' if cat_option == "Resin" else 'CHILD_PART'
    
    # [NEW] Tarik Master Data buat Dropdown & Mapping ID
    if category_code == 'RESIN':
        df_master_item = get_master_materials()
        options_item = df_master_item['full_name'].tolist() if not df_master_item.empty else []
        name_to_id = dict(zip(df_master_item['full_name'], df_master_item['id']))
    else:
        df_master_item = get_child_parts()
        options_item = df_master_item['part_name'].tolist() if not df_master_item.empty else []
        name_to_id = dict(zip(df_master_item['part_name'], df_master_item['id']))

    df_hist = get_incoming_history_filtered(category_code, filter_start, filter_end, search_txt)

    if not df_hist.empty:
        df_hist['po_number'] = df_hist['po_number'].fillna("").astype(str).replace("None", "")
        df_hist['date_in'] = pd.to_datetime(df_hist['date_in']).dt.date
        
        cols_to_show = ['id', 'date_in', 'po_number', 'doc_no', 'item_name', 'qty', 'supplier', 'input_by', 'notes', 'is_void']
        df_display = df_hist[cols_to_show].copy()

        df_display['is_void'] = df_display['is_void'].fillna(False).astype(bool)

        if is_edit_mode:
            st.info("💡 **Mode Edit Aktif:** Semua kolom bisa diedit. Centang 'Void' untuk membatalkan transaksi.")
            
            edited_df = st.data_editor(
                df_display,
                key="editor_log",
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                disabled=['id'], # [UPDATED] Cuman ID yang dikunci, sisanya bebas diedit
                column_config={
                    "date_in": st.column_config.DateColumn("Date IN", format="YYYY-MM-DD", required=True),
                    "po_number": st.column_config.TextColumn("PO Reference"),
                    "doc_no": st.column_config.TextColumn("Surat Jalan", required=True),
                    "item_name": st.column_config.SelectboxColumn("Nama Barang", options=options_item, required=True), # [UPDATED] Jadi Dropdown
                    "qty": st.column_config.NumberColumn("Qty", min_value=0, required=True),
                    "supplier": st.column_config.TextColumn("Supplier"),
                    "input_by": st.column_config.TextColumn("Penerima"),
                    "notes": st.column_config.TextColumn("Notes"),
                    "is_void": st.column_config.CheckboxColumn("Void? ❌"),
                    "id": None # Sembunyikan ID dari UI
                }
            )
            
            if st.button("💾 Simpan Perubahan Excel", type="primary"):
                with st.spinner("Menyimpan semua baris..."):
                    # [NEW] Balikin text nama barang menjadi ID buat di-save ke DB
                    id_col = "material_id" if category_code == 'RESIN' else "child_part_id"
                    edited_df[id_col] = edited_df['item_name'].map(name_to_id)
                    
                    success, msg = update_log_bulk(category_code, edited_df)
                    if success:
                        st.toast(msg, icon="✅")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        else:
            # Mode View Biasa
            st.dataframe(
                df_display.drop(columns=['id']), 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "date_in": "Date IN",
                    "po_number": "PO Reference",
                    "doc_no": "Surat Jalan",
                    "item_name": "Nama Barang",
                    "qty": "Qty",
                    "supplier": "Supplier",
                    "input_by": "Penerima",
                    "notes": "Notes",
                    "is_void": "Void?"
                }
            )
    else:
        st.info("Tidak ada data ditemukan untuk pencarian atau range tanggal tersebut.")