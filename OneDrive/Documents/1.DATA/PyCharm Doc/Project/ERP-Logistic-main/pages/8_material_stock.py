import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules import (
    inject_premium_theme, protect_page, 
    get_material_stock_view, get_child_stock_view,
    get_combined_history_global,
    get_products_for_filter, get_bom_map_by_product # Import fungsi baru
)

st.set_page_config(page_title="Stock & History", page_icon="📋", layout="wide")
inject_premium_theme()
protect_page("material")

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📋 Monitoring Stock & History")

# Ambil daftar produk sekali saja untuk kedua filter
list_products = get_products_for_filter()

# ==========================================
# HELPER: CARD GRID SYSTEM
# ==========================================
def render_stock_card(title, qty, unit, total_in, total_out, min_val):
    if min_val > 0:
        ratio = qty / min_val
    else:
        ratio = 1.5 if qty > 0 else 0
        
    if ratio > 1.2:
        status_color = "🟢 Aman"
    elif ratio >= 0.7:
        status_color = "🟡 Warning"
    else:
        status_color = "🔴 Kritis"

    max_capacity = min_val * 3 if min_val > 0 else 1000 
    pct_bar = min(1.0, max(0.0, qty / max_capacity))

    with st.container(border=True):
        display_title = (title[:35] + '..') if len(title) > 35 else title
        st.markdown(f"**{display_title}**")
        st.markdown(f"<h2 style='margin:0; padding:0;'>{qty:,.0f} <span style='font-size:16px'>{unit}</span></h2>", unsafe_allow_html=True)
        target_display = f"{min_val:,.0f}" if min_val > 0 else "N/A"
        st.caption(f"Status: {status_color} | Min. Target: {target_display} {unit}")
        ratio_label = f"Stok Ratio: {int(ratio*100)}% dari Batas Minimal" if min_val > 0 else "BOM belum terdaftar"
        st.progress(pct_bar, text=ratio_label)
        st.divider()
        c_in, c_out = st.columns(2)
        c_in.caption(f"📥 In: {total_in:,.0f}")
        c_out.caption(f"📤 Out: {total_out:,.0f}")

# ==========================================
# SECTION A: STOCK MONITORING (CARD GRID)
# ==========================================
st.subheader("📊 Stock Realtime Dashboard")
tab_resin, tab_part = st.tabs(["🛢️ Resin (Kg)", "🔩 Child Part (Unit)"])

# --- TAB 1: RESIN STOCK ---
with tab_resin:
    df_res_stk = get_material_stock_view()
    
    if not df_res_stk.empty:
        # 1. DOUBLE FILTER BAR
        col_fil_mat, col_fil_prod = st.columns(2)
        with col_fil_mat:
            sel_mats = st.multiselect("🔍 Filter Material:", df_res_stk['full_name'].unique().tolist(), placeholder="Pilih material...", key="filter_res_name")
        with col_fil_prod:
            sel_prod_res = st.selectbox("🔍 Filter by Product (Peruntukan):", ["Semua Produk"] + list_products, key="filter_res_prod")
        
        df_show = df_res_stk.copy()
        
        # Sync Logic Filter Produk
        if sel_prod_res != "Semua Produk":
            res_ids, _ = get_bom_map_by_product(sel_prod_res)
            df_show = df_show[df_show['id'].isin(res_ids)]
            
        # Filter Nama Material
        if sel_mats:
            df_show = df_show[df_show['full_name'].isin(sel_mats)]

        # 2. RENDER GRID
        if not df_show.empty:
            rows = [df_show.iloc[i:i+3] for i in range(0, len(df_show), 3)]
            for row_chunk in rows:
                cols = st.columns(3)
                for idx, (_, row) in enumerate(row_chunk.iterrows()):
                    with cols[idx]:
                        render_stock_card(row['full_name'], row['current_stock'], "Kg", row['total_in'], row['total_out'], row.get('min_stock', 0))
        else:
            st.info("Tidak ada material yang sesuai filter.")
    else:
        st.info("Data Stok Resin Kosong.")

# --- TAB 2: PART STOCK ---
with tab_part:
    df_cp_stk = get_child_stock_view()
    
    if not df_cp_stk.empty:
        # 1. DOUBLE FILTER BAR
        col_fil_cp, col_fil_prod_cp = st.columns(2)
        with col_fil_cp:
            sel_parts = st.multiselect("🔍 Filter Komponen:", df_cp_stk['part_name'].unique().tolist(), placeholder="Pilih komponen...", key="filter_cp_name")
        with col_fil_prod_cp:
            sel_prod_cp = st.selectbox("🔍 Filter by Product (Peruntukan):", ["Semua Produk"] + list_products, key="filter_cp_prod")
            
        df_show_cp = df_cp_stk.copy()
        
        # Sync Logic Filter Produk
        if sel_prod_cp != "Semua Produk":
            _, part_ids = get_bom_map_by_product(sel_prod_cp)
            df_show_cp = df_show_cp[df_show_cp['id'].isin(part_ids)]
        
        # Filter Nama Komponen
        if sel_parts:
            df_show_cp = df_show_cp[df_show_cp['part_name'].isin(sel_parts)]
            
        # 2. RENDER GRID
        if not df_show_cp.empty:
            rows = [df_show_cp.iloc[i:i+3] for i in range(0, len(df_show_cp), 3)]
            for row_chunk in rows:
                cols = st.columns(3)
                for idx, (_, row) in enumerate(row_chunk.iterrows()):
                    with cols[idx]:
                        render_stock_card(row['part_name'], row['current_stock'], row.get('uom', 'Pcs'), row['total_in'], row['total_out'], row.get('min_stock', 0))
        else:
            st.info("Tidak ada komponen yang sesuai filter.")
    else:
        st.info("Data Stok Part Kosong.")

st.divider()

# ==========================================
# SECTION B: GRAND UNIFIED HISTORY (UNCHANGED)
# ==========================================
st.subheader("📜 Global Log History (All Items)")

c_date, _ = st.columns([1, 2])
d_range = c_date.date_input("Periode Data", value=(date.today() - timedelta(days=30), date.today()), key="d_global")
start_d, end_d = d_range if isinstance(d_range, tuple) and len(d_range) == 2 else (date.today(), date.today())

df_hist = get_combined_history_global(start_d, end_d)

if not df_hist.empty:
    with st.expander("🔍 Filter Data Lanjutan (Klik untuk Buka)", expanded=True):
        f1, f2, f3 = st.columns([1, 1, 2])
        cat_opts = df_hist['category'].unique().tolist()
        sel_cat = f1.multiselect("Kategori", cat_opts, default=cat_opts, key="f_cat")
        type_opts = df_hist['trx_type'].unique().tolist()
        sel_type = f2.multiselect("Tipe Transaksi", type_opts, default=type_opts, key="f_type")
        item_opts = df_hist['item_name'].unique().tolist()
        sel_item = f3.multiselect("Nama Barang", item_opts, key="f_item")

        f4, f5, f6 = st.columns([1, 1, 1])
        search_doc = f4.text_input("Cari No SJ / Doc", key="f_doc")
        search_chk = f5.text_input("Cari Checker / User", key="f_chk")
        search_note = f6.text_input("Cari Notes", key="f_note")

    if sel_cat: df_hist = df_hist[df_hist['category'].isin(sel_cat)]
    if sel_type: df_hist = df_hist[df_hist['trx_type'].isin(sel_type)]
    if sel_item: df_hist = df_hist[df_hist['item_name'].isin(sel_item)]
    if search_doc: df_hist = df_hist[df_hist['doc_no'].str.contains(search_doc, case=False, na=False)]
    if search_chk: df_hist = df_hist[df_hist['input_by'].str.contains(search_chk, case=False, na=False)]
    if search_note: df_hist = df_hist[df_hist['notes'].str.contains(search_note, case=False, na=False)]

    st.dataframe(
        df_hist[['trx_date', 'category', 'trx_type', 'item_name', 'qty', 'uom', 'input_by', 'doc_no', 'notes']],
        column_config={
            "trx_date": "Date",
            "qty": st.column_config.NumberColumn("Qty", format="%.2f"),
            "item_name": "Nama Barang / Material"
        },
        use_container_width=True, hide_index=True
    )
    st.caption(f"Menampilkan {len(df_hist)} riwayat transaksi.")
else:
    st.info("Tidak ada data history pada periode ini.")