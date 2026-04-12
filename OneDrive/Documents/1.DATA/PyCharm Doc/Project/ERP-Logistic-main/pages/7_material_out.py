import streamlit as st
import pandas as pd
import time
from datetime import date
from modules import (
    inject_premium_theme, protect_page, 
    get_master_materials, get_material_stock_view, get_material_out_history, submit_outgoing_material_cart,
    get_child_parts, get_child_stock_view, get_child_out_history, submit_outgoing_child_cart
)

st.set_page_config(page_title="Outgoing Material", page_icon="🏭", layout="wide")
inject_premium_theme()
protect_page("material")

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("🏭 Outgoing Supply (Batch Request)")

# --- SESSION STATE ---
if 'cart_resin_out' not in st.session_state: st.session_state.cart_resin_out = []
if 'cart_child_out' not in st.session_state: st.session_state.cart_child_out = []

tab1, tab2 = st.tabs(["🛢️ Supply Resin", "🔩 Supply Komponen"])

# ==========================================
# TAB 1: RESIN OUT
# ==========================================
with tab1:
    df_mat = get_master_materials()
    df_stock = get_material_stock_view()
    
    # Filter hanya yang ada stok
    ready_list = []
    if not df_stock.empty:
        ids = df_stock[df_stock['current_stock'] > 0]['id'].tolist()
        ready_list = df_mat[df_mat['id'].isin(ids)]['full_name'].tolist()

    if not ready_list:
        st.warning("⚠️ Semua Stok Resin Kosong (0). Tidak bisa melakukan pengeluaran.")
    else:
        # --- HEADER ---
        with st.container():
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.subheader("1. Info Pengeluaran (Header)")
            c1, c2, c3 = st.columns(3)
            trx_date = c1.date_input("Tanggal Keluar", value=date.today(), key="d_out_res")
            input_by = c2.text_input("Dikeluarkan Oleh", key="chk_out_res", placeholder="Checker Gudang")
            receiver = c3.text_input("Diterima Oleh (Produksi)", key="rcv_out_res", placeholder="Foreman/Operator")
            st.markdown('</div>', unsafe_allow_html=True)

        # --- ITEM INPUT ---
        c_in, c_cart = st.columns([1, 1.5])
        
        with c_in:
            st.markdown("### 2. Pilih Resin")
            sel_res = st.selectbox("Pilih Material", ready_list, key="sel_out_res")
            
            # Get ID & Stock
            mat_id = df_mat[df_mat['full_name'] == sel_res].iloc[0]['id']
            curr_stk = df_stock[df_stock['id'] == mat_id]['current_stock'].values[0]
            
            st.caption(f"Stok Tersedia: **{float(curr_stk):,.2f} Kg**")
            
            qty_out = st.number_input("Qty Keluar (Kg)", min_value=0.0, max_value=float(curr_stk), step=25.0, key="q_out_res")
            note_item = st.text_input("Ket. Item", key="n_out_res")
            
            if st.button("➕ Tambah ke List", key="add_out_res"):
                if qty_out > 0:
                    st.session_state.cart_resin_out.append({
                        "id": mat_id,
                        "name": sel_res,
                        "qty": qty_out,
                        "notes": note_item
                    })
                    st.success("OK")
                    time.sleep(0.2)
                    st.rerun()
                else:
                    st.error("Qty Invalid")
        
        # --- CART ---
        with c_cart:
            st.markdown("### 3. List Pengeluaran")
            if len(st.session_state.cart_resin_out) > 0:
                
                # [UPDATE] Bikin Header Custom biar rapi
                h1, h2, h3, h4 = st.columns([4, 2, 3, 1])
                h1.caption("NAMA BARANG")
                h2.caption("QTY (Kg)")
                h3.caption("NOTES")
                h4.caption("AKSI")
                st.divider()
                
                # [UPDATE] Looping isi keranjang biar ada tombol hapus satuan
                for i, item in enumerate(st.session_state.cart_resin_out):
                    r1, r2, r3, r4 = st.columns([4, 2, 3, 1])
                    r1.write(item['name'])
                    r2.write(f"{item['qty']}")
                    r3.write(item['notes'])
                    # Tombol hapus satuan
                    if r4.button("❌", key=f"del_res_{i}", help="Hapus item ini"):
                        st.session_state.cart_resin_out.pop(i)
                        st.rerun()
                
                st.write("")
                if st.button("🗑️ Reset Semua List", key="clr_out_res"):
                    st.session_state.cart_resin_out = []
                    st.rerun()
                
                st.divider()
                if st.button("🚀 PROSES PENGELUARAN", type="primary", use_container_width=True, key="sav_out_res"):
                    if not input_by or not receiver:
                        st.error("⚠️ Checker & Penerima Wajib Diisi!")
                    else:
                        header_data = {
                            "date": trx_date, "input_by": input_by, 
                            "receiver": receiver, "notes": "-"
                        }
                        with st.spinner("Processing..."):
                            success, msg = submit_outgoing_material_cart(header_data, st.session_state.cart_resin_out)
                            if success:
                                st.success(msg)
                                st.session_state.cart_resin_out = []
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(msg)
            else:
                st.info("List Kosong.")

        # --- HISTORY RESIN ---
        st.divider()
        st.caption("📜 Riwayat Pengeluaran Terakhir")
        
        df_hist = get_material_out_history(10)
        
        if not df_hist.empty:
            target_cols = ['date_out', 'qty', 'input_by', 'material_name', 'notes']
            final_cols = [c for c in target_cols if c in df_hist.columns]
            
            df_view = df_hist[final_cols]
            
            rename_map = {
                'date_out': 'Date Out',
                'qty': 'Qty (Kg)',
                'input_by': 'Checker',
                'material_name': 'Material Name',
                'notes': 'Receiver / Notes'
            }
            df_view = df_view.rename(columns=rename_map)
            st.dataframe(df_view, use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada data history.")

# ==========================================
# TAB 2: CHILD PART OUT
# ==========================================
with tab2:
    df_cp = get_child_parts()
    df_cp_stk = get_child_stock_view()
    
    ready_cp = []
    if not df_cp_stk.empty:
        ids_cp = df_cp_stk[df_cp_stk['current_stock'] > 0]['id'].tolist()
        ready_cp = df_cp[df_cp['id'].isin(ids_cp)]['part_name'].tolist()
        
    if not ready_cp:
        st.warning("⚠️ Stok Komponen Kosong.")
    else:
        # --- HEADER ---
        with st.container():
            st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
            st.subheader("1. Info Pengeluaran (Header)")
            c1, c2, c3 = st.columns(3)
            d_cp = c1.date_input("Tanggal Keluar", value=date.today(), key="d_out_cp")
            chk_cp = c2.text_input("Dikeluarkan Oleh", key="chk_out_cp")
            rcv_cp = c3.text_input("Diterima Oleh", key="rcv_out_cp")
            st.markdown('</div>', unsafe_allow_html=True)
            
        # --- INPUT ---
        ci, cc = st.columns([1, 1.5])
        with ci:
            st.markdown("### 2. Pilih Komponen")
            sel_nm = st.selectbox("Nama Part", ready_cp, key="sel_nm_cp")
            
            cp_info = df_cp[df_cp['part_name'] == sel_nm].iloc[0]
            cp_id = cp_info['id']
            curr_qty = df_cp_stk[df_cp_stk['id'] == cp_id]['current_stock'].values[0]
            
            st.caption(f"Stok: **{int(curr_qty)} {cp_info.get('uom','Pcs')}**")
            
            q_out = st.number_input("Qty Keluar", 0, int(curr_qty), 0, key="q_out_cp")
            n_out = st.text_input("Ket.", key="n_out_cp")
            
            if st.button("➕ Tambah", key="add_out_cp"):
                if q_out > 0:
                    st.session_state.cart_child_out.append({
                        "id": cp_id,
                        "name": sel_nm,
                        "qty": q_out,
                        "notes": n_out
                    })
                    st.success("OK")
                    time.sleep(0.2)
                    st.rerun()
        
        # --- CART ---
        with cc:
             st.markdown("### 3. List Pengeluaran")
             if len(st.session_state.cart_child_out) > 0:
                
                # [UPDATE] Custom Header buat Child Part
                h1_c, h2_c, h3_c, h4_c = st.columns([4, 2, 3, 1])
                h1_c.caption("NAMA PART")
                h2_c.caption("QTY")
                h3_c.caption("NOTES")
                h4_c.caption("AKSI")
                st.divider()
                
                # [UPDATE] Looping item Child Part
                for idx, cp_item in enumerate(st.session_state.cart_child_out):
                    r1_c, r2_c, r3_c, r4_c = st.columns([4, 2, 3, 1])
                    r1_c.write(cp_item['name'])
                    r2_c.write(f"{cp_item['qty']}")
                    r3_c.write(cp_item['notes'])
                    # Tombol hapus satuan
                    if r4_c.button("❌", key=f"del_cp_{idx}", help="Hapus item ini"):
                        st.session_state.cart_child_out.pop(idx)
                        st.rerun()
                
                st.write("")
                if st.button("🗑️ Reset Semua List", key="clr_out_cp"):
                    st.session_state.cart_child_out = []
                    st.rerun()
                
                st.divider()
                if st.button("🚀 PROSES PENGELUARAN", type="primary", use_container_width=True, key="sav_out_cp"):
                    if not chk_cp or not rcv_cp:
                        st.error("⚠️ Header Wajib Lengkap!")
                    else:
                        header_data = {
                            "date": d_cp, "input_by": chk_cp, 
                            "receiver": rcv_cp, "notes": "-"
                        }
                        with st.spinner("Processing..."):
                            success, msg = submit_outgoing_child_cart(header_data, st.session_state.cart_child_out)
                            if success:
                                st.success(msg)
                                st.session_state.cart_child_out = []
                                time.sleep(1.5)
                                st.rerun()
                            else:
                                st.error(msg)
             else:
                st.info("List Kosong.")

        # --- HISTORY CHILD PART ---
        st.divider()
        st.caption("📜 Riwayat Pengeluaran Terakhir")
        
        df_hist_cp = get_child_out_history(10)
        
        if not df_hist_cp.empty:
            if 'uom' not in df_hist_cp.columns:
                df_hist_cp['uom'] = 'PCS'
                
            target_cols = ['date_out', 'qty', 'uom', 'input_by', 'part_name', 'notes']
            final_cols = [c for c in target_cols if c in df_hist_cp.columns]
            
            df_view_cp = df_hist_cp[final_cols]
            
            rename_map = {
                'date_out': 'Date Out',
                'qty': 'Qty',
                'uom': 'UOM',
                'input_by': 'Checker',
                'part_name': 'Part Name',
                'notes': 'Receiver / Notes'
            }
            df_view_cp = df_view_cp.rename(columns=rename_map)
            
            desired_order = ['Date Out', 'Qty', 'UOM', 'Checker', 'Part Name', 'Receiver / Notes']
            final_order = [c for c in desired_order if c in df_view_cp.columns]
            
            st.dataframe(df_view_cp[final_order], use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada history.")