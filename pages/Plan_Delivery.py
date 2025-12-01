import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from components.navbar import show_navbar # Navbar

# --- PAGE CONFIG ---
st.set_page_config(page_title="🚚 Plan Delivery", layout="wide")

# --- CONNECT SUPABASE ---
url = st.secrets.get("SUPABASE_URL", "URL_NOT_FOUND")
key = st.secrets.get("SUPABASE_KEY", "KEY_NOT_FOUND")
supabase = create_client(url, key)

# --- NAVBAR (Diaktifkan) ---
show_navbar()

# Inisialisasi state untuk form multi-input (Data Editor)
if 'delivery_items' not in st.session_state:
    st.session_state['delivery_items'] = pd.DataFrame({
        'PART_NAME': [''],
        'FORECAST_DATE': [''],
        'QTY_KIRIM': [0],
        'MODEL': [''] 
    })

# --- FUNGSI UTILITY ---

@st.cache_data(ttl=3600)
def load_part_options():
    """Mengambil daftar PART_NO, PART_NAME, dan Tanggal Acuan dari tabel forcast."""
    try:
        # Ambil semua data yang diperlukan dari tabel forcast
        # Asumsi kolom: part_no, part_name, delivery_date (huruf kecil)
        res_fc = supabase.table("forcast").select("part_no, part_name, delivery_date").execute()
        df_fc = pd.DataFrame(res_fc.data)
        
        # 1. Pemetaan Part Name ke Part No
        df_options = df_fc.rename(columns={'part_no': 'PART_NO', 'part_name': 'PART_NAME'})
        part_map = df_options[['PART_NAME', 'PART_NO']].drop_duplicates(subset=['PART_NAME'], keep='first')
        part_map = part_map.set_index('PART_NAME')['PART_NO'].to_dict()

        # Opsi yang akan ditampilkan (PART_NAME)
        part_name_list = sorted(part_map.keys())

        # 2. Opsi Tanggal (diambil dari delivery_date di forcast)
        if 'delivery_date' in df_fc.columns:
            forecast_dates = df_fc['delivery_date'].unique().tolist()
            # Pastikan format tanggal YYYY-MM-DD
            valid_dates = [str(d).split('T')[0] for d in forecast_dates if d and isinstance(d, str)]
        else:
            valid_dates = []

        return part_map, part_name_list, valid_dates

    except Exception as e:
        st.error(f"Gagal memuat opsi Part atau Tanggal dari database. Pastikan kolom 'part_no', 'part_name', dan 'delivery_date' ada di tabel 'forcast' (huruf kecil). Detail: {e}")
        return {}, [], []

def generate_do_number(delivery_date):
    """
    Menghasilkan Nomor DO unik (YYmm-XXXX) dengan mengincrement counter di Delivery_Counter.
    """
    today_str = delivery_date.strftime("%Y-%m-%d")
    prefix = delivery_date.strftime("%y%m")

    try:
        # 1. Coba ambil counter hari ini
        res = supabase.table("Delivery_Counter").select("last_sequence, id").eq("current_date", today_str).execute()
        
        if res.data:
            # Update sequence
            current_sequence = res.data[0]['last_sequence']
            entry_id = res.data[0]['id']
            new_sequence = current_sequence + 1
            supabase.table("Delivery_Counter").update({"last_sequence": new_sequence}).eq("id", entry_id).execute()
        else:
            # Insert sequence baru
            new_sequence = 1
            supabase.table("Delivery_Counter").insert({"current_date": today_str, "last_sequence": new_sequence}).execute()
            
    except Exception as e:
        # Ini akan menangkap error RLS atau 10054
        raise Exception(f"Gagal memproses counter DO: {e}")
            
    do_number = f"{prefix}-{new_sequence:04d}"
    return do_number

def insert_fg_out(do_number, customer_name, delivery_date, part_name, part_no, forecast_date, qty_kirim, model=""):
    """
    Melakukan INSERT ke tabel fg_out (mencatat transaksi keluar).
    """
    # Kolom forecast_month diasumsikan sudah ditambahkan di Supabase (sesuai instruksi terakhir)
    data = {
        "part_name": part_name,
        "part_no": part_no,
        "qty_out": qty_kirim,
        "date": delivery_date.strftime("%Y-%m-%d"),
        "no_do": do_number,
        "customer_name": customer_name,
        "model": model,
        # Mengirim data ke kolom 'forecast_month' di fg_out
        "forecast_month": forecast_date 
    }
    
    supabase.table("fg_out").insert(data).execute()
    return True

# --- HEADER SECTION ---
st.markdown("""
<div style="background: linear-gradient(90deg,#0f172a,#1e293b);
padding: 12px 16px; border-radius:8px; color:#fff;">
    <h3 style="margin:0;">🚚 Plan Delivery: Catat Transaksi Keluar</h3>
    <p style="margin:0;font-size:13px;color:#94a3b8;">
        Input data pengiriman untuk mencatat transaksi **keluar (fg_out)**.
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")


# --- LOAD OPTIONS ---
part_map, part_name_list, forecast_date_options = load_part_options()
forecast_date_options.sort(reverse=True)


# --- START FORM ---
with st.form("delivery_plan_form", clear_on_submit=True):
    
    st.subheader("Detail Transaksi (Header)")
    
    # 1. Header Inputs
    col1, col2 = st.columns(2)
    with col1:
        delivery_date = st.date_input("🗓️ Tanggal Pengiriman", value=date.today(), help="Tanggal pengiriman aktual barang.")
    with col2:
        customer_name = st.text_input("👤 Nama Customer", help="Nama perusahaan atau perorangan penerima barang.")
        
    st.markdown("---")
    st.subheader("Item Pengiriman (Detail)")
    st.info("Tambahkan satu atau lebih Part yang akan dikirim.")
    
    # 2. Multi-Input Form using Data Editor
    
    editor_cols = {
        'PART_NAME': st.column_config.SelectboxColumn(
            "Part Name",
            help="Pilih Part Name yang mudah diingat",
            options=part_name_list,
            required=True,
        ),
        # FORECAST_DATE digunakan sebagai referensi untuk transaksi keluar
        'FORECAST_DATE': st.column_config.SelectboxColumn(
            "Forecast Date Ref",
            help="Pilih Tanggal Forecast yang menjadi acuan stok ini",
            options=forecast_date_options,
            required=True,
        ),
        'QTY_KIRIM': st.column_config.NumberColumn(
            "Quantity Kirim",
            help="Jumlah QTY yang dikirim",
            min_value=1,
            required=True,
        ),
        'MODEL': st.column_config.TextColumn(
            "MODEL",
            help="Kolom Model (opsional)",
            default="",
        ),
    }

    # Data Editor untuk Multi-Input
    edited_data = st.data_editor(
        st.session_state['delivery_items'],
        column_config=editor_cols,
        num_rows="dynamic",
        use_container_width=True,
        key="delivery_editor"
    )

    st.markdown("---")
    submitted = st.form_submit_button("✅ Submit Delivery Plan & Catat Transaksi")

# --- FORM SUBMISSION LOGIC ---
if submitted:
    
    valid_deliveries = edited_data[(edited_data['QTY_KIRIM'] > 0) & (edited_data['PART_NAME'] != '')]
    
    if valid_deliveries.empty:
        st.warning("Mohon isi setidaknya satu Part dengan Quantity Kirim > 0.")
        st.stop()

    try:
        # 1. GENERATE NOMOR DO UNIK (Ini wajib sukses duluan)
        st.write("Generating DO Number...")
        do_number = generate_do_number(delivery_date)
        st.success(f"Nomor DO berhasil dibuat: **{do_number}**")
        
        # 2. LOOP UNTUK INSERT KE fg_out
        success_count = 0
        st.write("Mulai mencatat transaksi keluar (fg_out)...")
        
        for index, row in valid_deliveries.iterrows():
            part_name = row['PART_NAME']
            f_date_ref = row['FORECAST_DATE'] 
            qty = int(row['QTY_KIRIM'])
            model_val = row.get('MODEL', '') 

            # Konversi PART_NAME ke PART_NO
            part_no = part_map.get(part_name)
            
            if not part_no:
                st.error(f"🔴 Gagal: Tidak ditemukan Part No untuk Part Name **{part_name}**.")
                continue

            # INSERT TRANSAKSI KE fg_out
            if insert_fg_out(do_number, customer_name, delivery_date, part_name, part_no, f_date_ref, qty, model_val):
                st.info(f"🟢 Sukses mencatat kirim {qty} untuk Part **{part_name}** (DO: {do_number}).")
                success_count += 1
            else:
                st.error(f"🔴 Gagal mencatat transaksi Part {part_name}.")
                
        
        if success_count == len(valid_deliveries):
            st.balloons()
            # --- PENAMBAHAN KONFIRMASI YANG DIMINTA ---
            st.success(f"🎉 **Plan Pengiriman Berhasil Tersetting!** Total {success_count} item dicatat. DO: **{do_number}**")
            # --- AKHIR PENAMBAHAN ---

        # Reset state setelah submit
        st.session_state['delivery_items'] = pd.DataFrame({
            'PART_NAME': [''],
            'FORECAST_DATE': [''],
            'QTY_KIRIM': [0],
            'MODEL': ['']
        })
        st.rerun() 
        
    except Exception as e:
        st.error(f"❌ Transaksi Gagal Total: {e}")