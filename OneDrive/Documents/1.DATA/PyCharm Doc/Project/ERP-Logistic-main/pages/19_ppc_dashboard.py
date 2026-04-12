# (pages/19_ppc_dashboard.py)

import streamlit as st
import pandas as pd
from datetime import date, timedelta
import altair as alt # Buat chart yang ganteng

# Import Backend
from modules_ppc import get_ppc_po_list, get_po_items_details, get_production_performance
from modules import inject_premium_theme, protect_page
from modules_ppc import get_ppc_po_list, get_po_items_details, get_production_performance, get_po_mrp_breakdown

st.set_page_config(page_title="PPC Control Tower", page_icon="📡", layout="wide")
inject_premium_theme()
protect_page('production')

st.title("📡 PPC Command Center")

tab1, tab2 = st.tabs(["📊 Executive Summary", "📅 Production Monitoring (Tab 2)"])

# =========================================
# TAB 1: EXECUTIVE SUMMARY (PLANNING)
# =========================================
with tab1:
    st.header("📋 Production Planning (MRP Rundown)")
    
    # Filter PO
    c_plan1, c_plan2 = st.columns([2, 1])
    with c_plan1:
        po_list_plan = get_ppc_po_list()
        selected_po_plan = st.selectbox("Pilih PO untuk Analisa:", po_list_plan, key="sb_po_plan")
    
    st.divider()
    
    if selected_po_plan:
        po_num_plan = selected_po_plan.split(" | ")[0]
        mrp_data = get_po_mrp_breakdown(po_num_plan)
        
        if mrp_data:
            st.success(f"✅ Analisa Material & Waktu | PO: {po_num_plan}")
            
            for item in mrp_data:
                label = f"⚙️ {item['part_name']} | Order: {item['qty_order']:,} Pcs"
                with st.expander(label, expanded=True):
                    
                    # --- SECTION 1: WAKTU (Sama kayak kemaren) ---
                    st.markdown("##### ⏱️ Kapasitas Mesin (2 Shift)")
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Cycle Time", f"{item['ct_sec']}s", f"Cav: {item['cav']}")
                    
                    jam_butuh = item['est_hours']
                    hari_kerja = jam_butuh / 14 
                    k2.metric("Jam Mesin", f"{jam_butuh:.1f} Jam", "Eff 90%")
                    k3.metric("Est. Hari", f"{hari_kerja:.1f} Hari", "Target Selesai")
                    
                    minggu_kerja = jam_butuh / 80
                    str_minggu = "< 1 Minggu" if minggu_kerja < 1 else f"{minggu_kerja:.1f} Minggu"
                    k4.metric("Load", str_minggu, "Cap: 80H/Wk")

                    st.markdown("---")
                    
                    # --- SECTION 2: MATERIAL (UPDATED) ---
                    # Tampilkan Nama Lengkap Material
                    st.markdown(f"##### 🧱 Material: {item['mat_full_name']}")
                    
                    # Cek apakah ada Masterbatch (Mix)
                    if item['mb_kg'] > 0:
                        m1, m2 = st.columns(2)
                        with m1:
                            st.metric(
                                "Base Resin (Murni)", 
                                f"{item['resin_kg']:.2f} Kg", 
                                "Termasuk Buffer 2%"
                            )
                        with m2:
                            st.metric(
                                f"Mix: {item['mb_name']}", 
                                f"{item['mb_kg']:.2f} Kg", 
                                f"Dosis: {item['mb_pct']}%"
                            )
                    else:
                        # Single Material
                        st.metric("Total Resin", f"{item['resin_kg']:.2f} Kg", "+2% Buffer")
                    
                    # --- SECTION 3: CHILD PARTS (CLEAN TABLE) ---
                    if item['child_parts']:
                        st.markdown("##### 🔩 Komponen Insert (Child Parts)")
                        df_child = pd.DataFrame(item['child_parts'])
                        
                        st.dataframe(
                            df_child,
                            column_config={
                                "name": "Nama Part",
                                "usage": st.column_config.NumberColumn(
                                    "Usage per Unit",
                                    format="%.2f" # Max 2 desimal (misal 2.00)
                                ),
                                "total_req": st.column_config.NumberColumn(
                                    "Total Kebutuhan (Pcs)",
                                    format="%.0f" # Bulat tanpa desimal (misal 400)
                                )
                            },
                            use_container_width=True,
                            hide_index=True
                        )

# =========================================
# TAB 2: PRODUCTION MONITORING
# =========================================
with tab2:
    st.header("🏭 Production Control & Material Audit")

    # --- A. FILTER SECTION ---
    c1, c2 = st.columns([2, 1])
    with c1:
        po_list = get_ppc_po_list()
        selected_po_raw = st.selectbox("Pilih Active PO:", po_list)
    
    with c2:
        # Default tarik data bulan ini
        today = date.today()
        first_day = today.replace(day=1)
        last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        range_date = st.date_input("Filter Data Produksi:", [first_day, last_day])

    st.markdown("---")

    # --- B. PROCESS LOGIC ---
    if selected_po_raw and len(range_date) == 2:
        po_number = selected_po_raw.split(" | ")[0]
        start_d, end_d = range_date

        # 1. Ambil List Part di PO
        df_items = get_po_items_details(po_number)

        if not df_items.empty:
            for index, row in df_items.iterrows():
                part_no = row['part_no']
                target_po = row['qty_order']
                
                # Container per Part
                with st.expander(f"📦 {row['part_name']} | {part_no}", expanded=True):
                    
                    # 2. Tarik Data Performance dari Backend
                    df_prod, master_weight, days_count = get_production_performance(part_no, start_d, end_d)

                    if not df_prod.empty:
                        # --- Summary Calculations ---
                        total_ok = df_prod['qty'].sum()
                        total_ng = df_prod['total_ng'].sum()
                        total_shot = df_prod['total_qty'].sum() # Shot (OK + NG)
                        
                        # Material Calculations (Dalam KG biar enak)
                        mat_std_kg = df_prod['mat_std_usage'].sum() / 1000
                        mat_act_kg = df_prod['mat_act_usage'].sum() / 1000
                        
                        # Logic Variance Material
                        if mat_std_kg > 0:
                            diff_pct = ((mat_act_kg - mat_std_kg) / mat_std_kg) * 100
                        else:
                            diff_pct = 0
                            
                        # --- PERBAIKAN LOGIC WARNA (FIXED) ---
                        # Pakai 'inverse' biar kalau Positif (Boros) jadi Merah, Negatif (Irit) jadi Hijau
                        
                        if diff_pct > 1: # Boros > 1%
                            mat_color = "inverse" 
                            mat_status = f"BOROS (+{diff_pct:.2f}%)" # Arrow otomatis merah karena inverse
                        elif diff_pct < -1: # Irit < -1%
                            mat_color = "inverse"
                            mat_status = f"IRIT ({diff_pct:.2f}%)" # Arrow otomatis hijau karena inverse
                        else:
                            mat_color = "off"
                            mat_status = f"AMAN ({diff_pct:.2f}%)" # Netral

                        # Logic Waktu (Countdown Sederhana)
                        # Asumsi: Jika ada plan harian rata-rata, berapa hari lagi selesai?
                        avg_daily = df_prod['qty'].mean() if len(df_prod) > 0 else 0
                        sisa_qty = target_po - total_ok
                        if avg_daily > 0 and sisa_qty > 0:
                            estimasi_hari = int(sisa_qty / avg_daily)
                            time_msg = f"{estimasi_hari} Hari lagi (Avg: {int(avg_daily)}/day)"
                        elif sisa_qty <= 0:
                            time_msg = "DONE / CLOSED ✅"
                        else:
                            time_msg = "Belum ada data speed produksi"

                        # --- KPI CARDS ---
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("Target PO", f"{target_po:,} Pcs", f"Sisa: {target_po - total_ok:,}")
                        k2.metric("Actual OK", f"{total_ok:,} Pcs", f"NG: {total_ng:,} Pcs")
                        
                        # Completion Rate
                        progress = (total_ok / target_po) if target_po > 0 else 0
                        k3.progress(min(progress, 1.0), text=f"Progress: {progress*100:.1f}%")
                        k3.caption(f"⏱️ Estimasi: {time_msg}")

                        # Material Audit
                        k4.metric("Material Variance", f"{mat_act_kg:.2f} Kg", mat_status, delta_color=mat_color)
                        k4.caption(f"Std Plan: {mat_std_kg:.2f} Kg | Master Weight: {master_weight}gr")

                        st.divider()

                        # --- CHARTS & TABLE ---
                        c_chart, c_data = st.columns([1, 1])
                        
                        with c_chart:
                            st.caption("📊 Grafik Produksi Harian (Plan vs OK vs NG)")
                            # Format data for Altair (Melt)
                            chart_df = df_prod[['date_in', 'qty', 'plan_qty', 'total_ng']].melt('date_in', var_name='Category', value_name='Jumlah')
                            
                            c = alt.Chart(chart_df).mark_bar().encode(
                                x='date_in:T',
                                y='Jumlah:Q',
                                color=alt.Color('Category', scale=alt.Scale(domain=['qty', 'plan_qty', 'total_ng'], range=['#2ecc71', '#3498db', '#e74c3c'])),
                                tooltip=['date_in', 'Category', 'Jumlah']
                            ).interactive()
                            st.altair_chart(c, use_container_width=True)

                        with c_data:
                            st.caption("📝 Detail Data Harian")
                            # Tampilkan tabel yang lebih clean
                            display_cols = df_prod[['date_in', 'plan_qty', 'qty', 'total_ng', 'part_weight_act', 'mat_variance']]
                            display_cols.columns = ['Tanggal', 'Plan', 'OK', 'NG', 'Berat Act (gr)', 'Var Mat (gr)']
                            
                            # Highlight row logic bisa disini kalau mau kompleks, tapi pakai dataframe standard udah oke
                            st.dataframe(display_cols, use_container_width=True, height=250)

                    else:
                        st.warning(f"Belum ada record produksi di WIP_IN untuk Part: {part_no} dalam range tanggal ini.")
        else:
            st.error("PO ini tidak memiliki item parts.")
    else:
        st.info("👈 Pilih PO dan Range Tanggal dulu.")