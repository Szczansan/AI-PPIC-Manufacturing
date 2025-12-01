import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime
from fpdf import FPDF
import os
from components.navbar import show_navbar

# --- PAGE CONFIG ---
st.set_page_config(page_title="Material Out | Production", layout="wide", page_icon="📤")

# -----------------------------------------------------------------------------
# CUSTOM CSS (MODERN DARK THEME)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header Card Style */
    .header-container {
        background: linear-gradient(135deg, #1e293b, #334155);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        margin-bottom: 25px;
        display: flex;
        align-items: center;
        gap: 20px;
    }
    .header-icon {
        font-size: 40px;
        background: rgba(255,255,255,0.1);
        padding: 12px;
        border-radius: 12px;
    }
    .header-text h1 {
        margin: 0;
        font-size: 24px;
        font-weight: 700;
        color: #ffffff;
    }
    .header-text p {
        margin: 5px 0 0 0;
        font-size: 14px;
        color: #94a3b8;
    }

    /* Form Section Dividers */
    .form-section-title {
        color: #38bdf8; /* Light Blue */
        font-size: 16px;
        font-weight: 600;
        margin-top: 15px;
        margin-bottom: 10px;
        border-bottom: 1px solid rgba(56, 189, 248, 0.3);
        padding-bottom: 5px;
    }

    /* Input Fields Styling (Dark Mode) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
    }
    
    /* Submit Button */
    .stButton > button {
        background: linear-gradient(90deg, #3b82f6, #2563eb);
        color: white;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        border-radius: 8px;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #2563eb, #1d4ed8);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.4);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# --- CONNECT SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("⚠️ Koneksi database gagal. Cek Secrets Supabase.")
    st.stop()

# --- NAVBAR ---
show_navbar()

# --- HEADER SECTION ---
st.markdown("""
<div class="header-container">
    <div class="header-icon">📤</div>
    <div class="header-text">
        <h1>Material Out Form</h1>
        <p>Pencatatan material keluar dari Warehouse ke Line Produksi (Injection).</p>
    </div>
</div>
""", unsafe_allow_html=True)

# --- AMBIL DATA REFERENSI ---
try:
    response = supabase.table("List_Material").select("*").execute()
    df_ref = pd.DataFrame(response.data)
except:
    df_ref = pd.DataFrame()

# Helper list
if not df_ref.empty:
    list_type = sorted(df_ref["TYPE"].dropna().unique().tolist())
    list_grade = sorted(df_ref["GRADE"].dropna().unique().tolist())
    list_color = sorted(df_ref["COLOR"].dropna().unique().tolist())
else:
    list_type, list_grade, list_color = [], [], []

# --- MAIN FORM ---
with st.container():
    with st.form("out_form", clear_on_submit=False):
        
        # Section 1
        st.markdown('<div class="form-section-title">📦 1. Identitas Material</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            in_type = st.selectbox("Type Material", list_type) if list_type else st.text_input("Type Material")
        with c2:
            in_grade = st.selectbox("Grade Material", list_grade) if list_grade else st.text_input("Grade Material")
        with c3:
            in_color = st.selectbox("Color Material", list_color) if list_color else st.text_input("Color Material")

        # Section 2
        st.markdown('<div class="form-section-title">⚖️ 2. Kuantitas & Traceability</div>', unsafe_allow_html=True)
        c4, c5, c6 = st.columns(3)
        with c4:
            in_qty = st.number_input("Qty Out", min_value=0.1, step=0.1, format="%.2f", help="Jumlah material yang dikeluarkan")
        with c5:
            in_uom = st.selectbox("Satuan (UOM)", ["KG", "SAK", "PCS", "LITER", "UNIT"])
        with c6:
            in_lot = st.text_input("Lot Number / Batch", placeholder="Scan Barcode disini...")

        # Section 3
        st.markdown('<div class="form-section-title">🏭 3. Tujuan Produksi</div>', unsafe_allow_html=True)
        c7, c8, c9 = st.columns(3)
        with c7:
            in_line = st.selectbox("Line Production", ["MC 250T", "MC 450T", "MC 600T", "MC 850T(1)", "MC 850T(2)", "MC 1500T"])
        with c8:
            in_shift = st.selectbox("Shift", ["1", "2", "3"])
        with c9:
            in_spk = st.text_input("No SPK / WO", placeholder="Contoh: WO-2025-001")

        # Section 4
        st.markdown('<div class="form-section-title">🕒 4. Waktu & PIC</div>', unsafe_allow_html=True)
        c10, c11, c12 = st.columns(3)
        with c10:
            in_date = st.date_input("Tanggal", value=datetime.now())
        with c11:
            in_time = st.time_input("Jam", value=datetime.now())
        with c12:
            in_pic = st.text_input("PIC Material", placeholder="Nama Checker/Admin")

        st.markdown("---")
        submit = st.form_submit_button("🚀 Submit Transaksi")

# --- LOGIC SUBMIT ---
if submit:
    # Validasi
    if not in_lot or not in_pic:
        st.error("⚠️ Transaksi Gagal: 'Lot Number' dan 'PIC Material' wajib diisi!")
        st.stop()

    # Payload
    data_payload = {
        "type_material": in_type,
        "grade_material": in_grade,
        "color_material": in_color,
        "qty": in_qty,
        "uom": in_uom,
        "date": str(in_date),
        "waktu": str(in_time),
        "lot_no": in_lot,
        "line_production": in_line,
        "shift": in_shift,
        "no_spk": in_spk,
        "pic_material": in_pic
    }

    # Insert DB
    try:
        supabase.table("material_out").insert(data_payload).execute()
        
        # Success UI
        st.success("✅ BERHASIL! Material Out tercatat di Database.")
        
        # PDF Generation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "BUKTI PENGELUARAN MATERIAL", ln=True, align="C")
        pdf.ln(5)
        
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        pdf.line(10, 30, 200, 30)
        pdf.ln(10)
        
        # Table-like content
        fields = [
            ("Material", f"{in_type} {in_grade}"),
            ("Color", in_color),
            ("Quantity", f"{in_qty} {in_uom}"),
            ("Lot Number", in_lot),
            ("Line / Shift", f"{in_line} / {in_shift}"),
            ("No SPK", in_spk),
            ("PIC", in_pic)
        ]
        
        pdf.set_font("Arial", size=12)
        for label, value in fields:
            pdf.cell(40, 8, label, 0, 0)
            pdf.cell(5, 8, ":", 0, 0)
            pdf.cell(0, 8, value, 0, 1)
            
        # File output
        pdf_filename = f"MaterialOut_{in_lot}_{datetime.now().strftime('%H%M%S')}.pdf"
        pdf.output(pdf_filename)
        
        with open(pdf_filename, "rb") as f:
            st.download_button(
                label="📄 Download Bukti (PDF)",
                data=f,
                file_name=pdf_filename,
                mime="application/pdf"
            )
            
        # Optional: remove file after read to save space (uncomment if needed)
        # os.remove(pdf_filename)

    except Exception as e:
        st.error(f"❌ Terjadi kesalahan sistem: {e}")