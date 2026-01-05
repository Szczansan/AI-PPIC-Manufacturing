import streamlit as st
import pandas as pd
import plotly.express as px
from pages.data_loader_material import get_material_requirements, get_available_months
from components.navbar import show_navbar

def material_report_page():
    st.set_page_config(layout="wide", page_title="Material Dashboard")
    show_navbar()

    st.title("🧱 Material Requirement Dashboard")

    # --- 1. FILTER AREA (SIDEBAR & TOP) ---
    col_filter1, col_filter2 = st.columns([1, 3])
    
    # Ambil opsi bulan langsung dari data yang ada
    available_months = get_available_months()
    if not available_months:
        available_months = [pd.Timestamp.now().strftime("%Y-%m")] # Fallback kalau kosong

    with col_filter1:
        selected_period = st.selectbox("🗓️ Pilih Periode Forecast", available_months)

    # --- 2. LOAD DATA ---
    df = get_material_requirements(selected_period)

    if df.empty:
        st.info(f"Belum ada data forecast/material untuk periode {selected_period}.")
    else:
        # Buat kolom ID Unik gabungan (buat display)
        df['Full_Spec'] = df['TYPE_MATERIAL'] + " " + df['GRADE_MATERIAL'] + " " + df['COLOR_MATERIAL']

        # --- FILTER LANJUTAN (MATERIAL TYPE) ---
        # Kita taruh di expander biar rapi atau sidebar
        with st.expander("🔎 Filter Spesifik Material", expanded=True):
            all_types = df['TYPE_MATERIAL'].unique().tolist()
            selected_types = st.multiselect("Pilih Tipe Material:", all_types, default=all_types)
        
        # Filter Dataframe berdasarkan pilihan user
        filtered_df = df[df['TYPE_MATERIAL'].isin(selected_types)]

        st.markdown("---")

        # --- 3. KPI CARDS ---
        total_kg = filtered_df['total_required_kg'].sum()
        total_parts = filtered_df['total_forecast_parts'].sum()
        unique_mats = filtered_df['Full_Spec'].nunique()

        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Kebutuhan (Kg)", f"{total_kg:,.2f} Kg")
        kpi2.metric("Total Parts (Pcs)", f"{total_parts:,.0f} Pcs")
        kpi3.metric("Jenis Material", f"{unique_mats} Item")

        st.markdown("---")

        # --- 4. GRAFIK (VISUALISASI) ---
        chart_col1, chart_col2 = st.columns([2, 1])

        with chart_col1:
            st.subheader("📊 Top 10 Kebutuhan Material (Kg)")
            # Group by Full Spec biar ketahuan Grade/Warnanya
            top_materials = filtered_df.groupby('Full_Spec')['total_required_kg'].sum().nlargest(10).reset_index()
            
            fig_bar = px.bar(
                top_materials, 
                x='total_required_kg', 
                y='Full_Spec', 
                orientation='h',
                text_auto='.2s',
                color='total_required_kg',
                color_continuous_scale='Blues'
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with chart_col2:
            st.subheader("🍩 Komposisi Tipe")
            # Group by Tipe Material aja
            type_dist = filtered_df.groupby('TYPE_MATERIAL')['total_required_kg'].sum().reset_index()
            
            fig_pie = px.pie(
                type_dist, 
                values='total_required_kg', 
                names='TYPE_MATERIAL', 
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- 5. TABEL DETAIL ---
        st.subheader("📋 Rincian Data")
        st.dataframe(
            filtered_df[['TYPE_MATERIAL', 'GRADE_MATERIAL', 'COLOR_MATERIAL', 'total_required_kg', 'total_forecast_parts']]
            .sort_values('total_required_kg', ascending=False)
            .style.format({'total_required_kg': "{:,.2f}", 'total_forecast_parts': "{:,.0f}"}),
            use_container_width=True,
            height=400
        )

if __name__ == "__main__":
    material_report_page()