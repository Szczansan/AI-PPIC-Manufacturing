from supabase_client import get_supabase
import streamlit as st
from datetime import date, datetime

from components.navbar import show_navbar

# Initialize Supabase client
supabase = get_supabase()

def insert_material(data: dict):
    try:
        response = supabase.table("material_in").insert(data).execute()
        return response
    except Exception as e:
        return {"error": str(e)}

def main():
    # Setup Page Config (Optional, agar lebih rapi)
    st.set_page_config(page_title="Incoming Material", page_icon="📦", layout="centered")
    
    show_navbar()

    # --- CUSTOM CSS UNTUK MODERN UI ---
    st.markdown("""
    <style>
        /* Background & Main Font */
        .stApp {
            background-color: #0f172a;
            color: #f8fafc;
            font-family: 'Inter', sans-serif;
        }
        
        /* Input Fields Styling */
        .stTextInput > div > div > input, 
        .stSelectbox > div > div > div, 
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input,
        .stTimeInput > div > div > input {
            background-color: #1e293b; 
            color: #e2e8f0; 
            border: 1px solid #334155; 
            border-radius: 8px;
        }
        
        /* Focus State */
        input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 1px #3b82f6 !important;
        }

        /* Buttons */
        .stButton > button {
            background: linear-gradient(90deg, #2563eb, #3b82f6);
            color: white;
            border: none;
            padding: 0.6rem 1rem;
            border-radius: 8px;
            font-weight: 600;
            width: 100%;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background: linear-gradient(90deg, #1d4ed8, #2563eb);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
            transform: translateY(-1px);
        }

        /* Headers */
        h1, h2, h3 {
            color: #f1f5f9 !important;
        }
        
        /* Container Card Look */
        div[data-testid="stForm"] {
            background-color: #1e293b;
            padding: 2rem;
            border-radius: 16px;
            border: 1px solid #334155;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    st.title("📦 Incoming Material")
    st.caption("Form pencatatan material masuk ke warehouse produksi.")
    
    # --- DATA FETCHING ---
    # Mengambil data hanya sekali dan fix bug duplicate assignment
    try:
        material_data = supabase.table("List_Material").select("TYPE, GRADE, COLOR").execute().data
    except Exception:
        material_data = []

    type_options = sorted(list({item["TYPE"] for item in material_data})) if material_data else []
    grade_options = sorted(list({item["GRADE"] for item in material_data})) if material_data else []
    color_options = sorted(list({item["COLOR"] for item in material_data})) if material_data else []

    # --- FORM UI ---
    with st.form("incoming_form", clear_on_submit=False):
        
        # SECTION 1: SPESIFIKASI MATERIAL
        st.markdown("### 🛠️ Spesifikasi Material")
        col1, col2, col3 = st.columns(3)
        with col1:
            type_material = st.selectbox("Type Material", type_options)
        with col2:
            grade_material = st.selectbox("Grade Material", grade_options)
        with col3:
            color_material = st.selectbox("Color Material", color_options)

        # SECTION 2: KUANTITAS
        st.markdown("### ⚖️ Kuantitas")
        c_qty, c_uom = st.columns([2, 1])
        with c_qty:
            qty = st.number_input("Quantity", min_value=0.0, step=0.1, format="%.2f")
        with c_uom:
            uom = st.selectbox("UOM", ["KG", "G", "BATCH", "PCS"])

        st.divider()

        # SECTION 3: LOGISTIK & DOKUMEN
        st.markdown("### 🚛 Logistik & Dokumen")
        
        # Row 1 Logistik
        l_col1, l_col2 = st.columns(2)
        with l_col1:
            supplier_name = st.text_input("Supplier Name", placeholder="PT. Contoh Supplier")
            no_do = st.text_input("No. Delivery Order (DO)")
        with l_col2:
            po_number = st.text_input("PO Number")
            lot_no = st.text_input("Lot Number")

        # Row 2 Waktu & PIC
        l_col3, l_col4, l_col5 = st.columns(3)
        with l_col3:
            tanggal = st.date_input("Tanggal Terima", value=date.today())
        with l_col4:
            # Menggunakan datetime.now().time() agar defaultnya jam sekarang
            waktu = st.time_input("Waktu Terima", value=datetime.now().time())
        with l_col5:
            prepared_by = st.text_input("Diterima Oleh (PIC)")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- SUBMIT BUTTON ---
        submitted = st.form_submit_button("💾 Simpan Data Material")

        if submitted:
            if not type_material or not supplier_name:
                 st.warning("⚠️ Mohon lengkapi minimal Type Material dan Supplier Name.")
            else:
                with st.spinner("Menyimpan ke database..."):
                    data = {
                        "type_material": type_material,
                        "grade_material": grade_material,
                        "color_material": color_material,
                        "qty": qty,
                        "uom": uom,
                        "date": str(tanggal),
                        "waktu": str(waktu),
                        "supplier_name": supplier_name,
                        "no_do": no_do,
                        "po_number": po_number,
                        "lot_no": lot_no,
                        "prepared_by": prepared_by,
                    }

                    result = insert_material(data)

                    if "error" in result:
                        st.error(f"❌ Gagal menyimpan: {result['error']}")
                    else:
                        st.success("✅ Data berhasil disimpan ke Supabase!")
                        # Opsional: st.rerun() jika ingin mereset form total

if __name__ == "__main__":
    main()