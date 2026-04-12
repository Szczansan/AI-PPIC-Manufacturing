import streamlit as st
import pandas as pd
from datetime import datetime
from modules import inject_premium_theme, protect_page, get_box_stock_as_of

st.set_page_config(page_title="Stock Box", layout="wide")
inject_premium_theme()
protect_page("warehouse")

st.title("📊 Monitor Stok Box & Packaging")

c1, c2 = st.columns([1, 3])
target_date = c1.date_input("🗓️ Tampilkan Stok per Tanggal:", datetime.now())

st.divider()

with st.spinner("Mengkalkulasi stok..."):
    df_stock = get_box_stock_as_of(target_date)

if not df_stock.empty:
    # Summary Global taruh di atas biar langsung kelihatan
    total_all_boxes = df_stock['current_stock'].sum()
    st.info(f"**📦 Total Keseluruhan Box di Pabrik saat ini:** {total_all_boxes:,.0f} Pcs")
    st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)
    
    # --- UI CARD GRID ---
    cols = st.columns(3) # Bikin 3 card sejajar ke samping
    
    for idx, row in df_stock.iterrows():
        # Masukin ke kolom secara bergantian (0, 1, 2, 0, 1, 2...)
        with cols[idx % 3]: 
            with st.container(border=True):
                st.markdown(f"<h3 style='margin-bottom: 0px; color: #00f2ff;'>{row['box_name']}</h3>", unsafe_allow_html=True)
                st.caption(f"Spek: {row['specification']} | Model: {row['model']} | Cust: {row['customer']}")
                
                # Bikin garis batas tipis
                st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Masuk (IN)", int(row['total_in']))
                m2.metric("Keluar (OUT)", int(row['total_out']))
                m3.metric("SO (Adj)", int(row['total_variance']))
                
                st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                # Stok Akhir dibikin gede di bawah
                st.metric("📦 STOK ", int(row['current_stock']))
                
else:
    st.warning("Belum ada data stok Box.")