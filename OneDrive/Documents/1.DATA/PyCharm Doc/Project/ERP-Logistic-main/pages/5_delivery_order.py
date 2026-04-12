import streamlit as st
import pandas as pd
from datetime import date, timedelta
import math
import time
from modules import (
    inject_premium_theme, protect_page, 
    get_master_products, get_stockboard_fg_view,
    get_all_open_pos, generate_custom_do_number, 
    submit_delivery_cart, submit_general_delivery_cart,
    get_do_details, update_delivery_log_advanced,
    get_delivery_history_paged, create_pdf_do,
    get_items_by_po_number, create_blank_pdf_do,
    void_delivery_item
)

# 1. SETUP PAGE
st.set_page_config(page_title="Delivery Order", layout="wide")
inject_premium_theme()
protect_page('shipping')

if 'do_cart' not in st.session_state: st.session_state.do_cart = []
if 'gen_cart' not in st.session_state: st.session_state.gen_cart = []

st.title("🚛 Delivery Order (DO) System")

tab_sales, tab_general, tab_revisi, tab_hist = st.tabs([
    "📦 SALES DO (PO)", 
    "🛠️ GENERAL DO (MANUAL)", 
    "📝 REVISI DO", 
    "🗄️ HISTORY & REPRINT"
])

# ==============================================================================
# TAB 1: SALES DO (PO BASED)
# ==============================================================================
with tab_sales:
    st.caption("Penerbitan Surat Jalan Penjualan (Potong Stok FG & PO).")
    
    # --- A. HEADER ---
    with st.container(border=True):
        st.subheader("1. Header Surat Jalan")
        
        df_po = get_all_open_pos()
        po_options = df_po['po_number'].tolist() if not df_po.empty else []
        po_to_cust_map = dict(zip(df_po['po_number'], df_po['customer_name'])) if not df_po.empty else {}

        c1, c2, c3, c4 = st.columns(4)
        is_locked = len(st.session_state.do_cart) > 0
        
        trx_date = c1.date_input("Tanggal Kirim", date.today(), disabled=is_locked, key="s_date")
        po_number = c2.selectbox("Pilih No PO (Open)", po_options, index=None, placeholder="Cari PO...", disabled=is_locked, key="s_po")
        
        current_cust = ""
        current_do_no = "-"
        if po_number:
            current_cust = po_to_cust_map.get(po_number, "")
            if 'temp_do_no' not in st.session_state or not is_locked:
                st.session_state.temp_do_no = generate_custom_do_number(current_cust, trx_date)
            current_do_no = st.session_state.temp_do_no
        
        c3.text_input("Customer", value=current_cust, disabled=True)
        c4.text_input("No DO (Auto)", value=current_do_no, disabled=True)
        
        # Driver Info Only
        driver_info = st.text_input("Nama Supir | No. Polisi (Format: Nama | Nopol)", placeholder="Contoh: Ujang | B 1234 KA", disabled=is_locked, key="s_driver")

    # --- B. INPUT ITEM ---
    with st.container(border=True):
        st.subheader("2. Input Barang")
        
        if not po_number:
            st.info("👈 Pilih PO dulu di atas.")
        else:
            po_items_df = get_items_by_po_number(po_number)
            if po_items_df.empty:
                st.warning("⚠️ PO ini kosong/error.")
            else:
                ic1, ic2, ic3, ic4 = st.columns([3, 1, 1, 1])
                part_opts = po_items_df['part_name'].tolist()
                sel_part = ic1.selectbox("Pilih Barang", part_opts, index=None, key="s_part_in")
                
                curr_balance = 0; curr_stock = 0; curr_spq = 1; curr_part_no = ""
                
                if sel_part:
                    row_po = po_items_df[po_items_df['part_name'] == sel_part].iloc[0]
                    curr_balance = int(row_po['balance_qty']); curr_part_no = row_po['part_no']
                    
                    curr_stock = 0
                    df_stock = get_stockboard_fg_view()
                    if not df_stock.empty:
                        s_row = df_stock[df_stock['part_name'] == sel_part]
                        if not s_row.empty: curr_stock = int(s_row.iloc[0]['balance'])
                    
                    curr_spq = 1
                    curr_inv_id = "-" 
                    
                    df_master = get_master_products()
                    if not df_master.empty:
                        m_row = df_master[df_master['part_name'] == sel_part]
                        if not m_row.empty: 
                            raw_spq = int(m_row.iloc[0]['spq'])
                            curr_spq = raw_spq if raw_spq > 0 else 1 
        
                            curr_inv_id = str(m_row.iloc[0].get('inventory_id', '-'))

                    ic2.metric("Sisa PO", f"{curr_balance}"); ic3.metric("Stok FG", f"{curr_stock}")
                    st.caption(f"🆔 Inventory ID Client: **{curr_inv_id}**") 
                    
                    qty_send = ic4.number_input("Qty Kirim", min_value=1, value=1, step=curr_spq)
                    item_remark = st.text_input("Catatan Barang (Remarks)", placeholder="Contoh: Segel Baru / Box Coklat", key="s_item_rem")
                    
                    st.write("")
                    if st.button("➕ Tambah ke Daftar", use_container_width=True):
                        if qty_send > curr_balance:
                            st.toast("⚠️ Qty melebihi sisa PO!", icon="❌")
                        else:
                            item_data = {
                                "part_name": sel_part, "part_no": curr_part_no,
                                "qty": qty_send, "spq": curr_spq, "box": math.ceil(qty_send/curr_spq),
                                "inventory_id": curr_inv_id,
                                "notes": item_remark if item_remark else "-" 
                            }
                            st.session_state.do_cart.append(item_data)
                            st.rerun()

    # --- C. FINALISASI ---
    st.divider()
    if len(st.session_state.do_cart) > 0:
        st.dataframe(pd.DataFrame(st.session_state.do_cart), use_container_width=True, hide_index=True)
        
        ca1, ca2 = st.columns([1, 4])
        if ca1.button("❌ Reset", key="s_rst"):
            st.session_state.do_cart = []; 
            if 'temp_do_no' in st.session_state: del st.session_state['temp_do_no']
            st.rerun()
            
        if ca2.button("🚀 TERBITKAN SURAT JALAN", type="primary", use_container_width=True, key="s_sub"):
            head_data = {
                "date": trx_date, "do_no": current_do_no, "po_no": po_number, 
                "customer": current_cust, "prepared_by": st.session_state.current_user, 
                "notes": driver_info if driver_info else "-" 
            }
            with st.spinner("Processing..."):
                ok, msg = submit_delivery_cart(head_data, st.session_state.do_cart)
            
            if ok:
                st.success(msg)
                pdf_bytes = create_pdf_do(head_data, st.session_state.do_cart)
                st.download_button("📄 DOWNLOAD PDF", pdf_bytes, f"DO_{current_do_no.replace('/','-')}.pdf", "application/pdf", type="primary")
                st.session_state.do_cart = []; 
                if 'temp_do_no' in st.session_state: del st.session_state['temp_do_no']
            else: st.error(msg)

# ==============================================================================
# TAB 2: GENERAL DO
# ==============================================================================
with tab_general:
    st.caption("Surat Jalan Umum / Manual (Bisa Multi-Item). Cocok untuk Sample, Return, Mold, dll.")
    
    with st.container(border=True):
        st.subheader("1. Header SJ Umum")
        is_gen_locked = len(st.session_state.gen_cart) > 0
        
        gc1, gc2, gc3, gc4 = st.columns(4)
        g_date = gc1.date_input("Tanggal", date.today(), key="g_date", disabled=is_gen_locked)
        g_dest = gc2.text_input("Tujuan / Customer", placeholder="PT. ABC...", key="g_dest", disabled=is_gen_locked)
        
        g_do_val = "-"
        if g_dest:
            if 'gen_do_temp' not in st.session_state or not is_gen_locked:
                st.session_state.gen_do_temp = generate_custom_do_number("GENERAL", g_date)
            g_do_val = st.session_state.gen_do_temp
            
        gc3.text_input("No SJ (Auto)", value=g_do_val, disabled=True, key="g_do_show")
        g_po_manual = gc4.text_input("No PO Manual", key="g_po_manual", disabled=is_gen_locked)
        
        g_driver = st.text_input("Nama Supir | Nopol", placeholder="Ujang | B 1234 XYZ", key="g_driver", disabled=is_gen_locked)

    with st.container(border=True):
        st.subheader("2. Input Barang Manual")
        
        if not g_dest:
            st.info("👈 Isi Tujuan dulu di atas.")
        else:
            gi1, gi2 = st.columns([3, 1])
            g_part_name = gi1.text_input("Nama Barang / Deskripsi", placeholder="Misal: Mold Base Plate A", key="g_pname")
            g_part_no = gi2.text_input("Part No / Ukuran", placeholder="Optional", key="g_pno")
            
            gi3, gi4, gi5 = st.columns(3)
            g_qty = gi3.number_input("Qty Barang", min_value=1, key="g_qty_in")
            g_uom = gi4.text_input("Satuan (UoM)", value="Pcs", placeholder="Pcs/Set/Kg", key="g_uom_in")
            
            g_box = gi5.number_input("Jml Kemasan (Box/Colly)", min_value=0, key="g_box_in")
            
            g_item_remark = st.text_input("Catatan Barang (Remarks)", placeholder="Keterangan kondisi dll...", key="g_item_rem")
            
            st.write("")
            if st.button("➕ Tambah Barang", key="g_add", use_container_width=True):
                if not g_part_name:
                    st.warning("Nama barang wajib diisi!")
                else:
                    item_gen = {
                        "part_name": g_part_name, 
                        "part_no": g_part_no if g_part_no else "-",
                        "qty": g_qty, 
                        "uom": g_uom, 
                        "box": g_box, 
                        "spq": 0, 
                        "notes": g_item_remark if g_item_remark else "-"
                    }
                    st.session_state.gen_cart.append(item_gen)
                    st.rerun()

    st.divider()
    if len(st.session_state.gen_cart) > 0:
        st.dataframe(
            pd.DataFrame(st.session_state.gen_cart)[['part_name', 'qty', 'uom', 'box', 'notes']], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "part_name": "Nama Barang",
                "qty": "Qty",
                "uom": "Satuan",
                "box": "Colly/Box",
                "notes": "Ket"
            }
        )
        
        ga1, ga2 = st.columns([1, 4])
        if ga1.button("❌ Reset", key="g_rst"):
            st.session_state.gen_cart = []; 
            if 'gen_do_temp' in st.session_state: del st.session_state['gen_do_temp']
            st.rerun()
            
        if ga2.button("🚀 CETAK SJ UMUM (FINAL)", type="primary", use_container_width=True, key="g_sub"):
            head_gen = {
                "date": g_date, "do_no": g_do_val, "customer": g_dest, 
                "po_no": g_po_manual if g_po_manual else "-", 
                "prepared_by": st.session_state.current_user, 
                "notes": g_driver if g_driver else "-" 
            }
            with st.spinner("Menerbitkan SJ Umum..."):
                ok, msg = submit_general_delivery_cart(head_gen, st.session_state.gen_cart)
            
            if ok:
                st.success(msg)
                pdf_gen = create_pdf_do(head_gen, st.session_state.gen_cart)
                st.download_button("📄 DOWNLOAD PDF", pdf_gen, f"GEN_{g_do_val.replace('/','-')}.pdf", "application/pdf", type="primary")
                st.session_state.gen_cart = []; 
                if 'gen_do_temp' in st.session_state: del st.session_state['gen_do_temp']
            else: st.error(msg)
    else:
        st.info("List barang umum kosong.")

# ==============================================================================
# TAB 3: REVISI DO (UPDATED WITH VOID)
# ==============================================================================
with tab_revisi:
    st.header("📝 Revisi DO (Edit Mode)")
    rev_do_search = st.text_input("Masukkan No DO Lengkap", placeholder="Contoh: 2026/0001-ASTRA/15/01")
    
    if rev_do_search:
        do_items = get_do_details(rev_do_search)
        
        if not do_items:
            st.warning("❌ No DO tidak ditemukan.")
        else:
            st.success(f"✅ Ditemukan {len(do_items)} item.")
            
            df_rev = pd.DataFrame(do_items)
            if 'inventory_id' not in df_rev.columns: df_rev['inventory_id'] = '-'
            
            st.dataframe(
                df_rev[['transaction_date', 'part_name', 'qty', 'inventory_id', 'po_number']], 
                hide_index=True, use_container_width=True
            )
            
            st.markdown("---")
            
            item_opts = {f"{row['part_name']} (Qty: {row['qty']})": row['id'] for row in do_items}
            sel_item_label = st.selectbox("Pilih Item Edit:", list(item_opts.keys()))
            
            if sel_item_label:
                sel_id = item_opts[sel_item_label]
                curr_row = next((item for item in do_items if item['id'] == sel_id), None)
                
                # --- A. FORM EDIT DATA ---
                with st.form("form_revisi"):
                    st.caption("Silakan edit field di bawah ini:")
                    
                    try:
                        tgl_awal = pd.to_datetime(curr_row['transaction_date']).date()
                    except:
                        tgl_awal = date.today()

                    c1, c2, c3 = st.columns(3)
                    new_date = c1.date_input("Tanggal Transaksi", value=tgl_awal)
                    
                    df_open_po = get_all_open_pos()
                    open_po_list = df_open_po['po_number'].tolist() if not df_open_po.empty else []
                    
                    current_po = curr_row.get('po_number', '-')
                    if current_po and current_po != '-' and current_po not in open_po_list:
                        open_po_list.insert(0, current_po)
                        
                    try:
                        default_po_idx = open_po_list.index(current_po)
                    except ValueError:
                        default_po_idx = None
                        
                    new_po = c2.selectbox("No PO Baru", options=open_po_list, index=default_po_idx)
                    new_inv = c3.text_input("Inventory ID (Client Code)", value=curr_row.get('inventory_id', '-'))

                    c4, c5, c6 = st.columns(3)
                    new_part = c4.text_input("Nama Part", value=curr_row['part_name'])
                    new_qty = c5.number_input("Qty Baru", value=int(curr_row['qty']))
                    new_rem = c6.text_input("Remarks / Catatan", value=curr_row.get('notes', '-'))
                    
                    if st.form_submit_button("💾 SIMPAN PERUBAHAN", type="primary", use_container_width=True):
                        new_pl = {
                            "transaction_date": new_date,
                            "po_number": new_po if new_po else "-", 
                            "inventory_id": new_inv,
                            "part_name": new_part, 
                            "qty": new_qty, 
                            "notes": new_rem
                        }
                        with st.spinner("Menyimpan revisi..."):
                            ok, msg = update_delivery_log_advanced(sel_id, new_pl)
                        if ok: 
                            st.success(msg); time.sleep(1); st.rerun()
                        else: st.error(msg)

                # --- B. DANGER ZONE (VOID/DELETE) ---
                st.write("")
                with st.expander("🚨 Danger Zone (Hapus Item)"):
                    st.error("Perhatian: Menghapus item akan mengembalikan alokasi PO dan stok FG.")
                    
                    # Konfirmasi Popover sesuai request loe bre
                    with st.popover("🗑️ VOID / HAPUS ITEM INI", use_container_width=True):
                        st.markdown(f"**File akan hilang selama-lamanya yakin untuk void?**")
                        st.write(f"Item: {curr_row['part_name']} | Qty: {curr_row['qty']}")
                        
                        col_v1, col_v2 = st.columns(2)
                        if col_v1.button("✅ Yes, Hapus", type="primary", use_container_width=True):
                            with st.spinner("Sedang menghapus..."):
                                ok_v, msg_v = void_delivery_item(sel_id)
                                if ok_v:
                                    st.toast(msg_v)
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(msg_v)
                        
                        if col_v2.button("❌ No, Batal", use_container_width=True):
                            st.rerun()

# ==============================================================================
# TAB 4: HISTORY & REPRINT (UPDATED)
# ==============================================================================
with tab_hist:
    st.header("🗄️ Arsip")
    
    # --- BAGIAN ATAS: FILTER & TABEL HISTORY ---
    c1, c2 = st.columns([1, 2])
    d_range = c1.date_input("Filter Tanggal", value=(date.today() - timedelta(days=30), date.today()))
    start_d, end_d = d_range if isinstance(d_range, tuple) and len(d_range) == 2 else (date.today(), date.today())
    
    search_h = c2.text_input("Cari Customer / No DO / Part Name")
    
    page = st.number_input("Halaman", min_value=1, value=1)
    df_hist, total = get_delivery_history_paged(page, 10, start_d, end_d, search_h)
    
    st.caption(f"Total: {total} Data")
    if not df_hist.empty:
        # PENGAMAN PO NUMBER
        if 'po_number' not in df_hist.columns:
            df_hist['po_number'] = '-'
        df_hist['po_number'] = df_hist['po_number'].fillna('-')
            
        rename_cols = {
            'transaction_date': 'Date',
            'do_number': 'DO Number',
            'po_number': 'PO Number',
            'customer_name': 'Customer Name',
            'part_name': 'Part Name',
            'qty': 'QTY',
            'notes': 'Notes'
        }
        
        df_view = df_hist[['transaction_date', 'do_number', 'po_number', 'customer_name', 'part_name', 'qty', 'notes']].rename(columns=rename_cols)
        st.dataframe(df_view, use_container_width=True, hide_index=True)
        
    st.markdown("---")
    
    # --- BAGIAN BAWAH: REPRINT & DO KOSONG ---
    col_rep1, col_rep2 = st.columns(2)
    
    with col_rep1:
        st.markdown("### 🖨️ Reprint DO Lama")
        reprint_do = st.text_input("No DO Reprint", placeholder="Paste No DO...")
        if st.button("Generate PDF DO Lama"):
            items = get_do_details(reprint_do)
            if items:
                f = items[0]
                
                max_rev = max([int(item.get('rev_count') or 0) for item in items])
                
                h = {
                    "customer": f['customer_name'], 
                    "do_no": f['do_number'], 
                    "po_no": f['po_number'], 
                    "date": f['transaction_date'], 
                    "prepared_by": f.get('prepared_by','Admin'), 
                    "notes": f.get('notes',''),
                    "rev_count": max_rev 
                } 
                
                pdf = create_pdf_do(h, items)
                st.download_button("Download PDF", pdf, f"REPRINT_REV{max_rev}.pdf", "application/pdf")
            else: 
                st.error("Not Found")
                
    with col_rep2:
        st.markdown("### 📝 DO Kosong (Manual)")
        st.caption("Cetak Surat Jalan kosong untuk keperluan shift malam / sistem down.")
        
        blank_do_pdf = create_blank_pdf_do()
        st.download_button(
            label="📄 DOWNLOAD DO KOSONG",
            data=blank_do_pdf,
            file_name="DO_MANUAL_KOSONG.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )