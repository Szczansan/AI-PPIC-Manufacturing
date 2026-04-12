import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
from modules import (
    inject_premium_theme, protect_page, get_master_products, 
    get_ng_types, add_new_ng_type, submit_production_logsheet,
    get_wip_in_history_paged # <--- FUNGSI BARU
)

st.set_page_config(page_title="Input Produksi", layout="wide")
inject_premium_theme()
protect_page('production') 

if 'dt_cart' not in st.session_state: st.session_state.dt_cart = []

st.title("🏭 Production Entry & History")

# BIKIN TABS BIAR RAPI
tab_input, tab_hist = st.tabs(["📝 Input Laporan", "🗄️ Riwayat & Filter"])

# ==========================================
# TAB 1: INPUT LAPORAN (Kode Lama dipindah kesini)
# ==========================================
with tab_input:
    # --- HEADER ---
    with st.container(border=True):
        st.markdown("### 1. Identitas Kerja")
        c1, c2, c3, c4 = st.columns(4)
        trx_date = c1.date_input("Tanggal", date.today())
        shift = c2.selectbox("Shift", ["Shift 1", "Shift 2", "Shift 3", "Non-Shift"])
        machine = c3.selectbox("No Mesin", [f"MC-{i:02d}" for i in range(1, 21)]) 
        operator = c4.text_input("Nama Leader/Operator", value=st.session_state.current_user)

    # --- PRODUK ---
    with st.container(border=True):
        st.markdown("### 2. Produk & Target")
        df_part = get_master_products()
        part_opt = df_part['part_name'].tolist() if not df_part.empty else []
        sel_part = st.selectbox("Pilih Produk", part_opt)
        
        std_part_no, std_weight, std_ct = "", 0.0, 0.0
        if sel_part and not df_part.empty:
            row = df_part[df_part['part_name'] == sel_part].iloc[0]
            std_part_no = row['part_no']; std_weight = row.get('part_weight', 0.0); std_ct = row.get('std_cycle_time', 0.0)
            
        i1, i2, i3, i4 = st.columns([2, 1, 1, 1])
        i1.text_input("Part No", value=std_part_no, disabled=True)
        act_ct = i2.number_input("Cycle Time", value=float(std_ct))
        act_weight = i3.number_input("Berat Part", value=float(std_weight))
        plan_qty = i4.number_input("PLAN QTY", min_value=0, step=100)

    # --- RESULT ---
    with st.container(border=True):
        st.markdown("### 3. Hasil Produksi")
        total_qty = st.number_input("TOTAL OUTPUT (Gross)", min_value=0)
        st.divider()
        st.markdown("##### 📝 Rincian Reject (NG)")
        
        df_ng_types = get_ng_types()
        ng_names = df_ng_types['ng_name'].tolist() if not df_ng_types.empty else ["SILVER", "SHORT SHOT"]
        ng_inputs = {}
        ng_cols = st.columns(4)
        for idx, ng in enumerate(ng_names):
            with ng_cols[idx % 4]:
                val = st.number_input(f"{ng}", min_value=0, step=1, key=f"ng_{ng}")
                if val > 0: ng_inputs[ng] = val
        
        total_ng_calc = sum(ng_inputs.values())
        qty_ok_calc = total_qty - total_ng_calc
        
        m1, m2, m3 = st.columns(3)
        m1.metric("TOTAL OUTPUT", f"{total_qty}")
        if qty_ok_calc < 0:
            m2.metric("TOTAL NG", f"{total_ng_calc}", delta_color="inverse")
            m3.error("MINUS!")
            valid_math = False
        else:
            m2.metric("TOTAL NG", f"{total_ng_calc}", delta_color="inverse")
            m3.metric("QTY OK", f"{qty_ok_calc}", delta="Yield OK")
            valid_math = True

    # --- DOWNTIME ---
    with st.container(border=True):
        st.markdown("### 4. Hambatan")
        with st.expander("➕ Tambah Downtime"):
            d1, d2, d3 = st.columns(3)
            ts = d1.time_input("Mulai"); te = d2.time_input("Selesai")
            dur = int((datetime.combine(date.today(), te) - datetime.combine(date.today(), ts)).total_seconds() / 60)
            d3.metric("Durasi", f"{dur} Min")
            cat = st.selectbox("Kategori", ["A. MACHINE", "B. MATERIAL", "C. MAN", "D. MOLD", "E. METHOD", "F. OTHERS"])
            rem = st.text_input("Remarks")
            if st.button("Simpan DT") and dur > 0:
                st.session_state.dt_cart.append({"start": str(ts), "end": str(te), "duration": dur, "category": cat, "remarks": rem})
                st.rerun()
        if st.session_state.dt_cart:
            st.dataframe(pd.DataFrame(st.session_state.dt_cart), hide_index=True)
            if st.button("Clear DT"): st.session_state.dt_cart = []; st.rerun()

    # --- SUBMIT ---
    st.divider()
    if st.button("💾 SUBMIT LAPORAN", type="primary"):
        if not sel_part or not valid_math or total_qty == 0:
            st.error("Cek inputan!")
        else:
            payload = {
                "date": trx_date, "shift": shift, "machine": machine, "operator": operator,
                "doc_no": f"PRD/{trx_date.strftime('%y%m%d')}/{shift}/{machine}",
                "part_name": sel_part, "part_no": std_part_no, "part_weight_act": act_weight,
                "act_cycle_time": act_ct, "plan_qty": plan_qty, "total_qty": total_qty,
                "qty_ok": qty_ok_calc, "total_ng": total_ng_calc, "notes": "-"
            }
            final_ng = [{"type": k, "qty": v} for k, v in ng_inputs.items()]
            succ, msg = submit_production_logsheet(payload, final_ng, st.session_state.dt_cart)
            if succ: st.success(msg); st.session_state.dt_cart = []; st.balloons()
            else: st.error(msg)

# ==========================================
# TAB 2: RIWAYAT & FILTER (FITUR BARU)
# ==========================================
with tab_hist:
    st.subheader("🗄️ Arsip Laporan Produksi")
    
    # 1. FILTER BAR
    with st.container(border=True):
        fc1, fc2, fc3 = st.columns([2, 2, 1])
        today = date.today()
        # Range Filter
        d_range = fc1.date_input("Filter Tanggal", value=(today - timedelta(days=7), today))
        if isinstance(d_range, tuple) and len(d_range) == 2: start_d, end_d = d_range
        else: start_d, end_d = today, today
            
        # Search
        search = fc2.text_input("Cari Produk / Operator / No Dokumen")
        
        # Pagination
        page = fc3.number_input("Halaman", min_value=1, value=1)

    # 2. LOAD DATA
    df_hist, total = get_wip_in_history_paged(page, 10, start_d, end_d, search)
    st.caption(f"Halaman {page}. Total Data: {total}")

    # 3. TABEL
    if not df_hist.empty:
        # Pilih kolom penting
        cols = ['date_in', 'doc_no', 'shift', 'machine_no', 'part_name', 'total_qty', 'qty', 'total_ng', 'total_downtime']
        rename = {'date_in': 'Tanggal', 'doc_no': 'Dokumen', 'total_qty': 'Output', 'qty': 'OK', 'total_ng': 'NG', 'total_downtime': 'DT (Min)'}
        st.dataframe(df_hist[cols].rename(columns=rename), hide_index=True, use_container_width=True)
    else:
        st.info("Data tidak ditemukan.")
