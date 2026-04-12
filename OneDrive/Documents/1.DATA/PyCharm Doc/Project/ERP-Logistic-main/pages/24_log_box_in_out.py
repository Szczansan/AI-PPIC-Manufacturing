import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from modules import (
    inject_premium_theme, protect_page, get_master_boxes, 
    submit_box_transaction_cart, get_box_transaction_history, generate_box_history_pdf
)

st.set_page_config(page_title="Transaksi Box", layout="wide")
inject_premium_theme()
protect_page("warehouse")

st.title("📦 Log Transaksi Box & Packaging")

df_box = get_master_boxes()
if df_box.empty:
    st.error("Data Master Box kosong! Input dulu di Master Box."); st.stop()

box_options = {row['box_name']: row for _, row in df_box.iterrows()}
list_box_names = list(box_options.keys())

# --- TAMBAH TAB 3 (HISTORY) ---
tab1, tab2, tab3 = st.tabs(["📥 BOX IN (Masuk)", "📤 BOX OUT (Keluar)", "📜 HISTORY & EXPORT"])

# ==========================================
# TAB 1: BOX IN
# ==========================================
with tab1:
    st.subheader("Form Kedatangan Box")
    if "cart_box_in" not in st.session_state: st.session_state.cart_box_in = []
    
    col_h1, col_h2, col_h3 = st.columns(3)
    date_in = col_h1.date_input("Tanggal Masuk", datetime.now(), key="din")
    sj_no = col_h2.text_input("No Surat Jalan", placeholder="Opsional")
    pic_in = col_h3.text_input("PIC / Penerima", value=st.session_state.current_user, disabled=True)
    
    with st.container(border=True):
        st.markdown("**Tambah Item**")
        c1, c2, c3 = st.columns([2, 2, 1])
        selected_in = c1.selectbox("Pilih Box", list_box_names, key="sel_in")
        
        if selected_in:
            dt = box_options[selected_in]
            c2.info(f"**Spek:** {dt.get('specification','-')} | **Model:** {dt.get('model','-')} | **Cust:** {dt.get('customer','-')}")
            
        qty_in = c3.number_input("Qty Masuk", min_value=1, step=1, key="qty_in")
        
        if st.button("➕ Masukkan ke Keranjang IN", use_container_width=True):
            st.session_state.cart_box_in.append({
                "box_id": box_options[selected_in]['id'], "box_name": selected_in, "qty": qty_in
            })
            st.rerun()

    if st.session_state.cart_box_in:
        st.dataframe(pd.DataFrame(st.session_state.cart_box_in)[['box_name', 'qty']], use_container_width=True)
        if st.button("🚀 Submit Transaksi IN", type="primary"):
            hdr = {"date": date_in, "sj_number": sj_no, "pic": pic_in, "type": "IN"}
            sukses, pesan = submit_box_transaction_cart(hdr, st.session_state.cart_box_in)
            
            if sukses:
                st.toast(pesan, icon="✅")
                st.session_state.cart_box_in = [] # Reset Keranjang
                time.sleep(1) # Jeda dikit
                st.rerun() # Refresh biar form kosong
            else: 
                st.error(pesan)
                
        if st.button("🗑️ Clear Cart IN"): st.session_state.cart_box_in = []; st.rerun()

# ==========================================
# TAB 2: BOX OUT
# ==========================================
with tab2:
    st.subheader("Form Pengeluaran Box")
    if "cart_box_out" not in st.session_state: st.session_state.cart_box_out = []
    
    col_h1, col_h2 = st.columns(2)
    date_out = col_h1.date_input("Tanggal Keluar", datetime.now(), key="dout")
    pic_out = col_h2.text_input("PIC / Pengeluar", value=st.session_state.current_user, disabled=True)
    
    with st.container(border=True):
        st.markdown("**Tambah Item**")
        c1, c2, c3 = st.columns([2, 2, 1])
        selected_out = c1.selectbox("Pilih Box", list_box_names, key="sel_out")
        
        if selected_out:
            dt = box_options[selected_out]
            c2.info(f"**Spek:** {dt.get('specification','-')} | **Model:** {dt.get('model','-')} | **Cust:** {dt.get('customer','-')}")
            
        qty_out = c3.number_input("Qty Keluar", min_value=1, step=1, key="qty_out")
        
        if st.button("➕ Masukkan ke Keranjang OUT", use_container_width=True):
            st.session_state.cart_box_out.append({
                "box_id": box_options[selected_out]['id'], "box_name": selected_out, "qty": qty_out
            })
            st.rerun()

    if st.session_state.cart_box_out:
        st.dataframe(pd.DataFrame(st.session_state.cart_box_out)[['box_name', 'qty']], use_container_width=True)
        if st.button("🚀 Submit Transaksi OUT", type="primary"):
            hdr = {"date": date_out, "pic": pic_out, "type": "OUT"}
            sukses, pesan = submit_box_transaction_cart(hdr, st.session_state.cart_box_out)
            
            if sukses:
                st.toast(pesan, icon="✅")
                st.session_state.cart_box_out = [] # Reset Keranjang
                time.sleep(1)
                st.rerun() # Refresh biar form kosong
            else: 
                st.error(pesan)
                
        if st.button("🗑️ Clear Cart OUT"): st.session_state.cart_box_out = []; st.rerun()

# ==========================================
# TAB 3: HISTORY & PDF EXPORT
# ==========================================
with tab3:
    st.subheader("🔍 Filter & Cari History Box")
    
    # Filter UI (Dibikin 4 kolom biar muat filter status)
    f1, f2, f3, f4 = st.columns(4)
    
    start_date = f1.date_input("Dari Tanggal", datetime.now() - timedelta(days=7))
    end_date = f2.date_input("Sampai Tanggal", datetime.now())
    
    # Filter Baru: Status IN/OUT
    status_options = ["All", "IN", "OUT"]
    selected_status = f3.selectbox("Filter Status:", status_options)
    
    # Filter Box Name
    filter_options = ["All"] + list_box_names
    selected_filter = f4.selectbox("Filter Nama Box:", filter_options)
    
    st.divider()
    
    # Fetch Data dengan tambahan selected_status
    with st.spinner("Menarik data history..."):
        df_history = get_box_transaction_history(start_date, end_date, selected_filter, selected_status)
    
    if not df_history.empty:
        st.dataframe(
            df_history[['date_trans', 'box_name', 'specification', 'type', 'qty', 'sj_number', 'pic']],
            use_container_width=True,
            hide_index=True
        )
        
        # --- PDF EXPORT SECTION ---
        st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)
        col_dl1, col_dl2 = st.columns([1, 4])
        
        with col_dl1:
            if st.button("📄 Generate Report PDF", use_container_width=True):
                with st.spinner("Membuat PDF..."):
                    # Masukin parameter status ke generator PDF
                    pdf_bytes, status_msg = generate_box_history_pdf(df_history, start_date, end_date, selected_filter, selected_status)
                    
                if pdf_bytes:
                    file_name = f"Box_History_{start_date}_to_{end_date}.pdf"
                    st.success(status_msg)
                    st.download_button(
                        label="⬇️ Download PDF Sekarang",
                        data=pdf_bytes,
                        file_name=file_name,
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    st.error(status_msg)
    else:
        st.info("Tidak ada transaksi box pada rentang waktu dan filter yang dipilih.")