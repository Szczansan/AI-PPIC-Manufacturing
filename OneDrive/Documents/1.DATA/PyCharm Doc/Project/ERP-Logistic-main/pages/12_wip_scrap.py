import streamlit as st
from datetime import date
from modules import inject_premium_theme, protect_page, get_stockboard_view, submit_wip_scrap

st.set_page_config(page_title="Scrap WIP", layout="wide")
inject_premium_theme()
protect_page("scrap") 

# --- TOMBOL BALIK ---
st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")

st.title("🔥 Pemusnahan Barang (WIP Scrap)")
st.warning("Halaman ini untuk mengurangi stok WIP karena NG/Rusak (Tidak bisa dikirim).")

# Load Data Stok WIP
df_wip = get_stockboard_view()

# Filter hanya barang yang ada stoknya
parts = df_wip[df_wip['balance'] > 0]['part_name'].unique() if not df_wip.empty else []

if len(parts) == 0:
    st.error("Stok WIP Kosong. Tidak ada barang yang bisa di-scrap.")
    st.stop()

with st.container():
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    with st.form("form_scrap"):
        c1, c2 = st.columns(2)
        
        with c1:
            date_scrap = st.date_input("Tanggal Pemusnahan", value=date.today())
            part_sel = st.selectbox("Pilih Barang", parts)
            
            # Cari part_no & stok saat ini
            part_info = df_wip[df_wip['part_name'] == part_sel].iloc[0]
            part_no = part_info['part_no']
            current = int(part_info['balance'])
            
            st.info(f"Stok WIP saat ini: **{current} Pcs**")
            
        with c2:
            qty = st.number_input("Qty Dimusnahkan", min_value=1, max_value=current, step=1)
            reason = st.selectbox("Alasan NG", [
                "Molding Defect (Short Shot/Flash)", 
                "Material Kontaminasi", 
                "Setting Mesin Error", 
                "Trial / Sample",
                "Lainnya"
            ])
            pic = st.text_input("PIC Pemusnahan", placeholder="Nama Foreman / SPV")
        
        if st.form_submit_button("🔥 PROSES SCRAP (KURANGI STOK)"):
            if pic:
                if submit_wip_scrap(date_scrap, part_no, qty, reason, pic):
                    st.success(f"Berhasil! {qty} Pcs {part_sel} telah dimusnahkan.")
                    st.cache_data.clear()
            else:
                st.error("Nama PIC wajib diisi!")
    st.markdown('</div>', unsafe_allow_html=True)

