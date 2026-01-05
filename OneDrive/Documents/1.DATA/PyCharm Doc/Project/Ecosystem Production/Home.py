import streamlit as st
import time
from supabase import create_client, Client
from app_utils import HIDE_NAV_CSS, show_sidebar_user  # <--- IMPORT DARI UTILS

# --- 1. CONFIG HALAMAN ---
st.set_page_config(
    page_title="Manufacturing Control", 
    page_icon="⚙️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. INJECT CSS PEMBERSIH SIDEBAR ---
st.markdown(HIDE_NAV_CSS, unsafe_allow_html=True)

# --- 3. KONEKSI DATABASE ---
try:
    SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]
except:
    # Fallback manual (Key lo yang tadi)
    SUPABASE_URL = "https://laxagfijnbcpzxjvwutq.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxheGFnZmlqbmJjcHp4anZ3dXRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDE1ODIsImV4cCI6MjA3Njk3NzU4Mn0.VkYg-4zu1SjNzv1RqzccHnKCMY0NDHsDrd6Il3paC6U"

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 4. LOGIC AUTH (PENTING: JANGAN DIUBAH URUTANNYA) ---
# Cek dulu apakah session state sudah ada. Kalau belum, baru kita buat default-nya.
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['role'] = None
    st.session_state['username'] = None
    st.session_state['name'] = None

def do_login(username, password):
    client = get_supabase()
    try:
        response = client.table("users").select("*").eq("username", username).eq("password", password).execute()
        
        if response.data and len(response.data) > 0:
            user = response.data[0]
            
            # Simpan data user ke memory session
            st.session_state['logged_in'] = True
            st.session_state['role'] = user['role']     # <--- SUDAH DIBENERIN (Tadi typo 'rol   e')
            st.session_state['username'] = user['username']
            st.session_state['name'] = user['name']
            
            st.success(f"Login Sukses! {user['name']}")
            time.sleep(0.5)
            st.rerun() # Refresh halaman untuk masuk Dashboard
        else:
            st.error("Username atau Password salah!")
            
    except Exception as e:
        st.error(f"Error Database: {e}")

# --- 5. STYLING TAMBAHAN ---
st.markdown("""
    <style>
    .st-emotion-cache-1kyxost { padding-top: 20px !important; }
    h1 { text-align: center; color: #B0C4DE; font-family: 'Helvetica'; font-weight: 900; text-shadow: 0 0 5px rgba(176, 196, 222, 0.6); }
    h4 { text-align: center; color: #AAAAAA; font-family: 'Helvetica'; font-weight: 500; display: block; }
    .card { padding: 15px; border-radius: 12px; background-color: #262F39; border: 1px solid #3A4552; text-align: center; min-height: 160px; box-shadow: 4px 4px 15px rgba(0,0,0,0.5); }
    .card:hover { transform: translateY(-5px); background-color: #3C4752; }
    .card-title { font-size: 24px; font-weight: bold; color: #ADD8E6; }
    .card-icon { font-size: 50px; color: #ADD8E6; }
    .card-desc { font-size: 14px; color: #CCCCCC; margin-bottom: 15px; }
    div.stButton > button:first-child { background-color: #00A693; color: white; border: none; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# --- 6. FLOW CONTROL ---

if not st.session_state['logged_in']:
    # === SCREEN LOGIN ===
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1>SYSTEM ACCESS</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN"):
                do_login(u, p)

else:
    # === DASHBOARD (SUDAH LOGIN) ===
    
    # Sidebar: Parameter False = Jangan tampilkan tombol Home (karena sudah di Home)
    show_sidebar_user(show_home_button=False)

    # Layout Dashboard
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown('<h1>MANUFACTURING CONTROL</h1>', unsafe_allow_html=True)
        st.markdown('<h4>-- Silahkan pilih divisi yang ingin dimonitoring --</h4>', unsafe_allow_html=True)
        
        # Grid Cards
        col_c1, col_c2, col_c3 = st.columns(3)
        role = st.session_state.get('role') # Pakai .get() biar aman

        # Helper Card
        def card(col, icon, title, desc, path, key):
            with col:
                st.markdown(f"<div class='card'><div class='card-icon'>{icon}</div><div class='card-title'>{title}</div><p class='card-desc'>{desc}</p></div>", unsafe_allow_html=True)
                if st.button("Masuk →", key=key): st.switch_page(path)

        # 1. PRODUCTION
        if role in ['ADMIN', 'PPC', 'PRODUCTION']:
            card(col_c1, "🏭", "PRODUCTION", "Monitoring OEE & Prod", "pages/Production_Control.py", "btn_prod")
        else:
            with col_c1: st.empty()
        
        # 2. PPC
        if role in ['ADMIN', 'PPC']:
            card(col_c2, "📈", "PPC", "Planning & Schedule", "pages/ppc.py", "btn_ppc")
        else:
            with col_c2: st.empty()
            
        # 3. WAREHOUSE
        if role in ['ADMIN', 'PPC', 'WAREHOUSE']:
            card(col_c3, "📦", "WAREHOUSE", "Stok & Inventaris", "pages/warehouse.py", "btn_whs")
        else:
            with col_c3: st.empty()

        st.markdown("<br>", unsafe_allow_html=True)
        st.image("Shin Sam Plus 2.png", use_container_width=True)