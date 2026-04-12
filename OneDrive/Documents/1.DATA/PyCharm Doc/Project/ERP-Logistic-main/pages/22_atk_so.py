import streamlit as st
import pandas as pd
from datetime import date
import time
from modules import (
    inject_premium_theme, protect_page, 
    get_supplies_stock_view, submit_atk_adjustment, get_atk_adjustment_history
)

st.set_page_config(page_title="STO ATK", page_icon="📝", layout="wide")
inject_premium_theme()
protect_page("warehouse") # Sesuaikan role akses lo

st.page_link("main.py", label="Kembali ke Dashboard", icon="🏠")
st.title("📝 Stock Opname ATK & Supplies")

if "cart_sto_atk" not in st.session_state: st.session_state.cart_sto_atk = []

# Load Master Stock
df_stock = get_supplies_stock_view()

tab1, tab2 = st.tabs(["📝 Input STO", "📜 Riwayat Adjustment"])

# ==========================================
# TAB 1: INPUT & EKSEKUSI (MOBILE FRIENDLY)
# ==========================================
with tab1:
    if df_stock.empty:
        st.warning("Master Data ATK Kosong.")
    else:
        # [NEW] 1. Bikin Kolom Display Gabungan (Name + Spec)
        # Kita bikin kolom baru di memory dataframe biar dropdown-nya informatif
        df_stock['display_label'] = df_stock.apply(
            lambda x: f"{x['item_name']} - {x['specification']}" if x['specification'] and x['specification'] != '-' else x['item_name'], 
            axis=1
        )

        # A. FILTERING
        with st.expander("🔍 Filter & Pencarian Barang", expanded=False):
            c_f1, c_f2 = st.columns(2)
            
            user_list = df_stock['allocation_group'].unique().tolist()
            filter_user = c_f1.multiselect("Divisi / User", user_list)
            
            cat_list = df_stock['item_category'].unique().tolist()
            filter_cat = c_f2.multiselect("Kategori", cat_list)
            
            # Apply Filter
            df_filtered = df_stock.copy()
            if filter_user:
                df_filtered = df_filtered[df_filtered['allocation_group'].isin(filter_user)]
            if filter_cat:
                df_filtered = df_filtered[df_filtered['item_category'].isin(filter_cat)]
                
            # [CHANGED] Ambil list dari kolom 'display_label' yg baru kita bikin
            filtered_items = df_filtered['display_label'].tolist()

        # B. INPUT FORM
        st.markdown("#### 1. Input Hasil Hitung")
        
        # Row 1: Pilih Barang
        # [NOTE] sel_item isinya sekarang: "Cable Ties - 20cm Hitam"
        sel_item = st.selectbox("Pilih Barang dari List", filtered_items, key="sel_atk")
        
        # [CHANGED] Logic ambil detail barang harus dicocokin sama 'display_label' juga
        # Kalau lo cari pake 'item_name' == sel_item bakal error karena sel_item udah ada embel-embel speknya
        row_item = df_stock[df_stock['display_label'] == sel_item].iloc[0] if sel_item else None
        
        # ... (Sisa kode ke bawah sama persis, karena kita cuma butuh row_item yang bener)
        curr_sys = int(row_item['current_stock']) if row_item is not None else 0
        uom_txt = row_item['uom'] if row_item is not None else ""
        
        # Row 2: Info System & Input Fisik (Split 50:50 biar rapi di HP)
        c_info, c_input = st.columns([1, 1])
        
        with c_info:
            # Tampilan ala Card Stat
            st.caption("Stok System")
            st.markdown(f"<h3 style='margin:0; color:#4a90e2;'>{curr_sys} <span style='font-size:14px; color:#888;'>{uom_txt}</span></h3>", unsafe_allow_html=True)
            
        with c_input:
            # Input lebih gede
            act_qty = st.number_input("Stok Fisik (Actual)", min_value=0, step=1, key="qty_atk")
            
        # Row 3: Tombol Add (Full Width - Enak dipencet jempol)
        st.write("")
        if st.button("➕ Tambahkan ke List Audit", type="primary", use_container_width=True):
            if row_item is not None:
                # Logic Add/Update Cart sama persis
                existing_idx = next((index for (index, d) in enumerate(st.session_state.cart_sto_atk) if d["id"] == row_item['id']), None)
                
                new_data = {
                    "id": row_item['id'], 
                    "item_name": sel_item,
                    "spec": row_item['specification'],
                    "system": curr_sys,
                    "actual": int(act_qty),
                    "diff": int(act_qty) - curr_sys
                }
                
                if existing_idx is not None:
                    st.session_state.cart_sto_atk[existing_idx] = new_data
                    st.toast(f"Updated: {sel_item}")
                else:
                    st.session_state.cart_sto_atk.append(new_data)
                    st.toast(f"Added: {sel_item}")
                    
        # C. TABEL REVIEW (CART)
        if st.session_state.cart_sto_atk:
            st.divider()
            st.markdown("#### 2. Review List (Edit jika salah)")
            
            df_cart = pd.DataFrame(st.session_state.cart_sto_atk)
            
            # Mobile Friendly Config: Sembunyikan 'Spec' biar gak lebar ke samping
            edited_df = st.data_editor(
                df_cart,
                column_config={
                    "item_name": st.column_config.TextColumn("Nama", disabled=True, width="medium"),
                    "spec": None, # Hide Spec di HP biar muat
                    "system": st.column_config.NumberColumn("Sys", disabled=True, width="small"),
                    "actual": st.column_config.NumberColumn("Fisik", required=True, width="small"),
                    "diff": None, # Hide Diff sementara, itung di backend aja biar ringkas
                    "id": None 
                },
                use_container_width=True,
                hide_index=True,
                num_rows="dynamic",
                key="editor_atk"
            )
            
            # Sync Edit
            final_cart = []
            for idx, row in edited_df.iterrows():
                row['diff'] = row['actual'] - row['system']
                final_cart.append(row.to_dict())
            
            st.session_state.cart_sto_atk = final_cart

            # D. FINAL SUBMIT (Stacked Layout)
            st.markdown("---")
            st.markdown("##### 3. Finalisasi")
            
            # Stacked vertical biar aman di HP
            adj_date = st.date_input("Tanggal STO", value=date.today())
            pic_name = st.text_input("Nama PIC (Checker)", placeholder="Wajib diisi...")
            
            st.write("")
            if st.button("⚖️ POST / SIMPAN ADJUSTMENT", type="primary", use_container_width=True):
                if not pic_name:
                    st.error("⚠️ Nama PIC Wajib Diisi!")
                else:
                    with st.spinner("Menyimpan data..."):
                        success, msg = submit_atk_adjustment(adj_date, final_cart, pic_name)
                        if success:
                            st.success(msg)
                            st.session_state.cart_sto_atk = [] 
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(msg)

# ==========================================
# TAB 2: HISTORY & REPORT (REPLACE THIS SECTION)
# ==========================================
with tab2:
    st.markdown("### 📜 Laporan & Riwayat STO")
    
    # --- A. CONTROL BAR (Filter & Download) ---
    with st.container(border=True):
        c_date1, c_date2, c_btn = st.columns([1, 1, 2])
        
        # Default: Bulan berjalan (Tanggal 1 s/d Hari ini)
        today = date.today()
        first_day = today.replace(day=1)
        
        start_d = c_date1.date_input("Dari Tanggal", value=first_day)
        end_d = c_date2.date_input("Sampai Tanggal", value=today)
        
        # Tombol Download PDF
        # Note: Tombol ini mentrigger fungsi baru di modules.py
        from modules import generate_atk_sto_pdf # Import lokal biar aman
        
        with c_btn:
            st.write("") # Spacer biar sejajar
            st.write("")
            if st.button("🖨️ Download Laporan PDF (A4 Landscape)", type="secondary", use_container_width=True):
                with st.spinner("Generating PDF..."):
                    pdf_bytes, status_msg = generate_atk_sto_pdf(start_d, end_d)
                    if pdf_bytes:
                        st.success(status_msg)
                        st.download_button(
                            label="📥 Klik Disini untuk Simpan PDF",
                            data=pdf_bytes,
                            file_name=f"Laporan_STO_ATK_{start_d}_{end_d}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                    else:
                        st.error(status_msg)

    # --- B. TABLE PREVIEW ---
    st.markdown("##### Preview Data")
    
    # Tarik data manual buat preview di layar (Logic filter di python pandas)
    df_hist_all = get_atk_adjustment_history(200) # Ambil 200 terakhir
    
    if not df_hist_all.empty:
        # Filter Dataframe Local sesuai tanggal input user biar match sama PDF
        # Convert kolom adjust_date ke datetime biar bisa dicompare
        df_hist_all['adjust_date'] = pd.to_datetime(df_hist_all['adjust_date']).dt.date
        
        mask = (df_hist_all['adjust_date'] >= start_d) & (df_hist_all['adjust_date'] <= end_d)
        df_show = df_hist_all[mask]
        
        if not df_show.empty:
            st.dataframe(
                df_show[['adjust_date', 'item_name', 'qty_system', 'qty_actual', 'qty_diff', 'status', 'pic']],
                column_config={
                    "adjust_date": "Tgl",
                    "item_name": "Barang",
                    "qty_system": "System",
                    "qty_actual": "Fisik",
                    "qty_diff": "Selisih",
                    "status": "Status",
                    "pic": "PIC"
                },
                use_container_width=True,
                hide_index=True
            )
            st.caption(f"Menampilkan {len(df_show)} data periode terpilih.")
        else:
            st.info(f"Tidak ada data STO pada rentang {start_d} s/d {end_d}.")
    else:
        st.info("Belum ada data history STO sama sekali.")