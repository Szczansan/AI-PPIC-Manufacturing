import streamlit as st
import pandas as pd
from datetime import datetime
from components.navbar import show_navbar
from pages.data_loader import get_capacity_summary, get_capacity_detail, get_rules_info

# --- 1. CONFIG HALAMAN & CSS INJECTION ---
st.set_page_config(layout="wide", page_title="Production Capacity", page_icon="🏭")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .machine-card {
        background-color: #1c202a;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        border-left-width: 6px;
        border-left-style: solid;
    }
    .machine-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.5);
    }
    .metric-box {
        background: linear-gradient(145deg, #1f232d, #161920);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 4px 4px 10px rgba(0,0,0,0.2);
    }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; font-weight: 600; }
    .block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

show_navbar()

# --- 2. HEADER & FILTER SECTION ---
col_header, col_filter = st.columns([3, 1])

with col_header:
    st.title("🏭 Production Capacity Injection")
    st.markdown("<div style='margin-top: -15px; color: #888;'>Monitoring Load Mesin & Forecast Bulanan</div>", unsafe_allow_html=True)

with col_filter:
    month_options = []
    today = datetime.today()
    for i in range(-2, 7):
        d = today + pd.DateOffset(months=i)
        month_options.append(d.strftime("%Y-%m"))
    
    selected_period = st.selectbox("📅 Pilih Periode", month_options, index=2)

st.markdown("---")

# --- 3. LOAD DATA DARI DB ---
with st.spinner(f"🚀 Sedang memuat data {selected_period}..."):
    df_summary = get_capacity_summary(selected_period)
    df_detail = get_capacity_detail(selected_period)
    rules = get_rules_info()

# --- 4. SUMMARY DASHBOARD ---
if not df_summary.empty:
    total_safe = len(df_summary[df_summary['status'] == 'SAFE'])
    total_warning = len(df_summary[df_summary['status'] == 'WARNING']) 
    total_overload = len(df_summary[df_summary['status'] == 'OVERLOAD'])

    c1, c2, c3, c4 = st.columns(4)

    # HTML DI BAWAH INI SENGAJA DIRATAKAN KIRI BIAR GAK JADI CODE BLOCK
    with c1:
        st.markdown(f"""
<div class="metric-box" style="border-bottom: 4px solid #4ade80;">
<div style="font-size: 2.5em; font-weight: bold; color: #4ade80;">{total_safe}</div>
<div style="color: #ccc; font-weight: 600;">🟢 SAFE</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
<div class="metric-box" style="border-bottom: 4px solid #fbbf24;">
<div style="font-size: 2.5em; font-weight: bold; color: #fbbf24;">{total_warning}</div>
<div style="color: #ccc; font-weight: 600;">🟠 OVERTIME</div>
</div>
""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
<div class="metric-box" style="border-bottom: 4px solid #f87171;">
<div style="font-size: 2.5em; font-weight: bold; color: #f87171;">{total_overload}</div>
<div style="color: #ccc; font-weight: 600;">🔴 OVERLOAD</div>
</div>
""", unsafe_allow_html=True)
        
    with c4:
        if rules:
            st.markdown(f"""
<div class="metric-box" style="text-align: left; padding: 12px; font-size: 0.85em;">
<div style="color:#888;">⚙️ <b>PARAMETERS</b></div>
<div style="display:flex; justify-content:space-between;"><span>Work Hours:</span> <b style="color:white">{rules.get('shift_hours')}h x {rules.get('shifts_per_day')}</b></div>
<div style="display:flex; justify-content:space-between;"><span>Eff Rate:</span> <b style="color:white">{float(rules.get('efficiency_rate'))*100:.0f}%</b></div>
<div style="display:flex; justify-content:space-between;"><span>Loss Time:</span> <b style="color:white">{int(rules.get('dandory_minutes')) + int(rules.get('startup_minutes'))} min</b></div>
</div>
""", unsafe_allow_html=True)
    
    st.write("") 

# --- 5. MACHINE LIST (PREMIUM CARDS) ---
if df_summary.empty:
    st.info(f"ℹ️ Belum ada data forecast atau rules untuk periode {selected_period}.")
else:
    for index, row in df_summary.iterrows():
        machine_id = row['machine_id']
        tonnage = row.get('machine_tonnage', 0)
        tonnage_str = f"{int(tonnage)}T" if pd.notna(tonnage) and tonnage != 0 else "N/A"
        
        status = row['status']
        days_needed = row['days_needed']
        work_days = row['work_days_in_month']
        
        if status == 'OVERLOAD':
            color = "#f87171" 
            status_text = "OVERLOAD"
            icon = "🔥"
        elif status == 'WARNING':
            color = "#fbbf24" 
            status_text = "NEED OVERTIME"
            icon = "⚡"
        else:
            color = "#4ade80" 
            status_text = "SAFE"
            icon = "✅"

        # --- PREMIUM HTML CARD (RATA KIRI JUGA) ---
        html_card = f"""
<div class="machine-card" style="border-left-color: {color};">
<div style="display: flex; justify-content: space-between; align-items: center;">
<div>
<div style="display: flex; align-items: baseline; gap: 10px;">
<h3 style="margin: 0; color: #fff; font-size: 1.4rem;">{machine_id}</h3>
<span style="background: #333; color: #ccc; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; font-weight: bold;">{tonnage_str}</span>
</div>
<div style="margin-top: 5px; color: #888; font-size: 0.9rem;">Target Max: {work_days} Hari</div>
</div>
<div style="text-align: center;">
<div style="font-size: 2.8rem; font-weight: 800; color: {color}; line-height: 1;">{days_needed}</div>
<div style="font-size: 0.8rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px;">Days Load</div>
</div>
<div style="text-align: right;">
<div style="background-color: {color}20; border: 1px solid {color}; color: {color}; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; display: inline-block;">{icon} {status_text}</div>
<div style="margin-top: 8px; font-size: 0.85rem; color: #666;">Items: <b style="color: #ccc;">{row['total_mold_change']}</b> Part</div>
</div>
</div>
</div>
"""
        st.markdown(html_card, unsafe_allow_html=True)

        with st.expander(f"🔽 Lihat Detail Part Mesin {machine_id}"):
            filter_part = df_detail[df_detail['machine_id'] == machine_id].copy()
            
            if not filter_part.empty:
                display_table = filter_part[[
                    'part_name', 'part_no', 'ct_sec', 'qty_forecast', 'load_days'
                ]].copy()
                
                display_table.rename(columns={
                    'part_name': 'PART NAME',
                    'part_no': 'PART NO',
                    'ct_sec': 'Cycle Time',
                    'qty_forecast': 'Qty Plan',
                    'load_days': 'Capacity Usage'
                }, inplace=True)

                st.dataframe(
                    display_table,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "PART NAME": st.column_config.TextColumn("Part Name", width="medium"),
                        "Cycle Time": st.column_config.NumberColumn("C/T (Sec)", format="%d s"),
                        "Qty Plan": st.column_config.NumberColumn("Qty Forecast", format="%d pcs"),
                        "Capacity Usage": st.column_config.ProgressColumn(
                            "Load Impact (Days)",
                            help="Seberapa banyak hari yang dihabiskan part ini",
                            format="%.2f Hari",
                            min_value=0,
                            max_value=float(work_days),
                        ),
                    }
                )
            else:
                st.caption("Tidak ada data part detail.")
        
        st.write("")