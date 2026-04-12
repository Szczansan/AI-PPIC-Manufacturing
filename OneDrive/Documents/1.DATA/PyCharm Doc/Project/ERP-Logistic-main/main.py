import streamlit as st
import time
from datetime import datetime
import pandas as pd
from modules import inject_premium_theme

# ==========================================
# 1. CONFIG & DATA USER
# ==========================================
st.set_page_config(page_title="ERP Logistic Command", page_icon="🏭", layout="wide", initial_sidebar_state="collapsed")

# Definisi User & Jabatan (Hardcoded di UI level biar cepet)
USER_ROLES = {
    # --- GOD MODE (SUPER ADMIN) ---
    "Dede": "SPV Logistic",
    "Fauzan": "PPC Specialist",
    "Aqil_N": "Staff Logistic",
    "Rudy_C": "Manager",
    
    # --- OPERATIONAL ---
    "Adit": "Admin Produksi",
    "Rudy_L": "Operator Gudang",
    "E_Solihin": "Operator Gudang"
}

# Mapping Permission Manual (Override modules.py sementara untuk UI)
def get_user_permissions(username):
    god_mode = ["Dede", "Fauzan", "Aqil_N", "Rudy_C"]
    
    # Permission Flags
    perms = {
        "production": False, "warehouse": False, 
        "shipping": False, "material": False, 
        "master": False, "po": False, "atk": False
    }
    
    if username in god_mode:
        return {k: True for k in perms} # Enable All
        
    if username == "Adit":
        perms["production"] = True
        perms["master"] = True
        perms["po"] = True
        perms["atk"] = True # Admin prod kadang butuh input ATK
        
    if username in ["Rudy_L", "E_Solihin"]:
        perms["warehouse"] = True
        perms["shipping"] = True
        perms["material"] = True
        perms["atk"] = True # Gudang bisa cek stok ATK
        
    return perms

# ==========================================
# 2. DEFINISI MENU (DATABASE MENU)
# ==========================================
# Struktur: Judul, Icon, Page File, Kategori, Deskripsi, Permission Key
ALL_MENUS = [
    # -- PRODUCTION --
    {"title": "Input Logsheet", "icon": "📝", "page": "pages/1_production_entry.py", "cat": "Production", "desc": "Input hasil produksi harian", "perm": "production"},
    {"title": "Dashboard Prod", "icon": "📊", "page": "pages/2_production_dashboard.py", "cat": "Production", "desc": "Analisa output mesin", "perm": "production"},
    {"title": "Monitor WIP", "icon": "👀", "page": "pages/3_stock_wip.py", "cat": "Production", "desc": "Cek stok barang setengah jadi", "perm": "production"},
    {"title": "SO WIP", "icon": "🧐", "page": "pages/14_so_wip.py", "cat": "Production", "desc": "Stock Opname WIP", "perm": "production"},
    {"title": "PPC Tower", "icon": "📡", "page": "pages/19_ppc_dashboard.py", "cat": "Production", "desc": "PPC Command Center", "perm": "production"},
    {"title": "Rundown Part", "icon": "🧩", "page": "pages/20_rundown_part.py", "cat": "Production", "desc": "Cek usage part komponen", "perm": "production"},
    
    # -- WAREHOUSE --
    {"title": "Transfer FG", "icon": "🔄", "page": "pages/2_transfer_to_fg.py", "cat": "Warehouse", "desc": "Terima barang dari produksi", "perm": "warehouse"},
    {"title": "Monitor FG", "icon": "📈", "page": "pages/4_stock_fg.py", "cat": "Warehouse", "desc": "Cek stok Finish Good", "perm": "warehouse"},
    {"title": "SO FG", "icon": "📦", "page": "pages/15_so_fg.py", "cat": "Warehouse", "desc": "Stock Opname Finish Good", "perm": "warehouse"},
    {"title": "Stock Material", "icon": "📋", "page": "pages/8_material_stock.py", "cat": "Warehouse", "desc": "Cek stok Resin & Component", "perm": "material"},
    {"title": "SO Material", "icon": "⚖️", "page": "pages/21_material_sto.py", "cat": "Warehouse", "desc": "Stock Opname Material", "perm": "material"},

    # -- BOX & PACKAGING --
    {"title": "Master Box", "icon": "📦", "page": "pages/23_master_box.py", "cat": "Warehouse", "desc": "Database ukuran box", "perm": "master"},
    {"title": "IN/OUT Box", "icon": "🔀", "page": "pages/24_log_box_in_out.py", "cat": "Warehouse", "desc": "Transaksi keluar masuk box", "perm": "warehouse"},
    {"title": "Stock Box", "icon": "📊", "page": "pages/25_stock_box.py", "cat": "Warehouse", "desc": "Monitor stok box kardus", "perm": "warehouse"},
    {"title": "SO Box", "icon": "⚖️", "page": "pages/26_so_box.py", "cat": "Warehouse", "desc": "Stock opname fisik box", "perm": "warehouse"},

    # -- LOGISTIC / SUPPLY --
    {"title": "Incoming Material", "icon": "🛢️", "page": "pages/6_material_in.py", "cat": "Logistic", "desc": "Input kedatangan material", "perm": "material"},
    {"title": "Supply Produksi", "icon": "🏭", "page": "pages/7_material_out.py", "cat": "Logistic", "desc": "Kirim material ke produksi", "perm": "material"},
    {"title": "Buat DO (Shipping)", "icon": "🚛", "page": "pages/5_delivery_order.py", "cat": "Logistic", "desc": "Cetak Surat Jalan", "perm": "shipping"},
    {"title": "Retur Customer", "icon": "↩️", "page": "pages/13_cust_return.py", "cat": "Logistic", "desc": "Input barang retur", "perm": "warehouse"},

    # -- MANAGEMENT --
    {"title": "Master Part", "icon": "⚙️", "page": "pages/9_master_part.py", "cat": "Management", "desc": "Database Part Number", "perm": "master"},
    {"title": "Master Material", "icon": "🛢️", "page": "pages/10_master_mat.py", "cat": "Management", "desc": "Database Resin", "perm": "master"},
    {"title": "Control PO Sales", "icon": "📑", "page": "pages/16_control_po.py", "cat": "Management", "desc": "Monitoring PO Customer", "perm": "po"},
    
    # [TAMBAHIN BARIS INI BRE]
    {"title": "PO Supplier", "icon": "🛒", "page": "pages/27_po_supplier.py", "cat": "Management", "desc": "Monitoring PO Purchasing", "perm": "po"}, 
    
    {"title": "Scrap WIP", "icon": "🔥", "page": "pages/12_wip_scrap.py", "cat": "Management", "desc": "Pemusnahan barang NG", "perm": "production"},
    
    # -- GENERAL AFFAIR (ATK) --
    {"title": "Input ATK", "icon": "✏️", "page": "pages/17_atk_supplies.py", "cat": "Management", "desc": "Kelola Barang ATK", "perm": "atk"},
    {"title": "Stock ATK", "icon": "📊", "page": "pages/18_atk_stock.py", "cat": "Management", "desc": "Kartu Stok ATK", "perm": "atk"},
    {"title": "SO ATK", "icon": "📝", "page": "pages/22_atk_so.py", "cat": "Management", "desc": "Stock Opname ATK", "perm": "atk"},
]

# ==========================================
# 3. HELPER UI
# ==========================================
def render_menu_card(item):
    """Render satu kotak menu"""
    st.markdown(
        f"""
        <div style="
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 15px;
            text-align: left;
            height: 100%;
            transition: all 0.2s ease-in-out;
            cursor: pointer;
        " onmouseover="this.style.background='rgba(255, 255, 255, 0.08)'"
          onmouseout="this.style.background='rgba(255, 255, 255, 0.03)'">
            <div style="font-size: 24px; margin-bottom: 8px;">{item['icon']}</div>
            <div style="font-weight: 600; font-size: 15px; color: #e2e8f0; margin-bottom: 4px;">{item['title']}</div>
            <div style="font-size: 12px; color: #94a3b8; line-height: 1.3;">{item['desc']}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )
    # Tombol invisible full cover agar bisa diklik
    if st.button(f"Go to {item['title']}", key=item['title'], use_container_width=True):
        st.switch_page(item['page'])

def main():
    inject_premium_theme()
    
    # --- LOGIN SYSTEM ---
    if "current_user" not in st.session_state: st.session_state.current_user = None

    if st.session_state.current_user is None:
        c1, c2, c3 = st.columns([1, 0.8, 1])
        with c2:
            st.markdown("<div style='height: 15vh'></div>", unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 3rem; margin-bottom: 10px;">🔐</h1>
                <h2 style="font-weight: 700;">ERP SYSTEM ACCESS</h2>
                <p style="color: #64748b;">Silakan identifikasi diri Anda</p>
            </div>
            """, unsafe_allow_html=True)
            
            user_list = list(USER_ROLES.keys())
            selected_user = st.selectbox("Pilih User", user_list, index=None, placeholder="Klik untuk memilih...")
            
            if st.button("MASUK SISTEM 🚀", type="primary", use_container_width=True):
                if selected_user:
                    st.session_state.current_user = selected_user
                    st.toast("Login Berhasil! Mengalihkan...", icon="✅")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Pilih user dulu, Bre!")
        st.stop()

    # --- SIDEBAR (LOGOUT ONLY) ---
    with st.sidebar:
        st.caption(f"Logged in as: {st.session_state.current_user}")
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

    # --- HEADER SECTION (INFO & CLOCK) ---
    user = st.session_state.current_user
    role_title = USER_ROLES.get(user, "User")
    permissions = get_user_permissions(user)
    
    # Waktu
    now = datetime.now()
    date_str = now.strftime("%A, %d %B %Y")
    time_str = now.strftime("%H:%M")
    
    # Greeting Logic
    hour = now.hour
    if 5 <= hour < 12: greeting = "Selamat Pagi"
    elif 12 <= hour < 15: greeting = "Selamat Siang"
    elif 15 <= hour < 18: greeting = "Selamat Sore"
    else: greeting = "Selamat Malam"

    # Header Layout
    h1, h2 = st.columns([2, 1])
    with h1:
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; justify-content: center; height: 100%;">
            <div style="color: #00f2ff; font-size: 13px; font-weight: 600; letter-spacing: 1px; margin-bottom: 5px;">
                ● SYSTEM ONLINE | v2.1.0
            </div>
            <h1 style="margin: 0; font-size: 2.8rem; font-weight: 800; background: -webkit-linear-gradient(0deg, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                ERP Logistic
            </h1>
            <p style="color: #94a3b8; font-size: 1.1rem; margin-top: 5px;">
                Integrated Supply Chain Command Center
            </p>
        </div>
        """, unsafe_allow_html=True)
        
    with h2:
        st.markdown(f"""
        <div style="
            background: rgba(15, 23, 42, 0.6); 
            border: 1px solid rgba(255,255,255,0.1); 
            border-radius: 16px; 
            padding: 15px 20px; 
            text-align: right;
        ">
            <div style="color: #00f2ff; font-size: 2rem; font-weight: 700; line-height: 1;">{time_str} <span style="font-size: 1rem; color: #64748b;">WIB</span></div>
            <div style="color: #94a3b8; font-size: 0.9rem; margin-bottom: 10px;">{date_str}</div>
            <div style="border-top: 1px solid rgba(255,255,255,0.1); margin: 8px 0;"></div>
            <div style="font-weight: 600; color: #fff;">{greeting}, {user}</div>
            <div style="color: #64748b; font-size: 0.85rem; font-style: italic;">{role_title}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)

    # ==========================================
    # 4. GLOBAL SEARCH BAR
    # ==========================================
    search_query = st.text_input("🔍 Cari Menu...", placeholder="Ketik 'Stock', 'Retur', 'PO'...", label_visibility="collapsed")
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

    # ==========================================
    # 5. RENDER MENU (SMART FILTER)
    # ==========================================
    
    # Filter Menu berdasarkan Permission User
    allowed_menus = [m for m in ALL_MENUS if permissions.get(m['perm'], False)]
    
    # Jika Search Active -> Tampilkan Grid Hasil Search
    if search_query:
        st.subheader(f"Hasil Pencarian: '{search_query}'")
        results = [m for m in allowed_menus if search_query.lower() in m['title'].lower() or search_query.lower() in m['desc'].lower()]
        
        if results:
            cols = st.columns(4)
            for idx, item in enumerate(results):
                with cols[idx % 4]:
                    render_menu_card(item)
        else:
            st.warning("Tidak ditemukan menu yang cocok, Bre.")
            
    # Jika Search Kosong -> Tampilkan Tabbed Layout
    else:
        # Tab Categories
        tab1, tab2, tab3, tab4 = st.tabs([
            "🏭 PRODUCTION", 
            "📦 WAREHOUSE & FG", 
            "🚛 LOGISTIC & SHIPPING", 
            "🛠️ MANAGEMENT & ATK"
        ])
        
        # --- TAB 1: PRODUCTION ---
        with tab1:
            prod_items = [m for m in allowed_menus if m['cat'] == "Production"]
            if prod_items:
                c = st.columns(4)
                for i, item in enumerate(prod_items):
                    with c[i % 4]: render_menu_card(item)
            else:
                st.info("Akses Production tidak tersedia untuk role Anda.")

        # --- TAB 2: WAREHOUSE ---
        with tab2:
            wh_items = [m for m in allowed_menus if m['cat'] == "Warehouse"]
            if wh_items:
                c = st.columns(4)
                for i, item in enumerate(wh_items):
                    with c[i % 4]: render_menu_card(item)
            else:
                st.info("Akses Warehouse tidak tersedia.")

        # --- TAB 3: LOGISTIC ---
        with tab3:
            log_items = [m for m in allowed_menus if m['cat'] == "Logistic"]
            if log_items:
                c = st.columns(4)
                for i, item in enumerate(log_items):
                    with c[i % 4]: render_menu_card(item)
            else:
                st.info("Akses Logistic tidak tersedia.")

        # --- TAB 4: MANAGEMENT ---
        with tab4:
            mgmt_items = [m for m in allowed_menus if m['cat'] == "Management"]
            if mgmt_items:
                c = st.columns(4)
                for i, item in enumerate(mgmt_items):
                    with c[i % 4]: render_menu_card(item)
            else:
                st.info("Akses Management tidak tersedia.")

if __name__ == "__main__":
    main()