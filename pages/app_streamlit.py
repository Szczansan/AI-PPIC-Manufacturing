# pages/app_streamlit.py

import streamlit as st
import pandas as pd
from datetime import datetime
import calendar
# --- FIX IMPORT BARU ---
from streamlit_javascript import st_javascript 
from pages.data_loader import calculate_capacity_report, get_rules_params
from components.navbar import show_navbar
# ---------------------

# --- FUNGSI 1: MENENTUKAN STATUS KAPASITAS ---
def get_capacity_status(days: float) -> tuple[str, str]:
    """Menentukan status dan warna yang diterima Streamlit (normal, inverse, off)."""
    if days > 26:
        status_text = "🔴 Need Adjustment Machine"
        status_color = "inverse" 
    elif days > 22:
        status_text = "🟠 Need Overtime"
        status_color = "off" 
    elif days >= 20:
        status_text = "🟢 Safe"
        status_color = "normal" 
    else:
        status_text = "🔵 Very Safe (Available Capacity)"
        status_color = "normal" 
        
    return status_text, status_color
# -----------------------------------------------


# --- FUNGSI 2: TOMBOL EXPORT PDF (FIX FINAL DELAY) ---
def add_printing_button():
    """Menggunakan st.button dan st_javascript dengan penundaan untuk memicu dialog cetak."""
    
    # CSS untuk print media (di-inject setiap kali dijalankan)
    st.markdown(
        """
        <style>
            @media print {
                /* Sembunyikan sidebar dan tombol saat mencetak */
                section[data-testid="stSidebar"], .navbar, header, footer, 
                section[data-testid="stToolbar"] {
                    display: none !important;
                }
                /* Pastikan layout mengikuti A4 */
                @page { size: A4; margin: 1cm; }
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 2. Menggunakan elemen st.button native
    if st.button("📄 Export Dashboard to PDF (A4)", key="print_pdf_btn"):
        # FIX UTAMA: Panggilan JS secara instan (menghapus setTimeout)
        st_javascript("window.print();")
# -----------------------------------


# --- 1. Konfigurasi Halaman ---
st.set_page_config(layout="wide", page_title="Dashboard Kapasitas Produksi")

# Panggil Navbar
show_navbar() 

# --- PANGGIL TOMBOL EXPORT DI SINI ---
add_printing_button()
# ------------------------------------

st.title("🏭 Dashboard Perhitungan Kapasitas")
st.caption("Menghitung Kebutuhan Hari Produksi berdasarkan Forecast")

# --- 2. Input Filter BULAN-TAHUN ---
current_year_month = datetime.now().strftime("%Y-%m")
today = datetime.now()
year_month_options = []
for i in range(-2, 12):
    date_option = today.replace(day=1) + pd.DateOffset(months=i)
    year_month_options.append(date_option.strftime("%Y-%m"))

selected_period = st.sidebar.selectbox(
    "PILIH FORECAST (BULAN-TAHUN)",
    options=year_month_options,
    index=year_month_options.index(current_year_month) 
)

st.header(f"Forecast untuk Bulan: **{selected_period}**")

# --- 3. Memuat dan Menjalankan Perhitungan ---
@st.cache_data(ttl=600)
def load_and_calculate_data(period: str):
    rules = get_rules_params()
    report_data = calculate_capacity_report(period)
    return report_data, rules

# Memuat data dan hasil perhitungan
report_data, rules = load_and_calculate_data(selected_period)

if not report_data:
    st.error(f"⚠️ Tidak ada data forecast atau terjadi kesalahan perhitungan untuk periode {selected_period}.")
else:
    # --- 4. Tampilan Dashboard Utama ---
    
    total_days_needed = max(data['total_sum_day'] for data in report_data.values())
    
    st.metric(label="Total Hari Produksi yang Dibutuhkan (Bottleneck)", 
              value=f"{total_days_needed:.2f} Hari",
              delta_color="off")
    
    st.markdown("---")
    
    # Safeguard potential_hours access
    first_report = next(iter(report_data.values())) 
    potential_hours = first_report['potential_hours_per_day']
    
    st.subheader("Parameter Dasar Perhitungan")
    col1, col2, col3 = st.columns(3)
    col1.metric("Jam Kerja Efektif Harian", f"{potential_hours:.2f} Jam", help=f"({rules.get('shift_hours', 8)}h x {rules.get('shift_per_day', 3)} shift x {rules.get('efficiency', 0.85)*100:.0f}%)")
    col2.metric("Dandory/Pergantian", f"{rules.get('dandory_min', 0)} Menit")
    col3.metric("Start Up/Pergantian", f"{rules.get('startup_min', 0)} Menit")
    
    st.markdown("---")

    # 5. Iterasi dan Tampilan per Mesin (TONAGE)
    st.subheader("Detail Kebutuhan Kapasitas per Mesin (TONAGE)")
    
    sorted_tonages = sorted(report_data.keys(), key=lambda x: float(str(x).replace(' T', '').replace('T', '')))
    
    for tonage in sorted_tonages:
        data = report_data[tonage]
        df_display = pd.DataFrame(data['data_detail']).copy() 
        
        # Formatting
        df_display['cycle_time'] = df_display['cycle_time'].apply(lambda x: f"{x:.1f} sec")
        df_display['total_hours'] = df_display['total_hours'].apply(lambda x: f"{x:.2f}")
        df_display['total_day'] = df_display['total_day'].apply(lambda x: f"{x:.2f}")

        # Tampilan Header Mesin
        st.markdown(f"### Mesin {tonage}")
        
        # --- HITUNG DAN TAMPILKAN STATUS ---
        total_day_sum = data['total_sum_day']
        status_text, status_color = get_capacity_status(total_day_sum)

        col_m1, col_m2 = st.columns([1, 2])
        
        col_m1.metric(
            label="TOTAL DAY (SUM)", 
            value=f"{total_day_sum:.2f} Hari",
            delta=status_text, 
            delta_color=status_color # Warna status
        )
        # ----------------------------------
        
        col_m2.info(f"Total Pergantian (CHANGE): **{data['total_changes']}x** | Total Waktu NOA: **{data['total_noa_hours']:.2f} Jam**")
        
        # Rename kolom agar sesuai dengan desain interface
        df_display.rename(columns={
            'part_name': 'PART NAME',
            'part_no': 'PART NO',
            'cycle_time': 'CT (Cycle Time)',
            'total_hours': 'TOTAL HOURS', 
            'total_day': 'TOTAL DAY'
        }, inplace=True)

        # Tampilan Tabel Hasil
        st.dataframe(
            df_display[['PART NAME', 'PART NO', 'CT (Cycle Time)', 'TOTAL HOURS', 'TOTAL DAY']],
            use_container_width=True
        )

# --- Petunjuk Menjalankan ---
st.sidebar.markdown("---")
st.sidebar.markdown("### Cara Menjalankan")
st.sidebar.code("streamlit run pages/app_streamlit.py")