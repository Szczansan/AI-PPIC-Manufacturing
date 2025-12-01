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
# 2. CSS MODERN STYLING (SAMA DENGAN PPC MENU)
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
    
    /* CUSTOM BUTTON STYLE */
    div.stButton > button {
        width: 100%;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 1rem;
        border: none;
        transition: all 0.3s;
    }
    
    /* --- VARIASI WARNA TOMBOL --- */
    
    /* 1. Injection (Biru Laut) */
    .btn-inject button {
        background: linear-gradient(90deg, #0072ff 0%, #00c6ff 100%);
        color: white;
    }
    .btn-inject button:hover {
        box-shadow: 0 5px 15px rgba(0, 198, 255, 0.4);
        transform: translateY(-2px);
    }

    /* 2. Painting (Ungu/Pink) */
    .btn-paint button {
        background: linear-gradient(90deg, #da22ff 0%, #9733ee 100%);
        color: white;
    }
    .btn-paint button:hover {
        box-shadow: 0 5px 15px rgba(218, 34, 255, 0.4);
        transform: translateY(-2px);
    }
    
    /* 3. Assembly (Orange/Emas) */
    .btn-assembly button {
        background: linear-gradient(90deg, #f85032 0%, #e73827 100%);
        color: white;
    }
    .btn-assembly button:hover {
        box-shadow: 0 5px 15px rgba(248, 80, 50, 0.4);
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
st.markdown('<div class="main-header">🏭 Production Planning</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Pilih departemen untuk mengatur jadwal produksi</div>', unsafe_allow_html=True)

# Grid Layout 3 Kolom
c1, c2, c3 = st.columns(3)

# --- KARTU 1: INJECTION ---
with c1:
    with st.container(border=True):
        st.markdown("""
            <div style="text-align: center;">
                <div class="card-icon">⚙️</div>
                <div class="card-title">Injection Molding</div>
                <div class="card-desc">
                    Perencanaan mesin injection, tonnage capacity, dan mold allocation.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="btn-inject">', unsafe_allow_html=True)
        if st.button("🔧 Plan Injection", key="btn_inj"):
            st.switch_page("pages/plan_injection.py")
        st.markdown('</div>', unsafe_allow_html=True)

# --- KARTU 2: PAINTING ---
with c2:
    with st.container(border=True):
        st.markdown("""
            <div style="text-align: center;">
                <div class="card-icon">🎨</div>
                <div class="card-title">Painting Line</div>
                <div class="card-desc">
                    Jadwal pengecatan, color batching, dan line efficiency monitoring.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="btn-paint">', unsafe_allow_html=True)
        # Note: Pastikan file tujuannya ada, kalau belum ada bisa ganti string kosong
        if st.button("🖌️ Plan Painting", key="btn_pnt"):
            st.info("Fitur Painting masih dalam pengembangan 🚧")
            # st.switch_page("pages/plan_painting.py") 
        st.markdown('</div>', unsafe_allow_html=True)

# --- KARTU 3: ASSEMBLY ---
with c3:
    with st.container(border=True):
        st.markdown("""
            <div style="text-align: center;">
                <div class="card-icon">🔩</div>
                <div class="card-title">Assembly Line</div>
                <div class="card-desc">
                    Final assembly schedule, manpower planning, dan output target.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="btn-assembly">', unsafe_allow_html=True)
        # Note: Pastikan file tujuannya ada
        if st.button("🛠️ Plan Assembly", key="btn_asm"):
            st.info("Fitur Assembly masih dalam pengembangan 🚧")
            # st.switch_page("pages/plan_assembly.py")
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("<br>", unsafe_allow_html=True)
st.divider()