import streamlit as st
import pandas as pd
import time
from datetime import date
from modules import (
    inject_premium_theme, protect_page, 
    get_master_materials, get_child_parts,
    submit_vendor_po, get_all_vendor_pos, get_vendor_po_details, close_vendor_po
)

st.set_page_config(page_title="PO Supplier", page_icon="🛒", layout="wide")
inject_premium_theme()
protect_page("po") # Izin akses ngikut "po" seperti di main.py

st.title("🛒 PO Purchasing & Monitoring")

# Keranjang untuk Tab 1
if 'po_vendor_cart' not in st.session_state: st.session_state.po_vendor_cart = []

tab1, tab2 = st.tabs(["➕ BUAT PO BARU", "📊 MONITORING KEDATANGAN"])

# ==============================================================================
# TAB 1: BUAT PO BARU
# ==============================================================================
with tab1:
    st.caption("Penerbitan Purchase Order (PO) ke Supplier untuk Resin / Komponen.")
    
    with st.container(border=True):
        st.subheader("1. Header PO")
        h1, h2, h3 = st.columns(3)
        po_date = h1.date_input("Tanggal PO", date.today(), key="vpo_date")
        po_number = h2.text_input("Nomor PO", placeholder="Contoh: PO/2026/03/001", key="vpo_no")
        sup_name = h3.text_input("Nama Supplier", placeholder="PT. Vendor Plastik", key="vpo_sup")

    with st.container(border=True):
        st.subheader("2. Tambah Barang")
        c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
        
        kategori = c1.radio("Kategori Barang", ["RESIN", "CHILD PART"], horizontal=True)
        
        # Dinamis ngikutin kategori
        if kategori == "RESIN":
            df_mat = get_master_materials()
            item_list = df_mat['full_name'].tolist() if not df_mat.empty else []
            sel_item = c2.selectbox("Pilih Resin", item_list, key="vpo_sel_mat")
            def_uom = "Kg"
        else:
            df_cp = get_child_parts()
            item_list = df_cp['part_name'].tolist() if not df_cp.empty else []
            sel_item = c2.selectbox("Pilih Komponen", item_list, key="vpo_sel_cp")
            def_uom = "Pcs"
            
        qty_target = c3.number_input("Target Qty", min_value=1.0, step=1.0, key="vpo_qty")
        
        # [REVISI 1]: UOM diubah jadi Dropdown (Selectbox)
        uom_options = ["Kg", "Ml", "Pcs", "Sheet"]
        default_idx = uom_options.index(def_uom) if def_uom in uom_options else 0
        uom = c4.selectbox("UOM", options=uom_options, index=default_idx, key="vpo_uom")
        
        st.write("")
        if st.button("➕ Masukkan ke PO", use_container_width=True):
            if not sel_item:
                st.warning("Pilih barang dulu!")
            else:
                # Cari ID aslinya
                item_id = ""
                if kategori == "RESIN":
                    item_id = df_mat[df_mat['full_name'] == sel_item].iloc[0]['id']
                else:
                    item_id = df_cp[df_cp['part_name'] == sel_item].iloc[0]['id']
                
                # Masukin ke state cart
                st.session_state.po_vendor_cart.append({
                    "category": kategori,
                    "item_id": item_id,
                    "item_name": sel_item,
                    "qty": qty_target,
                    "uom": uom
                })
                st.success(f"{sel_item} masuk ke list!")
                time.sleep(0.5)
                st.rerun()

    # --- TAMPILAN KERANJANG ---
    if st.session_state.po_vendor_cart:
        st.divider()
        st.markdown("### 🛒 List Pesanan")
        
        # [REVISI 2]: Keranjang dibikin per baris biar bisa dihapus satuan
        # Bikin Header Tabel Manual biar rapi
        hc1, hc2, hc3, hc4, hc5 = st.columns([1.5, 3, 1, 1, 1])
        hc1.write("**Kategori**")
        hc2.write("**Nama Barang**")
        hc3.write("**Qty**")
        hc4.write("**UOM**")
        hc5.write("**Aksi**")
        st.markdown("---")
        
        # Loop isi keranjang dan pasang tombol hapus per baris
        for idx, item in enumerate(st.session_state.po_vendor_cart):
            col_item1, col_item2, col_item3, col_item4, col_act = st.columns([1.5, 3, 1, 1, 1])
            col_item1.write(f"{item['category']}")
            col_item2.write(f"{item['item_name']}")
            col_item3.write(f"{item['qty']}")
            col_item4.write(f"{item['uom']}")
            
            # Tombol hapus satuan
            if col_act.button("🗑️ Hapus", key=f"del_cart_{idx}"):
                st.session_state.po_vendor_cart.pop(idx)
                st.rerun()
                
        st.write("")
        ca1, ca2 = st.columns([1, 4])
        if ca1.button("❌ Kosongkan Semua", key="rst_vpo"):
            st.session_state.po_vendor_cart = []
            st.rerun()
            
        if ca2.button("🚀 SIMPAN PO KE SISTEM", type="primary", use_container_width=True):
            if not po_number or not sup_name:
                st.error("⚠️ Nomor PO dan Nama Supplier Wajib Diisi!")
            else:
                with st.spinner("Menyimpan PO..."):
                    ok, msg = submit_vendor_po(po_number, sup_name, po_date, st.session_state.po_vendor_cart)
                    if ok:
                        st.success(msg)
                        st.session_state.po_vendor_cart = []
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        st.error(msg)

# ==============================================================================
# TAB 2: MONITORING KEDATANGAN
# ==============================================================================
with tab2:
    st.caption("Pantau kedatangan barang. Data ditarik otomatis dari form Incoming Material.")
    
    df_po = get_all_vendor_pos()
    
    if df_po.empty:
        st.info("Belum ada data PO Purchasing.")
    else:
        po_options = df_po['po_number'].tolist()
        sel_monitor = st.selectbox("🔍 Pilih Nomor PO untuk Dimonitor", po_options, index=0)
        
        if sel_monitor:
            header, items = get_vendor_po_details(sel_monitor)
            
            if header:
                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Supplier", header['supplier_name'])
                mc2.metric("Tanggal Order", str(header['order_date']))
                
                status_color = "🟢" if header['status'] == 'OPEN' else "🔴"
                mc3.metric("Status PO", f"{status_color} {header['status']}")
                
                st.markdown("### 📦 Detail Pemenuhan Barang")
                
                # Bikin tabel yang gampang dibaca
                display_list = []
                all_completed = True # Penanda kalau semua udah terpenuhi
                
                for i in items:
                    target = i['target_qty']
                    received = i['received_qty']
                    balance = i['balance']
                    
                    # Logic Dynamic Status buat di UI
                    if balance <= 0:
                        if balance < 0:
                            stat_txt = "⚠️ OVER DELIVERED"
                            all_completed = False # Biar tetep dipantau
                        else:
                            stat_txt = "✅ COMPLETED"
                    else:
                        stat_txt = "⏳ PENDING"
                        all_completed = False
                        
                    display_list.append({
                        "Kategori": i['category'],
                        "Nama Barang": i['item_name'],
                        "Target PO": target,
                        "Sudah Datang": received,
                        "Sisa (Balance)": balance,
                        "UOM": i['uom'],
                        "Status": stat_txt
                    })
                
                st.dataframe(pd.DataFrame(display_list), use_container_width=True, hide_index=True)
                
                # TOMBOL FORCE CLOSE
                st.write("")
                if header['status'] == 'OPEN':
                    if all_completed:
                        st.success("Semua barang sudah terpenuhi! Anda bisa menutup PO ini.")
                    else:
                        st.info("Masih ada barang yang belum dikirim / Over delivered.")
                        
                    if st.button("🔒 TUTUP PO INI (CLOSE MANUAL)", type="primary"):
                        ok, msg = close_vendor_po(header['id'])
                        if ok:
                            st.success(msg)
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(msg)