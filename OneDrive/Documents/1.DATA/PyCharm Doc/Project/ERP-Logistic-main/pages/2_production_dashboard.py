import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta
import io
import xlsxwriter
from supabase_client import supabase 
from modules import inject_premium_theme, protect_page

# 1. SETUP PAGE
st.set_page_config(page_title="Production Dashboard", layout="wide")
inject_premium_theme()
protect_page('production')

st.title("📊 Production Performance Monitor")

# 2. FILTER DATA (GLOBAL)
with st.container(border=True):
    c1, c2 = st.columns([2, 3])
    today = date.today()
    last_week = today - timedelta(days=6)
    
    date_range = c1.date_input("Pilih Periode Analisa", value=(last_week, today), max_value=today, format="DD/MM/YYYY")
    
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        st.caption(f"Menampilkan data: **{start_date}** s/d **{end_date}**")
        try:
            res = supabase.table("wip_in").select("*").gte("date_in", str(start_date)).lte("date_in", str(end_date)).order("date_in", desc=False).execute()
            df = pd.DataFrame(res.data)
        except Exception as e:
            st.error(f"Gagal tarik data: {e}"); df = pd.DataFrame()
    else:
        st.warning("⚠️ Harap pilih tanggal awal dan akhir."); st.stop()

# --- PRE-PROCESSING DATA ---
df_ng_flat = pd.DataFrame()
df_dt_flat = pd.DataFrame()

if not df.empty:
    # 1. Flatten NG Data
    all_ng = []
    for index, row in df.iterrows():
        if row.get('ng_detail'):
            for item in row['ng_detail']:
                item['parent_date'] = row['date_in']
                item['parent_part'] = row['part_name']
                item['parent_machine'] = row['machine_no']
                # Ambil Problem Category dari Header
                item['parent_problem_cat'] = row.get('problem_category') or "-"
                all_ng.append(item)
    if all_ng:
        df_ng_flat = pd.DataFrame(all_ng)

    # 2. Flatten Downtime Data
    all_dt = []
    for index, row in df.iterrows():
        if row.get('downtime_detail'):
            for item in row['downtime_detail']:
                if 'remarks' not in item or item['remarks'] is None:
                    item['remarks'] = "-"
                
                item['parent_date'] = row['date_in']
                item['parent_part'] = row['part_name']
                item['parent_machine'] = row['machine_no']
                # [NEW] Ambil Problem Category dari Header buat Analisa Downtime
                item['parent_problem_cat'] = row.get('problem_category') or "-"
                
                all_dt.append(item)
    if all_dt:
        df_dt_flat = pd.DataFrame(all_dt)

# 3. GLOBAL METRICS
if not df.empty:
    total_qty = df['total_qty'].sum(); total_ok = df['qty'].sum(); total_ng = df['total_ng'].sum(); total_dt = df['total_downtime'].sum()
    yield_rate = (total_ok / total_qty * 100) if total_qty > 0 else 0
else:
    total_qty = 0; total_ok = 0; total_ng = 0; yield_rate = 0; total_dt = 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Output", f"{total_qty:,} Pcs")
m2.metric("Total OK", f"{total_ok:,} Pcs", delta=f"Yield Avg: {yield_rate:.1f}%")
m3.metric("Total NG", f"{total_ng:,} Pcs", delta_color="inverse")
m4.metric("Total Downtime", f"{total_dt:,} Menit", delta_color="inverse")

st.divider()

# 4. TABS ANALISA KOMPLIT
tab_overview, tab_part, tab_machine, tab_plan = st.tabs([
    "📉 Global Overview", 
    "🔍 Focus: Part Analysis", 
    "⚙️ Focus: Machine Analysis", 
    "⚖️ Plan vs Actual Efficiency"
])

# ==========================================
# TAB 1: GLOBAL OVERVIEW
# ==========================================
with tab_overview:
    c_chart1, c_chart2 = st.columns(2)
    
    with c_chart1:
        st.subheader("📊 Top 5 Masalah Quality (Pareto NG)")
        if not df_ng_flat.empty:
            ng_summary = df_ng_flat.groupby("type")['qty'].sum().reset_index().sort_values("qty", ascending=False).head(5)
            chart_ng = alt.Chart(ng_summary).mark_bar().encode(
                x='qty', y=alt.Y('type', sort='-x'), color=alt.value('#ff4b4b'), tooltip=['type', 'qty']
            )
            st.altair_chart(chart_ng, use_container_width=True)
        else:
            st.info("Zero Defect / Data Kosong")

    with c_chart2:
        st.subheader("📉 Top 5 Penyebab Downtime")
        if not df_dt_flat.empty:
            dt_summary = df_dt_flat.groupby("category")['duration'].sum().reset_index().sort_values("duration", ascending=False).head(5)
            chart_dt = alt.Chart(dt_summary).mark_bar().encode(
                x='duration', y=alt.Y('category', sort='-x'), color=alt.value('#ffa500'), tooltip=['category', 'duration']
            )
            st.altair_chart(chart_dt, use_container_width=True)
            
            # --- [UPDATED] DETAIL REMARKS GLOBAL + PROBLEM CODE ---
            st.markdown("##### 📋 Top 10 Detail Masalah & Kode Error")
            # Grouping by Remarks AND Problem Category
            remarks_global = df_dt_flat.groupby(["remarks", "parent_problem_cat"])['duration'].sum().reset_index().sort_values("duration", ascending=False).head(10)
            st.dataframe(
                remarks_global, 
                column_config={
                    "parent_problem_cat": "Kode Problem (Header)",
                    "remarks": "Masalah Spesifik (Detail)", 
                    "duration": st.column_config.NumberColumn("Durasi (Min)", format="%d")
                },
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Mesin Lancar Jaya")
            
    st.subheader("📈 Trend Produksi Harian")
    if not df.empty:
        trend = df.groupby("date_in")[['total_qty', 'qty']].sum().reset_index()
        base = alt.Chart(trend).encode(x='date_in:T')
        l1 = base.mark_line(color='#00ADB5').encode(y='total_qty', tooltip=['date_in', 'total_qty'])
        l2 = base.mark_line(color='#76b900').encode(y='qty', tooltip=['date_in', 'qty'])
        st.altair_chart((l1 + l2).interactive(), use_container_width=True)

# ==========================================
# TAB 2: PART ANALYSIS
# ==========================================
with tab_part:
    st.caption("Analisa mendalam performa per Part Number.")
    if not df.empty:
        part_list = sorted(df['part_name'].unique().tolist())
        selected_part = st.selectbox("🎯 Pilih Part Number:", part_list)
        
        df_part = df[df['part_name'] == selected_part]
        p_qty = df_part['total_qty'].sum(); p_ok = df_part['qty'].sum(); p_ng = df_part['total_ng'].sum()
        p_yield = (p_ok / p_qty * 100) if p_qty > 0 else 0
        
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("Prod. Qty", f"{p_qty:,}")
        col_p2.metric("Yield Rate", f"{p_yield:.1f}%")
        col_p3.metric("Total NG", f"{p_ng:,}", delta_color="inverse")
        
        st.divider()
        cp1, cp2 = st.columns(2)
        
        with cp1:
            st.markdown("##### 🚫 Komposisi Defect (NG)")
            if not df_ng_flat.empty:
                ng_part_specific = df_ng_flat[df_ng_flat['parent_part'] == selected_part]
                if not ng_part_specific.empty:
                    ng_p_group = ng_part_specific.groupby("type")['qty'].sum().reset_index().sort_values('qty', ascending=False)
                    c_ng = alt.Chart(ng_p_group).mark_bar().encode(
                        x='qty', y=alt.Y('type', sort='-x'), color=alt.value('#ff4b4b'), tooltip=['type', 'qty']
                    )
                    st.altair_chart(c_ng, use_container_width=True)
                else: st.success("Zero Defect!")
            else: st.info("No Data.")

        with cp2:
            st.markdown("##### ⚠️ Top Downtime Category")
            if not df_dt_flat.empty:
                dt_part_specific = df_dt_flat[df_dt_flat['parent_part'] == selected_part]
                if not dt_part_specific.empty:
                    dt_p_group = dt_part_specific.groupby("category")['duration'].sum().reset_index().sort_values('duration', ascending=False).head(5)
                    c_dt = alt.Chart(dt_p_group).mark_bar().encode(
                        x='duration', y=alt.Y('category', sort='-x'), color=alt.value('#ffa500'), tooltip=['category', 'duration']
                    )
                    st.altair_chart(c_dt, use_container_width=True)
                    
                    # --- [UPDATED] DETAIL REMARKS PER PART ---
                    st.markdown("##### 📋 Detail Masalah & Kode (Part Ini)")
                    rem_part = dt_part_specific.groupby(["remarks", "parent_problem_cat"])['duration'].sum().reset_index().sort_values('duration', ascending=False).head(5)
                    st.dataframe(
                        rem_part, 
                        column_config={
                            "parent_problem_cat": "Kode Problem",
                            "remarks": "Masalah Spesifik", 
                            "duration": st.column_config.NumberColumn("Durasi (Min)", format="%d")
                        },
                        use_container_width=True, hide_index=True
                    )

                else: st.success("Zero Downtime!")
            else: st.info("No Data.")
    else: st.info("Data Kosong.")

# ==========================================
# TAB 3: MACHINE ANALYSIS
# ==========================================
with tab_machine:
    st.caption("Analisa kesehatan dan performa per Mesin/Tonnage.")
    if not df.empty:
        mc_list = sorted(df['machine_no'].unique().tolist())
        selected_mc = st.selectbox("⚙️ Pilih Mesin:", mc_list)
        
        df_mc = df[df['machine_no'] == selected_mc]
        mc_output = df_mc['total_qty'].sum(); mc_dt = df_mc['total_downtime'].sum(); mc_ng_total = df_mc['total_ng'].sum()
        
        cm1, cm2, cm3 = st.columns(3)
        cm1.metric("Output (Pcs)", f"{mc_output:,}")
        cm2.metric("Downtime (Min)", f"{mc_dt:,}", delta_color="inverse")
        cm3.metric("Defect (Pcs)", f"{mc_ng_total:,}", delta_color="inverse")
        
        st.divider()
        row1_1, row1_2 = st.columns(2)
        
        with row1_1:
            st.markdown("##### 🛠️ Top Downtime Category")
            if not df_dt_flat.empty:
                dt_mc_spec = df_dt_flat[df_dt_flat['parent_machine'] == selected_mc]
                if not dt_mc_spec.empty:
                    dt_grp = dt_mc_spec.groupby("category")['duration'].sum().reset_index().sort_values('duration', ascending=False)
                    c_dtm = alt.Chart(dt_grp).mark_bar().encode(
                        x='duration', y=alt.Y('category', sort='-x'), color=alt.value('#ffa500')
                    )
                    st.altair_chart(c_dtm, use_container_width=True)
                    
                    # --- [UPDATED] DETAIL REMARKS PER MACHINE ---
                    st.markdown("##### 📋 Detail Masalah & Kode (Mesin Ini)")
                    rem_mc = dt_mc_spec.groupby(["remarks", "parent_problem_cat"])['duration'].sum().reset_index().sort_values('duration', ascending=False).head(10)
                    st.dataframe(
                        rem_mc, 
                        column_config={
                            "parent_problem_cat": "Kode Problem",
                            "remarks": "Masalah Spesifik", 
                            "duration": st.column_config.NumberColumn("Durasi (Min)", format="%d")
                        },
                        use_container_width=True, hide_index=True
                    )

                else: st.success("Mesin Sehat.")

        with row1_2:
            st.markdown("##### 📉 Top Defect Contribution")
            if not df_ng_flat.empty:
                ng_mc_spec = df_ng_flat[df_ng_flat['parent_machine'] == selected_mc]
                if not ng_mc_spec.empty:
                    ng_grp = ng_mc_spec.groupby("type")['qty'].sum().reset_index().sort_values('qty', ascending=False).head(10)
                    c_ngm = alt.Chart(ng_grp).mark_bar().encode(
                        x='qty', y=alt.Y('type', sort='-x'), color=alt.value('#ff4b4b')
                    )
                    st.altair_chart(c_ngm, use_container_width=True)
                else: st.success("Produksi Mulus.")
    else: st.info("Data Kosong.")

# ==========================================
# TAB 4: PLAN VS ACTUAL (EFFICIENCY & LOSS)
# ==========================================
with tab_plan:
    st.header("⚖️ Plan vs Actual Efficiency")
    st.caption("Analisa kerugian material & waktu (Hanya menampilkan produksi yang mencapai target).")

    # 1. FETCH DATA MASTER
    try:
        res_prod = supabase.table("products").select("part_no, part_weight, std_cycle_time, id").execute()
        df_prod = pd.DataFrame(res_prod.data)
        res_bom = supabase.table("master_bom").select("product_id, usage_qty, child_parts(part_name)").execute()
        bom_data = res_bom.data
    except Exception as e:
        st.error(f"Gagal tarik master data: {e}"); df_prod = pd.DataFrame(); bom_data = []

    if not df.empty and not df_prod.empty:
        df_analysis = df[df['qty'] >= df['plan_qty']].copy()
        
        if df_analysis.empty:
            st.warning("⚠️ Tidak ada data produksi yang mencapai target (Plan Qty).")
        else:
            std_map = {}
            for idx, row in df_prod.iterrows():
                std_map[row['part_no']] = {
                    'std_weight': float(row.get('part_weight') or 0), 
                    'std_ct': float(row.get('std_cycle_time') or 0),
                    'id': row['id']
                }

            bom_map = {}
            for b in bom_data:
                pid = b['product_id']; child_nm = b['child_parts']['part_name'] if b['child_parts'] else "Unknown"; usage = b['usage_qty']
                if pid not in bom_map: bom_map[pid] = []
                bom_map[pid].append({'name': child_nm, 'usage': usage})

            analysis_result = []
            time_loss_breakdown = [] 
            total_loss_resin_kg = 0; total_loss_time_min = 0
            
            for idx, row in df_analysis.iterrows():
                p_no = row['part_no']
                if p_no in std_map:
                    std = std_map[p_no]
                    act_qty_shot = row['total_qty']; act_ng = row['total_ng']; act_weight = float(row['part_weight_act'] or 0); act_ct = float(row['act_cycle_time'] or 0)
                    
                    loss_overweight_kg = ((act_qty_shot * act_weight) - (act_qty_shot * std['std_weight'])) / 1000
                    loss_ng_material_kg = (act_ng * act_weight) / 1000
                    total_mat_loss = max(0, loss_overweight_kg + loss_ng_material_kg)
                    
                    if std['std_ct'] > 0:
                        loss_ct_min = ((act_ct - std['std_ct']) * act_qty_shot) / 60
                    else:
                        loss_ct_min = 0 
                    
                    loss_dt_min = float(row['total_downtime'] or 0)
                    total_time_loss = max(0, loss_ct_min + loss_dt_min)

                    if total_time_loss > 1:
                        if loss_dt_min > 0:
                            time_loss_breakdown.append({'Part Name': row['part_name'], 'Loss Type': 'Downtime', 'Minutes': loss_dt_min})
                        if loss_ct_min > 0:
                            time_loss_breakdown.append({'Part Name': row['part_name'], 'Loss Type': 'Speed Loss (Slow CT)', 'Minutes': loss_ct_min})

                    child_loss_desc = []
                    if act_ng > 0 and std['id'] in bom_map:
                        for c in bom_map[std['id']]:
                            wasted_qty = c['usage'] * act_ng
                            child_loss_desc.append(f"{c['name']}: {wasted_qty:,.0f}")
                    str_child_loss = ", ".join(child_loss_desc) if child_loss_desc else "-"

                    total_loss_resin_kg += total_mat_loss
                    total_loss_time_min += total_time_loss

                    analysis_result.append({
                        "Date": row['date_in'], "Part Name": row['part_name'], "Output OK": int(row['qty']),
                        "Std CT": std['std_ct'], "Act CT": act_ct,
                        "Loss Resin (Kg)": round(total_mat_loss, 2), "Loss Waktu (Min)": round(total_time_loss, 1),
                        "Child Part Wasted": str_child_loss
                    })
            
            if analysis_result:
                df_res = pd.DataFrame(analysis_result)
                k1, k2, k3 = st.columns(3)
                k1.metric("Total Rugi Material", f"{total_loss_resin_kg:,.2f} Kg", delta_color="inverse")
                k2.metric("Total Waktu Terbuang", f"{total_loss_time_min:,.0f} Menit", delta_color="inverse")
                k3.metric("Batch Dianalisa", f"{len(df_res)} Batch")
                
                st.divider()
                st.subheader("📊 Visualisasi Kerugian")
                chart_row1_1, chart_row1_2 = st.columns(2)
                
                with chart_row1_1:
                    st.markdown("##### 🟥 Top Boros Material")
                    mat_loss_grp = df_res.groupby("Part Name")['Loss Resin (Kg)'].sum().reset_index().sort_values('Loss Resin (Kg)', ascending=False).head(10)
                    c_mat = alt.Chart(mat_loss_grp).mark_bar().encode(
                        x=alt.X('Loss Resin (Kg)', title='Total Loss (Kg)'), y=alt.Y('Part Name', sort='-x', title=''), color=alt.value('#d32f2f'), tooltip=['Part Name', 'Loss Resin (Kg)']
                    ).properties(height=300)
                    st.altair_chart(c_mat, use_container_width=True)
                
                with chart_row1_2:
                    st.markdown("##### ⏳ Top Buang Waktu")
                    if time_loss_breakdown:
                        df_time_breakdown = pd.DataFrame(time_loss_breakdown)
                        df_time_grp = df_time_breakdown.groupby(['Part Name', 'Loss Type'])['Minutes'].sum().reset_index()
                        sort_order = df_time_grp.groupby('Part Name')['Minutes'].sum().sort_values(ascending=False).head(10).index.tolist()
                        df_time_final = df_time_grp[df_time_grp['Part Name'].isin(sort_order)]
                        c_time = alt.Chart(df_time_final).mark_bar().encode(
                            x=alt.X('Minutes', title='Total Loss (Menit)'), y=alt.Y('Part Name', sort=sort_order, title=''), 
                            color=alt.Color('Loss Type', scale=alt.Scale(domain=['Downtime', 'Speed Loss (Slow CT)'], range=['#d32f2f', '#f57c00'])), tooltip=['Part Name', 'Loss Type', 'Minutes']
                        ).properties(height=300)
                        st.altair_chart(c_time, use_container_width=True)
                    else: st.info("Tidak ada time loss signifikan.")

                st.divider()
                st.subheader("📋 Detail Data Table")
                st.dataframe(df_res, column_config={"Std CT": st.column_config.NumberColumn("Std CT", format="%.1f s"), "Act CT": st.column_config.NumberColumn("Act CT", format="%.1f s"), "Loss Resin (Kg)": st.column_config.NumberColumn("Loss Resin", format="%.2f kg"), "Loss Waktu (Min)": st.column_config.NumberColumn("Loss Waktu", format="%.1f min")}, use_container_width=True, hide_index=True)
                
                if st.button("📥 Download Analisa"):
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df_res.to_excel(writer, sheet_name='Plan_vs_Actual', index=False)
                    st.download_button(label="Klik Disini", data=output.getvalue(), file_name=f"Efficiency_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Data Part belum terdaftar di Master Product.")
    else:
        st.info("Silakan pilih filter tanggal.")