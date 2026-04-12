import streamlit as st
import pandas as pd
from datetime import date
import time
import io
from modules import (
    inject_premium_theme, protect_page, 
    get_material_stock_view, get_child_stock_view,
    submit_stock_adjustment, get_so_history, 
    create_so_header, get_so_details_for_excel
)

# ==========================================
# 1. CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="STO Material", page_icon="⚖️", layout="wide")
inject_premium_theme()
protect_page("material")

# Session State Management
if "so_mat_active" not in st.session_state: st.session_state.so_mat_active = False
if "mat_header" not in st.session_state: st.session_state.mat_header = None
if "sto_res_cart" not in st.session_state: st.session_state.sto_res_cart = []
if "sto_cp_cart" not in st.session_state: st.session_state.sto_cp_cart = []

# Helper: Excel Converter
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Dialog Pop-up Mulai SO
@st.dialog("🚀 Mulai Sesi SO Material/Part")
def start_so_material_dialog(cat_label):
    st.write(f"Buat dokumen SO baru untuk kategori: **{cat_label}**")
    pic = st.text_input("Nama PIC Checker", value=st.session_state.get('current_user', ''))
    
    if st.button("Buat Dokumen", type="primary", use_container_width=True):
        if pic:
            # Kita tentukan kategori database berdasarkan tab
            db_cat = "RESIN" if cat_label == "Resin" else "CHILD_PART"
            success, header = create_so_header(db_cat, pic)
            if success:
                st.session_state.so_mat_active = True
                st.session_state.mat_header = header
                st.rerun()
        else:
            st.error("Isi nama PIC dulu, Bre!")

# ==========================================
# HEADER UI
# ==========================================
st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("⚖️ Stock Opname Material & Part")

# ==========================================
# MAIN LOGIC: CEK APAKAH SO LAGI AKTIF
# ==========================================
if not st.session_state.so_mat_active:
    # --- TAMPILAN AWAL (RIWAYAT & TOMBOL MULAI) ---
    tab_hist_res, tab_hist_cp = st.tabs(["📜 Riwayat Resin", "📜 Riwayat Child Part"])
    
    with tab_hist_res:
        if st.button("➕ Mulai SO Resin Baru", type="primary"): start_so_material_dialog("Resin")
        st.divider()
        df_h = get_so_history("RESIN")
        if not df_h.empty:
            for _, r in df_h.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**📄 {r['so_number']}**")
                    c2.caption(f"👤 {r['pic']} | 📅 {r['adjust_date']}")
                    df_det = get_so_details_for_excel(r['id'])
                    c3.download_button("📥 Excel", to_excel(df_det), f"{r['so_number']}.xlsx", key=f"dl_res_{r['id']}")
        else: st.info("Belum ada riwayat.")

    with tab_hist_cp:
        if st.button("➕ Mulai SO Child Part Baru", type="primary"): start_so_material_dialog("Child Part")
        st.divider()
        df_h_cp = get_so_history("CHILD_PART")
        if not df_h_cp.empty:
            for _, r in df_h_cp.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.markdown(f"**📄 {r['so_number']}**")
                    c2.caption(f"👤 {r['pic']} | 📅 {r['adjust_date']}")
                    df_det = get_so_details_for_excel(r['id'])
                    c3.download_button("📥 Excel", to_excel(df_det), f"{r['so_number']}.xlsx", key=f"dl_cp_{r['id']}")
        else: st.info("Belum ada riwayat.")

else:
    # --- TAMPILAN SEDANG SO (INPUT MODE) ---
    header = st.session_state.mat_header
    with st.container(border=True):
        col_h1, col_h2 = st.columns([4, 1])
        col_h1.write(f"📝 **Sesi Aktif:** {header['so_number']} ({header['category']}) | 👤 {header['pic']}")
        if col_h2.button("❌ Batalkan", use_container_width=True):
            st.session_state.so_mat_active = False
            st.rerun()

    # Logika Tab (Hanya tampilkan tab yang sesuai kategori header)
    if header['category'] == "RESIN":
        st.subheader("Input Hasil Hitung Resin")
        df_res = get_material_stock_view()
        # [Bagian Input Resin lo yang lama - tetep sama]
        with st.expander("📝 Input Fisik", expanded=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            sel_res = c1.selectbox("Pilih Resin", df_res['full_name'].tolist() if not df_res.empty else [])
            act_res = c2.number_input("Qty Fisik (Kg)", min_value=0.0, step=0.1)
            if c3.button("➕ List"):
                r_row = df_res[df_res['full_name'] == sel_res].iloc[0]
                st.session_state.sto_res_cart.append({
                    "id": r_row['id'], "part_name": sel_res, 
                    "system": float(r_row['current_stock']), "actual": act_res, "diff": act_res - float(r_row['current_stock'])
                })
                st.rerun()

        if st.session_state.sto_res_cart:
            df_edit = st.data_editor(pd.DataFrame(st.session_state.sto_res_cart), use_container_width=True, hide_index=True)
            if st.button("⚖️ POST ADJUSTMENT RESIN", type="primary", use_container_width=True):
                # KIRIM HEADER ID KE BACKEND!
                success, msg = submit_stock_adjustment(header['id'], date.today(), "RESIN", df_edit.to_dict('records'), header['pic'])
                if success:
                    st.success(msg)
                    st.session_state.so_mat_active = False
                    st.session_state.sto_res_cart = []
                    time.sleep(2); st.rerun()

    elif header['category'] == "CHILD_PART":
        st.subheader("Input Hasil Hitung Child Part")
        df_cp = get_child_stock_view()
        # [Bagian Input Child Part lo yang lama - tetep sama]
        with st.expander("📝 Input Fisik", expanded=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            sel_cp = c1.selectbox("Pilih Part", df_cp['part_name'].tolist() if not df_cp.empty else [])
            act_cp = c2.number_input("Qty Fisik (Pcs)", min_value=0)
            if c3.button("➕ List"):
                row_cp = df_cp[df_cp['part_name'] == sel_cp].iloc[0]
                st.session_state.sto_cp_cart.append({
                    "id": row_cp['id'], "part_name": sel_cp, "part_no": row_cp['part_no'],
                    "system": int(row_cp['current_stock']), "actual": int(act_cp), "diff": int(act_cp) - int(row_cp['current_stock'])
                })
                st.rerun()

        if st.session_state.sto_cp_cart:
            df_edit_cp = st.data_editor(pd.DataFrame(st.session_state.sto_cp_cart), use_container_width=True, hide_index=True)
            if st.button("⚖️ POST ADJUSTMENT PART", type="primary", use_container_width=True):
                # KIRIM HEADER ID KE BACKEND!
                success, msg = submit_stock_adjustment(header['id'], date.today(), "CHILD_PART", df_edit_cp.to_dict('records'), header['pic'])
                if success:
                    st.success(msg)
                    st.session_state.so_mat_active = False
                    st.session_state.sto_cp_cart = []
                    time.sleep(2); st.rerun()