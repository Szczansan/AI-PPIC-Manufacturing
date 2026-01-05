import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import datetime, date
from components.navbar import show_navbar 

# --- PAGE CONFIG ---
st.set_page_config(page_title="🚚 Plan Delivery", layout="wide", page_icon="🚚")

# --- CUSTOM CSS (FUTURISTIC UI) ---
st.markdown("""
<style>
    /* Card Container Style */
    .history-card {
        background-color: #0e1117;
        border: 1px solid #1f2937;
        border-left: 4px solid #00d4ff; /* Cyan Neon */
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0, 212, 255, 0.1);
        margin-bottom: 20px;
    }
    .history-header {
        font-family: 'Courier New', monospace;
        color: #00d4ff;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    .stDataFrame {
        border: 1px solid #374151;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONNECT SUPABASE ---
url = st.secrets.get("SUPABASE_URL", "")
key = st.secrets.get("SUPABASE_KEY", "")
supabase = create_client(url, key)

show_navbar()

# --- 1. LOAD OPTIONS & DATA ---
@st.cache_data(ttl=60)
def load_part_data():
    try:
        res = supabase.table("forecast_monthly").select("part_no, part_name, forecast_month").execute()
        if not res.data: return {}, [], []
        df = pd.DataFrame(res.data)
        
        # Logic Mapping Part Name -> Part No
        df['label_name'] = df['part_name'].fillna(df['part_no'])
        df_unique = df.drop_duplicates(subset=['label_name'])
        
        part_map = df_unique.set_index('label_name')['part_no'].to_dict()
        part_name_list = sorted(part_map.keys())
        valid_dates = sorted(list(set(df['forecast_month'].dropna().astype(str))))

        return part_map, part_name_list, valid_dates
    except Exception as e:
        return {}, [], []

def get_recent_transactions():
    """Mengambil 5 transaksi terakhir dari fg_out"""
    try:
        # Asumsi ada kolom 'created_at' default dari Supabase. 
        # Kalau error, ganti 'created_at' jadi 'id' atau 'date'.
        res = supabase.table("fg_out").select("*").order("created_at", desc=True).limit(5).execute()
        if res.data:
            return pd.DataFrame(res.data)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

# Load Data Awal
part_map, part_name_options, forecast_month_options = load_part_data()

# --- 2. STATE INITIALIZATION ---
if 'delivery_items' not in st.session_state:
    st.session_state['delivery_items'] = pd.DataFrame({
        'PART_NAME': [''], 'PART_NO': [''], 
        'FORECAST_MONTH': [''], 'QTY_KIRIM': [0], 'MODEL': [''] 
    })

# --- FUNGSI UTILITY ---
def generate_do_number(delivery_date):
    today_str = delivery_date.strftime("%Y-%m-%d")
    prefix = delivery_date.strftime("%y%m")
    try:
        res = supabase.table("Delivery_Counter").select("last_sequence, id").eq("current_date", today_str).execute()
        if res.data:
            new_seq = res.data[0]['last_sequence'] + 1
            supabase.table("Delivery_Counter").update({"last_sequence": new_seq}).eq("id", res.data[0]['id']).execute()
        else:
            new_seq = 1
            supabase.table("Delivery_Counter").insert({"current_date": today_str, "last_sequence": new_seq}).execute()
    except: pass
    return f"{prefix}-{new_seq:04d}"

def insert_fg_out(data_dict):
    supabase.table("fg_out").insert(data_dict).execute()

# --- HEADER SECTION ---
st.markdown("### 🚚 Plan Delivery")
col1, col2 = st.columns(2)
with col1:
    delivery_date = st.date_input("🗓️ Tanggal Surat Jalan", value=date.today())
with col2:
    customer_name = st.text_input("👤 Nama Customer")
st.markdown("---")

# --- 3. AUTO-FILL LOGIC & INPUT ---
df_current = st.session_state['delivery_items']
df_current['PART_NO'] = df_current['PART_NAME'].map(part_map).fillna('')

editor_config = {
    'PART_NAME': st.column_config.SelectboxColumn("Cari Part Name", options=part_name_options, required=True, width="medium"),
    'PART_NO': st.column_config.TextColumn("Part No (Auto)", disabled=True, width="medium"),
    'FORECAST_MONTH': st.column_config.SelectboxColumn("Forecast Month", options=forecast_month_options, required=True),
    'QTY_KIRIM': st.column_config.NumberColumn("Qty", min_value=1, required=True),
    'MODEL': st.column_config.TextColumn("Model")
}

edited_df = st.data_editor(df_current, column_config=editor_config, num_rows="dynamic", use_container_width=True, key="editor_delivery")

if not edited_df.equals(st.session_state['delivery_items']):
    st.session_state['delivery_items'] = edited_df
    st.rerun()

st.markdown("---")

# --- 4. SUBMIT BUTTON ---
if st.button("✅ Submit Delivery Plan", type="primary", use_container_width=True):
    valid_items = edited_df[(edited_df['PART_NAME'] != '') & (edited_df['QTY_KIRIM'] > 0)]
    
    if valid_items.empty:
        st.warning("Data kosong atau Qty masih 0.")
    elif not customer_name:
        st.warning("Nama Customer belum diisi.")
    else:
        try:
            with st.spinner("🚀 Mengirim Data ke Server..."):
                do_number = generate_do_number(delivery_date)
                count = 0
                for _, row in valid_items.iterrows():
                    payload = {
                        "part_name": row['PART_NAME'], "part_no": row['PART_NO'],
                        "forecast_month": row['FORECAST_MONTH'], "qty_out": int(row['QTY_KIRIM']),
                        "model": row['MODEL'], "customer_name": customer_name,
                        "no_do": do_number, "date": delivery_date.strftime("%Y-%m-%d")
                    }
                    insert_fg_out(payload)
                    count += 1
                
                st.success(f"SUCCESS! {count} Items Processed. DO: {do_number}")
                st.session_state['delivery_items'] = pd.DataFrame({'PART_NAME': [''], 'PART_NO': [''], 'FORECAST_MONTH': [''], 'QTY_KIRIM': [0], 'MODEL': ['']})
                # Rerun sebentar lagi biar tabel history di bawah update otomatis
                
        except Exception as e:
            st.error(f"System Error: {e}")

# --- 5. HISTORY SECTION (FUTURISTIC UI) ---
st.write("")
st.write("")

# Container Styling
st.markdown('<div class="history-card"><div class="history-header">📡 LIVE TRANSACTION FEED (LAST 5)</div>', unsafe_allow_html=True)

df_history = get_recent_transactions()

if not df_history.empty:
    # Pilih kolom yang mau ditampilin biar rapi
    # Pastikan nama kolom sesuai sama database lu
    cols_to_show = ['no_do', 'customer_name', 'part_name', 'qty_out', 'date']
    
    # Filter kolom yang ada aja (biar gak error kalau kolom beda dikit)
    final_cols = [c for c in cols_to_show if c in df_history.columns]
    df_show = df_history[final_cols]

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "no_do": st.column_config.TextColumn("Nomor DO", width="medium"),
            "customer_name": st.column_config.TextColumn("Customer", width="medium"),
            "part_name": st.column_config.TextColumn("Part Name", width="large"),
            "qty_out": st.column_config.NumberColumn(
                "Qty Out", 
                format="%d Pcs",
                help="Jumlah barang keluar"
            ),
            "date": st.column_config.DateColumn("Tgl Kirim", format="DD MMM YYYY")
        }
    )
else:
    st.info("Belum ada data transaksi tercatat hari ini.")

st.markdown('</div>', unsafe_allow_html=True)