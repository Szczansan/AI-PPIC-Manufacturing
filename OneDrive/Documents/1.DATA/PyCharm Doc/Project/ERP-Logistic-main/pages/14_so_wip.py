import streamlit as st
import pandas as pd
import time # <--- INI YANG TADI KURANG
from datetime import date
from modules import (
    inject_premium_theme, protect_page, 
    get_stockboard_view, submit_stock_adjustment, get_adjustment_history
)

st.set_page_config(page_title="Stock Opname WIP", layout="wide")
inject_premium_theme()
protect_page("production") 

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("🧐 Stock Opname WIP")

if "so_wip_cart" not in st.session_state: st.session_state.so_wip_cart = []

# Load System Stock
df_sys = get_stockboard_view()

# ==========================================
# FASE 1: BLIND COUNT
# ==========================================
with st.expander("📝 FASE 1: Input Hasil Hitung (Blind Count)", expanded=True):
    c1, c2, c3 = st.columns([3, 2, 1])
    
    with c1:
        part_list = df_sys['part_name'].unique().tolist() if not df_sys.empty else []
        so_part = st.selectbox("Pilih Part", part_list)
        
    with c2:
        so_qty = st.number_input("Qty Actual (Fisik)", min_value=0, step=1)
        
    with c3:
        st.write("Action")
        if st.button("➕ Catat"):
            if not so_part: st.error("Pilih Part!")
            else:
                p_no = df_sys[df_sys['part_name'] == so_part].iloc[0]['part_no']
                st.session_state.so_wip_cart.append({
                    "part_name": so_part,
                    "part_no": p_no,
                    "actual": so_qty
                })
                st.success("Tercatat.")

    if st.session_state.so_wip_cart:
        st.caption("Daftar Hitungan Sementara:")
        st.dataframe(pd.DataFrame(st.session_state.so_wip_cart), use_container_width=True)
        if st.button("Reset List", type="secondary"):
            st.session_state.so_wip_cart = []
            st.rerun()

# ==========================================
# FASE 2: COMPARE & ADJUSTMENT
# ==========================================
st.divider()
st.subheader("📊 FASE 2: Compare & Adjustment")

if not st.session_state.so_wip_cart:
    st.info("Belum ada data hitungan. Silakan input di Fase 1.")
else:
    compare_data = []
    
    for item in st.session_state.so_wip_cart:
        sys_row = df_sys[df_sys['part_no'] == item['part_no']]
        qty_sys = int(sys_row.iloc[0]['balance']) if not sys_row.empty else 0
        qty_act = item['actual']
        diff = qty_act - qty_sys
        
        status = "✅ MATCH"
        if diff > 0: status = "🔼 GAIN"
        elif diff < 0: status = "🔻 LOSS"
        
        compare_data.append({
            "part_name": item['part_name'], "part_no": item['part_no'],
            "system": qty_sys, "actual": qty_act, "diff": diff, "status": status
        })
    
    df_compare = pd.DataFrame(compare_data)
    
    st.dataframe(
        df_compare, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "system": st.column_config.NumberColumn("Stok System"),
            "actual": st.column_config.NumberColumn("Hasil SO (Fisik)"),
            "diff": st.column_config.NumberColumn("Selisih", format="%d")
        }
    )
    
    with st.form("form_adj_wip"):
        st.warning("⚠️ Perhatian: Menekan tombol di bawah akan mengubah Stok System secara permanen.")
        col_a, col_b = st.columns(2)
        with col_a: date_adj = st.date_input("Tanggal SO", value=date.today())
        with col_b: pic_adj = st.text_input("PIC Stock Opname")
            
        if st.form_submit_button("⚖️ POST ADJUSTMENT (UPDATE STOK)"):
            if not pic_adj: st.error("PIC Wajib diisi!")
            else:
                success, msg = submit_stock_adjustment(date_adj, "WIP", compare_data, pic_adj)
                if success:
                    st.success(msg)
                    st.session_state.so_wip_cart = []
                    st.cache_data.clear()
                    time.sleep(2) # Sekarang aman karena sudah import time
                    st.rerun()
                else: st.error(msg)

st.divider()
st.caption("Riwayat Adjustment Terakhir")
st.dataframe(get_adjustment_history("WIP"), use_container_width=True)
