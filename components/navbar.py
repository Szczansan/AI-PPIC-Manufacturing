import streamlit as st

def show_navbar():
    st.markdown("""
        <style>
        .navbar {
            background: linear-gradient(90deg,#101827,#16243b);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: white;
            margin-bottom: 1rem;
        }
        .navbar-title {
            font-size: 1.2rem;
            font-weight: 600;
        }
        .navbar-links a {
            color: #ffffffcc;
            margin-left: 1rem;
            text-decoration: none;
        }
        .navbar-links a:hover {
            color: white;
            text-decoration: underline;
        }
        </style>

        <div class="navbar">
            <div class="navbar-title">⚙️ Ecosystem Production</div>
            <div class="navbar-links">
                <a href="/" target="_self">🏠 Home</a>
                <a href="/Production_Control" target="_self">Production</a>
                <a href="/ppc" target="_self">PPC</a>
                <a href="/warehouse" target="_self">Warehouse</a>
            </div>
        </div>
    """, unsafe_allow_html=True)
