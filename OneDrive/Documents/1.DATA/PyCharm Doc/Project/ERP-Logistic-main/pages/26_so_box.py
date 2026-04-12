import streamlit as st
import pandas as pd
from datetime import datetime
from modules import inject_premium_theme, protect_page, get_box_stock_as_of, submit_box_so_cart
import time

st.set_page_config(page_title="SO Box", layout="wide")
inject_premium_theme()
protect_page("warehouse")

st.title("⚖️ Stock Opname (SO) Box")

if "cart_box_so" not in st.session_state: st.session_state.cart_box_so = []

c1, c2, c3 = st.columns(3)
so_date = c1.date_input("Tanggal SO", datetime.now())
pic_so = c2.text_input("PIC SO", value=st.session_state.current_user, disabled=True)
notes_so = c3.text_input("Catatan / Notes")

st.divider()

# Ambil stok sistem HARI INI untuk patokan
df_system = get_box_stock_as_of(datetime.now())
if df_system.empty:
    st.error("Data Master Box kosong!"); st.stop()

# Mapping Data Stok
stock_map = {row['box_name']: row for _, row in df_system.iterrows()}

with st.container(border=True):
    st.subheader("Hitung Fisik")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    selected_box = col1.selectbox("Pilih Box", list(stock_map.keys()))
    sys_qty = stock_map[selected_box]['current_stock'] if selected_box else 0
    
    col2.metric("Qty System", sys_qty)
    actual_qty = col3.number_input("Qty Fisik (Actual)", min_value=0, step=1)
    
    diff = actual_qty - sys_qty
    if diff != 0: col3.caption(f"Selisih: :red[{diff}]" if diff < 0 else f"Selisih: :green[+{diff}]")
    else: col3.caption("Selisih: 0 (Balance)")

    if st.button("➕ Tambah ke List SO", use_container_width=True):
        st.session_state.cart_box_so.append({
            "box_id": stock_map[selected_box]['box_id'],
            "box_name": selected_box,
            "qty_system": sys_qty,
            "qty_actual": actual_qty,
            "diff": diff
        })
        st.rerun()

# --- TAMPILAN KERANJANG ---
if st.session_state.cart_box_so:
    st.subheader("Daftar Penyesuaian (Adjustment)")
    st.dataframe(pd.DataFrame(st.session_state.cart_box_so)[['box_name', 'qty_system', 'qty_actual', 'diff']], use_container_width=True)
    
    if st.button("🚀 SUBMIT STOCK OPNAME", type="primary"):
        hdr = {"date": so_date, "pic": pic_so, "notes": notes_so}
        sukses, pesan = submit_box_so_cart(hdr, st.session_state.cart_box_so)
        
        # --- UBAH BAGIAN INI ---
        if sukses:
            st.toast(pesan, icon="✅")
            st.session_state.cart_box_so = []
            time.sleep(1)
            st.rerun()
        else: 
            st.error(pesan)
        
    if st.button("🗑️ Clear List SO"): st.session_state.cart_box_so = []; st.rerun()