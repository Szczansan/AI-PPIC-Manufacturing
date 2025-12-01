import streamlit as st

# =============================
# 1. PAGE CONFIG
# =============================
st.set_page_config(page_title="Injection Hub", layout="wide")

# =============================
# 2. CSS MODERN & RESPONSIVE
# =============================
st.markdown("""
<style>
    /* RESET & BACKGROUND */
    .stApp {
        background-color: #0f172a; /* Slate-900: Dark Blue-ish Gray */
    }

    /* NAVBAR STYLING */
    .navbar {
        background: rgba(30, 41, 59, 0.8); /* Glassmorphism Effect */
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1rem 2rem;
        border-radius: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
    }
    .nav-brand {
        font-size: 1.25rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .nav-links a {
        color: #94a3b8;
        text-decoration: none;
        margin-left: 1.5rem;
        font-weight: 500;
        transition: color 0.3s;
    }
    .nav-links a:hover {
        color: #fff;
    }

    /* CARD CONTAINER */
    .card-box {
        background: #1e293b; /* Slate-800 */
        border: 1px solid #334155;
        border-radius: 16px 16px 0 0; /* Rounded atas */
        padding: 2rem 1.5rem 1rem 1.5rem;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        height: 100%;
    }
    
    /* ICON & TEXT */
    .card-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
        background: rgba(255,255,255,0.05);
        width: 80px;
        height: 80px;
        line-height: 80px;
        border-radius: 50%;
        margin-left: auto;
        margin-right: auto;
    }
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #f1f5f9;
        margin-bottom: 0.5rem;
    }
    .card-desc {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-bottom: 1rem;
        min-height: 40px; /* Biar tinggi kartu seragam */
    }

    /* BUTTON STYLING (Override Streamlit) */
    div[data-testid="stPageLink"] a {
        background: linear-gradient(90deg, #2563eb, #0f172a); 
        border: 1px solid #334155 !important;
        border-top: none !important;
        border-radius: 0 0 16px 16px !important; /* Rounded bawah */
        color: white !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.8rem !important;
        padding: 0.75rem !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stPageLink"] a:hover {
        background: linear-gradient(90deg, #3b82f6, #1e40af) !important;
        letter-spacing: 2px;
        box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.5) !important;
    }

    /* DISABLED STATE */
    .card-disabled {
        opacity: 0.5;
        filter: grayscale(100%);
        pointer-events: none;
    }
</style>
""", unsafe_allow_html=True)

# =============================
# 3. HEADER & NAVBAR
# =============================
st.markdown("""
<div class="navbar">
    <div class="nav-brand">⚙️ ECOSYSTEM PRODUCTION</div>
    <div class="nav-links">
        <a href="/" target="_self">🏠 Home</a>
        <a href="/Production_Control" target="_self">🏭 Production</a>
        <a href="/ppc" target="_self">📊 PPC</a>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("") # Spacer

# Title Section
col_head1, col_head2 = st.columns([2, 1])
with col_head1:
    st.markdown("<h1 style='margin-bottom:0; color:white;'>Injection Control Center</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#94a3b8; font-size:1.1rem;'>Pilih modul operasional di bawah ini untuk memulai aktivitas.</p>", unsafe_allow_html=True)

st.divider()

# =============================
# 4. CARD COMPONENT (REUSABLE)
# =============================
def render_card(icon, title, desc, link, enabled=True):
    # Bagian Visual Atas (HTML)
    opacity = "1" if enabled else "0.6"
    
    html_card = f"""
    <div class="card-box" style="opacity: {opacity}">
        <div class="card-icon">{icon}</div>
        <div class="card-title">{title}</div>
        <div class="card-desc">{desc}</div>
    </div>
    """
    st.markdown(html_card, unsafe_allow_html=True)
    
    # Bagian Tombol Bawah (Streamlit Native)
    if enabled:
        st.page_link(f"pages/{link}", label="ACCESS MODULE ➔", use_container_width=True)
    else:
        st.button("🔒 COMING SOON", disabled=True, use_container_width=True, key=title)

# =============================
# 5. GRID LAYOUT SYSTEM (3 x 2)
# =============================

# Definisi Menu Items biar rapi
menu_row1 = [
    {"icon": "📝", "title": "Hasil Produksi", "desc": "Input laporan hasil produksi harian operator.", "link": "input_data_inj.py"},
    {"icon": "🕒", "title": "Hourly Input", "desc": "Update output per jam (Realtime Tracking).", "link": "monitor_inj_hour.py"},
    {"icon": "📊", "title": "Monitoring Board", "desc": "Dashboard visual monitoring produksi per jam.", "link": "monitor_dashboard.py"},
]

menu_row2 = [
    {"icon": "🚚", "title": "Transfer WIP", "desc": "Kirim barang finish good ke Warehouse.", "link": "inj_to_wip.py"},
    {"icon": "📑", "title": "Bon Material", "desc": "Request raw material tambahan ke gudang.", "link": "bon_material.py"},
    {"icon": "⛔", "title": "Hold Part", "desc": "Karantina part NG atau suspect quality.", "link": "", "enabled": False},
]

# RENDER ROW 1
cols1 = st.columns(3, gap="large")
for i, item in enumerate(menu_row1):
    with cols1[i]:
        render_card(item["icon"], item["title"], item["desc"], item["link"], item.get("enabled", True))

st.write("") # Spacer antar baris
st.write("") 

# RENDER ROW 2
cols2 = st.columns(3, gap="large")
for i, item in enumerate(menu_row2):
    with cols2[i]:
        render_card(item["icon"], item["title"], item["desc"], item["link"], item.get("enabled", True))

# =============================
# 6. FOOTER
# =============================
st.markdown("""
<div style='text-align: center; margin-top: 50px; padding: 20px; border-top: 1px solid #334155; color: #64748b; font-size: 0.8rem;'>
    <p>© 2025 Production Planning & Inventory Control System<br>
    Connected to Database: <strong>Supabase Production</strong></p>
</div>
""", unsafe_allow_html=True)