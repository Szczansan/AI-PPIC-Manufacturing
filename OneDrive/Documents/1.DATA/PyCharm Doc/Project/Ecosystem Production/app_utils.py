import streamlit as st

# Ini variabel yang dicari sama Home.py
HIDE_NAV_CSS = """
    <style>
        [data-testid="stSidebarNav"] {display: none;}
    </style>
"""

def show_sidebar_user(show_home_button=True):
    with st.sidebar:
        # Pake .get() biar aman
        nama = st.session_state.get('name', 'Guest')
        role = st.session_state.get('role', '-')
        
        st.write(f"User: **{nama}**")
        st.write(f"Role: **{role}**")
        st.divider()
        
        # LOGIKA BARU: Cuma munculin tombol Home kalau diminta
        if show_home_button:
            if st.button("🏠 Dashboard", use_container_width=True):
                st.switch_page("Home.py")
        
        # Tombol Logout
        if st.button("Logout", type="primary", use_container_width=True):
            # Hapus semua session biar bersih
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

def init_page(allowed_roles=None):
    st.markdown(HIDE_NAV_CSS, unsafe_allow_html=True)
    
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        st.warning("Anda harus login terlebih dahulu!")
        st.switch_page("Home.py")
        return False

    if allowed_roles:
        user_role = st.session_state.get('role')
        if user_role not in allowed_roles:
            st.error("⛔ AKSES DITOLAK!")
            if st.button("Kembali"):
                st.switch_page("Home.py")
            st.stop()
            return False
            
    show_sidebar_user(show_home_button=True)
    return True