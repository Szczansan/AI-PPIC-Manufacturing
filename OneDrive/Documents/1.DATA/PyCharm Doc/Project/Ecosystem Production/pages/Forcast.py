import sys, os
import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from supabase_client import get_supabase
from components.navbar import show_navbar

# ===== PAGE CONFIG & INIT =====
st.set_page_config(page_title="Forecast Command Center", page_icon="⚡", layout="wide")
supabase = get_supabase()
show_navbar()

# ====== LIGHTWEIGHT CYBERPUNK CSS (PERFORMANCE MODE) ======
st.markdown("""
<style>
    /* 1. FONT SYSTEM (NGEBUT, GAK PERLU DOWNLOAD) */
    html, body, [class*="css"] {
        font-family: 'Consolas', 'Courier New', monospace; 
        background-color: #050505; 
        color: #e0e0e0;
    }

    /* 2. NEON ACCENTS - MINIMAL SHADOW */
    h1, h2, h3, h4 {
        color: #00ff41; /* Hacker Green */
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 2px solid #00ff41;
        padding-bottom: 5px;
        margin-bottom: 20px;
    }

    /* 3. METRICS YANG TAJAM */
    [data-testid="stMetricValue"] {
        font-size: 28px; /* Dikecilin dikit biar muat */
        color: #00e5ff !important; /* Cyan */
        font-weight: 700;
        font-family: 'Verdana', sans-serif;
    }
    [data-testid="stMetricLabel"] {
        color: #888 !important;
        font-size: 12px;
    }

    /* 4. BUTTONS - FLAT & FAST */
    div.stButton > button {
        background-color: #000;
        color: #00ff41;
        border: 1px solid #00ff41;
        border-radius: 0px; /* Kotak tegas */
        font-family: 'Consolas', monospace;
        font-weight: bold;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #00ff41;
        color: #000;
        border-color: #fff;
    }

    /* 5. CONTAINER - SOLID (NO BLUR) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #111; /* Solid Dark Grey */
        border: 1px solid #333;
        border-radius: 4px;
        padding: 15px;
    }

    /* 6. INPUT FIELD - TERMINAL STYLE */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #000;
        color: #00ff41;
        border: 1px solid #333;
        font-family: 'Consolas', monospace;
    }
    
    /* SCROLLBAR IJO */
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #000; }
    ::-webkit-scrollbar-thumb { background: #003300; border: 1px solid #00ff41; }
</style>
""", unsafe_allow_html=True)

# ====== HELPER FUNCTIONS ====== #

def safe_execute(query):
    try:
        res = query.execute()
        return res.data
    except Exception as e:
        # INI YANG PENTING: Tampilkan error asli ke UI Streamlit
        st.error(f"🔥 DETAIL ERROR SUPABASE: {str(e)}") 
        # Cek terminal juga
        print(f"DB Error: {e}") 
        return None

def get_future_months(num_months=24):
    current_date = date.today().replace(day=1)
    months = []
    for i in range(num_months):
        d = current_date + relativedelta(months=i)
        months.append(d.strftime("%Y-%m"))
    return months

def next_revision_number(supabase_client, forecast_month, customer_name):
    try:
        q = supabase_client.table("forecast_monthly").select("revision_no", count="exact")\
            .eq("forecast_month", forecast_month)\
            .eq("customer_name", customer_name)\
            .order("revision_no", desc=True).limit(1)
        res = safe_execute(q)
        if res and len(res) > 0:
            return int(res[0].get("revision_no", 0)) + 1
    except Exception:
        pass
    return 1

def generate_forecast_id(forecast_month, revision_no):
    return f"FCT-{forecast_month}-R{revision_no}"

# --- FETCH DATA (OPTIMIZED WITH CACHE) ---
@st.cache_data(ttl=60, show_spinner=False) 
def fetch_forecasts_with_master(limit=5000):
    try:
        res_fct = supabase.table("forecast_monthly").select("*").order("created_at", desc=True).limit(limit).execute()
        if not res_fct.data:
            return pd.DataFrame()
        
        df_fct = pd.DataFrame(res_fct.data)

        try:
            res_master = supabase.table("MASTER").select("part_no, PART_NAME").execute()
            if res_master.data:
                df_master = pd.DataFrame(res_master.data)
                df_master.rename(columns={"PART_NAME": "part_name"}, inplace=True)
                
                df_merged = pd.merge(
                    df_fct, 
                    df_master[['part_no', 'part_name']], 
                    on='part_no', 
                    how='left'
                )
                df_merged['part_name'] = df_merged['part_name'].fillna("-")
                return df_merged
        except Exception as e:
            df_fct['part_name'] = "-"
            return df_fct

        return df_fct

    except Exception as e:
        return pd.DataFrame()

# --- PROCESS UPLOAD ---
def process_forecast_csv(df_raw, forecast_month, work_day_val, created_by=None): 
    if forecast_month is None:
        st.error("⚠️ SYSTEM ALERT: Target Month Not Selected.")
        return None

    # ... (Bagian cleaning column & rename part_no SAMA KAYA SEBELUMNYA, skip biar ga panjang ...)
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}
    
    part_col = None
    for candidate in ['part_no', 'part no', 'material']:
        if candidate in col_map:
            part_col = col_map[candidate]
            break
            
    if not part_col:
        st.error("❌ CRITICAL: 'part_no' column missing.")
        return None
        
    df = df.rename(columns={part_col: "part_no"})
    df = df[df["part_no"].notna()].reset_index(drop=True)
    
    # ... (Bagian cleaning customer & source SAMA KAYA SEBELUMNYA ...)
    cust_col_name = None
    for c in ['customer_name', 'customer', 'cust_name']:
        if c in col_map: cust_col_name = col_map[c]; break
    
    source_col_name = None
    for c in ['cast_source', 'source', 'forecast_source']:
        if c in col_map: source_col_name = col_map[c]; break

    # ... (Logic hitung qty SAMA ...)
    if "forecast_qty_monthly" in df.columns:
        df["forecast_qty_monthly"] = pd.to_numeric(df["forecast_qty_monthly"], errors='coerce').fillna(0).astype(int)
    else:
        day_cols = [str(i) for i in range(1, 32)]
        def safe_sum_row(r):
            s = 0
            for c in day_cols:
                if c in r and pd.notna(r[c]):
                    try: s += float(r[c])
                    except: pass
            return int(round(s))
        df["forecast_qty_monthly"] = df.apply(safe_sum_row, axis=1)

    if cust_col_name: df['temp_customer'] = df[cust_col_name].astype(str).str.strip()
    else: df['temp_customer'] = "Unknown"

    if source_col_name: df['temp_source'] = df[source_col_name].astype(str).str.strip()
    else: df['temp_source'] = "Manual Upload"

    # === CORE INSERT LOGIC ===
    current_date = str(date.today())
    all_monthly_rows = []
    unique_customers = df['temp_customer'].unique()
    
    for cust_name in unique_customers:
        df_sub = df[df['temp_customer'] == cust_name]
        rev_no = next_revision_number(supabase, forecast_month, cust_name)
        f_id = generate_forecast_id(forecast_month, rev_no)
        
        for _, row in df_sub.iterrows():
            qty = int(row["forecast_qty_monthly"])
            if qty >= 0:
                all_monthly_rows.append({
                    "forecast_id": f_id,
                    "forecast_month": forecast_month,
                    "upload_date": current_date,
                    "forecast_source": row['temp_source'],
                    "customer_name": cust_name,
                    "part_no": str(row["part_no"]).strip(),
                    "forecast_qty_monthly": qty,
                    "work_day": int(work_day_val), # <--- DATA HARI KERJA DISIMPAN DISINI
                    "revision_no": rev_no,
                    "min_days": 2.0,
                    "created_by": created_by,
                    "updated_by": created_by
                })

    if all_monthly_rows:
        res = safe_execute(supabase.table("forecast_monthly").insert(all_monthly_rows))
        if res is None:
            st.error("Database Connection Failed.")
            return None
        
        st.cache_data.clear()
        st.success(f"✅ UPLOAD COMPLETE. Processed {len(all_monthly_rows)} units. (Work Days: {work_day_val})")
        return {"status": "ok"}
    else:
        st.warning("No valid data processed.")
        return None


# ====== MAIN UI ====== #

st.title("⚡ FORECAST CONTROL")
st.markdown("#### SYSTEM STATUS: ONLINE")
st.divider()

# --- 1. DATA LOADING (CACHED) ---
df_all = fetch_forecasts_with_master(limit=5000)

# --- 2. GLOBAL FILTERS ---
df_view = pd.DataFrame()
if not df_all.empty:
    # 1. Siapkan List Filter
    customers = ["All"] + sorted(df_all["customer_name"].dropna().unique().tolist())
    
    part_names = ["All"]
    if "part_name" in df_all.columns:
        unique_parts = sorted(df_all["part_name"].astype(str).unique().tolist())
        part_names += unique_parts

    # --- NEW: List Forecast Month yang ada di Database ---
    # Diurutkan descending (bulan terbaru di atas)
    available_months = ["All"] + sorted(df_all["forecast_month"].dropna().unique().tolist(), reverse=True)

    # 2. Tampilan Filter (4 Kolom)
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([1, 1.5, 1, 1]) 
        
        with c1:
            sel_customer = st.selectbox("CUSTOMER", customers, index=0)
        with c2:
            sel_part_name = st.selectbox("PART NAME", part_names, index=0)
        with c3:
            # --- NEW UI ELEMENT ---
            sel_month = st.selectbox("FORECAST MONTH", available_months, index=0)
        
        # 3. Logic Filtering
        df_view = df_all.copy()
        
        if sel_customer != "All": 
            df_view = df_view[df_view["customer_name"] == sel_customer]
        
        if sel_part_name != "All":
            df_view = df_view[df_view["part_name"] == sel_part_name]
            
        # --- NEW FILTER LOGIC ---
        if sel_month != "All":
            df_view = df_view[df_view["forecast_month"] == sel_month]
        
        with c4:
            total_parts = len(df_view)
            total_qty = df_view['forecast_qty_monthly'].sum() if 'forecast_qty_monthly' in df_view else 0
            st.metric("TOTAL QTY", f"{total_qty:,.0f}", f"{total_parts} ROWS")

else:
    df_view = pd.DataFrame()


# --- 3. SPLIT LAYOUT ---
st.markdown("<br>", unsafe_allow_html=True)
left_panel, right_panel = st.columns([1.2, 2.5], gap="large")

# ================= LEFT PANEL =================
with left_panel:
    with st.container(border=True):
        st.markdown("#### 📥 DATA UPLINK")
        
        # --- LAYOUT BARU: 2 KOLOM (BULAN & HARI KERJA) ---
        col_month, col_days = st.columns([2, 1.2]) # Proporsi lebar kolom
        
        with col_month:
            month_options = get_future_months(24)
            forecast_month_input = st.selectbox("TARGET MONTH", month_options)
        
        with col_days:
            # Input angka, default 22 hari, min 1, max 31
            work_day_input = st.number_input("WORK DAYS", min_value=1, max_value=31, value=22)
        
        st.caption("Required: part_no, customer_name, forecast_qty_monthly")

        file = st.file_uploader("DROP FILE", type=["xlsx", "csv"], label_visibility="collapsed")

        if file:
            try:
                if file.name.endswith(".csv"):
                    df_preview = pd.read_csv(file)
                else:
                    df_preview = pd.read_excel(file)

                # ... (Logic preview kolom sama kaya sebelumnya) ...
                df_preview.columns = [str(c).strip() for c in df_preview.columns]
                cols_lower = [c.lower() for c in df_preview.columns]
                has_part = any(x in cols_lower for x in ['part_no', 'part no', 'material'])
                
                if not has_part:
                    st.error("MISSING 'part_no'")
                else:
                    # Info preview ditambahin info Work Days biar user aware
                    st.info(f"READY: {len(df_preview)} Rows | Month: {forecast_month_input} | Days: {work_day_input}")
                    
                    if st.button("🚀 EXECUTE UPLOAD", type="primary", use_container_width=True):
                        with st.spinner("PROCESSING..."):
                            # PANGGIL FUNCTION DENGAN PARAMETER BARU
                            process_forecast_csv(df_preview, forecast_month_input, work_day_input)
                            time.sleep(0.5)
                            st.rerun()
            except Exception as e:
                st.error(f"ERROR: {e}")

# ================= RIGHT PANEL =================
with right_panel:
    with st.container(border=True):
        st.markdown("#### 📋 DATABASE LOG")

        if not df_view.empty:
            cols_config = {
                    "forecast_id": st.column_config.TextColumn("ID", width="small"),
                    "forecast_month": "Month",
                    "customer_name": "Cust",
                    "part_no": "Part No",
                    "part_name": st.column_config.TextColumn("Part Name", width="medium"),
                    "forecast_qty_monthly": st.column_config.NumberColumn("Qty", format="%d"),
                    "revision_no": st.column_config.NumberColumn("Rev", format="%d"),
                    "created_at": st.column_config.DatetimeColumn("Time", format="DD/MM HH:mm"),
            }
            
            display_cols = ["forecast_id", "forecast_month", "customer_name", "part_no", "part_name", "forecast_qty_monthly", "revision_no", "created_at"]
            final_cols = [c for c in display_cols if c in df_view.columns]

            st.dataframe(
                df_view[final_cols],
                use_container_width=True,
                height=550,
                column_config=cols_config,
                hide_index=True
            )
        else:
            st.info("NO DATA STREAM.")