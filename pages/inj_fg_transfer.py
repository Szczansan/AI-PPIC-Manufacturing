import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date, timedelta
from fpdf import FPDF
import time
from components.navbar import show_navbar 

# ===================== INIT SUPABASE ===================== #
# Gunakan st.secrets.get untuk keamanan
url = st.secrets.get("SUPABASE_URL", "URL_NOT_FOUND") 
key = st.secrets.get("SUPABASE_KEY", "KEY_NOT_FOUND")
supabase = create_client(url, key)

# --- NAVBAR ---
show_navbar()

# --- HEADER SECTION ---
st.markdown("""
<div style="background: linear-gradient(90deg,#0f172a,#1e293b);
padding: 12px 16px; border-radius:8px; color:#fff;">
    <h3 style="margin:0;">➡️ Transfer ke Finish Good (Injection)</h3>
    <p style="margin:0;font-size:13px;color:#94a3b8;">
        Input data barang masuk untuk mencatat transaksi di tabel **fg_in**.
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")

# -------------------------
# Helper functions
# -------------------------
def generate_ifg_no():
    """Generate IFG-YYYY-XXXX menggunakan timestamp unik."""
    year = datetime.now().year
    suffix = int(time.time()) % 10000
    return f"IFG-{year}-{suffix:04d}"

def create_pdf_bytes(header_info, parts_list):
    """Buat PDF BON Transfer ke FG."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Header
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 8, "PT. SHIN SAM PLUS INDUSTRY", ln=True, align="C")
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 7, "BON TRANSFER TO FINISH GOOD", ln=True, align="C")
    pdf.ln(6)

    pdf.set_font("Arial", size=11)
    pdf.cell(100, 7, f"No BON: {header_info['NO_BON']}", ln=0)
    pdf.cell(0, 7, f"Tanggal: {header_info['DATE_TRANSFER'].strftime('%d-%b-%Y')}", ln=1)
    pdf.cell(0, 7, f"Prepared By: {header_info['PREPARED_BY']}", ln=1)
    # Gunakan Tanggal Forecast sebagai acuan dokumen
    pdf.cell(0, 7, f"Tgl Acuan Forecast: {header_info['FORECAST_MONTH']}", ln=1) 
    pdf.ln(6)

    # Table header
    pdf.set_font("Arial", "B", 11)
    pdf.cell(10, 8, "No", border=1, align="C")
    pdf.cell(40, 8, "Part No", border=1, align="C")
    pdf.cell(90, 8, "Part Name", border=1, align="C")
    pdf.cell(30, 8, "Qty", border=1, align="C")
    pdf.ln()

    # Isi tabel
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
    pdf.cell(0, 6, "Diterima oleh (Warehouse): ____________________", ln=1)
    pdf.cell(0, 6, "Tanda tangan: _________________________________", ln=1)

    s = pdf.output(dest="S")
    if isinstance(s, str):
        s = s.encode("latin-1")
    return s

def to_int_safe(x):
    """Konversi nilai ke integer secara aman."""
    try:
        return int(x)
    except Exception:
        return 0

# --- FUNGSI BARU: INSERT DATA KE fg_in ---
def insert_fg_in(part_name, part_no, qty_in, bon_number, transfer_date, forecast_month, model=""):
    """
    Melakukan INSERT ke tabel fg_in (model transaksional baru).
    """
    
    # PERBAIKAN V3: Ubah placeholder menjadi None jika belum dipilih
    if forecast_month == "-- Pilih Bulan Forecast --":
        forecast_month = None
    
    data = {
        "part_name": part_name,
        "part_no": part_no,
        "qty_in": qty_in,
        "date": transfer_date.strftime("%Y-%m-%d"), # Tanggal Transaksi
        "ref_dokumen": bon_number, # Nomor BON/Dokumen Referensi
        "forecast_month": forecast_month, # <<< Mengirim nilai ke kolom yang kita tambahkan
        "model": model, 
        "created_at": datetime.now().isoformat()
    }
    # Target tabel baru: fg_in
    supabase.table("fg_in").insert(data).execute()
    return True
# ------------------------------------------

# =========================================================================
# === SESSION STATE HANDLERS (Callback functions) ===
# =========================================================================
if "n_parts" not in st.session_state:
    st.session_state.n_parts = 1

def add_part():
    if st.session_state.n_parts < 8:
        st.session_state.n_parts += 1

def remove_part():
    if st.session_state.n_parts > 1:
        st.session_state.n_parts -= 1
# =========================================================================


# --- HELPER 1: LOAD PART DARI MASTER (FIXED V4) ---
@st.cache_data(ttl=60)
def get_all_parts():
    """Ambil daftar part dari tabel MASTER (memastikan case-insensitive)."""
    try:
        # Mengambil SEMUA kolom dari MASTER untuk mengatasi case sensitivity
        res = supabase.table("MASTER").select("*").execute() 
        df_master = pd.DataFrame(res.data)
        
        if df_master.empty:
            return []

        # Mencari nama kolom yang benar secara case-insensitive
        part_no_col = next((col for col in df_master.columns if col.lower() == 'part_no'), None)
        part_name_col = next((col for col in df_master.columns if col.lower() == 'part_name'), None)
        
        if not part_no_col or not part_name_col:
            # Jika kolom tidak ditemukan, tampilkan daftar kolom yang ada
            print(f"ERROR: Kolom PART_NO atau PART_NAME tidak ditemukan di MASTER. Kolom yang ada: {list(df_master.columns)}")
            return []

        # Proses data
        processed_data = []
        for index, row in df_master.iterrows():
            part_no = row.get(part_no_col)
            part_name = row.get(part_name_col)
            
            # Kita akan menggunakan PART_NAME sebagai opsi yang dipilih user
            if part_no and part_name:
                processed_data.append({
                    "PART_NO": part_no, 
                    "PART_NAME": part_name
                })
        
        return processed_data
        
    except Exception as e:
        print(f"Error fetching parts from MASTER: {e}")
        return []

# --- HELPER 2: LOAD TANGGAL FORECAST UNIK BARU (FINAL FIX FORMAT) ---
@st.cache_data(ttl=60)
def get_unique_full_forecast_dates():
    """Ambil tanggal penuh unik (YYYY-MM-DD) dari kolom delivery_date di tabel 'forcast', 
        tapi tampilkan sebagai YYYY-MM."""
    try:
        # Perlu dipastikan kolom ini ada di tabel forcast
        res = supabase.table("forcast").select("delivery_date").execute()
        
        date_map = {}
        for item in res.data:
            date_str = item.get("delivery_date")
            if date_str:
                full_date = date_str[:10] # Ambil YYYY-MM-DD
                display_month = full_date[:7] # Ambil YYYY-MM untuk tampilan
                date_map[full_date] = display_month 
                
        unique_months = sorted(list(set(date_map.values())), reverse=True)
        return unique_months
        
    except Exception as e:
        print(f"ERROR fetching forecast dates: {e}")
        return []


# -------------------------
# Load List_Part
# -------------------------
df_parts = pd.DataFrame(get_all_parts())

if df_parts.empty:
    st.warning("Data Part dari MASTER kosong. Isi daftar part dulu di Supabase.")
    st.stop()

# Mapping Part Name - Part No
has_part_no = "PART_NO" in df_parts.columns
df_parts["DISPLAY"] = df_parts.apply(lambda r: f"{r.get('PART_NAME','')} | {r.get('PART_NO','')}", axis=1)
display_list = df_parts["DISPLAY"].tolist()
part_map = {row["DISPLAY"]: (row.get("PART_NAME", ""), row.get("PART_NO", "")) for _, row in df_parts.iterrows()}


# -------------------------
# Form Input
# -------------------------
st.markdown("### 📋 Form Transfer to FG (Injection)")

# Load data tanggal forecast unik
forecast_months_list = get_unique_full_forecast_dates()

# --- INPUT DI LUAR FORM (UNTUK MENGATASI ISSUE SCOPE) ---
st.markdown("#### Detail Header Transfer")
col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    prepared_by = st.text_input("Prepared By", "", key="prepared_by_input")
with col2:
    date_transfer = st.date_input("Tanggal Transfer", value=date.today(), key="date_transfer_input")
    
    # --- INPUT BARU: TANGGAL FORECAST UNIK (Hanya YYYY-MM) ---
    selected_forecast_month = st.selectbox(
        "Tanggal Forecast (Bulan/Tahun Acuan Pengiriman)",
        options=["-- Pilih Bulan Forecast --"] + forecast_months_list,
        key="forecast_date_sel"
    )
    # ----------------------------------------
    
with col3:
    note = st.text_input("Catatan (opsional)", "", key="note_input")


# --- START FORM ---
with st.form("transfer_form"):

    st.markdown("#### Pilih part dan qty (maks 8 baris). Gunakan tombol Add/Remove untuk menambah/menghapus baris.")
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        st.form_submit_button("➕ Add Part", on_click=add_part)
    with btn_col2:
        st.form_submit_button("➖ Remove Part", on_click=remove_part)

    part_rows = []
    for i in range(st.session_state.n_parts):
        st.markdown(f"**Part {i+1}**")
        c1, c2 = st.columns([4, 1])
        with c1:
            sel = st.selectbox(f"Pilih Part {i+1}", ["-- kosong --"] + display_list, key=f"part_sel_{i}")
            pname, pno = part_map.get(sel, ("", "")) if sel != "-- kosong --" else ("", "")
            st.caption(f"🧩 {pname}")
            if has_part_no:
                st.caption(f"📦 {pno}")
        with c2:
            qty = st.number_input(f"Qty {i+1}", min_value=0, step=1, key=f"qty_{i}")
        
        # Simpan PART_NO, PART_NAME, dan QTY untuk diproses
        part_rows.append({"PART_NAME": pname, "PART_NO": pno, "QTY": int(qty)})

    submit = st.form_submit_button("➡️ Transfer Barang ke FG")

# -------------------------
# Handle Submit
# -------------------------
if submit:
    # Ambil nilai dari session state karena input berada di luar form
    prepared_by = st.session_state.prepared_by_input
    date_transfer = st.session_state.date_transfer_input
    forecast_month_value = st.session_state.forecast_date_sel
    note_value = st.session_state.note_input 

    if forecast_month_value == "-- Pilih Bulan Forecast --":
        st.error("⚠️ Pilih Tanggal Forecast (Acuan Pengiriman) terlebih dahulu!")
        st.stop()
        
    filled = [r for r in part_rows if r["PART_NAME"] and r["QTY"] > 0]
    if len(filled) == 0:
        st.error("Minimal 1 part harus diisi dengan qty > 0.")
        st.stop()
    if not prepared_by:
        st.error("Field 'Prepared By' wajib diisi.")
        st.stop()

    no_bon = generate_ifg_no()
    
    try:
        # 1. Loop untuk INSERT ke fg_in
        st.write("Mulai mencatat transaksi ke fg_in...")
        success_count = 0
        
        for p in filled:
            part_name, part_no, q = p["PART_NAME"], p["PART_NO"], int(p["QTY"])

            # NEW LOGIC: INSERT KE TABEL TRANSAKSIONAL fg_in
            if insert_fg_in(part_name, part_no, q, no_bon, date_transfer, forecast_month_value, note_value):
                st.info(f"🟢 Sukses mencatat masuk {q} untuk Part **{part_name}** (BON: {no_bon}).")
                success_count += 1
            else:
                st.error(f"🔴 Gagal mencatat Part {part_name}.")

        st.success(f"✅ Transfer berhasil. BON: {no_bon} — {success_count} item telah dicatat ke fg_in.")

        # 2. Generate PDF BON
        parts_for_pdf = [(r["PART_NO"] or "-", r["PART_NAME"], r["QTY"]) for r in filled]
        pdf_bytes = create_pdf_bytes(
            {
                "NO_BON": no_bon, 
                "DATE_TRANSFER": date_transfer, 
                "PREPARED_BY": prepared_by,
                # Menggunakan Forecast Month sebagai referensi utama dokumen
                "FORECAST_MONTH": forecast_month_value 
            },
            parts_for_pdf
        )

        st.download_button(
            label="📄 Download BON Transfer (PDF)",
            data=pdf_bytes,
            file_name=f"{no_bon}.pdf",
            mime="application/pdf"
        )

        st.info("BON Transfer siap. Halaman akan direfresh.")
        st.rerun()

    except Exception as e:
        st.error(f"Gagal melakukan transfer: {e}")