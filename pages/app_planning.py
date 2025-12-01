import streamlit as st
import pandas as pd
import math
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from supabase_client import get_supabase

# --- IMPORT NAVBAR DARI COMPONENTS ---
from components.navbar import show_navbar

# ==========================================
# 1. KONFIGURASI HALAMAN & CSS
# ==========================================
st.set_page_config(layout="wide", page_title="AI Injection Planner Pro")

st.markdown("""
<style>
    /* --- PERBAIKAN DISINI --- */
    /* Kita naikin padding-top jadi 6rem biar konten turun ke bawah */
    /* tidak ketutup header bawaan streamlit */
    .block-container {
        padding-top: 6rem; 
        padding-bottom: 5rem;
    }
    
    /* OPSI TAMBAHAN: Kalau mau header bawaan Streamlit (Deploy/Menu) jadi transparan/hilang */
    /* Uncomment baris di bawah ini kalau mau tampilan lebih bersih: */
    /* header[data-testid="stHeader"] {visibility: hidden;} */

    /* --- SISA CSS LAMA --- */
    div[data-testid="metric-container"] {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    th {
        background-color: #0e1117 !important;
        color: #fafafa !important;
        font-size: 13px !important;
    }
    .stDataFrame {font-size: 12px;}
    div.stButton > button:first-child {
        background-color: #0078D4;
        color: white;
        font-weight: bold;
        border-radius: 5px;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #005a9e;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA LOADERS (ROBUST & CLEAN)
# ==========================================
@st.cache_resource
def init_connection():
    return get_supabase()

def load_master_data(selected_machine_id):
    supabase = init_connection()
    
    # Machine
    mach_resp = supabase.table('machine').select('machine_id, tonnage').eq('status', 'Active').execute()
    df_machine = pd.DataFrame(mach_resp.data)
    if not df_machine.empty: 
        df_machine.columns = [c.lower() for c in df_machine.columns]
        df_machine['label'] = df_machine['machine_id'] + " (" + df_machine['tonnage'].astype(str) + "T)"

    # Shift (Auto-Cleaning Data)
    shift_resp = supabase.table('SHIFT').select('*').execute()
    df_shift = pd.DataFrame(shift_resp.data)
    if not df_shift.empty: 
        df_shift.columns = [c.lower() for c in df_shift.columns]
        # PEMBERSIH: Paksa String, Strip Spasi, Huruf Besar
        if 'day_type' in df_shift.columns:
            df_shift['day_type'] = df_shift['day_type'].astype(str).str.strip().str.upper()

    # Master Part
    query = supabase.table('MASTER').select('*')
    if selected_machine_id:
        query = query.eq('machine_id', selected_machine_id)
        
    master_resp = query.execute()
    df_master = pd.DataFrame(master_resp.data)
    if not df_master.empty: df_master.columns = [c.lower() for c in df_master.columns]

    return df_machine, df_shift, df_master

def load_dynamic_data(part_list, start_date, days):
    supabase = init_connection()
    # Buffer forecast lebih panjang
    end_date = start_date + timedelta(days=days+30) 
    
    # Forecast
    fc_resp = supabase.table('v_daily_forecast')\
        .select('*')\
        .in_('part_no', part_list)\
        .gte('forecast_date', start_date.strftime('%Y-%m-%d'))\
        .lte('forecast_date', end_date.strftime('%Y-%m-%d'))\
        .execute()
    df_fc = pd.DataFrame(fc_resp.data)
    if not df_fc.empty: df_fc.columns = [c.lower() for c in df_fc.columns]

    # Stock (FG & WIP)
    fg_resp = supabase.table('v_fg_latest_stock').select('part_no, fg_stock').in_('part_no', part_list).execute()
    df_fg = pd.DataFrame(fg_resp.data)
    wip_resp = supabase.table('v_wip_latest_stock').select('part_no, wip_stock').in_('part_no', part_list).execute()
    df_wip = pd.DataFrame(wip_resp.data)

    # Gabung Stock
    df_stock_total = pd.DataFrame({'part_no': part_list})
    if not df_fg.empty: df_stock_total = df_stock_total.merge(df_fg, on='part_no', how='left')
    else: df_stock_total['fg_stock'] = 0
        
    if not df_wip.empty: df_stock_total = df_stock_total.merge(df_wip, on='part_no', how='left')
    else: df_stock_total['wip_stock'] = 0
        
    df_stock_total = df_stock_total.fillna(0)
    df_stock_total['total_stock'] = df_stock_total['fg_stock'] + df_stock_total['wip_stock']

    return df_fc, df_stock_total

# ==========================================
# 3. THE BRAIN: INJECTION SIMULATION (MIN-MAX)
# ==========================================
def run_injection_simulation(df_fc, df_stock, df_master, start_date, horizon_days):
    job_tickets = [] 
    
    # Satpam Data Kosong
    if df_fc.empty or df_master.empty or 'part_no' not in df_fc.columns:
        return pd.DataFrame()
    
    # STRATEGY SETTINGS
    MIN_COVERAGE_DAYS = 2   # Trigger Point
    MAX_COVERAGE_DAYS = 15  # Target Point (Agresif)
    
    for index, row_master in df_master.iterrows():
        part = row_master['part_no']
        part_name = row_master['part_name']
        ct = row_master['cycle_time']
        cav = row_master['cav']
        
        try:
            output_per_shift = int((420 * 60 / ct) * cav)
        except:
            output_per_shift = 0
        if output_per_shift == 0: continue

        # Init Stock
        stock_row = df_stock[df_stock['part_no'] == part]
        current_stock = stock_row['total_stock'].values[0] if not stock_row.empty else 0
        
        # Forecast
        fc_part = df_fc[df_fc['part_no'] == part].sort_values('forecast_date')
        if fc_part.empty: continue
        
        # Avg Demand (Fallback jika forecast bolong)
        avg_demand = fc_part['daily_qty'].mean()
        if pd.isna(avg_demand) or avg_demand == 0: avg_demand = 1

        temp_stock = current_stock
        sim_start = pd.to_datetime(start_date)
        
        for d in range(horizon_days):
            curr_sim_date = sim_start + timedelta(days=d)
            curr_date_str = curr_sim_date.strftime('%Y-%m-%d')
            
            # 1. Makan Stock
            demand_row = fc_part[fc_part['forecast_date'] == curr_date_str]
            if not demand_row.empty:
                daily_demand = demand_row['daily_qty'].values[0]
            else:
                daily_demand = avg_demand 
            temp_stock -= daily_demand
            
            # 2. Cek Trigger (Min Coverage)
            future_demand_min = 0
            for k in range(1, MIN_COVERAGE_DAYS + 1):
                check_date = curr_sim_date + timedelta(days=k)
                chk_row = fc_part[fc_part['forecast_date'] == check_date.strftime('%Y-%m-%d')]
                if not chk_row.empty: future_demand_min += chk_row['daily_qty'].values[0]
                else: future_demand_min += avg_demand
            
            # 3. Keputusan
            if temp_stock < future_demand_min:
                # 4. Target Isi (Max Coverage)
                future_demand_max = 0
                for k in range(1, MAX_COVERAGE_DAYS + 1):
                    check_date = curr_sim_date + timedelta(days=k)
                    chk_row = fc_part[fc_part['forecast_date'] == check_date.strftime('%Y-%m-%d')]
                    if not chk_row.empty: future_demand_max += chk_row['daily_qty'].values[0]
                    else: future_demand_max += avg_demand
                
                deficit = future_demand_max - temp_stock
                if deficit <= 0: deficit = 1
                
                shifts_needed = math.ceil(deficit / output_per_shift)
                if shifts_needed < 1: shifts_needed = 1
                
                # CATAT TIKET
                for i in range(shifts_needed):
                    job_tickets.append({
                        'job_id': f"{part}_{curr_date_str}_{i}", 
                        'part_no': part,
                        'part_name': part_name,
                        'earliest_start_date': curr_sim_date, 
                        'duration_shifts': 1
                    })
                
                temp_stock += (shifts_needed * output_per_shift)

    return pd.DataFrame(job_tickets)

# ==========================================
# 4. THE SCHEDULER: OR-TOOLS (FIXED DATES)
# ==========================================
def generate_timeline_slots(start_date, days, df_shift):
    slots = []
    start_dt = pd.to_datetime(start_date)
    
    for i in range(days):
        curr_date = start_dt + timedelta(days=i)
        day_name = curr_date.strftime('%A')
        
        # Logic Mapping (Standard HURUF BESAR)
        target_day_type = 'WEEKDAY'
        if day_name == 'Saturday': target_day_type = 'SATURDAY'
        elif day_name == 'Sunday': target_day_type = 'SUNDAY'
        
        if target_day_type == 'SUNDAY': continue
        
        # Filter (Sekarang aman karena df_shift udah dipaksa Upper)
        rules = df_shift[df_shift['day_type'] == target_day_type]

        for _, r in rules.iterrows():
            s_name = r.get('shift_name', r.get('SHIFT_NAME'))
            slots.append({
                'date': curr_date,
                'day_num': curr_date.day,
                'assigned_shift': s_name, 
                'slot_id': f"{curr_date}_{s_name}"
            })
    return pd.DataFrame(slots)

def solve_schedule(df_slots, df_jobs):
    model = cp_model.CpModel()
    
    # Reset index biar urut dan aman
    df_slots = df_slots.reset_index(drop=True)
    df_jobs = df_jobs.reset_index(drop=True)
    
    job_ids = df_jobs.index.tolist()
    slot_ids = df_slots.index.tolist()
    
    x = {} 
    for j in job_ids:
        for s in slot_ids:
            x[j, s] = model.NewBoolVar(f'x_{j}_{s}')
            
    # Constraints
    for j in job_ids: model.Add(sum(x[j, s] for s in slot_ids) == 1)
    for s in slot_ids: model.Add(sum(x[j, s] for j in job_ids) <= 1)
        
    # STRING DATE MATCHING (SOLUSI ANTI-MELESET)
    slot_dates_str = pd.to_datetime(df_slots['date']).dt.strftime('%Y-%m-%d').to_dict()
    job_earliest_str = pd.to_datetime(df_jobs['earliest_start_date']).dt.strftime('%Y-%m-%d').to_dict()

    for j in job_ids:
        earliest = job_earliest_str[j]
        for s in slot_ids:
            current = slot_dates_str[s]
            if current < earliest:
                model.Add(x[j, s] == 0)

    # Objective: Earliness
    obj_earliness = []
    for j in job_ids:
        for s in slot_ids:
            obj_earliness.append(x[j, s] * s)
    model.Minimize(sum(obj_earliness))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0 
    status = solver.Solve(model)
    
    res = []
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        for s in slot_ids:
            for j in job_ids:
                if solver.Value(x[j, s]):
                    res.append({
                        'date': df_slots.loc[s, 'date'],
                        'assigned_shift': df_slots.loc[s, 'assigned_shift'],
                        'part_name': df_jobs.loc[j, 'part_name'],
                        'part_no': df_jobs.loc[j, 'part_no'],
                        'val': '1 Lot'
                    })
    return pd.DataFrame(res)

# ==========================================
# 5. UI MAIN (FINAL POLISH)
# ==========================================
def style_board(val):
    s = str(val).lower()
    if 'lot' in s:
        if '3 lot' in s:
            return 'background-color: #311b92; color: white; font-weight: bold; border: 1px solid #7c4dff;'
        elif '2 lot' in s:
            return 'background-color: #01579b; color: white; font-weight: bold; border: 1px solid #4fc3f7;'
        else:
            return 'background-color: #0288d1; color: white; font-weight: bold; border: 1px solid #29b6f6;'
    else:
        return 'background-color: #262730; color: #444; border: 1px solid #333;'

def main():
    # --- PANGGIL NAVBAR DISINI AGAR PALING ATAS ---
    show_navbar()
    
    c_logo, c_title = st.columns([1, 6])
    with c_title:
        st.title("🏭 AI Production Planner")
        st.caption("Intelligent Scheduling System | Coverage Logic: Min 2 Days - Max 15 Days")

    with st.container():
        st.write("")
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        
        with c1:
            try:
                df_mach, _, _ = load_master_data("") 
                df_mach = df_mach.drop_duplicates('machine_id')
                if df_mach.empty:
                    st.error("Table Machine Kosong")
                    return
                label = st.selectbox("Select Machine", df_mach['label'])
                mach_id = df_mach.loc[df_mach['label'] == label, 'machine_id'].iloc[0]
            except Exception as e:
                st.error(f"Database Error: {e}")
                return

        with c2:
            start_date = st.date_input("Start Date", datetime.now())
            
        with c3:
            horizon = st.slider("Horizon (Days)", 7, 30, 30)
            
        with c4:
            st.write("") 
            st.write("")
            run_btn = st.button("RUN PLANNING 🚀", type="primary", use_container_width=True)

    st.divider()

    if run_btn:
        st.session_state['run'] = True

    if st.session_state.get('run'):
        with st.spinner(f"🔍 AI sedang menganalisa data mesin {mach_id}..."):
            df_mach, df_shift, df_master = load_master_data(mach_id)
            if df_master.empty:
                st.warning(f"⚠️ Mesin {mach_id} Gabut: Tidak ada Part yang terdaftar.")
                st.stop()
                
            part_list = df_master['part_no'].unique().tolist()
            df_fc, df_stock = load_dynamic_data(part_list, start_date, horizon)
            
            if df_fc.empty:
                st.warning(f"⚠️ Mesin {mach_id} Santai: Tidak ada forecast di horizon ini.")
                st.stop()
        
        # 1. RUN SIMULATION
        df_jobs = run_injection_simulation(df_fc, df_stock, df_master, start_date, horizon)
        
        if df_jobs.empty:
            st.success("✅ **STOCK AMAN!** Tidak ada injection yang diperlukan. Ngopi dulu bre! ☕")
        else:
            # 2. RUN SCHEDULER (WITH EXTENDED TIMELINE +7)
            # Napas tambahan 7 hari biar job di ujung gak jatuh
            df_slots = generate_timeline_slots(start_date, horizon + 7, df_shift)
            
            if df_slots.empty:
                st.error("⛔ Timeline Kosong. Cek Data SHIFT (Day Type harus WEEKDAY/SATURDAY).")
                st.stop()

            df_schedule = solve_schedule(df_slots, df_jobs)
            
            # KPI Metrics
            total_jobs = len(df_jobs)
            total_parts = df_jobs['part_no'].nunique()
            utilization = (len(df_schedule) / len(df_slots)) * 100 if len(df_slots) > 0 else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Shifts Needed", f"{total_jobs} Lot")
            m2.metric("Parts Scheduled", f"{total_parts} Items")
            m3.metric("Machine Occupancy", f"{utilization:.1f}%")
            
            if df_schedule.empty:
                m4.metric("Status", "INFEASIBLE ❌", delta_color="inverse")
                st.error("Jadwal Gagal Disusun. Kapasitas tidak cukup untuk mengakomodir kebutuhan tanggal tersebut.")
            elif len(df_jobs) > len(df_slots):
                m4.metric("Status", "OVERLOAD ⚠️", delta_color="inverse")
            else:
                m4.metric("Status", "OPTIMAL ✅")

            with st.expander("📄 Lihat Detail 'Tiket' Pekerjaan (Raw Data)"):
                st.dataframe(df_jobs)

            if not df_schedule.empty:
                st.subheader(f"📅 Schedule Board: {mach_id}")
                
                df_schedule['header'] = df_schedule['date'].dt.strftime('%d (%a)')
                all_dates = [start_date + timedelta(days=i) for i in range(horizon)]
                all_headers = [d.strftime('%d (%a)') for d in all_dates]

                pivot = df_schedule.pivot_table(
                    index=['part_name', 'part_no'],
                    columns='header',
                    values='assigned_shift',
                    aggfunc=lambda x: f"{len(x.unique())} Lot"
                )
                
                pivot = pivot.reindex(columns=all_headers).fillna('-')
                
                st.dataframe(
                    pivot.style.applymap(style_board), 
                    use_container_width=True, 
                    height=550
                )
                
                st.markdown("""
                <div style='display: flex; gap: 20px; font-size: 12px; color: #888;'>
                    <span>🟦 <b>Biru Muda:</b> 1 Lot</span>
                    <span>🔵 <b>Biru Sedang:</b> 2 Lot</span>
                    <span>🟣 <b>Ungu:</b> 3 Lot (Full Day)</span>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()