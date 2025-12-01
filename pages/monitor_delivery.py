import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from fpdf import FPDF
from io import BytesIO
from components.navbar import show_navbar  # ✅ Navbar

# --- PAGE CONFIG ---
st.set_page_config(page_title="🚚 Monitor Delivery (Finish Good)", layout="wide")

# --- CONNECT SUPABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# --- NAVBAR ---
show_navbar()

# --- HEADER ---
st.markdown("""
<div style="background: linear-gradient(90deg,#0f172a,#1e293b);
padding: 12px 16px; border-radius:8px; color:#fff;">
    <h3 style="margin:0;">🚚 Monitor Delivery — Surat Jalan (Finish Good)</h3>
    <p style="margin:0;font-size:13px;color:#94a3b8;">
        Buat Surat Jalan (maksimal 8 part). Setelah submit, stok FG otomatis terupdate dan PDF Surat Jalan tersedia.
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")

# -------------------------
# Helper functions
# -------------------------
def generate_no_delivery():
    year = datetime.now().year
    try:
        res = supabase.table("Delivery_FG").select("NO_DELIVERY").execute()
        df = pd.DataFrame(res.data)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        next_num = 1
    else:
        df = df.dropna(subset=["NO_DELIVERY"])
        df["year"] = df["NO_DELIVERY"].astype(str).str.extract(r"SSP-(\d{4})-")[0]
        df["num"] = df["NO_DELIVERY"].astype(str).str.extract(r"-(\d{4})$")[0]
        df = df[df["year"] == str(year)]
        next_num = 1 if df.empty else int(df["num"].astype(int).max()) + 1

    return f"SSP-{year}-{next_num:04d}"

def to_int_safe(x):
    try:
        return int(x)
    except Exception:
        return 0

def convert_df_to_excel_bytes(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Delivery_FG")
        writer.save()
    return output.getvalue()

def create_pdf_bytes(header_info, parts_list):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "PT. SHIN SAM PLUS INDUSTRY", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, "SURAT JALAN PENGIRIMAN BARANG (FINISH GOOD)", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Arial", size=11)
    pdf.cell(100, 7, f"No. Delivery : {header_info['NO_DELIVERY']}", ln=0)
    pdf.cell(0, 7, f"No. PO : {header_info['NO_PO']}", ln=1)
    pdf.cell(100, 7, f"Customer     : {header_info['CUSTOMER']}", ln=0)
    pdf.cell(0, 7, f"Tanggal : {header_info['DATE_DELIVERY'].strftime('%d-%b-%Y')}", ln=1)
    pdf.cell(0, 7, f"Prepared By  : {header_info['PREPARED_BY']}", ln=1)
    pdf.ln(6)

    # Table header
    pdf.set_font("Arial", "B", 11)
    pdf.cell(10, 8, "No", border=1, align="C")
    pdf.cell(40, 8, "Part No", border=1, align="C")
    pdf.cell(90, 8, "Part Name", border=1, align="C")
    pdf.cell(30, 8, "Qty", border=1, align="C")
    pdf.ln()

    pdf.set_font("Arial", size=11)
    for i, (pno, pname, qty) in enumerate(parts_list, start=1):
        pdf.cell(10, 8, str(i), border=1, align="C")
        pdf.cell(40, 8, str(pno), border=1)
        x_pos = pdf.get_x()
        y_pos = pdf.get_y()
        pdf.multi_cell(90, 8, str(pname), border=1)
        new_y = pdf.get_y()
        pdf.set_xy(x_pos + 90, y_pos)
        pdf.cell(30, 8, f"{qty:,}", border=1, align="R")
        pdf.ln()
        if pdf.get_y() < new_y:
            pdf.set_y(new_y)

    pdf.ln(8)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 6, "Diterima oleh: ____________________", ln=1)
    pdf.cell(0, 6, "Tanggal: ___________________________", ln=1)
    pdf.cell(0, 6, "Tanda tangan: ______________________", ln=1)

    s = pdf.output(dest="S")
    if isinstance(s, str):
        s = s.encode("latin-1")
    return s

# -------------------------
# Load Stock FG
# -------------------------
try:
    res_stock = supabase.table("Stock_FG").select("*").execute()
    df_stock_all = pd.DataFrame(res_stock.data)
except Exception as e:
    st.error(f"Gagal mengambil data Stock_FG: {e}")
    st.stop()

if df_stock_all.empty:
    st.warning("Belum ada data Finish Good di Stock_FG.")
    st.stop()

df_stock_all["BALANCE"] = df_stock_all["BALANCE"].apply(to_int_safe)
part_options = df_stock_all.apply(lambda r: f"{r['PART_NO']} | {r['PART_NAME']} (Bal: {int(r['BALANCE'])})", axis=1).tolist()
part_map = {opt: (r["PART_NO"], r["PART_NAME"], int(r["BALANCE"])) for opt, (_, r) in zip(part_options, df_stock_all.iterrows())}

# -------------------------
# Form input Surat Jalan
# -------------------------
st.markdown("### 🧾 Form Surat Jalan")
with st.form("delivery_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        no_po = st.text_input("No. PO", "")
    with col2:
        customer = st.text_input("Customer", "PT. ITSP")
    with col3:
        prepared_by = st.text_input("Prepared By", "")

    date_delivery = st.date_input("Tanggal Kirim", value=date.today())
    st.markdown("#### Pilih Part (max 8 part)")
    parts_inputs = []
    for i in range(1, 9):
        st.markdown(f"**Part {i}**")
        part_sel = st.selectbox(f"Part {i}", ["-- kosong --"] + part_options, key=f"part_{i}")
        qty = st.number_input(f"Qty {i}", min_value=0, step=1, key=f"qty_{i}")
        if part_sel != "-- kosong --":
            pno, pname, bal = part_map.get(part_sel, ("", "", 0))
        else:
            pno, pname, bal = ("", "", 0)
        parts_inputs.append({"PART_NO": pno, "PART_NAME": pname, "QTY": int(qty), "BAL": int(bal)})

    submit = st.form_submit_button("🚚 Kirim Barang")

# -------------------------
# Handle submit
# -------------------------
if submit:
    filled = [p for p in parts_inputs if p["PART_NO"] and p["QTY"] > 0]
    if not filled:
        st.error("Minimal 1 part harus diisi dengan qty > 0.")
        st.stop()

    for p in filled:
        if p["QTY"] > p["BAL"]:
            st.error(f"Qty part {p['PART_NO']} melebihi stok ({p['BAL']}).")
            st.stop()

    if not prepared_by:
        st.error("Field 'Prepared By' wajib diisi.")
        st.stop()

    no_delivery = generate_no_delivery()
    created_at = datetime.now().isoformat()
    date_ts = datetime.combine(date_delivery, datetime.min.time()).isoformat()

    try:
        for p in filled:
            row = {
                "NO_DELIVERY": no_delivery,
                "NO_PO": no_po,
                "PART_NO": p["PART_NO"],
                "PART_NAME": p["PART_NAME"],
                "CUSTOMER": customer,
                "QTY_DELIVERY": p["QTY"],
                "DATE_DELIVERY": date_ts,
                "STATUS": "Terkirim",
                "PREPARED_BY": prepared_by,
                "CREATED_AT": created_at
            }
            supabase.table("Delivery_FG").insert(row).execute()

            res = supabase.table("Stock_FG").select("*").eq("PART_NO", p["PART_NO"]).execute()
            df_exist = pd.DataFrame(res.data)
            if df_exist.empty:
                data_stock = {
                    "PART_NO": p["PART_NO"],
                    "PART_NAME": p["PART_NAME"],
                    "QTY_IN": 0,
                    "QTY_OUT": p["QTY"],
                    "BALANCE": -p["QTY"],
                    "LAST_UPDATE": datetime.now().isoformat(),
                    "UPDATED_BY": prepared_by
                }
                supabase.table("Stock_FG").insert(data_stock).execute()
            else:
                row0 = df_exist.iloc[0].to_dict()
                new_out = to_int_safe(row0.get("QTY_OUT", 0)) + p["QTY"]
                new_bal = to_int_safe(row0.get("QTY_IN", 0)) - new_out
                supabase.table("Stock_FG").update({
                    "QTY_OUT": new_out,
                    "BALANCE": new_bal,
                    "LAST_UPDATE": datetime.now().isoformat(),
                    "UPDATED_BY": prepared_by
                }).eq("PART_NO", p["PART_NO"]).execute()

        st.success(f"✅ Surat Jalan {no_delivery} berhasil dibuat dan stok diupdate.")
        header = {
            "NO_DELIVERY": no_delivery,
            "NO_PO": no_po,
            "CUSTOMER": customer,
            "DATE_DELIVERY": date_delivery,
            "PREPARED_BY": prepared_by
        }
        parts_pdf = [(p["PART_NO"], p["PART_NAME"], p["QTY"]) for p in filled]
        pdf_bytes = create_pdf_bytes(header, parts_pdf)

        st.download_button(
            label="📄 Download Surat Jalan (PDF)",
            data=pdf_bytes,
            file_name=f"{no_delivery}.pdf",
            mime="application/pdf"
        )
        st.info("Halaman akan direfresh untuk menampilkan data terbaru.")
        st.rerun()

    except Exception as e:
        st.error(f"Gagal menyimpan data pengiriman: {e}")

# -------------------------
# Riwayat pengiriman
# -------------------------
st.markdown("---")
st.markdown("### 📜 Riwayat Pengiriman")

col1, col2 = st.columns([2, 1])
with col1:
    search = st.text_input("🔍 Cari data (Delivery / PO / Customer / Part No):", "")
with col2:
    hist_date = st.date_input("📅 Filter Tanggal", value=None)

try:
    res_hist = supabase.table("Delivery_FG").select("*").order("DATE_DELIVERY", desc=True).execute()
    df_hist = pd.DataFrame(res_hist.data)
except Exception as e:
    st.error(f"Gagal mengambil data riwayat: {e}")
    df_hist = pd.DataFrame()

if not df_hist.empty:
    df_hist["DATE_DELIVERY"] = pd.to_datetime(df_hist["DATE_DELIVERY"]).dt.strftime("%d-%b-%Y")
    if hist_date:
        df_hist = df_hist[df_hist["DATE_DELIVERY"] == hist_date.strftime("%d-%b-%Y")]
    if search:
        df_hist = df_hist[df_hist.apply(lambda r:
            search.lower() in str(r["NO_DELIVERY"]).lower() or
            search.lower() in str(r.get("NO_PO", "")).lower() or
            search.lower() in str(r.get("CUSTOMER", "")).lower() or
            search.lower() in str(r.get("PART_NO", "")).lower(), axis=1)]

    st.dataframe(
        df_hist[["NO_DELIVERY", "NO_PO", "CUSTOMER", "PART_NO", "PART_NAME", "QTY_DELIVERY", "DATE_DELIVERY", "PREPARED_BY", "STATUS"]],
        use_container_width=True
    )
else:
    st.info("Belum ada data pengiriman.")
