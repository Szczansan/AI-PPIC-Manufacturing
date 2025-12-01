import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timedelta
from components.navbar import show_navbar

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="Material Stock Center", layout="wide", initial_sidebar_state="collapsed")
HEADER_ICON = "/mnt/data/eba2f11a-9e95-4d83-b8c6-67011fd4d33f.png"  # <-- uploaded image path

# -----------------------------
# CONNECT TO SUPABASE
# -----------------------------
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# -----------------------------
# STYLES (global modern look)
# -----------------------------
st.markdown(
    """
    <style>
    /* Page background */
    .stApp, .reportview-container {
        background: linear-gradient(180deg,#090b10,#0f172a);
        color: #e6eef8;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }

    /* Header card */
    .header-card {
        background: linear-gradient(90deg,#0b1220,#142533);
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 6px 22px rgba(2,6,23,0.6);
        color: #e6eef8;
        margin-bottom: 18px;
    }
    .header-title { font-size: 22px; font-weight:700; margin:0 0 6px 0; }
    .header-sub { color:#98a6bf; margin:0; font-size:13px; }

    /* Filter Bar */
    .filter-bar { display:flex; gap:12px; align-items:center; margin-bottom:14px; }

    /* Cards */
    .card {
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        padding: 14px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.03);
        box-shadow: 0 6px 18px rgba(2,6,23,0.45);
    }
    .card-title { color:#9fb0d6; font-weight:600; font-size:13px; margin-bottom:6px; }
    .card-value { font-size:22px; font-weight:800; }

    /* Status pills */
    .pill {
        display:inline-block;
        padding:8px 12px;
        border-radius:18px;
        color: #071029;
        font-weight:700;
    }
    .pill-green { background: linear-gradient(90deg,#34d399,#10b981); }
    .pill-yellow { background: linear-gradient(90deg,#fbbf24,#f59e0b); color:#071029; }
    .pill-red { background: linear-gradient(90deg,#fb7185,#ef4444); color:#071029; }
    .pill-unknown { background: linear-gradient(90deg,#d1d5db,#9ca3af); color:#071029; }

    /* Table dark */
    .stDataFrame table {
        background-color: transparent !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# NAVBAR
# -----------------------------
show_navbar()

# -----------------------------
# HEADER
# -----------------------------
col1, col2 = st.columns([0.12, 1])
with col1:
    try:
        st.image(HEADER_ICON, width=72)
    except Exception:
        st.write("")  # if image not found, ignore
with col2:
    st.markdown(
        f"""
        <div class="header-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <div class="header-title">📦 Material Stock Center</div>
                    <div class="header-sub">Menggabungkan snapshot stock dari transaksi material_in & material_out. Pantau stok, identifikasi minus, dan konfirmasi permintaan.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# -----------------------------
# Filter row
# -----------------------------
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.2, 1.2, 2, 1])

with filter_col1:
    snapshot_date = st.date_input("Pilih tanggal snapshot stok", value=date.today())

with filter_col2:
    status_options = ["Semua Status", "READY DELIVERY", "STOCK MINUS", "UNKNOWN"]
    status_filter = st.selectbox("Filter berdasarkan Status Stok", status_options, index=0)

with filter_col3:
    search_text = st.text_input("🔎 Cari berdasarkan Part No / Part Name / Type (kosong = semua)")

with filter_col4:
    st.markdown("### ")
    refresh_btn = st.button("🔁 Refresh")

# -----------------------------
# Fetch view data (v_material_balance)
# Important: we load ALL transactions up to the snapshot_date (inclusive)
# -----------------------------
st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
try:
    # Query all rows with date <= snapshot_date
    res = supabase.table("v_material_balance").select("*").lte("date", snapshot_date.isoformat()).execute()
    df_view = pd.DataFrame(res.data)
except Exception as e:
    st.error(f"Gagal mengambil data dari Supabase: {e}")
    st.stop()

# --- TAMBAHAN PENTING DI SINI ---
# Paksa kolom 'date' jadi object date python biar match sama snapshot_date
if not df_view.empty:
    df_view["date"] = pd.to_datetime(df_view["date"]).dt.date

# If still empty, show placeholders
if df_view.empty:
    st.warning("Tidak ditemukan data transaksi sampai tanggal ini.")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown('<div class="card"><div class="card-title">Total Part</div><div class="card-value">0</div></div>', unsafe_allow_html=True)
    with c2: st.markdown('<div class="card"><div class="card-title">Total Ready Delivery</div><div class="card-value">0</div></div>', unsafe_allow_html=True)
    with c3: st.markdown('<div class="card"><div class="card-title">Total Stock Minus</div><div class="card-value">0</div></div>', unsafe_allow_html=True)
else:
    # -----------------------------
    # LOGIC UPDATE: PISAHKAN KUMULATIF & HARIAN
    # -----------------------------

    # 1. Hitung BALANCE KUMULATIF (Total Masuk - Total Keluar dari awal s/d snapshot_date)
    cumulative_agg = (
        df_view.groupby(["type_material", "grade_material", "color_material"], as_index=False)
        .agg({"qty_in_harian": "sum", "qty_out_harian": "sum"})
    )
    # Balance = Total In - Total Out
    cumulative_agg["balance"] = cumulative_agg["qty_in_harian"] - cumulative_agg["qty_out_harian"]
    
    # Siapkan Master Stock (Type, Grade, Color, Balance)
    master_stock = cumulative_agg[["type_material", "grade_material", "color_material", "balance"]].rename(columns={
        "type_material": "TYPE",
        "grade_material": "GRADE",
        "color_material": "COLOR"
    })

    # 2. Hitung PERGERAKAN HARIAN (Khusus tanggal snapshot_date)
    daily_df = df_view[df_view["date"] == snapshot_date]
    
    if daily_df.empty:
        # Jika hari ini tidak ada transaksi, Qty In/Out 0
        daily_agg = pd.DataFrame(columns=["TYPE", "GRADE", "COLOR", "QTY_IN", "QTY_OUT"])
    else:
        daily_agg = (
            daily_df.groupby(["type_material", "grade_material", "color_material"], as_index=False)
            .agg({"qty_in_harian": "sum", "qty_out_harian": "sum"})
            .rename(columns={
                "type_material": "TYPE",
                "grade_material": "GRADE",
                "color_material": "COLOR",
                "qty_in_harian": "QTY_IN",
                "qty_out_harian": "QTY_OUT"
            })
        )

    # 3. MERGE (GABUNGKAN)
    # Left join Master Stock dengan Daily Agg
    snapshot = pd.merge(master_stock, daily_agg, how="left", on=["TYPE", "GRADE", "COLOR"])

    # Isi NaN dengan 0 untuk pergerakan harian
    snapshot["QTY_IN"] = snapshot["QTY_IN"].fillna(0).astype(float)
    snapshot["QTY_OUT"] = snapshot["QTY_OUT"].fillna(0).astype(float)

    # -----------------------------
    # 4. AMBIL INFO TAMBAHAN (Last Update Saja)
    # -----------------------------
    # Kita ambil tanggal created_at dari transaksi paling terakhir sebagai "Last Update"
    meta_df = (
        df_view.sort_values("created_at", ascending=False)
        .drop_duplicates(subset=["type_material", "grade_material", "color_material"])
    )
    # Cuma ambil kolom kunci + created_at (PART_NAME dibuang sesuai request)
    meta_df = meta_df[["type_material", "grade_material", "color_material", "created_at"]]
    meta_df = meta_df.rename(columns={
        "type_material": "TYPE", 
        "grade_material": "GRADE", 
        "color_material": "COLOR",
        "created_at": "LAST_UPDATE_RAW"
    })
    
    # Gabung ke snapshot
    snapshot = snapshot.merge(meta_df, how="left", on=["TYPE", "GRADE", "COLOR"])
    
    # Format Tanggal
    if "LAST_UPDATE_RAW" in snapshot.columns:
        snapshot["LAST_UPDATE"] = pd.to_datetime(snapshot["LAST_UPDATE_RAW"]).dt.strftime("%d-%b-%Y %H:%M")
    else:
        snapshot["LAST_UPDATE"] = "-"

    # -----------------------------
    # FILTER & DISPLAY
    # -----------------------------

    # apply search filter
    if search_text:
        mask = (
            snapshot["TYPE"].astype(str).str.contains(search_text, case=False, na=False) |
            snapshot["GRADE"].astype(str).str.contains(search_text, case=False, na=False) |
            snapshot["COLOR"].astype(str).str.contains(search_text, case=False, na=False)
        )
        snapshot = snapshot[mask]

    # apply status filter
    def status_label(balance):
        try:
            bal = float(balance)
        except Exception:
            return "UNKNOWN"
        if bal < 0:
            return "STOCK MINUS"
        elif bal > 0:
            return "READY DELIVERY"
        else:
            return "UNKNOWN"

    snapshot["STATUS"] = snapshot["balance"].apply(status_label)

    if status_filter and status_filter != "Semua Status":
        snapshot = snapshot[snapshot["STATUS"] == status_filter]

    # summary cards
    total_item = snapshot.shape[0]
    total_ready = (snapshot["STATUS"] == "READY DELIVERY").sum()
    total_minus = (snapshot["STATUS"] == "STOCK MINUS").sum()

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Total Part</div>
                <div class="card-value">{total_item}</div>
            </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Total Ready Delivery</div>
                <div class="card-value"><span class="pill pill-green"></span> {total_ready}</div>
            </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Total Stock Minus</div>
                <div class="card-value"><span class="pill pill-red"></span> {total_minus}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # -----------------------------
    # DATA TABLE DENGAN WARNA (PANDAS STYLER)
    # -----------------------------
    st.markdown("### 📦 Data Integrated STOCK")
    
    # PART_NAME sudah dihapus dari sini
    display_cols = ["TYPE","GRADE","COLOR","QTY_IN","QTY_OUT","balance","STATUS","LAST_UPDATE"]
    present_cols = [c for c in display_cols if c in snapshot.columns]
    
    # Fungsi styling khusus buat kolom STATUS
    def highlight_status(val):
        color = ''
        font_color = 'white' # Default text white
        
        if val == "STOCK MINUS":
            color = '#ef4444' # Merah (Red-500)
        elif val == "READY DELIVERY":
            color = '#22c55e' # Hijau (Green-500)
        else: 
            color = '#eab308' # Kuning/Orange (Yellow-500)
            font_color = 'black' # Text hitam biar kontras

        # CSS untuk bikin kotak rounded
        return f'background-color: {color}; color: {font_color}; font-weight: bold; border-radius: 4px; text-align: center;'

    # Apply style ke dataframe
    styled_df = snapshot[present_cols].sort_values(["TYPE","GRADE","COLOR"]).style.map(highlight_status, subset=['STATUS'])
    
    # Render Dataframe
    st.dataframe(
        styled_df, 
        use_container_width=True, 
        height=420,
        column_config={
            "balance": st.column_config.NumberColumn(format="%.1f"), # Balance tetap 2 desimal
            "QTY_IN": st.column_config.NumberColumn(format="%.1f"),  # <-- IN jadi 1 desimal
            "QTY_OUT": st.column_config.NumberColumn(format="%.1f"), # <-- OUT jadi 1 desimal
        }
    )

    st.markdown("---")

    # BON MATERIAL
    st.markdown("### 🧾 Daftar Permintaan Material (BON Injection)")

    def load_bon_data():
        res = supabase.table("BON_MATERIAL").select("*").order("NO_BON", desc=True).execute()
        return pd.DataFrame(res.data)

    df_bon = load_bon_data()
    if df_bon.empty:
        st.info("Belum ada data permintaan material dari Injection.")
    else:
        # show BON table
        st.dataframe(df_bon[["NO_BON","TYPE","GRADE","COLOR","QTY","REQUESTER","STATUS","APPROVED_AT"]], use_container_width=True)

        # actions: approve / reject with insertion to material_out
        pending = df_bon[df_bon["STATUS"] == "Menunggu Konfirmasi"]
        if not pending.empty:
            st.markdown("#### 🔧 Konfirmasi Permintaan Material")
            for i, row in pending.iterrows():
                with st.container():
                    r1, r2, r3, r4 = st.columns([2,3,1,1])
                    with r1:
                        st.write(f"**No BON:** {row['NO_BON']}")
                        st.write(f"{row['TYPE']} | {row['GRADE']} | {row['COLOR']}")
                    with r2:
                        st.write(f"Requester: {row.get('REQUESTER','-')} — Qty: {row['QTY']}")
                    with r3:
                        if st.button(f"✅ Approve {row['NO_BON']}", key=f"approve_{i}"):
                            now_iso = datetime.now().isoformat()
                            # update BON
                            supabase.table("BON_MATERIAL").update({"STATUS":"Disetujui","APPROVED_AT":now_iso}).eq("NO_BON",row["NO_BON"]).execute()
                            # insert material_out
                            supabase.table("material_out").insert({
                                "type_material": row["TYPE"],
                                "grade_material": row["GRADE"],
                                "color_material": row["COLOR"],
                                "qty": int(row["QTY"]),
                                "created_at": now_iso,
                                "prepared_by": row.get("REQUESTER","system")
                            }).execute()
                            st.success(f"BON {row['NO_BON']} disetujui. Material keluar tercatat.")
                            st.experimental_rerun()
                    with r4:
                        if st.button(f"❌ Tolak {row['NO_BON']}", key=f"reject_{i}"):
                            now_iso = datetime.now().isoformat()
                            supabase.table("BON_MATERIAL").update({"STATUS":"Ditolak","APPROVED_AT": now_iso}).eq("NO_BON", row["NO_BON"]).execute()
                            st.warning(f"BON {row['NO_BON']} ditolak.")
                            st.experimental_rerun()

# auto refresh on button
if refresh_btn:
    st.experimental_rerun()