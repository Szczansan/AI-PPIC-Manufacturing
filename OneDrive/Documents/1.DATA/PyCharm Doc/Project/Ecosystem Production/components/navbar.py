import streamlit as st
import time

def show_navbar():
    # 1. CSS Custom
    st.markdown("""
        <style>
        /* Container Navbar Utama */
        div[data-testid="stHorizontalBlock"] {
            background: linear-gradient(90deg, #101827, #16243b);
            padding: 8px; /* Padding dikit aja biar gak tebel */
            border-radius: 12px;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.3);
        }
        
        /* Ubah tampilan tombol biar kayak teks menu */
        div.stButton > button {
            background-color: transparent !important;
            color: #e0e0e0 !important; /* Putih agak abu biar soft */
            border: none !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            font-size: 14px !important;
            padding: 0px !important; /* Hapus padding default tombol */
            
            /* INI KUNCINYA BIAR TEKS GAK TURUN */
            white-space: nowrap !important; 
            width: 100% !important;
        }

        /* Efek Hover */
        div.stButton > button:hover {
            color: #ffffff !important;
            background-color: rgba(255, 255, 255, 0.1) !important; /* Highlight dikit pas hover */
            border-radius: 5px;
        }

        /* Judul Navbar */
        .nav-title {
            font-size: 18px;
            font-weight: 800;
            color: white;
            margin: 0;
            white-space: nowrap;
            display: flex;
            align-items: center;
        }
        </style>
    """, unsafe_allow_html=True)

    # 2. Layout Kolom (DIPERBAIKI)
    # Gue kecilin porsi Judul (c1), gue gedein porsi tombol (c2-c5) biar lega.
    # vertical_alignment="center" -> Biar icon sama teks sejajar vertikal otomatis (Fitur baru Streamlit)
    
    c1, c2, c3, c4, c5 = st.columns([2.5, 1, 1.5, 1, 1.5], vertical_alignment="center")

    # Judul
    with c1:
        st.markdown('<div class="nav-title">⚙️ Ecosystem</div>', unsafe_allow_html=True)
    
    # Tombol Navigasi
    with c2:
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            st.switch_page("Home.py")
            
    with c3:
        # Production teksnya panjang, makanya di st.columns gue kasih ratio 1.5
        if st.button("🏭 Production", key="nav_prod", use_container_width=True):
            st.switch_page("pages/Production_Control.py")

    with c4:
        if st.button("📊 PPC", key="nav_ppc", use_container_width=True):
            st.switch_page("pages/ppc.py")
            
    with c5:
        if st.button("📦 Warehouse", key="nav_whs", use_container_width=True):
            st.switch_page("pages/warehouse.py")

    st.markdown("<br>", unsafe_allow_html=True)