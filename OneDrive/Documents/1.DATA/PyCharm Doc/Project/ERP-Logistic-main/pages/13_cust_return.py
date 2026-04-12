import streamlit as st
import pandas as pd
import time # <--- INI YANG TADI KURANG
from datetime import date
from modules import inject_premium_theme, protect_page, get_master_products, submit_return_cart

# 1. Config & Security
st.set_page_config(page_title="Customer Return", layout="wide")
inject_premium_theme()
protect_page("warehouse") 

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("↩️ Input Retur Customer (Multi-Item)")
st.info("Pencatatan barang NG dari Customer. Stok FG **TIDAK** bertambah (Hanya Log).")

# Init Cart
if "ret_cart" not in st.session_state: st.session_state.ret_cart = []

# Load Master
df_prod = get_master_products()
if df_prod.empty: st.error("Master Kosong"); st.stop()
parts_list = df_prod['part_name'].tolist()

# ==========================================
# 1. HEADER INFORMASI (DOKUMEN)
# ==========================================
with st.container():
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.subheader("1. Informasi Dokumen Retur")
    
    c1, c2 = st.columns(2)
    with c1:
        date_ret = st.date_input("Tanggal Terima", value=date.today())
        # Customer input manual atau dropdown master (kita manual dulu biar fleksibel)
        cust_name = st.text_input("Nama Customer")
        original_do = st.text_input("Ref No. DO Asli (Dari Kita)", placeholder="DO-2026/XXXX")
    with c2:
        doc_no = st.text_input("No. SJ Retur (Dari Customer)", placeholder="SJ-RET-001")
        reason = st.text_area("Alasan Retur Global", placeholder="Contoh: NG Pengiriman / Karat / Short Shot")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. INPUT BARANG (ADD TO CART)
# ==========================================
with st.container():
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    st.subheader("2. Input Item NG")
    
    ic1, ic2, ic3 = st.columns([3, 1, 1])
    with ic1:
        part_sel = st.selectbox("Pilih Barang", parts_list)
        # Auto Info
        info = df_prod[df_prod['part_name'] == part_sel].iloc[0]
        part_no = info['part_no']
        st.caption(f"Part No: {part_no}")
        
    with ic2:
        qty_ng = st.number_input("Qty NG", min_value=1, value=1)
        
    with ic3:
        st.write("Action")
        if st.button("➕ Tambah Item"):
            # Validasi
            if any(x['part_no'] == part_no for x in st.session_state.ret_cart):
                st.error("Item sudah ada di list!")
            else:
                st.session_state.ret_cart.append({
                    "part_name": part_sel,
                    "part_no": part_no,
                    "qty": qty_ng
                })
                st.rerun()
    
    # TABLE CART
    if st.session_state.ret_cart:
        st.markdown("---")
        df_cart = pd.DataFrame(st.session_state.ret_cart)
        st.dataframe(df_cart, use_container_width=True, hide_index=True)
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            if st.button("🗑️ Reset", type="secondary"):
                st.session_state.ret_cart = []
                st.rerun()
        with col_btn2:
            if st.button("📥 SIMPAN SEMUA DATA RETUR", type="primary", use_container_width=True):
                if not cust_name or not doc_no:
                    st.error("Nama Customer & No SJ Retur Wajib Diisi!")
                else:
                    header = {
                        "date": date_ret, "customer": cust_name,
                        "doc_no": doc_no, "original_do": original_do,
                        "reason": reason
                    }
                    success, msg = submit_return_cart(header, st.session_state.ret_cart)
                    if success:
                        st.success(f"Berhasil! {len(st.session_state.ret_cart)} Item tersimpan.")
                        st.session_state.ret_cart = [] # Clear
                        time.sleep(1.5) # <--- INI SEKARANG AMAN
                        st.rerun()
                    else: st.error(msg)

    st.markdown('</div>', unsafe_allow_html=True)
