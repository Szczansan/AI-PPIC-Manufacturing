import streamlit as st
import pandas as pd
from datetime import datetime, date
from calendar import monthrange
from supabase_client import get_supabase

# --- IMPORT NAVBAR ---
try:
    from components.navbar import show_navbar
except ImportError:
    st.error("Gagal import navbar. Pastikan folder 'components' dan file 'navbar.py' sudah benar posisinya.")

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="Warehouse to Finish Good", layout="centered")

# --- 2. TAMPILKAN NAVBAR ---
try:
    show_navbar()
except NameError:
    pass 

# --- 3. INIT CONNECTION ---
supabase = get_supabase()

# --- HELPER FUNCTIONS ---

def get_wip_parts():
    """Mengambil daftar unik Part Name dan Part No dari tabel wip_in."""
    try:
        response = supabase.table("wip_in").select("part_name, part_no").execute()
        data = response.data
        if not data: return {}
        return {item['part_name']: item['part_no'] for item in data}
    except Exception as e:
        st.error(f"Gagal mengambil data part: {e}")
        return {}

def get_transfer_history():
    """Mengambil 50 data transfer terakhir dari tabel fg_in."""
    try:
        # UPDATE: qty_out diganti jadi qty_in
        response = supabase.table("fg_in")\
            .select("date, part_name, qty_in, prepared_by")\
            .order("date", desc=True)\
            .limit(50)\
            .execute()
        return response.data
    except Exception as e:
        return []

# --- MAIN APP ---

def app():
    # --- CUSTOM HEADER STYLE (GLOW) ---
    st.markdown("""
        <style>
        .glow-header {
            text-align: center;
            font-size: 2.5em;
            font-weight: bold;
            color: #ffffff;
            text-shadow: 0 0 10px #ffffff, 0 0 20px #ffffff;
            margin-top: 20px; 
            margin-bottom: 20px;
        }
        /* Style untuk Time Input biar background biru gelap kayak di gambar */
        [data-testid="stTimeInput"] input {
            background-color: #1e3a8a !important; /* Biru gelap */
            color: white !important;
        }
        </style>
        <div class="glow-header">Form Transfer Warehouse to Finish Good</div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center; color: white; display:none;'>WAREHOUSE TO FINISH GOOD</h2>", unsafe_allow_html=True)

    st.markdown("""
        <script>
        const elements = window.parent.document.querySelectorAll('.glow-header');
        elements.forEach(el => el.innerHTML = 'WAREHOUSE TO FINISH GOOD');
        </script>
        <style>
        .glow-header { text-transform: uppercase; }
        </style>
        """, unsafe_allow_html=True)


    # --- MAIN FORM CONTAINER ---
    with st.container(border=True):
        
        # 1. Date & Time
        st.caption("Tanggal Transfer")
        tgl_transfer = st.date_input("Tanggal", value=date.today(), label_visibility="collapsed")
        
        st.write("") 
        
        # Waktu
        waktu_sekarang = datetime.now().time()
        st.time_input("Waktu", value=waktu_sekarang, label_visibility="collapsed")

        st.write("") 

        # 2. Prepared By
        st.caption("Prepared By (nama pengirim)")
        prepared_by = st.text_input("Prepared By", placeholder="Nama PIC...", label_visibility="collapsed")
        
        st.write("---")

        # 3. Dynamic Rows Logic
        part_map = get_wip_parts()
        list_part_names = list(part_map.keys())

        if 'n_rows' not in st.session_state:
            st.session_state.n_rows = 1

        c_btn1, c_btn2, _ = st.columns([0.3, 0.4, 0.3])
        with c_btn1:
            if st.button("ADD PART", use_container_width=True):
                if st.session_state.n_rows < 8:
                    st.session_state.n_rows += 1
        with c_btn2:
            if st.button("REMOVE LAST PART", use_container_width=True):
                if st.session_state.n_rows > 1:
                    st.session_state.n_rows -= 1

        st.write("") 

        input_data = [] 

        # 4. Loop Rows
        for i in range(st.session_state.n_rows):
            c_name, c_qty, c_code = st.columns([3, 1.2, 1.5])
            
            with c_name:
                if i == 0: st.caption("Part Name")
                selected_part_name = st.selectbox(
                    f"part_select_{i}", 
                    options=["-- kosong --"] + list_part_names,
                    key=f"part_name_{i}",
                    label_visibility="collapsed"
                )

            with c_qty:
                if i == 0: st.caption("Qty")
                qty_val = st.number_input(
                    f"qty_{i}", 
                    min_value=0, 
                    value=0, 
                    key=f"qty_{i}",
                    label_visibility="collapsed"
                )
            
            with c_code:
                auto_part_no = "-"
                if selected_part_name != "-- kosong --":
                    auto_part_no = part_map.get(selected_part_name, "-")
                
                if i == 0: st.caption("Part No")
                st.markdown(f"<div style='padding-top: 10px; color: grey; font-size: 0.9em;'>Part No: {auto_part_no}</div>", unsafe_allow_html=True)

            if selected_part_name != "-- kosong --" and qty_val > 0:
                input_data.append({
                    "part_name": selected_part_name,
                    "part_no": auto_part_no,
                    "qty": qty_val
                })

        st.write("")
        st.write("")

        # 5. Submit Button
        if st.button("Submit Transfer", type="primary"):
            if not prepared_by:
                st.error("Nama pengirim (Prepared By) harus diisi!")
            elif not input_data:
                st.warning("Pilih minimal satu part dan isi Qty-nya.")
            else:
                try:
                    payload = []
                    
                    for item in input_data:
                        entry = {
                            "date": tgl_transfer.isoformat(), 
                            "prepared_by": prepared_by,
                            "part_name": item['part_name'],
                            "part_no": item['part_no'],
                            # UPDATE: Masuk ke kolom qty_in di tabel fg_in
                            "qty_in": item['qty'] 
                        }
                        payload.append(entry)

                    supabase.table("fg_in").insert(payload).execute()
                    
                    st.success("✅ Transfer Berhasil!")
                    st.session_state.n_rows = 1 
                    st.rerun()

                except Exception as e:
                    st.error(f"Database Error: {e}")

    # --- SUMMARY & LATEST ACTIVITY SECTION ---
    st.write("")
    st.write("")
    
    c_icon, c_title = st.columns([0.5, 5])
    with c_icon:
        st.markdown("📊", unsafe_allow_html=True)
    with c_title:
        st.subheader("Summary & Latest Activity")

    # --- LOGIC SUMMARY ---
    # Inisialisasi default variable biar gak error UnboundLocalError
    qty_today, trx_today = 0, 0
    qty_month, trx_month = 0, 0
    
    today_str = str(date.today())
    curr_year = date.today().year
    curr_month = date.today().month
    first_day = f"{curr_year}-{curr_month:02d}-01"
    last_day = f"{curr_year}-{curr_month:02d}-{monthrange(curr_year, curr_month)[1]}"

    try:
        # Today Summary (Ganti qty_out -> qty_in)
        resp_today = supabase.table("fg_in").select("qty_in").eq("date", today_str).execute()
        data_today = resp_today.data if resp_today.data else []
        qty_today = sum([item['qty_in'] for item in data_today])
        trx_today = len(data_today)

        # Month Summary (Ganti qty_out -> qty_in)
        resp_month = supabase.table("fg_in").select("qty_in, date").gte("date", first_day).lte("date", last_day).execute()
        data_month = resp_month.data if resp_month.data else []
        qty_month = sum([item['qty_in'] for item in data_month])
        trx_month = len(data_month)

    except Exception as e:
        st.error(f"Gagal hitung summary: {e}")

    # CSS Cards
    st.markdown("""
        <style>
        .summary-container {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-bottom: 20px;
        }
        .stat-card {
            flex: 1;
            min-width: 200px;
            padding: 20px;
            border-radius: 10px;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card-blue { background: linear-gradient(135deg, #3b82f6, #06b6d4); }
        .card-purple { background: linear-gradient(135deg, #8b5cf6, #3b82f6); }
        .card-orange { background: linear-gradient(135deg, #f97316, #fca5a5); }
        .card-teal { background: linear-gradient(135deg, #14b8a6, #3b82f6); }
        
        .stat-title { font-size: 0.85rem; opacity: 0.9; margin-bottom: 5px; }
        .stat-value { font-size: 2rem; font-weight: bold; margin-bottom: 5px; }
        .stat-sub { font-size: 0.75rem; opacity: 0.8; }
        </style>
    """, unsafe_allow_html=True)

    # Render HTML Cards
    st.markdown(f"""
        <div class="summary-container">
            <div class="stat-card card-blue">
                <div class="stat-title">Qty Today</div>
                <div class="stat-value">{qty_today}</div>
                <div class="stat-sub">Transactions: {trx_today}</div>
            </div>
            <div class="stat-card card-purple">
                <div class="stat-title">Transactions Today</div>
                <div class="stat-value">{trx_today}</div>
                <div class="stat-sub">Date: {today_str}</div>
            </div>
            <div class="stat-card card-orange">
                <div class="stat-title">Qty This Month</div>
                <div class="stat-value">{qty_month}</div>
                <div class="stat-sub">Transactions: {trx_month}</div>
            </div>
            <div class="stat-card card-teal">
                <div class="stat-title">Transactions This Month</div>
                <div class="stat-value">{trx_month}</div>
                <div class="stat-sub">Range: {first_day} → {last_day}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- HISTORY TABLE ---
    history_data = get_transfer_history()
    
    if history_data:
        df = pd.DataFrame(history_data)
        try:
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df = df.rename(columns={
                'date': 'Tanggal',
                'part_name': 'Part Name',
                'qty_in': 'Qty In',  # Rename display juga
                'prepared_by': 'PIC'
            })
            df_display = df[['Tanggal', 'Part Name', 'Qty In', 'PIC']]
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error display table: {e}")

if __name__ == "__main__":
    app()