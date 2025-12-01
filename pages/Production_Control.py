import streamlit as st
from streamlit_option_menu import option_menu

# =============================
# SETUP HALAMAN
# =============================
st.set_page_config(page_title="Production Control", layout="wide", initial_sidebar_state="collapsed")

# =============================
# CSS & STYLING
# =============================
st.markdown("""
<style>
    /* Latar Belakang */
    [data-testid="stAppViewContainer"] { background-color: #0d1117; }
    
    /* Judul Gradient */
    .gradient-text {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00dbde, #fc00ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 10px;
    }
    
    .sub-text {
        text-align: center;
        color: #a0a0a0;
        font-size: 1.2rem;
        margin-bottom: 40px;
    }

    /* Card Utama */
    .prod-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 30px 20px;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
        position: relative;
    }
    
    /* Efek Hover hanya untuk Card Aktif (Nanti kita atur di Python) */
    .prod-card.active:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
        border-color: #58a6ff;
    }

    /* Card Disabled (Gelap & Transparan) */
    .prod-card.disabled {
        opacity: 0.6;
        background-color: #0d1117; /* Lebih gelap */
        border: 1px dashed #30363d;
        cursor: not-allowed;
    }

    .card-icon { font-size: 50px; margin-bottom: 15px; }
    .card-title { color: #ffffff; font-size: 22px; font-weight: 700; margin-bottom: 10px; }
    .card-desc { color: #8b949e; font-size: 14px; margin-bottom: 20px; }

    /* Styling Tombol "Coming Soon" */
    .coming-soon-btn {
        background-color: #21262d;
        color: #8b949e;
        padding: 10px;
        border-radius: 8px;
        font-weight: 600;
        text-align: center;
        width: 100%;
        border: 1px solid #30363d;
    }

    /* Styling Tombol Streamlit (Hijau) */
    div[data-testid="stPageLink"] a {
        background-color: #238636 !important;
        color: white !important;
        border: none !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stPageLink"] a:hover {
        background-color: #2ea043 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# NAVBAR
# =============================
with st.container():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Production"],
        icons=["house", "factory"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal",
        styles={
            "container": {"padding": "5px", "background-color": "#161b22", "border-radius": "10px"},
            "icon": {"color": "#58a6ff", "font-size": "18px"}, 
            "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px 5px", "color": "#c9d1d9"},
            "nav-link-selected": {"background-color": "#1f6feb", "color": "white"},
        }
    )
    if selected == "Home":
        st.switch_page("Home.py")

# =============================
# HEADER
# =============================
st.markdown('<div class="gradient-text">Production Control</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Pilih departemen untuk memonitor proses produksi</div>', unsafe_allow_html=True)

# =============================
# LOGIC CARD (ACTIVE vs INACTIVE)
# =============================
def draw_card(col, title, icon, desc, page_link, is_active=True):
    with col:
        # Tentukan kelas CSS berdasarkan status aktif/tidak
        css_class = "active" if is_active else "disabled"
        
        # Render Visual Card
        st.markdown(f"""
            <div class="prod-card {css_class}">
                <div class="card-icon">{icon}</div>
                <div class="card-title">{title}</div>
                <div class="card-desc">{desc}</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True) # Spacer

        # LOGIC PENTING DISINI:
        if is_active:
            # Kalau Aktif: Tampilkan Tombol Navigasi Hijau
            st.page_link(page_link, label=f"Masuk ke {title}", icon="🚀", use_container_width=True)
        else:
            # Kalau Tidak Aktif: Tampilkan Tulisan "Coming Soon" (HTML Statis)
            # Gak pake st.button biar gak bisa diklik sama sekali
            st.markdown(f"""
                <div class="coming-soon-btn">
                    🚧 Coming Soon
                </div>
            """, unsafe_allow_html=True)

# =============================
# LAYOUT
# =============================
col1, col2, col3 = st.columns(3, gap="medium")

# 1. INJECTION (AKTIF)
# Pastikan file pages/injection.py beneran ada ya
draw_card(
    col1, 
    "Injection Molding", 
    "⚙️", 
    "Monitoring mesin injeksi, tonase, dan cycle time.", 
    "pages/injection.py",
    is_active=True  # <--- Ini diset TRUE
)

# 2. ASSEMBLY (NON-AKTIF / OTW)
draw_card(
    col2, 
    "Assembly Line", 
    "🛠️", 
    "Proses perakitan part, manpower, dan target output.", 
    "#", # Link asal aja gak ngaruh karena gak akan dipanggil
    is_active=False # <--- Ini diset FALSE biar mode 'Coming Soon'
)

# 3. PAINTING (NON-AKTIF / OTW)
draw_card(
    col3, 
    "Painting & Finishing", 
    "🎨", 
    "Kontrol kualitas cat, mixing room, dan oven curing.", 
    "#", 
    is_active=False # <--- Ini diset FALSE
)