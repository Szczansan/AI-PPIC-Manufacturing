import streamlit as st
from datetime import date
import pandas as pd
import time
# [UPDATE]: Panggil get_fg_report_by_date (untuk Saldo) & get_stockboard_fg_view (untuk Jam Live)
from modules import inject_premium_theme, protect_page, get_fg_report_by_date, get_stockboard_fg_view 
from supabase_client import supabase

# 1. Config & Theme
st.set_page_config(page_title="Stock Finish Good", page_icon="📈", layout="wide")
inject_premium_theme()
protect_page("warehouse")

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📈 Monitoring Finish Good (FG)")

# ==========================================
# [NEW] HELPER: FETCH GAMBAR DARI MASTER
# ==========================================
@st.cache_data(ttl=60)
def get_part_images():
    """Ambil URL gambar terupdate dari master products"""
    try:
        res = supabase.table("products").select("part_no, image_url, customer").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# ==========================================
# HELPER: CARD RENDERER (SMART UI)
# ==========================================
def render_fg_card(row, max_cap=5000):
    """
    Render kartu FG dengan layout split: Teks di Kiri, Gambar di Kanan
    """
    qty = row['balance']
    pct = qty / max_cap if max_cap > 0 else 0
    pct = min(1.0, max (0.0, pct))
    
    status_color = "🟢 Aman"
    if pct < 0.1: status_color = "🔴 Low"
    elif pct < 0.3: status_color = "🟡 Warning"

    with st.container(border=True):
        col_kiri, col_kanan = st.columns([3, 1.5])
        
        with col_kiri:
            # Header Teks
            part_name = row['part_name']
            display_name = (part_name[:30] + '..') if len(part_name) > 30 else part_name
            st.markdown(f"**{display_name}**")
            
            # [LIVE UPDATE]: Jam update ini ditarik dari View (Absolut/Real-time)
            last_time = row.get('last_update_str', '-')
            st.caption(f"{row['part_no']} | 🕒 {last_time}")
            
            # Angka Balance (Ngikutin filter tanggal)
            st.markdown(f"<h2 style='margin:0; padding:0;'>{int(qty):,} <span style='font-size:16px'>Pcs</span></h2>", unsafe_allow_html=True)
            st.progress(pct, text=f"Status: {status_color}")

        with col_kanan:
            img_url = row.get('image_url')
            if pd.notna(img_url) and img_url not in ['-', 'None', '']:
                st.write("") 
                st.image(img_url, use_container_width=True)
        
        # Smart Footer (Data pergerakan sesuai tanggal laporan)
        cols_info = []
        if row.get('qty_in', 0) > 0: cols_info.append(f"📥 WIP: +{int(row['qty_in'])}")
        if row.get('qty_out', 0) > 0: cols_info.append(f"📤 DO: -{int(row['qty_out'])}")
        
        net_adj = row.get('qty_adj_in', 0) - row.get('qty_adj_out', 0)
        if net_adj != 0:
            sign = "+" if net_adj > 0 else ""
            cols_info.append(f"⚖️ Adj: {sign}{int(net_adj)}")
            
        if cols_info:
            st.divider()
            st.caption(" | ".join(cols_info))
        else:
            st.write("") 

# ==========================================
# MAIN PAGE LOGIC
# ==========================================

# 2. Control Bar (Filter Tanggal & Reset)
with st.container():
    c1, c2, c3 = st.columns([2, 4, 1])
    with c1:
        filter_date = st.date_input("📅 Pilih Tanggal Laporan", value=date.today())
    with c2:
        st.info(f"Saldo Stok per: **{filter_date.strftime('%d %B %Y')}** | Jam Update: **REAL-TIME**")
    with c3:
        if st.button("Refresh ↻", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

# 3. Load Data - KAWINKAN SALDO & Jam Live
df_balance = get_fg_report_by_date(filter_date) # Narik Saldo (Historical)
df_live_time = get_stockboard_fg_view()        # Narik Jam Update (Live)
df_images = get_part_images()                  # Narik Gambar & Customer

if not df_balance.empty:
    # --- MERGE PROCESS ---
    # [UPDATE]: Filter df_live_time biar cuma bawa part_no dan jamnya aja, ngehindarin clash 'balance' & 'part_name'
    if not df_live_time.empty:
        df_live_time = df_live_time[['part_no', 'last_update_str']]

    # 1. Gabungkan Saldo dengan Jam Live
    df_report = pd.merge(df_balance, df_live_time, on='part_no', how='left')
    
    # 2. Gabungkan dengan Gambar & Customer dari Master
    if not df_images.empty:
        df_report = pd.merge(df_report, df_images, on='part_no', how='left', suffixes=('', '_master'))
        if 'image_url_master' in df_report.columns:
            df_report['image_url'] = df_report['image_url'].fillna(df_report['image_url_master'])

    # 4. Metrics Global (Berdasarkan tanggal laporan)
    total_stock = df_report['balance'].sum()
    total_in = df_report['qty_in'].sum()
    total_out = df_report['qty_out'].sum()
    total_adj = df_report['qty_adj_in'].sum() - df_report['qty_adj_out'].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Stok FG", f"{int(total_stock):,} Pcs")
    m2.metric("Total Masuk (WIP)", f"{int(total_in):,} Pcs")
    m3.metric("Total Keluar (DO)", f"{int(total_out):,} Pcs")
    m4.metric("Net Adjustment", f"{int(total_adj):,} Pcs")

    st.divider()

    # 5. Filter & Grid Display
    f1, f2 = st.columns(2)
    with f1:
        all_cust = sorted(df_report['customer'].dropna().unique().tolist())
        sel_cust = st.multiselect("🏢 Filter by Customer:", all_cust, placeholder="Semua Customer")

    with f2:
        df_filtered_cust = df_report.copy()
        if sel_cust:
            df_filtered_cust = df_filtered_cust[df_filtered_cust['customer'].isin(sel_cust)]
        all_parts = sorted(df_filtered_cust['part_name'].unique().tolist())
        sel_parts = st.multiselect("🔍 Cari / Filter Part Name:", all_parts, placeholder="Ketikan nama part...")

    df_show = df_filtered_cust.copy()
    if sel_parts:
        df_show = df_show[df_show['part_name'].isin(sel_parts)]

    # 6. Render Grid
    if not df_show.empty:
        rows = [df_show.iloc[i:i+3] for i in range(0, len(df_show), 3)]
        for row_chunk in rows:
            cols = st.columns(3)
            for idx, (_, row) in enumerate(row_chunk.iterrows()):
                with cols[idx]:
                    render_fg_card(row)
    else:
        st.info("Tidak ada data yang sesuai filter.")
else:
    st.warning(f"Tidak ada pergerakan stok pada tanggal {filter_date.strftime('%d %B %Y')}.")