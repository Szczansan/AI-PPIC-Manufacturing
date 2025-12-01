import streamlit as st
from components.navbar import show_navbar

# ==========================================
# 1. PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Plan Production Control", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. CSS MODERN STYLING
# ==========================================
st.markdown("""
<style>
    /* FIX PADDING ATAS AGAR TIDAK KETUTUP NAVBAR */
    .block-container {
        padding-top: 6rem;
        padding-bottom: 5rem;
    }

    /* HEADER STYLE */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #00C9FF, #92FE9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 3rem;
    }

    /* CARD CONTAINER STYLE */
    div.css-card {
        background-color: #1e2130; 
        border: 1px solid #2e344e;
        border-radius: 15px;
        padding: 25px;
        height: 100%;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    /* CUSTOM BUTTON STYLE BIAR FULL WIDTH & MODERN */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 1rem;
        border: none;
        transition: all 0.3s;
    }
    
    /* VARIASI TOMBOL */
    /* Tombol Planning (Biru) */
    .btn-plan button {
        background: linear-gradient(90deg, #0072ff 0%, #00c6ff 100%);
        color: white;
    }
    .btn-plan button:hover {
        box-shadow: 0 5px 15px rgba(0, 198, 255, 0.4);
        transform: translateY(-2px);
    }

    /* Tombol Monitoring (Ungu) */
    .btn-monitor button {
        background: linear-gradient(90deg, #7F00FF 0%, #E100FF 100%);
        color: white;
    }
    .btn-monitor button:hover {
        box-shadow: 0 5px 15px rgba(225, 0, 255, 0.4);
        transform: translateY(-2px);
    }
    
    /* ICON DALAM KARTU */
    .card-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }
    .card-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #f0f0f0;
        margin-bottom: 0.5rem;
    }
    .card-desc {
        font-size: 0.9rem;
        color: #b0b0b0;
        margin-bottom: 1.5rem;
        min-height: 40px;
    }
    
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. MAIN UI
# ==========================================

# Tampilkan Navbar Custom
show_navbar()

# Hero Section
st.markdown('<div class="main-header">🏭 Production Control Hub</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Pusat komando perencanaan dan monitoring produksi harian</div>', unsafe_allow_html=True)

# Grid Layout (Menggunakan Columns dengan Container/Border)
c_spacer_left, c1, c2, c_spacer_right = st.columns([1, 4, 4, 1])

# --- KARTU 1: PLANNING ---
with c1:
    with st.container(border=True):
        st.markdown("""
            <div style="text-align: center;">
                <div class="card-icon">📅</div>
                <div class="card-title">Injection Planning</div>
                <div class="card-desc">
                    Generate jadwal produksi otomatis berdasarkan forecast demand dan kapasitas mesin.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Bungkus tombol dengan div class untuk styling khusus
        st.markdown('<div class="btn-plan">', unsafe_allow_html=True)
        if st.button("🚀 Buat Planning Baru", key="btn_plan"):
            st.switch_page("pages/app_planning.py")
        st.markdown('</div>', unsafe_allow_html=True)

# --- KARTU 2: MONITORING ---
with c2:
    with st.container(border=True):
        st.markdown("""
            <div style="text-align: center;">
                <div class="card-icon">📊</div>
                <div class="card-title">Real-time Monitoring</div>
                <div class="card-desc">
                    Pantau progress produksi Actual vs Plan dan status mesin secara langsung.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Bungkus tombol dengan div class untuk styling khusus
        st.markdown('<div class="btn-monitor">', unsafe_allow_html=True)
        if st.button("📈 Buka Dashboard", key="btn_mon"):
            st.switch_page("pages/monitoring_inj.py")
        st.markdown('</div>', unsafe_allow_html=True)

# Footer Space
st.markdown("<br><br>", unsafe_allow_html=True)
st.divider()
st.caption("© 2025 Ecosystem Production System | AI-Powered Planning")