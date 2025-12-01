import streamlit as st
from streamlit_option_menu import option_menu

# =============================
# SETUP HALAMAN
# =============================
st.set_page_config(page_title="Warehouse System", layout="wide", initial_sidebar_state="collapsed")

# =============================
# CSS & STYLING (DARK PREMIUM)
# =============================
st.markdown("""
<style>
    /* Background App */
    [data-testid="stAppViewContainer"] { background-color: #0d1117; }
    
    /* Judul Gradient */
    .gradient-text {
        font-size: 3rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #ffd700, #007bff);
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

    /* CARD STYLING */
    .wh-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 15px;
        padding: 25px 20px;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
    }
    
    /* Hover Effect hanya untuk card aktif */
    .wh-card.active:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        border-color: #e1b12c;
    }

    /* Disabled Card Style */
    .wh-card.disabled {
        opacity: 0.6;
        border: 1px dashed #30363d;
        cursor: not-allowed;
    }

    .card-icon { font-size: 45px; margin-bottom: 15px; }
    .card-title { color: white; font-size: 20px; font-weight: 700; margin-bottom: 5px; }
    .card-desc { color: #8b949e; font-size: 13px; margin-bottom: 20px; line-height: 1.4;}

    /* TOMBOL NAVIGASI (CUSTOMIZED) */
    div[data-testid="stPageLink"] a {
        background-color: #1f2937 !important;
        border: 1px solid #30363d !important;
        color: white !important;
        transition: 0.2s;
    }
    div[data-testid="stPageLink"] a:hover {
        background-color: #e1b12c !important;
        color: black !important;
        font-weight: bold !important;
    }

    /* LABEL MAINTENANCE */
    .maintenance-badge {
        background-color: #21262d;
        color: #8b949e;
        padding: 8px;
        border-radius: 8px;
        font-size: 14px;
        border: 1px solid #30363d;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# NAVBAR
# =============================
with st.container():
    selected = option_menu(
        menu_title=None,
        options=["Home", "Warehouse"],
        icons=["house", "building"],
        menu_icon="cast",
        default_index=1,
        orientation="horizontal",
        styles={
            "container": {"padding": "5px", "background-color": "#161b22", "border-radius": "10px"},
            "icon": {"color": "#e1b12c", "font-size": "18px"},
            "nav-link": {"font-size": "16px", "margin": "0px 5px", "color": "#c9d1d9"},
            "nav-link-selected": {"background-color": "#30363d", "color": "#e1b12c"},
        }
    )
    if selected == "Home":
        st.switch_page("Home.py")

# =============================
# HEADER
# =============================
st.markdown('<div class="gradient-text">🏭 Warehouse System</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Dashboard Monitoring Stok & Logistik</div>', unsafe_allow_html=True)

# =============================
# FUNGSI CARD DENGAN LOGIC ACTIVE/INACTIVE
# =============================
def draw_wh_card(col, title, icon, desc, page_link, is_active=True):
    with col:
        # Tentukan class CSS
        status_class = "active" if is_active else "disabled"
        
        st.markdown(f"""
            <div class="wh-card {status_class}">
                <div>
                    <div class="card-icon">{icon}</div>
                    <div class="card-title">{title}</div>
                    <div class="card-desc">{desc}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Logic Tombol: Hanya render st.page_link jika Active = True
        st.markdown("<div style='margin-top: -20px; position: relative; z-index: 2;'>", unsafe_allow_html=True)
        
        if is_active:
            st.page_link(page_link, label="Buka Menu ➡️", use_container_width=True)
        else:
            # Kalau False, tampilkan badge statis
            st.markdown('<div class="maintenance-badge">🚧 Coming Soon</div>', unsafe_allow_html=True)
            
        st.markdown("</div>", unsafe_allow_html=True)


# =============================
# LAYOUT GRID
# =============================

# --- BARIS 1 (MONITORING UTAMA) ---
row1_col1, row1_col2, row1_col3 = st.columns(3, gap="medium")

# 1. STOCK WIP
draw_wh_card(
    row1_col1, "Stock WIP", "🏗️", 
    "Monitor Work In Process di area produksi.", 
    "pages/monitor_wip.py", 
    is_active=True 
)

# 2. FINISH GOOD
draw_wh_card(
    row1_col2, "Finish Good", "✅", 
    "Stock barang jadi siap kirim.", 
    "pages/monitor_finishgood.py", 
    is_active=True
)

# 3. MATERIAL
draw_wh_card(
    row1_col3, "Raw Material", "🧱", 
    "Monitor ketersediaan bahan baku.", 
    "pages/monitor_material.py", 
    is_active=True
)


# --- SPACER ---
st.markdown("<br>", unsafe_allow_html=True)


# --- BARIS 2 (TRANSAKSI & LAINNYA) ---
row2_col1, row2_col2, row2_col3 = st.columns(3, gap="medium")

# 4. TRANSFER WIP TO FG
draw_wh_card(
    row2_col1, "Transfer WIP to FG", "🔄", 
    "Input transfer stok dari WIP ke Finish Good.", 
    "pages/wip_to_fg.py", 
    is_active=True 
)

# 5. CKD (NON-AKTIF)
draw_wh_card(
    row2_col2, "Stock CKD", "🔧", 
    "Komponen Complete Knock Down.", 
    "#", 
    is_active=False 
)

# 6. DELIVERY (NON-AKTIF)
draw_wh_card(
    row2_col3, "Delivery Control", "🚚", 
    "Jadwal & status pengiriman logistik.", 
    "#", 
    is_active=False 
)


# --- SPACER ---
st.markdown("<br>", unsafe_allow_html=True)


# --- BARIS 3 (INCOMING MATERIAL - NEW) ---
row3_col1, row3_col2, row3_col3 = st.columns(3, gap="medium")

# 7. INCOMING MATERIAL
draw_wh_card(
    row3_col1, "Incoming Material", "📥", 
    "Input penerimaan material dari Supplier.", 
    "pages/incoming_material.py", 
    is_active=True 
)

# Kolom 2 dan 3 di baris ini dibiarkan kosong untuk saat ini
# Bisa dipakai untuk menu masa depan

st.markdown("<br><br>", unsafe_allow_html=True)