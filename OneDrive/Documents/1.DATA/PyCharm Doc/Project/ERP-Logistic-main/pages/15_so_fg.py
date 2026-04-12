import streamlit as st
import pandas as pd
from datetime import date
import time
import io
from modules import (
    inject_premium_theme, protect_page, 
    get_stockboard_fg_view, submit_stock_adjustment, 
    get_so_history, get_master_products, create_so_header,
    get_so_details_for_excel # Import fungsi baru kita
)

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="Stock Opname FG", layout="wide")
inject_premium_theme()
protect_page("warehouse") 

# State Management
if "so_active" not in st.session_state: st.session_state.so_active = False
if "current_header" not in st.session_state: st.session_state.current_header = None
if "so_fg_cart" not in st.session_state: st.session_state.so_fg_cart = []

# Helper: Convert DF to Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# =st.dialog buat Pop-up Mulai SO =
@st.dialog("🚀 Mulai Sesi Stock Opname")
def start_so_dialog():
    st.write("Isi detail dulu sebelum mulai hitung, Bre.")
    pic_name = st.text_input("Nama PIC / Petugas", value=st.session_state.get('current_user', ''))
    date_so = st.date_input("Tanggal SO", value=date.today())
    
    if st.button("Gas, Mulai Sekarang!", type="primary", use_container_width=True):
        if pic_name:
            success, header_data = create_so_header("FG", pic_name)
            if success:
                st.session_state.so_active = True
                st.session_state.current_header = header_data
                st.session_state.so_fg_cart = [] # Reset keranjang
                st.rerun()
            else:
                st.error(f"Gagal: {header_data}")
        else:
            st.error("Nama PIC jangan kosong, Bre!")

# ==========================================
# HEADER UI
# ==========================================
st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📦 Stock Opname Finish Good (FG)")

# ==========================================
# MAIN FLOW CONTROL
# ==========================================
if not st.session_state.so_active:
    # ------------------------------------------
    # VIEW AWAL: Tombol Mulai & Riwayat
    # ------------------------------------------
    col1, col2 = st.columns([1, 1])
    with col1:
        with st.container(border=True):
            st.markdown("### 🆕 Sesi Baru")
            st.write("Klik tombol di bawah buat bikin nomor dokumen SO baru.")
            if st.button("➕ Mulai Stock Opname", type="primary", use_container_width=True):
                start_so_dialog()
    
    st.divider()
    st.subheader("📜 Riwayat Adjustment FG")
    df_hist = get_so_history("FG")

    if not df_hist.empty:
        for _, row in df_hist.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
                c1.markdown(f"**📄 {row['so_number']}**")
                c2.write(f"👤 {row['pic']} | 📅 {row['adjust_date']}")
                
                # Tombol Download Excel per Baris
                df_detail = get_so_details_for_excel(row['id'])
                if not df_detail.empty:
                    excel_data = to_excel(df_detail)
                    c4.download_button(
                        label="📥 Excel",
                        data=excel_data,
                        file_name=f"SO_DETAIL_{row['so_number']}.xlsx",
                        mime="application/vnd.ms-excel",
                        key=f"dl_{row['id']}"
                    )
                else:
                    c4.caption("No Data")
    else:
        st.info("Belum ada riwayat SO.")

else:
    # ------------------------------------------
    # VIEW SO AKTIF (Proses Hitung)
    # ------------------------------------------
    header = st.session_state.current_header
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        c1.write(f"📌 **No Dokumen:** {header['so_number']}")
        c2.write(f"👤 **PIC:** {header['pic']}")
        if c3.button("❌ Batalkan Sesi", type="secondary", use_container_width=True):
            st.session_state.so_active = False
            st.session_state.current_header = None
            st.rerun()

    # (FASE 1: KALKULATOR - Mirip code lo yang lama tapi datanya lari ke current session)
    # ... [Load Data Master & System df_sys & df_master tetep di sini] ...
    try:
        df_sys = get_stockboard_fg_view()
        df_master = get_master_products()
        spq_map = {r['part_name']: int(r.get('spq', 1)) for _, r in df_master.iterrows()}
    except:
        df_sys = pd.DataFrame(); spq_map = {}

    with st.expander("📝 FASE 1: Input Hasil Hitung", expanded=True):
        part_list = df_sys['part_name'].unique().tolist() if not df_sys.empty else []
        selected_part = st.selectbox("Pilih Barang FG", part_list, index=None)
        
        d_spq = max(1, int(spq_map.get(selected_part, 1)))
        c1, c2, c3, c4 = st.columns([1,1,1,1])
        in_spq = c1.number_input("SPQ", min_value=1, value=d_spq)
        in_box = c2.number_input("Box", min_value=0, value=0)
        in_loose = c3.number_input("Eceran", min_value=0, value=0)
        total_f = (in_spq * in_box) + in_loose
        c4.metric("Total Fisik", f"{total_f:,}")

        if st.button("➕ Masukkan ke List", type="primary", use_container_width=True):
            if selected_part:
                p_no = df_sys[df_sys['part_name'] == selected_part].iloc[0]['part_no']
                st.session_state.so_fg_cart.append({
                    "part_name": selected_part, "part_no": p_no,
                    "spq": in_spq, "box": in_box, "loose": in_loose, "actual": total_f
                })
                st.rerun()

    # (FASE 2: COMPARE & EXECUTE)
    if st.session_state.so_fg_cart:
        st.subheader("📊 FASE 2: Compare & Approval")
        compare_list = []
        for item in st.session_state.so_fg_cart:
            sys_q = int(df_sys[df_sys['part_no'] == item['part_no']].iloc[0]['balance']) if item['part_no'] in df_sys['part_no'].values else 0
            diff = item['actual'] - sys_q
            compare_list.append({
                "part_name": item['part_name'], "part_no": item['part_no'],
                "system": sys_q, "actual": item['actual'], "diff": diff
            })
        
        st.dataframe(pd.DataFrame(compare_list), use_container_width=True)

        if st.button("⚖️ POST ADJUSTMENT (FINISH)", type="primary", use_container_width=True):
            # Kirim header['id'] ke backend!
            success, msg = submit_stock_adjustment(header['id'], date.today(), "FG", compare_list, header['pic'])
            if success:
                st.success("Mantap Bre! Data SO Berhasil Disimpan.")
                # Show Download Link Langsung Setelah Finish
                df_final = get_so_details_for_excel(header['id'])
                st.download_button("📥 Download Hasil SO (Excel)", data=to_excel(df_final), file_name=f"{header['so_number']}.xlsx")
                
                time.sleep(3)
                st.session_state.so_active = False
                st.session_state.current_header = None
                st.rerun()