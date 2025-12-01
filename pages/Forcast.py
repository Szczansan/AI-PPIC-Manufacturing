import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import numpy as np
import math
import calendar
import time
from datetime import datetime, date
from supabase_client import get_supabase
from components.navbar import show_navbar

# ===== PAGE CONFIG & INIT =====
st.set_page_config(page_title="Forecast Management", page_icon="📊", layout="wide")
supabase = get_supabase()
show_navbar()

# ====== CSS STYLING ======
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; color: #007bff; }
    div[data-testid="stToast"] { padding: 10px; width: 400px; }
</style>
""", unsafe_allow_html=True)

# ====== HELPER FUNCTIONS ====== #
def to_month_label(date_val):
    if pd.isna(date_val): return None
    if isinstance(date_val, str): date_val = pd.to_datetime(date_val)
    return date_val.strftime("%B %Y")

def safe_execute(query):
    try:
        res = query.execute()
        return res.data
    except Exception as e:
        print(f"DB Error: {e}")
        return None

# --- NEW HELPER FUNCTIONS ---

def next_revision_number(supabase_client, forecast_month, customer_name):
    """
    Cari revision tertinggi untuk forecast_month + customer,
    lalu return next revision number (int).
    """
    try:
        q = supabase_client.table("forecast_monthly").select("revision_no", count="exact")\
            .eq("forecast_month", forecast_month)\
            .eq("customer_name", customer_name)\
            .order("revision_no", desc=True).limit(1)
        res = safe_execute(q)
        if res and len(res) > 0:
            try:
                return int(res[0].get("revision_no", 0)) + 1
            except:
                return 1
    except Exception:
        return 1
    return 1

def generate_forecast_id(forecast_month, revision_no):
    """
    Format forecast_id: FCT-YYYY-MM-R{n}
    """
    return f"FCT-{forecast_month}-R{revision_no}"

def process_forecast_csv(df_raw, forecast_month, customer_name, forecast_source="manual", created_by=None):
    """
    Convert uploaded DataFrame (columns: part_name, part_no, '1'..'31')
    into forecast_monthly + forecast_daily inserts to Supabase.
    """
    # basic validation
    if forecast_month is None or len(forecast_month) != 7:
        st.error("Format forecast_month harus 'YYYY-MM' (contoh: 2025-12).")
        return None

    # normalize column names and ensure strings
    df = df_raw.copy()
    df.columns = [str(c).strip() for c in df.columns]

    # expected day columns as strings '1'..'31'
    day_cols = [str(i) for i in range(1, 32)]
    
    # Check kolom Part No (bisa 'part_no' atau 'part no' atau 'material')
    if "part_no" not in df.columns:
        st.error("Kolom 'part_no' tidak ditemukan di file (setelah normalisasi).")
        return None

    # filter only valid rows with a part_no
    df = df[df["part_no"].notna()].reset_index(drop=True)

    # 🔰 HANDLING DUPLICATE PART_NO
    dup_count = df["part_no"].duplicated().sum()
    if dup_count > 0:
        st.warning(f"Terdeteksi {dup_count} duplikat part_no pada file. Sistem otomatis menghapus duplikasi.")
        df = df.drop_duplicates(subset=["part_no"], keep="first").reset_index(drop=True)

    # calculate monthly totals (sum only available day cols)
    def safe_sum_row(r):
        s = 0
        for c in day_cols:
            if c in r and pd.notna(r[c]):
                try:
                    s += float(r[c])
                except:
                    pass
        return int(round(s))

    df["forecast_qty_monthly"] = df.apply(safe_sum_row, axis=1)

    # determine revision number and generate forecast_id
    revision_no = next_revision_number(supabase, forecast_month, customer_name)
    forecast_id = generate_forecast_id(forecast_month, revision_no)

    # prepare monthly records
    monthly_rows = []
    for _, row in df.iterrows():
        monthly_rows.append({
            "forecast_id": forecast_id,
            "forecast_month": forecast_month,
            "upload_date": str(date.today()),
            "forecast_source": forecast_source,
            "customer_name": customer_name,
            "part_no": str(row["part_no"]).strip(),
            "forecast_qty_monthly": int(row["forecast_qty_monthly"]),
            "revision_no": revision_no,
            "min_days": 2.0, # Default logic
            "note": None,
            "created_by": created_by
        })

    # insert monthly rows
    res_monthly = safe_execute(supabase.table("forecast_monthly").insert(monthly_rows))
    if res_monthly is None:
        st.error("Gagal menyimpan ke tabel 'forecast_monthly'. Cek struktur database.")
        return None

    # prepare daily rows
    year = int(forecast_month.split("-")[0])
    month = int(forecast_month.split("-")[1])
    last_day = calendar.monthrange(year, month)[1]

    daily_rows = []
    for _, row in df.iterrows():
        part_no = str(row["part_no"]).strip()
        for d in range(1, last_day + 1):
            col = str(d)
            qty = 0
            if col in row and pd.notna(row[col]):
                try:
                    qty = int(round(float(row[col])))
                except:
                    qty = 0
            
            # Skip entry kalo qty 0 biar hemat DB storage
            if qty > 0: 
                forecast_date = date(year, month, d)
                daily_rows.append({
                    "forecast_id": forecast_id,
                    "part_no": part_no,
                    "forecast_date": str(forecast_date),
                    "daily_demand": qty,
                    "revision_no": revision_no
                })

    # insert daily rows in chunks
    chunk_size = 500
    if daily_rows:
        try:
            for i in range(0, len(daily_rows), chunk_size):
                chunk = daily_rows[i:i+chunk_size]
                safe_execute(supabase.table("forecast_daily").insert(chunk))
        except Exception as e:
            st.error(f"Error insert daily: {e}")
            return None

    st.success(f"✅ Forecast uploaded. ID: **{forecast_id}** | Parts: {len(df)} | Daily Entries: {len(daily_rows)}")
    return {"forecast_id": forecast_id, "parts": len(df)}

# --- END NEW HELPER FUNCTIONS ---

# --- EXISTING CACHED FETCH ---
@st.cache_data(ttl=60)
def fetch_forecasts_cached(limit=3000):
    query = supabase.table("forecast_monthly").select("*").order("created_at", desc=True).limit(limit)
    data = safe_execute(query)
    return pd.DataFrame(data) if data else pd.DataFrame()

def clear_cache():
    fetch_forecasts_cached.clear()

# ====== MAIN UI ====== #

st.title("📊 Forecast Management System")
st.markdown("### Monthly Schedule Upload & Monitoring")
st.divider()

# --- 1. DATA LOADING ---
df_all = fetch_forecasts_cached(limit=3000)

# --- 2. GLOBAL FILTERS ---
if not df_all.empty:
    customers = ["All"] + sorted(df_all["customer_name"].dropna().unique().tolist())
    c1, c2 = st.columns([1, 4]) 
    with c1:
        sel_customer = st.selectbox("🏢 Filter Customer", customers, index=0)
    
    # Filter View
    df_view = df_all.copy()
    if sel_customer != "All": df_view = df_view[df_view["customer_name"] == sel_customer]
    
    # Simple Metric
    total_parts = len(df_view)
    total_qty = df_view['forecast_qty_monthly'].sum() if 'forecast_qty_monthly' in df_view else 0
    st.metric("Total Monthly Qty", f"{total_qty:,.0f}", f"{total_parts} Lines")
else:
    df_view = pd.DataFrame()


# --- 3. SPLIT LAYOUT ---
left_panel, right_panel = st.columns([1.2, 2.5], gap="medium")

# ================= LEFT PANEL: UPLOAD ZONE =================
with left_panel:
    st.info("📝 **Upload Monthly Schedule**")
    
    tab_upload, tab_manual = st.tabs(["📂 Upload Matrix (1-31)", "✍️ Manual"])
    
    # --- TAB 1: UPLOAD (REVISED for forecast_monthly -> forecast_daily) ---
    with tab_upload:
        st.caption("Upload file `.xlsx` or `.csv` (columns: part_name, part_no, 1..31).")
        forecast_month_input = st.text_input("Forecast Month (YYYY-MM)", value=datetime.today().strftime("%Y-%m"))
        customer_input = st.text_input("Customer", value="Toyota")
        source_input = st.text_input("Forecast Source", value="Customer File")
        file = st.file_uploader("Drop Excel/CSV File Here", type=["xlsx", "csv"], label_visibility="collapsed")

        if file:
            try:
                # read file into dataframe (accept .csv or .xlsx)
                if file.type == "text/csv" or str(file.name).lower().endswith(".csv"):
                    df_preview = pd.read_csv(file)
                else:
                    df_preview = pd.read_excel(file)

                # normalize headers preview
                df_preview.columns = [str(c).strip() for c in df_preview.columns]
                st.dataframe(df_preview.head(5), use_container_width=True)
                st.caption(f"Preview: {len(df_preview)} rows found.")

                # show quick validation
                missing = []
                # Check case-insensitive part_no existence
                if "part_no" not in [c.lower() for c in df_preview.columns]:
                    missing.append("part_no")
                
                # check day columns 1..31 existence (at least one)
                day_cols_exist = any(str(i) in df_preview.columns for i in range(1, 32))
                if not day_cols_exist:
                    st.warning("File tidak ditemukan kolom tanggal 1..31. Pastikan format: part_name, part_no, 1..31")
                elif missing:
                    st.error(f"Kolom wajib hilang: {missing}")
                else:
                    st.success("File valid untuk konversi.")
                
                if st.button("🚀 Process & Upload", type="primary", use_container_width=True):
                    # validate month format
                    try:
                        datetime.strptime(forecast_month_input, "%Y-%m")
                    except Exception:
                        st.error("Format Forecast Month harus 'YYYY-MM' (contoh: 2025-12).")
                    else:
                        # lower-case column mapping for safety
                        # but keep numeric day columns as strings '1'..'31' if present
                        # ensure part_no column exists possibly with different case
                        cols_lower = {c.lower(): c for c in df_preview.columns}
                        
                        if "part_no" not in cols_lower:
                            st.error("Kolom 'part_no' tidak ditemukan (case-insensitive check failed).")
                        else:
                            # rename real column name to standard 'part_no' and keep day cols
                            actual_part_col = cols_lower["part_no"]
                            if actual_part_col != "part_no":
                                df_preview = df_preview.rename(columns={actual_part_col: "part_no"})
                            
                            # ensure day columns are strings '1'..'31' (if excel has numeric header 1.0 convert)
                            new_cols = {}
                            for c in df_preview.columns:
                                sc = str(c).strip()
                                # some Excel exports can make numeric headers float -> '1.0'
                                if sc.endswith(".0"):
                                    sc2 = sc.replace(".0", "")
                                    new_cols[c] = sc2
                            if new_cols:
                                df_preview = df_preview.rename(columns=new_cols)
                            
                            # run processing
                            with st.spinner("Processing & Uploading..."):
                                result = process_forecast_csv(
                                    df_preview, 
                                    forecast_month_input, 
                                    customer_input, 
                                    forecast_source=source_input, 
                                    created_by=None
                                )
                                if result:
                                    st.toast("✅ Forecast uploaded & daily generated!", icon="🎉")
                                    st.balloons()
                                    clear_cache()
                                    time.sleep(1)
                                    st.rerun()

            except Exception as e:
                st.error(f"Error saat membaca file: {e}")

    # --- TAB 2: MANUAL ---
    with tab_manual:
        st.warning("Manual input logic is currently disabled. Please use Excel upload.")

# ================= RIGHT PANEL: DATA TABLE =================
with right_panel:
    st.success("📋 **Forecast Monthly History**")

    if not df_view.empty:
        # Menampilkan data dari tabel forecast_monthly
        st.dataframe(
            df_view,
            use_container_width=True,
            height=600,
            column_config={
                "forecast_id": st.column_config.TextColumn("ID", width="medium"),
                "forecast_month": "Month",
                "customer_name": "Customer",
                "part_no": "Part No",
                "forecast_qty_monthly": st.column_config.NumberColumn("Total Qty", format="%d"),
                "revision_no": st.column_config.NumberColumn("Rev", format="%d"),
                "created_at": st.column_config.DatetimeColumn("Uploaded At", format="DD/MM/YY HH:mm"),
            },
            hide_index=True
        )
    else:
        st.info("Belum ada data di tabel 'forecast_monthly'. Silakan upload data baru.")