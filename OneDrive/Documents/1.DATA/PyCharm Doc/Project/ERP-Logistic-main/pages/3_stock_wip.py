import streamlit as st
from datetime import date
import pandas as pd
import time
from modules import inject_premium_theme, protect_page, get_wip_report_by_date

# 1. Config & Theme
st.set_page_config(page_title="Stock WIP", page_icon="⚙️", layout="wide")
inject_premium_theme()
protect_page("production")

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("⚙️ Monitoring Stock WIP (Work In Process)")

# ==========================================
# HELPER: CARD RENDERER (WIP EDITION)
# ==========================================
def render_wip_card(row, max_cap=5000):
    """
    Render kartu WIP dengan indikator khusus Scrap/NG.
    """
    # 1. Status Warna & Progress
    qty = row['balance']
    pct = qty / max_cap if max_cap > 0 else 0
    pct = min(1.0, max(0.0, pct))
    
    status_color = "🟢 Aman"
    if pct < 0.1: status_color = "🔴 Low"
    elif pct < 0.3: status_color = "🟡 Warning"

    with st.container(border=True):
        # Header
        part_name = row['part_name']
        display_name = (part_name[:30] + '..') if len(part_name) > 30 else part_name
        st.markdown(f"**{display_name}**")
        st.caption(f"{row['part_no']}")
        
        # Main Number (Balance)
        # WIP biasanya fluktuatif, jadi progress bar ngebantu visualisasi beban line
        st.markdown(f"<h2 style='margin:0; padding:0;'>{int(qty):,} <span style='font-size:16px'>{row.get('uom', 'Pcs')}</span></h2>", unsafe_allow_html=True)
        st.progress(pct, text=f"Load: {status_color}")
        
        # Smart Footer (Hanya muncul jika ada transaksi)
        cols_info = []
        
        # Masuk dari Produksi
        if row['qty_in'] > 0: 
            cols_info.append(f"📥 Prod: +{int(row['qty_in'])}")
        
        # Transfer ke FG
        if row['qty_out'] > 0: 
            cols_info.append(f"➡️ FG: -{int(row['qty_out'])}")
            
        # Scrap / NG (Highlight Merah di Text kalau mau)
        if row['qty_scrap'] > 0:
            cols_info.append(f"🗑️ NG: -{int(row['qty_scrap'])}")
        
        # Adjustment
        net_adj = row['qty_adj_in'] - row['qty_adj_out']
        if net_adj != 0:
            sign = "+" if net_adj > 0 else ""
            cols_info.append(f"⚖️ Adj: {sign}{int(net_adj)}")
            
        if cols_info:
            st.divider()
            # Join pakai pipe
            st.caption(" | ".join(cols_info))
        else:
            st.write("") 

# ==========================================
# MAIN PAGE LOGIC
# ==========================================

# 2. Control Bar
with st.container():
    c1, c2, c3 = st.columns([2, 4, 1])
    with c1:
        filter_date = st.date_input("📅 Pilih Tanggal Laporan", value=date.today())
    with c2:
        st.info(f"Posisi Stok WIP per Akhir Hari: **{filter_date.strftime('%d %B %Y')}**")
    with c3:
        if st.button("Refresh ↻", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# 3. Load Data
df_report = get_wip_report_by_date(filter_date)

if not df_report.empty:
    # 4. Metrics Global
    total_stock = df_report['balance'].sum()
    total_in = df_report['qty_in'].sum()
    total_out = df_report['qty_out'].sum()
    total_scrap = df_report['qty_scrap'].sum()
    
    # Hitung Net Adjustment
    total_adj = df_report['qty_adj_in'].sum() - df_report['qty_adj_out'].sum()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total WIP (Bal)", f"{int(total_stock):,} Pcs")
    m2.metric("Masuk (Prod)", f"{int(total_in):,} Pcs")
    m3.metric("Transfer to FG", f"{int(total_out):,} Pcs")
    m4.metric("Total Scrap (NG)", f"{int(total_scrap):,} Pcs")
    m5.metric("Net Adjustment", f"{int(total_adj):,} Pcs")

    st.divider()

    # 5. Filter & Grid Display
    # Ambil data yg aktif aja
    df_active = df_report[
        (df_report['balance'] != 0) | 
        (df_report['qty_in'] != 0) | 
        (df_report['qty_out'] != 0) |
        (df_report['qty_scrap'] != 0) |
        (df_report['qty_adj_in'] != 0) |
        (df_report['qty_adj_out'] != 0)
    ]

    if not df_active.empty:
        # A. Filter Nama Part
        all_parts = df_active['part_name'].unique().tolist()
        sel_parts = st.multiselect("🔍 Cari / Filter Part Name:", all_parts, placeholder="Ketikan nama part...")
        
        # Apply Filter
        df_show = df_active.copy()
        if sel_parts:
            df_show = df_show[df_show['part_name'].isin(sel_parts)]
            
        # B. Render Grid (3 Kolom)
        if not df_show.empty:
            rows = [df_show.iloc[i:i+3] for i in range(0, len(df_show), 3)]
            for row_chunk in rows:
                cols = st.columns(3)
                for idx, (_, row) in enumerate(row_chunk.iterrows()):
                    with cols[idx]:
                        render_wip_card(row)
        else:
            st.info("Tidak ada part yang sesuai filter.")
    else:
        st.warning("Line Stop / Tidak ada pergerakan WIP hari ini.")
else:
    st.warning("Laporan Kosong.")