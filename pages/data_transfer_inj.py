import streamlit as st
from supabase import create_client
import datetime
from datetime import timedelta
from components.navbar import show_navbar 

# ===================== INIT SUPABASE ===================== #
# Asumsi: Kamu sudah memiliki st.secrets di lingkungan Streamlit
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# ===================== NAVBAR ===================== #
show_navbar()

# ===================== PAGE HEADER ===================== #
st.markdown("""
<div style="background: linear-gradient(90deg,#0f172a,#1e293b);
padding: 12px 16px; border-radius:8px; color:#fff;">
    <h3 style="margin:0;">📦 Transfer ke Warehouse</h3>
    <p style="margin:0;font-size:13px;color:#94a3b8;">
        Catat barang hasil produksi dari Injection ke gudang (Warehouse).
    </p>
</div>
""", unsafe_allow_html=True)
st.write("")

# ===================== HELPER FUNCTIONS ===================== #
@st.cache_data(ttl=60)
def get_all_parts():
    """Ambil daftar part dari tabel MASTER (part_no, PART_NAME)."""
    try:
        # --- FIX AKHIR: Menggunakan nama kolom persis dari DB Supabase ---
        # part_no (lowercase), PART_NAME (uppercase)
        res = supabase.table("MASTER").select("part_no, PART_NAME").execute() 
        
        data = res.data
        
        processed_data = []
        for item in data:
            # FIX: Ambil kunci sesuai nama DB, lalu ubah ke PART_NO dan PART_NAME
            part_no = item.get("part_no") 
            part_name = item.get("PART_NAME") 
            
            if part_no and part_name:
                processed_data.append({
                    "PART_NO": part_no,
                    "PART_NAME": part_name
                })
        
        return processed_data
        
    except Exception as e:
        print(f"Error fetching parts from MASTER: {e}")
        return []

@st.cache_data(ttl=60)
def get_unique_forecast_months():
    """Ambil bulan unik (YYYY-MM) dari kolom delivery_date di tabel 'forcast'."""
    try:
        # Kita pakai nama tabel yang sudah dikonfirmasi (forcast)
        res = supabase.table("forcast").select("delivery_date").execute()
        
        months = set()
        for item in res.data:
            date_str = item.get("delivery_date")
            if date_str:
                # Ambil hanya YYYY-MM dari string tanggal (misal: "2025-12-01T...")
                months.add(date_str[:7]) 
                
        # Urutkan dari yang terbaru ke yang terlama
        return sorted(list(months), reverse=True)
        
    except Exception as e:
        print(f"ERROR fetching forecast dates: {e}")
        # Kembalikan list kosong jika gagal
        return []

def get_transfer_data(selected_month=None):
    """Ambil data transfer warehouse berdasarkan bulan"""
    try:
        if selected_month is None:
            selected_month = datetime.datetime.now().strftime('%Y-%m')
        
        start_date = f"{selected_month}-01"
        # Menghitung tanggal akhir bulan
        next_month = (datetime.datetime.strptime(selected_month + '-01', '%Y-%m-%d') + timedelta(days=32)).replace(day=1)
        end_date = (next_month - timedelta(days=1)).strftime('%Y-%m-%d')
        
        res = (
            supabase.table("Data_Transfer")
            .select("*")
            .gte("DATE", start_date)
            .lte("DATE", end_date)
            .order("DATE", desc=True)
            .execute()
        )
        return res.data
    except Exception:
        return []

def get_available_months():
    """Generate list of available months from Data_Transfer"""
    try:
        res = supabase.table("Data_Transfer").select("DATE").execute()
        months = set()
        for item in res.data:
            if item["DATE"]:
                months.add(item["DATE"][:7])  # Ambil YYYY-MM
        current_month = datetime.datetime.now().strftime("%Y-%m")
        months.add(current_month)
        return sorted(list(months), reverse=True)
    except:
        return [datetime.datetime.now().strftime("%Y-%m")]

# ===================== FORM INPUT ===================== #
all_parts = get_all_parts()
# Mengambil nama part unik
part_names = list(set([p["PART_NAME"] for p in all_parts]))
forecast_months = get_unique_forecast_months()

with st.form("transfer_form"):
    st.subheader("🚚 Form Input Transfer ke Warehouse")
    col1, col2 = st.columns(2)

    with col1:
        date = st.date_input("Tanggal", value=datetime.date.today())
        waktu = st.time_input("Waktu", value=datetime.datetime.now().time())
        selected_name = st.selectbox(
            "Pilih Nama Part",
            options=[""] + part_names,
            placeholder="Pilih nama part...",
            index=0
        )

    with col2:
        quantity = st.number_input("Quantity (pcs)", min_value=0)
        
        # --- INPUT BARU: TANGGAL FORECAST ---
        selected_forecast_month = st.selectbox(
            "Tanggal Forecast (Bulan/Tahun Part diproduksi)",
            options=forecast_months,
            index=0 if forecast_months else 0 # Pilih index 0 jika ada, jika tidak, index 0
        )
        # ------------------------------------

    # Auto detect PART_NO
    PART_NO = ""
    if selected_name:
        # Mencari PART_NO dari PART_NAME
        matching_parts = [p for p in all_parts if p["PART_NAME"] == selected_name]
        if matching_parts:
            PART_NO = matching_parts[0]["PART_NO"]
            st.text_input("Part Number", value=PART_NO, disabled=True)
        else:
            st.error("❌ Tidak ada PART_NO yang cocok untuk part ini.")
    
    # Check if PART_NO is found before showing the submit button logic
    if not PART_NO and selected_name:
        st.warning("Part Number tidak ditemukan di MASTER. Data tidak dapat disimpan.")

    submitted = st.form_submit_button("💾 Kirim Barang ke Warehouse", disabled=(not PART_NO and selected_name != ""))

# ===================== INSERT LOGIC ===================== #
if submitted:
    if not selected_name or not PART_NO:
        st.error("⚠️ Pilih nama part dan pastikan Part Number terdeteksi!")
    else:
        waktu_str = waktu.strftime("%H:%M:%S")
        
        # Tambahkan kolom Forecast_Month ke data
        data = {
            "DATE": date.isoformat(),
            "TIME": waktu_str,
            "PART_NO": PART_NO,
            "PART_NAME": selected_name,
            "QUANTITY": quantity,
            "FORECAST_MONTH": selected_forecast_month # <<< NILAI BARU DISIMPAN
        }

        try:
            # Asumsi: Tabel Data_Transfer sudah memiliki kolom FORECAST_MONTH (tipe TEXT/VARCHAR)
            response = supabase.table("Data_Transfer").insert(data).execute()
            if response.data:
                st.success("✅ Data transfer berhasil disimpan ke Warehouse!")
                # Membersihkan cache agar daftar part dan data transfer terbaru terambil
                st.cache_data.clear() 
            else:
                st.error(f"❌ Gagal menyimpan data! Error: {response.error}")
        except Exception as e:
            st.error(f"❌ Error: {e}")

# ===================== DISPLAY DATA ===================== #
st.markdown("---")
st.subheader("📋 Data Transfer Terkini")

available_months = get_available_months()
selected_month = st.selectbox(
    "Pilih Bulan",
    options=available_months,
    index=0
)

st.write(f"Menampilkan data untuk bulan: **{selected_month}**")

transfer_data = get_transfer_data(selected_month)

if transfer_data:
    display_data = []
    for item in transfer_data:
        tanggal = item.get("DATE", "")
        waktu = item.get("TIME", "")
        part_no = item.get("PART_NO", "")
        part_name = item.get("PART_NAME", "")
        qty = item.get("QUANTITY", 0)
        forecast_month_display = item.get("FORECAST_MONTH", "N/A") # <<< MENAMPILKAN NILAI BARU

        display_data.append({
            "Tanggal": tanggal,
            "Waktu": waktu,
            "Part Number": part_no,
            "Nama Part": part_name,
            "Quantity": qty,
            "Forecast Month": forecast_month_display # Menambahkan kolom display
        })

    st.dataframe(display_data, use_container_width=True)

    total_qty = sum([d["Quantity"] for d in display_data])
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Barang Dikirim", total_qty)
    with col2:
        st.metric("Jumlah Record", len(display_data))
else:
    st.info("ℹ️ Belum ada data transfer untuk bulan ini.")