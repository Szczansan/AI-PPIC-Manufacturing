import streamlit as st

# 1. Konfigurasi Halaman (Tidak Berubah)
st.set_page_config(
    page_title="Manufacturing Control", 
    page_icon="⚙️", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. Injeksi CSS Kustom (Fokus Perubahan di h1 dan h4)
st.markdown("""
    <style>
    /* Styling Umum */
    .st-emotion-cache-1kyxost { 
        padding-top: 20px !important;
    }
    
    /* PERBAIKAN PENTING: Penyeimbangan Horizontal (Margin Auto) */
    h1 {
        text-align: center;
        color: #B0C4DE; 
        font-family: 'Helvetica', sans-serif;
        font-weight: 900;
        margin-top: 0;
        line-height: 1.2; 
        padding-bottom: 5px; 
        
        /* Menghilangkan margin horizontal agar benar-benar di tengah */
        margin-left: auto;
        margin-right: auto;
        
        /* Efek Glow */
        text-shadow: 
            0 0 5px rgba(176, 196, 222, 0.6), 
            0 0 15px rgba(176, 196, 222, 0.4), 
            0 0 30px rgba(176, 196, 222, 0.2);
    }
    
    /* PERBAIKAN PENTING: Penyeimbangan Horizontal (Margin Auto) */
    h4 {
        text-align: center;
        color: #AAAAAA;
        font-family: 'Helvetica', sans-serif;
        font-weight: 500;
        margin-bottom: 30px;
        margin-top: 10px;
        
        /* Menghilangkan margin horizontal agar benar-benar di tengah */
        margin-left: auto;
        margin-right: auto;
        
        /* Jika h4 berupa div (yang Streamlit lakukan), ini akan memusatkan secara horizontal */
        display: block; 
    }
    
    /* CSS untuk Kartu Interaktif (Tidak Berubah) */
    .card {
        padding: 15px 20px 5px 20px;
        border-radius: 12px;
        box-shadow: 4px 4px 15px rgba(0, 0, 0, 0.5);
        text-align: center;
        margin: 10px 0 0 0; 
        transition: all 0.3s ease-in-out;
        min-height: 160px; 
        background-color: #262F39; 
        border: 1px solid #3A4552;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 8px 8px 25px rgba(0, 0, 0, 0.7);
        background-color: #3C4752;
    }
    .card-title {
        font-size: 24px;
        font-weight: bold;
        color: #ADD8E6;
        margin-top: 5px;
        line-height: 1.1; 
    }
    .card-icon {
        font-size: 50px;
        color: #ADD8E6;
        margin-bottom: 5px;
    }
    .card-desc {
        font-size: 14px;
        color: #CCCCCC;
        margin-top: 5px;
        margin-bottom: 15px; 
    }
    
    /* Styling Tombol Aksi (Tidak Berubah) */
    div.stButton > button:first-child {
        background-color: #00A693; 
        color: white;
        font-size: 14px;
        font-weight: bold;
        border-radius: 6px; 
        border: none;
        margin-top: 0; 
        padding: 8px 15px;
        width: 100%;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        transition: background-color 0.2s;
    }
    div.stButton > button:first-child:hover {
        background-color: #00BFA5;
        transform: none; 
    }
    .st-emotion-cache-1mnr8h6 {
        padding-bottom: 0.5rem; 
    }
    </style>
    """, unsafe_allow_html=True)


# 3. Fungsi Pendukung (Tidak Berubah)
def create_card_with_button(icon, title, description, page_path, key, col):
    with col:
        st.markdown(
            f"""
            <div class="card">
                <div class="card-icon">{icon}</div>
                <div class="card-title">{title}</div>
                <p class='card-desc'>{description}</p>
            </div>
            """, unsafe_allow_html=True
        )
        if st.button("Masuk →", key=key, use_container_width=True): 
            st.switch_page(page_path)

# 4. Layout Utama (Rasio Kolom Lebar Tetap)
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    st.markdown('<h1>MANUFACTURING CONTROL</h1>', unsafe_allow_html=True)
    st.markdown('<h4>-- Silahkan pilih divisi yang ingin dimonitoring --</h4>', unsafe_allow_html=True)
    
    # Rasio Ultimate: [0.1, 1.7, 0.05, 1.7, 0.05, 1.7, 0.1]
    col_s1, col_c1, col_s2, col_c2, col_s3, col_c3, col_s4 = st.columns([0.1, 1.7, 0.05, 1.7, 0.05, 1.7, 0.1])
    
    # PENGGUNAAN CARDS
    create_card_with_button(icon="🏭", title="PRODUCTION", description="Monitoring performa mesin (OEE) dan siklus produksi real-time.",
                page_path="pages/Production_Control.py", key="btn_production", col=col_c1)
    
    create_card_with_button(icon="📈", title="PPC", description="Perencanaan, penjadwalan, dan kontrol material produksi.",
                page_path="pages/ppc.py", key="btn_ppc", col=col_c2)
    
    create_card_with_button(icon="📦", title="WAREHOUSE", description="Manajemen stok, lokasi material, dan kontrol inventaris gudang.",
                page_path="pages/warehouse.py", key="btn_warehouse", col=col_c3)

    st.image("Shin Sam Plus 2.png", use_container_width=True, clamp=True)


# 5. Footer (Tidak Berubah)
st.markdown("""
    <hr style="border: 0; height: 1px; background-image: linear-gradient(to right, rgba(0, 0, 0, 0), rgba(0, 0, 0, 0.5), rgba(0, 0, 0, 0)); margin-top: 50px;">
    <p style="text-align: center; color: #aaaaaa; font-size: 12px;">© 2025 Manufacturing Digital Control. All rights reserved.</p>
    """, unsafe_allow_html=True)