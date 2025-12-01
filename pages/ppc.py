import streamlit as st
from streamlit_option_menu import option_menu

# --- PAGE CONFIG ---
st.set_page_config(page_title="Plan Production Control", layout="wide")

# --- DATA MENU ---
# Saya tambahkan 'desc' (deskripsi) biar kartunya tidak sepi
MENU_ITEMS = [
    {"title": "Forecast", "icon": "📊", "path": "pages/Forcast.py", "desc": "Analisa prediksi produksi."},
    {"title": "Material Req.", "icon": "🧱", "path": "pages/material_report.py", "desc": "Kebutuhan bahan baku."}, 
    {"title": "Plan Delivery", "icon": "🚚", "path": "pages/Plan_Delivery.py", "desc": "Jadwal pengiriman barang."},
    {"title": "Plan Production", "icon": "⚙️", "path": "pages/plan_production.py", "desc": "Perencanaan proses produksi."},
    {"title": "Capacity Machine", "icon": "🏭", "path": "pages/app_streamlit.py", "desc": "Dashboard kapasitas mesin."},
]

# --- CSS STYLING (DARK PREMIUM) ---
st.markdown("""
<style>
    /* Background Utama */
    [data-testid="stAppViewContainer"] { background-color: #0e1117; }
    
    /* Judul Gradient */
    .gradient-text {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    
    .sub-text {
        text-align: center;
        color: #8b949e;
        font-size: 1.1rem;
        margin-bottom: 40px;
    }

    /* CARD CONTAINER */
    .ppc-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-top-left-radius: 15px;
        border-top-right-radius: 15px;
        padding: 30px 20px 10px 20px;
        text-align: center;
        height: 180px; /* Tinggi fix biar rata */
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border-bottom: none; /* Hilangkan border bawah biar nyatu sama tombol */
    }
    
    .card-icon { font-size: 40px; margin-bottom: 10px; }
    .card-title { 
        color: white; 
        font-size: 18px; 
        font-weight: 700; 
        margin-bottom: 5px; 
        line-height: 1.2;
    }
    .card-desc { 
        color: #8b949e; 
        font-size: 12px; 
        line-height: 1.3;
    }

    /* TOMBOL "BUKA MENU" (st.page_link) */
    div[data-testid="stPageLink"] a {
        background-color: #1f2937 !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        
        /* Bentuk Tombol menempel ke card atas */
        border-top-left-radius: 0px !important;
        border-top-right-radius: 0px !important;
        border-bottom-left-radius: 15px !important;
        border-bottom-right-radius: 15px !important;
        
        transition: all 0.2s ease-in-out !important;
        display: block !important;
        text-align: center !important;
    }

    /* Hover Effect Tombol */
    div[data-testid="stPageLink"] a:hover {
        background-color: #0072ff !important; /* Biru pas hover */
        color: white !important;
        border-color: #00c6ff !important;
        box-shadow: 0 4px 12px rgba(0, 114, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- NAVBAR (Home + PPC) ---
with st.container():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Plan Production Control"],
        icons=["house", "building"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal",
        styles={
            "container": {"padding": "5px", "background-color": "#161b22", "border-radius": "10px"},
            "icon": {"color": "#00c6ff", "font-size": "18px"},
            "nav-link": {
                "font-size": "16px",
                "text-align": "center",
                "margin": "0px 5px",
                "color": "#c9d1d9",
            },
            "nav-link-selected": {"background-color": "#1f6feb", "color": "white"},
        }
    )

if selected == "Home":
    try:
        st.switch_page("Home.py")
    except Exception:
        st.info("🏠 Halaman Home (fallback).")

# --- HEADER PAGE ---
st.markdown('<div class="gradient-text">Plan Production Control</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Dashboard Monitoring & Perencanaan Produksi</div>', unsafe_allow_html=True)


# --- FUNGSI DRAW CARD ---
def draw_ppc_card(col, item):
    with col:
        # 1. Bagian Atas (Visual HTML)
        st.markdown(f"""
            <div class="ppc-card">
                <div class="card-icon">{item['icon']}</div>
                <div class="card-title">{item['title']}</div>
                <div class="card-desc">{item.get('desc', '')}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # 2. Bagian Bawah (Tombol Widget)
        # Link styling css 'div[data-testid="stPageLink"] a'
        st.page_link(item['path'], label="Buka Menu ➡️", use_container_width=True)


# --- GRID LAYOUT (5 KOLOM) ---
# Karena ada 5 menu, kita buat 5 kolom
cols = st.columns(5, gap="medium")

for i, item in enumerate(MENU_ITEMS):
    draw_ppc_card(cols[i], item)

st.markdown("<br><br>", unsafe_allow_html=True)