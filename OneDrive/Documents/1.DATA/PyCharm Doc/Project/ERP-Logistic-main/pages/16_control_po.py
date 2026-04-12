import streamlit as st
import pandas as pd
import time
from modules import (
    inject_premium_theme, protect_page, 
    get_master_products, submit_new_po_master, 
    get_po_monitoring_data, close_po_status,
    get_closed_pos, generate_po_closing_pdf # <--- Fungsi Baru Diimport
)

st.set_page_config(page_title="Control PO", page_icon="📑", layout="wide")
inject_premium_theme()
protect_page("control_po") 

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📑 Control PO Customer")

# [UPDATE] Jadi 3 Tab
tab1, tab2, tab3 = st.tabs(["📝 Register PO Baru", "📊 Monitoring (Active)", "📜 Riwayat PO (Closed)"])

# ==========================================
# TAB 1: INPUT PO BARU (LOGIC SAMA KAYAK DULU)
# ==========================================
with tab1:
    if "po_cart" not in st.session_state: st.session_state.po_cart = []
    df_prod = get_master_products()
    
    with st.container():
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("1. Header PO")
        c1, c2 = st.columns(2)
        with c1: po_num_input = st.text_input("Nomor PO Customer", placeholder="Contoh: PO-2026/ADM-001")
        with c2: cust_input = st.selectbox("Customer", df_prod['customer'].unique() if not df_prod.empty else [])
            
        st.divider()
        st.subheader("2. Detail Barang")
        ic1, ic2, ic3 = st.columns([3, 2, 1])
        with ic1:
            parts_cust = df_prod[df_prod['customer'] == cust_input]['part_name'].tolist() if not df_prod.empty else []
            po_item = st.selectbox("Pilih Part", parts_cust)
            p_no = ""
            if po_item:
                p_no = df_prod[df_prod['part_name'] == po_item].iloc[0]['part_no']
                st.caption(f"Part No: {p_no}")
        with ic2: po_qty = st.number_input("Qty Order (Target)", min_value=1, step=100)
        with ic3:
            st.write("Action")
            if st.button("➕ Add Item"):
                if not po_item: st.error("Pilih Barang!")
                else:
                    st.session_state.po_cart.append({"part_name": po_item, "part_no": p_no, "qty": po_qty})
                    st.rerun()
        
        if st.session_state.po_cart:
            st.dataframe(pd.DataFrame(st.session_state.po_cart), use_container_width=True)
            if st.button("💾 SIMPAN PO KE DATABASE", type="primary", use_container_width=True):
                if not po_num_input: st.error("Nomor PO Wajib Diisi!")
                else:
                    success, msg = submit_new_po_master(po_num_input, cust_input, st.session_state.po_cart)
                    if success:
                        st.success(msg)
                        st.session_state.po_cart = []
                        time.sleep(1.5); st.rerun()
                    else: st.error(msg)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# TAB 2: MONITORING ACTIVE
# ==========================================
with tab2:
    st.info("Data Actual Delivery diambil otomatis dari Surat Jalan (DO) tipe SALES.")
    
    col_f1, _ = st.columns([1, 3])
    with col_f1:
        list_cust = df_prod['customer'].unique().tolist()
        list_cust.insert(0, "All")
        filter_cust = st.selectbox("Filter Customer", list_cust)
    
    # Load Data
    df_mon = get_po_monitoring_data(filter_cust)
    
    if not df_mon.empty:
        # 1. Pastikan kolom tanggal dikenali sebagai datetime
        df_mon['po_date'] = pd.to_datetime(df_mon['po_date'])
        
        # 2. Urutkan PO berdasarkan Tanggal Terbaru (Descending) biar yang baru diatas
        # Kita ambil unique PO numbers tapi yang sudah terurut tanggalnya
        sorted_po_list = df_mon.sort_values(by='po_date', ascending=False)['po_number'].unique()
        
        current_month_group = None # Penanda Bulan
        
        for po in sorted_po_list:
            # Ambil data spesifik PO ini
            df_po = df_mon[df_mon['po_number'] == po]
            cust_name = df_po.iloc[0]['customer_name']
            po_date_val = df_po.iloc[0]['po_date']
            
            # --- LOGIC GROUPING BULAN ---
            # Format contoh: "February 2026"
            month_str = po_date_val.strftime("%B %Y")
            
            # Jika bulan PO ini beda sama bulan sebelumnya, cetak JUDUL BULAN
            if month_str != current_month_group:
                st.markdown(f"### 🗓️ {month_str}") # <--- INI PEMISAHNYA
                current_month_group = month_str
            # -----------------------------

            # Hitung Progress
            total_target = df_po['target_qty'].sum()
            total_actual = df_po['actual_delivery'].sum()
            prog_pct = (total_actual / total_target) if total_target > 0 else 0
            
            # Labeling Status
            status_label = "✅ COMPLETED" if prog_pct >= 1 else f"⏳ OPEN ({prog_pct*100:.1f}%)"
            
            # Expander PO
            with st.expander(f"**{po}** | {cust_name} | {status_label}", expanded=False):
                st.progress(min(prog_pct, 1.0), text=f"Total Fulfillment: {total_actual} / {total_target}")
                
                st.dataframe(
                    df_po, use_container_width=True, hide_index=True,
                    column_config={
                        "part_name": "Part Name", "part_no": "Part No",
                        "target_qty": st.column_config.NumberColumn("Target PO", format="%d"),
                        "actual_delivery": st.column_config.NumberColumn("Sudah Kirim", format="%d"),
                        "balance_qty": st.column_config.NumberColumn("Sisa Hutang", format="%d"),
                        "po_date": st.column_config.DateColumn("Tgl PO", format="DD/MM/YYYY") # Tampilin juga tanggalnya
                    }
                )
                
                st.divider()
                # --- FITUR FORCE CLOSE (LOGIC TETAP SAMA) ---
                c_act1, c_act2 = st.columns([3, 1])
                with c_act1:
                    st.caption("Jika target belum tercapai tapi customer minta Close/Cancel sisa, gunakan tombol di kanan.")
                with c_act2:
                    if st.button(f"🛑 Close PO Manual", key=f"btn_cls_{po}"):
                        st.session_state[f"confirm_close_{po}"] = True
                    
                    if st.session_state.get(f"confirm_close_{po}"):
                        st.warning(f"⚠️ Progress baru {prog_pct*100:.1f}%. Close PO ini?")
                        col_y, col_n = st.columns(2)
                        with col_y:
                            if st.button("✅ Ya", key=f"yes_{po}"):
                                ok, msg = close_po_status(po)
                                if ok:
                                    st.success(f"Closed!")
                                    del st.session_state[f"confirm_close_{po}"]
                                    time.sleep(1); st.rerun()
                                else: st.error(msg)
                        with col_n:
                            if st.button("❌ Batal", key=f"no_{po}"):
                                del st.session_state[f"confirm_close_{po}"]
                                st.rerun()
    else:
        st.info("Belum ada data PO Aktif.")

# ==========================================
# TAB 3: RIWAYAT PO (CLOSED) - [NEW]
# ==========================================
with tab3:
    st.markdown("### 📜 Arsip PO (Completed/Force Closed)")
    
    df_closed = get_closed_pos()
    
    if not df_closed.empty:
        for i, row in df_closed.iterrows():
            po_num = row['po_number']
            cust = row['customer_name']
            date_cls = row['created_at'][:10] # Ambil tanggal aja
            
            # Tampilan Card Simple
            with st.container():
                st.markdown(f"""
                <div style="border:1px solid #333; padding:15px; border-radius:10px; margin-bottom:10px; background:rgba(255,255,255,0.05)">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <h4 style="margin:0; color:#e5e7eb">{po_num}</h4>
                            <small style="color:#9ca3af">{cust} | Tgl PO: {date_cls}</small>
                        </div>
                        <div>
                            <span style="background:#ef4444; color:white; padding:4px 8px; border-radius:5px; font-size:12px;">CLOSED</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Tombol Download PDF
                # Kita pakai kolom buat tombolnya biar gak lebar banget
                cd1, cd2 = st.columns([4, 1])
                with cd2:
                    if st.button(f"📥 Unduh Laporan", key=f"pdf_{po_num}"):
                        with st.spinner("Generating Report..."):
                            pdf_bytes, msg = generate_po_closing_pdf(po_num)
                            if pdf_bytes:
                                st.download_button(
                                    label="📄 Click to Save PDF",
                                    data=pdf_bytes,
                                    file_name=f"Final_Report_{po_num}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{po_num}"
                                )
                            else:
                                st.error(msg)
    else:
        st.info("Belum ada riwayat PO yang ditutup.")