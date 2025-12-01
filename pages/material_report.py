# pages/material_report.py

import streamlit as st
import pandas as pd
from datetime import datetime

# Impor dari file loader material yang baru
from pages.data_loader_material import calculate_material_report
# Impor navbar
from components.navbar import show_navbar

# --- FUNGSI HALAMAN UTAMA ---
def material_report_page():
    
    # --- 1. Konfigurasi Halaman ---
    st.set_page_config(layout="wide", page_title="Laporan Kebutuhan Material")

    show_navbar() 

    st.title("🧱 Laporan Kebutuhan Material")
    
    # --- 2. Logika Filter Periode (DIPINDAHKAN KE MAIN PAGE) ---
    current_year_month = datetime.now().strftime("%Y-%m")
    today = datetime.now()
    year_month_options = []
    
    # Generate opsi bulan (2 bulan ke belakang s/d 1 tahun ke depan)
    for i in range(-2, 12):
        date_option = today.replace(day=1) + pd.DateOffset(months=i)
        year_month_options.append(date_option.strftime("%Y-%m"))

    # Bikin kolom biar dropdown gak menuhin satu layar (ratio 1:3)
    col_filter, col_empty = st.columns([1, 4])

    with col_filter:
        # GANTI DARI st.sidebar.selectbox JADI st.selectbox
        selected_period = st.selectbox(
            "🗓️ PILIH FORECAST (BULAN-TAHUN)",
            options=year_month_options,
            index=year_month_options.index(current_year_month) 
        )

    st.markdown("---") # Garis pemisah biar rapi
    st.header(f"Kebutuhan Material untuk Bulan: **{selected_period}**")

    # --- 3. Memuat dan Menjalankan Perhitungan ---
    @st.cache_data(ttl=600)
    def load_material_data(period: str):
        return calculate_material_report(period)

    material_report_df = load_material_data(selected_period)

    if material_report_df.empty:
        st.error(f"⚠️ Tidak ada data atau terjadi kegagalan saat JOIN/perhitungan Material untuk periode {selected_period}. Cek data 'forcast' dan 'MASTER' (GROSS/Material Specs).")
    else:
        # --- 4. Tampilan Dashboard Material ---
        
        total_material_items = len(material_report_df)
        total_kg_needed = material_report_df['total_required_kg'].sum()
        
        col1, col2 = st.columns(2)
        # Style metric biar lebih menonjol (optional)
        col1.metric("Total Jenis Material Unik", f"{total_material_items} Jenis")
        col2.metric("TOTAL KEBUTUHAN MATERIAL", f"{total_kg_needed:,.2f} Kg")

        st.markdown("---")

        st.subheader("Detail Kebutuhan Material (Total Required Quantity)")
        
        df_display = material_report_df.copy()
        
        # Formatting angka string buat display
        df_display['total_required_kg'] = df_display['total_required_kg'].apply(lambda x: f"{x:,.2f}")
        df_display['total_forecast_parts'] = df_display['total_forecast_parts'].apply(lambda x: f"{x:,.0f}")
        
        df_display.rename(columns={
            'material_id_unique': 'MATERIAL ID UNIK',
            'material_type': 'TIPE',
            'material_grade': 'GRADE',
            'material_color': 'WARNA',
            'total_required_kg': 'TOTAL KEBUTUHAN (Kg)',
            'unit': 'UNIT',
            'total_forecast_parts': 'PARTS TERKAIT (QTY)'
        }, inplace=True)

        st.dataframe(
            df_display[['MATERIAL ID UNIK', 'TIPE', 'GRADE', 'WARNA', 'TOTAL KEBUTUHAN (Kg)', 'UNIT', 'PARTS TERKAIT (QTY)']],
            use_container_width=True
        )

if __name__ == "__main__":
    material_report_page()