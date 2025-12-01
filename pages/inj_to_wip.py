import streamlit as st
from supabase_client import get_supabase
from components.navbar import show_navbar
from datetime import datetime
from calendar import monthrange
import pandas as pd

# optional timezone
try:
    from zoneinfo import ZoneInfo
except:
    ZoneInfo = None

supabase = get_supabase()
st.set_page_config(page_title="Inj → WIP Transfer", layout="centered")

# show navbar
show_navbar()

# ==========================================
# CUSTOM TITLE (CENTER + GLOW WHITE)
# ==========================================
st.markdown("""
    <style>
    .glow-title {
        text-align: center;
        font-size: 42px;
        font-weight: 700;
        color: #FFFFFF;
        /* Efek Glow Putih */
        text-shadow: 
            0 0 10px rgba(255, 255, 255, 0.8), 
            0 0 20px rgba(255, 255, 255, 0.6), 
            0 0 30px rgba(255, 255, 255, 0.4);
        margin-bottom: 30px;
        margin-top: 10px;
        font-family: 'Segoe UI', sans-serif;
    }
    </style>
    <div class="glow-title">
        Form Transfer Part to Warehouse
    </div>
""", unsafe_allow_html=True)
# ==========================================


# -----------------------
# Helper functions
# -----------------------
@st.cache_data
def load_master_parts():
    resp = supabase.table("MASTER").select("PART_NAME, part_no").execute()
    return resp.data if hasattr(resp, "data") else []

def get_jakarta_time():
    now = datetime.now()
    try:
        if ZoneInfo:
            now = datetime.now(tz=ZoneInfo("Asia/Jakarta"))
            return now.strftime("%H:%M"), now.date()
    except:
        pass
    return now.strftime("%H:%M"), now.date()

def generate_no_do(prefix):
    try:
        resp = (
            supabase.table("wip_in")
            .select("no_do")
            .ilike("no_do", f"{prefix}-%")
            .order("no_do", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return f"{prefix}-001"
        last_do = rows[0]["no_do"]
        last_num = int(last_do.split("-")[1])
        return f"{prefix}-{last_num + 1:03d}"
    except:
        return f"{prefix}-001"

# -----------------------
# Load MASTER parts
# -----------------------
master_parts = load_master_parts()
if not master_parts:
    st.error("MASTER kosong / gagal load. Pastikan table MASTER ada.")
    st.stop()

part_names = [m["PART_NAME"] for m in master_parts]
part_map = {m["PART_NAME"]: m["part_no"] for m in master_parts}

# -----------------------
# Session state
# -----------------------
if "num_parts" not in st.session_state:
    st.session_state.num_parts = 1
if "parts_values" not in st.session_state:
    st.session_state.parts_values = [{} for _ in range(8)]

# -----------------------
# Form
# -----------------------
with st.form("inj_to_wip_form"):
    # Variabel python tetap 'entry_date' gapapa, tapi nanti pas insert key-nya 'date'
    entry_date = st.date_input("Tanggal Transfer")

    waktu_str, jakarta_date = get_jakarta_time()
    st.info(waktu_str)

    prepared_by = st.text_input("Prepared By (nama pengirim)")

    # ADD/REMOVE buttons inside form (near parts)
    c_add, c_rm = st.columns([1,1])
    add_clicked = c_add.form_submit_button("ADD PART")
    remove_clicked = c_rm.form_submit_button("REMOVE LAST PART")

    if add_clicked:
        if st.session_state.num_parts < 8:
            st.session_state.num_parts += 1
        else:
            st.warning("Maksimal 8 part bro.")
        st.rerun()

    if remove_clicked:
        if st.session_state.num_parts > 1:
            idx = st.session_state.num_parts - 1
            st.session_state.parts_values[idx] = {}
            st.session_state.num_parts -= 1
        else:
            st.info("Minimal 1 part harus ada.")
        st.rerun()

    # Render dynamic part rows
    for i in range(st.session_state.num_parts):
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            part_sel = st.selectbox(f"Part name {i+1}", options=part_names, key=f"part_name_{i}")
        with col2:
            qty = st.number_input(f"Qty{i+1}", min_value=0, step=1, key=f"qty_{i}")
        with col3:
            part_no_view = part_map.get(part_sel, "")
            st.caption(f"Part No: {part_no_view}")

        st.session_state.parts_values[i] = {
            "part_name": part_sel,
            "part_no": part_no_view,
            "qty": qty
        }

    submitted = st.form_submit_button("Submit Transfer")

# -----------------------
# Submit handler
# -----------------------
if submitted:
    if not prepared_by.strip():
        st.error("Prepared By wajib diisi.")
        st.stop()

    rows_to_insert = []
    for i in range(st.session_state.num_parts):
        p = st.session_state.parts_values[i]
        qty = p.get("qty", 0) or 0
        if qty <= 0:
            continue
        rows_to_insert.append({
            # UPDATE DI SINI: ganti "entry_date" jadi "date"
            "date": str(entry_date), 
            "waktu": waktu_str,
            "no_do": None,
            "prepared_by": prepared_by.strip(),
            "part_name": p.get("part_name", ""),
            "part_no": p.get("part_no", ""),
            "qty_in": int(qty)
        })

    if not rows_to_insert:
        st.error("Tidak ada part dengan qty > 0.")
        st.stop()

    yy = str(entry_date.year)[-2:]
    mm = f"{entry_date.month:02d}"
    prefix = f"{yy}{mm}"
    no_do = generate_no_do(prefix)
    for r in rows_to_insert:
        r["no_do"] = no_do

    try:
        supabase.table("wip_in").insert(rows_to_insert).execute()
        st.success(f"Berhasil submit {len(rows_to_insert)} rows. NO_DO: {no_do}")
        st.json({"no_do": no_do, "rows": rows_to_insert})

        # reset
        st.session_state.num_parts = 1
        st.session_state.parts_values = [{} for _ in range(8)]
        for i in range(8):
            st.session_state.pop(f"part_name_{i}", None)
            st.session_state.pop(f"qty_{i}", None)
        st.rerun()
    except Exception as e:
        st.error(f"Gagal insert: {e}")

# -----------------------
# Stylish Summary + History (UI A: Modern Gradient Cards)
# -----------------------
st.markdown("---")

# custom CSS for cards
st.markdown(
    """
    <style>
    .summary-row {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
        margin-bottom: 18px;
    }
    .card {
        flex: 1 1 220px;
        padding: 18px;
        border-radius: 12px;
        color: white;
        min-width: 180px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.45);
        position: relative;
        overflow: hidden;
    }
    .card .title { font-size: 13px; opacity: 0.9; margin-bottom: 6px; }
    .card .value { font-size: 28px; font-weight: 700; }
    .card .sub { font-size: 11px; opacity: 0.85; margin-top:6px; }
    .gradient-1 { background: linear-gradient(135deg,#1e88e5,#6dd5ed); }
    .gradient-2 { background: linear-gradient(135deg,#8e44ad,#3498db); }
    .gradient-3 { background: linear-gradient(135deg,#ff7e5f,#feb47b); color:#2b2b2b; }
    .gradient-4 { background: linear-gradient(135deg,#43cea2,#185a9d); }
    .summary-header {
        display:flex; align-items:center; gap:12px; margin-bottom:8px;
    }
    .summary-header img { width:44px; height:44px; border-radius:8px; }
    .history-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 6px 18px rgba(0,0,0,0.45);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# header with small icon (local uploaded image)
icon_path = "/mnt/data/8bf34203-3494-42f4-9eb3-6c6bcda0f6cd.png"
left, right = st.columns([1, 6])
with left:
    try:
        st.image(icon_path, width=56)
    except:
        pass
with right:
    st.markdown("## 📊 Summary & Latest Activity")

# compute summary numbers safely
try:
    # today summary
    today_str = str(entry_date)
    # UPDATE DI SINI: .eq("date", ...)
    resp_today = supabase.table("wip_in").select("qty_in").eq("date", today_str).execute()
    total_today_qty = sum([r["qty_in"] for r in (resp_today.data or [])])
    total_today_rows = len(resp_today.data or [])

    # month summary using date range
    year = entry_date.year
    month = entry_date.month
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{monthrange(year, month)[1]}"

    # UPDATE DI SINI: select("qty_in, date"), .gte("date", ...), .lte("date", ...)
    resp_month = (
        supabase.table("wip_in")
        .select("qty_in, date") 
        .gte("date", first_day)
        .lte("date", last_day)
        .execute()
    )
    total_month_qty = sum([r["qty_in"] for r in (resp_month.data or [])])
    total_month_rows = len(resp_month.data or [])

    # Build cards (HTML)
    card_html = f"""
    <div class="summary-row">
        <div class="card gradient-1">
            <div class="title">Qty Today</div>
            <div class="value">{total_today_qty}</div>
            <div class="sub">Transactions: {total_today_rows}</div>
        </div>
        <div class="card gradient-2">
            <div class="title">Transactions Today</div>
            <div class="value">{total_today_rows}</div>
            <div class="sub">Date: {today_str}</div>
        </div>
        <div class="card gradient-3">
            <div class="title">Qty This Month</div>
            <div class="value">{total_month_qty}</div>
            <div class="sub">Transactions: {total_month_rows}</div>
        </div>
        <div class="card gradient-4">
            <div class="title">Transactions This Month</div>
            <div class="value">{total_month_rows}</div>
            <div class="sub">Range: {first_day} → {last_day}</div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
except Exception as e:
    st.error(f"Summary error: {e}")

# History card
st.markdown("<div class='history-card'>", unsafe_allow_html=True)
st.markdown("### 📝 Latest 10 Shipments")

try:
    resp_history = (
        supabase.table("wip_in")
        .select("*")
        .order("id", desc=True)
        .limit(10)
        .execute()
    )
    if resp_history.data:
        df = pd.DataFrame(resp_history.data)
        # UPDATE DI SINI: ganti "entry_date" jadi "date" di list columns
        cols = ["no_do", "date", "waktu", "part_name", "part_no", "qty_in", "prepared_by"]
        df = df[[c for c in cols if c in df.columns]]
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Belum ada transaksi.")
except Exception as e:
    st.error(f"History error: {e}")

st.markdown("</div>", unsafe_allow_html=True)