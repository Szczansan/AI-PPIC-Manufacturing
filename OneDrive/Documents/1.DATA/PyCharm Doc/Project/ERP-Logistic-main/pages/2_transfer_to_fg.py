import streamlit as st
import pandas as pd
from datetime import date, timedelta
import time
from modules import (
    inject_premium_theme, protect_page, get_master_products, 
    submit_wip_out_cart, get_wip_out_history_paged,
    get_wip_stock_balance, update_wip_out_bulk
)

# 1. Config & Security
st.set_page_config(page_title="Transfer to FG", layout="wide")
inject_premium_theme()
protect_page('warehouse')

# --- [SAFETY]: DIALOG KONFIRMASI ---
@st.dialog("Konfirmasi Perubahan")
def confirm_save_dialog(changed_rows, full_edited_df, df_parts_master):
    st.warning(f"⚠️ Lo akan ngerubah **{len(changed_rows)}** baris data riwayat!")
    
    # Tampilkan ringkasan apa yang dirubah
    st.write("Item yang lo edit:")
    # Tambahin kolom sender di tabel konfirmasi
    st.table(changed_rows[['doc_no', 'part_name', 'qty', 'sender', 'receiver']])
    
    st.write("Apakah data ini udah bener?")
    
    c1, c2 = st.columns(2)
    if c1.button("❌ Batal", use_container_width=True):
        st.rerun()
        
    if c2.button("✅ Ya, Simpan!", type="primary", use_container_width=True):
        with st.spinner("Menyimpan ke Database..."):
            success, msg = update_wip_out_bulk(full_edited_df, df_parts_master)
            if success:
                st.success(msg)
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(msg)

# --- INISIALISASI SESSION STATE ---
if 'cart_fg' not in st.session_state:
    st.session_state['cart_fg'] = []

st.title("📦 Transfer WIP to Finish Good (FG)")

# TABS
tab_form, tab_hist = st.tabs(["📝 Input Transfer (Multi-Item)", "🗄️ Riwayat Transfer"])

# ==========================================
# TAB 1: FORM INPUT DENGAN KERANJANG
# ==========================================
with tab_form:
    # --- BAGIAN 1: HEADER DOKUMEN ---
    with st.container(border=True):
        st.markdown("### 1. Header Dokumen")
        hc1, hc2, hc3, hc4 = st.columns(4) # Pecah jadi 4 kolom
        
        with hc1:
            trx_date = st.date_input("Tanggal Transfer", date.today())
        with hc2:
            doc_no = st.text_input("No Dokumen / Surat Jalan", placeholder="Contoh: TF/FG/26/001")
        with hc3:
            # List Sender (WIP Side) - Lo bisa sesuaikan namanya di sini
            sender_opts = ["EKA", "SAM"] 
            sender = st.selectbox("Yang Menyerahkan (WIP)", sender_opts)
        with hc4:
            receiver_opts = ["AQIL", "RUDI H", "SOLIHIN", "IMAM H", "DEDE"]
            receiver = st.selectbox("Diterima Oleh (FG)", receiver_opts)

    # --- BAGIAN 2: INPUT ITEM ---
    with st.container(border=True):
        st.markdown("### 2. Input Item")
        df_part = get_master_products()
        part_list = df_part['part_name'].tolist() if not df_part.empty else []
        
        col_inp1, col_inp2 = st.columns([2, 1])
        with col_inp1:
            selected_part = st.selectbox("Pilih Barang", part_list, index=None, placeholder="Cari Part Name...", key="wip_part_select")
        
        curr_part_no = ""
        current_wip_stock = 0
        if selected_part and not df_part.empty:
            curr_part_no = df_part[df_part['part_name'] == selected_part]['part_no'].values[0]
            current_wip_stock = get_wip_stock_balance(curr_part_no)
            if current_wip_stock <= 0:
                st.warning(f"⚠️ Stok WIP: {current_wip_stock} Pcs (Kosong/Minus)")
            else:
                st.info(f"📦 Stok WIP Tersedia: {current_wip_stock} Pcs")

        ic1, ic2, ic3 = st.columns([1, 1, 2])
        with ic1:
            qty_input = st.number_input("Qty Transfer", min_value=1, value=1, step=1, key="wip_qty")
        with ic2:
            st.text_input("Part No", value=curr_part_no, disabled=True)
        with ic3:
            notes_input = st.text_input("Catatan Item", placeholder="Cth: Box 1", key="wip_notes")

        if st.button("➕ Tambah ke Keranjang", use_container_width=True):
            if not selected_part or qty_input <= 0:
                st.error("⚠️ Pilih barang dan isi Qty dengan benar!")
            else:
                if qty_input > current_wip_stock:
                    st.toast(f"⚠️ Perhatian: Qty ({qty_input}) melebihi Stok System ({current_wip_stock})!", icon="⚠️")
                
                item_data = {
                    "part_name": selected_part,
                    "part_no": curr_part_no,
                    "qty": qty_input,
                    "notes": notes_input
                }
                st.session_state['cart_fg'].append(item_data)
                st.success(f"✅ {selected_part} masuk keranjang!")

    # --- BAGIAN 3: REVIEW KERANJANG & SUBMIT ---
    if st.session_state['cart_fg']:
        st.divider()
        st.markdown(f"### 🛒 Keranjang Transfer ({len(st.session_state['cart_fg'])} Item)")
        
        # --- HEADER TABEL CUSTOM ---
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([3, 2, 1.2, 2, 0.8])
        h_col1.caption("**Nama Barang**")
        h_col2.caption("**Part No**")
        h_col3.caption("**Qty (Edit)**")
        h_col4.caption("**Catatan**")
        h_col5.caption("**Hapus**")

        # --- LOOPING DATA KERANJANG ---
        for i, item in enumerate(st.session_state['cart_fg']):
            r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([3, 2, 1.2, 2, 0.8])
            r_col1.write(item['part_name'])
            r_col2.code(item['part_no'])
            
            # --- FITUR EDIT QTY LANGSUNG ---
            new_qty = r_col3.number_input("Qty", min_value=1, value=int(item['qty']), key=f"edit_qty_{i}", label_visibility="collapsed")
            if new_qty != item['qty']:
                st.session_state['cart_fg'][i]['qty'] = new_qty
            
            r_col4.write(item['notes'] if item['notes'] else "-")
            
            if r_col5.button("❌", key=f"del_{i}", help="Hapus item ini"):
                st.session_state['cart_fg'].pop(i)
                st.rerun()

        st.divider()
        ac1, ac2 = st.columns([1, 4])
        with ac1:
            if st.button("🗑️ Hapus Semua", type="secondary", use_container_width=True):
                st.session_state['cart_fg'] = []
                st.rerun()
        with ac2:
            if st.button("🚀 PROSES TRANSFER SEKARANG", type="primary", use_container_width=True):
                if not doc_no:
                    st.error("⚠️ Harap isi Nomor Dokumen / Surat Jalan di bagian Header!")
                else:
                    # Tambahin sender ke header_data
                    header_data = {"date": trx_date, "doc_no": doc_no, "sender": sender, "receiver": receiver}
                    success, msg = submit_wip_out_cart(header_data, st.session_state['cart_fg'])
                    if success:
                        st.balloons(); st.success(msg); st.session_state['cart_fg'] = []; st.rerun()
                    else: st.error(msg)
    else:
        st.info("ℹ️ Keranjang masih kosong. Silakan input item di atas.")

# ==========================================
# TAB 2: RIWAYAT & EDIT (EXCEL STYLE)
# ==========================================
with tab_hist:
    st.subheader("🗄️ Arsip Transfer FG")
    
    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 1, 1])
        today = date.today()
        d_range = fc1.date_input("Filter Tanggal", value=(today - timedelta(days=7), today))
        
        if isinstance(d_range, tuple) and len(d_range) == 2: start_d, end_d = d_range
        else: start_d, end_d = today, today
            
        search = fc2.text_input("Cari Barang / Penyerah / Penerima / No Dokumen")
        page = fc3.number_input("Halaman", min_value=1, value=1)
        is_edit_mode = fc4.toggle("✏️ Mode Edit", value=False)

    # Load Data Paged
    df_hist, total = get_wip_out_history_paged(page, 10, start_d, end_d, search)
    st.caption(f"Halaman {page}. Total Data: {total}")

    if not df_hist.empty:
        df_hist['date_out'] = pd.to_datetime(df_hist['date_out']).dt.date
        
        if is_edit_mode:
            st.info("💡 **Mode Edit Aktif:** Anda dapat mengubah data langsung di tabel bawah.")
            
            df_parts_master = get_master_products()
            part_names = df_parts_master['part_name'].unique().tolist()
            
            # List opsi untuk selectbox di editor
            s_opts = ["EKA", "SAM"]
            r_opts = ["AQIL", "RUDI H", "SOLIHIN", "IMAM H", "DEDE"]
            
            # Data Editor
            edited_df = st.data_editor(
                df_hist,
                column_config={
                    "id": None, 
                    "date_out": st.column_config.DateColumn("Tanggal", format="YYYY-MM-DD", required=True),
                    "doc_no": st.column_config.TextColumn("Dokumen", required=True),
                    "part_name": st.column_config.SelectboxColumn("Barang", options=part_names, required=True),
                    "part_no": st.column_config.TextColumn("Part No", disabled=True), 
                    "qty": st.column_config.NumberColumn("Jumlah", min_value=0, required=True),
                    "sender": st.column_config.SelectboxColumn("Penyerah", options=s_opts, required=True), # ADDED
                    "receiver": st.column_config.SelectboxColumn("Penerima", options=r_opts, required=True),
                    "notes": st.column_config.TextColumn("Ket")
                },
                use_container_width=True,
                hide_index=True,
                disabled=["id", "part_no", "created_at"]
            )
            
            changed_mask = (edited_df != df_hist).any(axis=1)
            changed_rows = edited_df[changed_mask]

            if st.button("💾 Simpan Perubahan Riwayat", type="primary", use_container_width=True):
                if changed_rows.empty:
                    st.info("Nggak ada perubahan yang dideteksi, Bre.")
                else:
                    confirm_save_dialog(changed_rows, edited_df, df_parts_master)
        else:
            # Tampilan View Biasa (Tambahin sender ke list cols)
            cols = ['date_out', 'doc_no', 'part_name', 'qty', 'sender', 'receiver', 'notes']
            rename = {
                'date_out': 'Tanggal', 
                'doc_no': 'Dokumen', 
                'part_name': 'Barang', 
                'qty': 'Jumlah', 
                'sender': 'Penyerah', 
                'receiver': 'Penerima', 
                'notes': 'Ket'
            }
            st.dataframe(df_hist[cols].rename(columns=rename), hide_index=True, use_container_width=True)
    else:
        st.info("Data tidak ditemukan.")