import streamlit as st
import pandas as pd
import time
from datetime import date, timedelta
from modules import (
    inject_premium_theme, protect_page, 
    get_supplies_stock_view, get_global_supplies_history,
    # Import fungsi baru:
    update_log_transaction_safe, delete_log_transaction_safe, get_master_item_map
)

# 1. SETUP PAGE
st.set_page_config(page_title="Monitor Stock ATK", page_icon="📋", layout="wide")
inject_premium_theme()

st.title("📋 Dashboard Stock ATK & Supplies")

# 2. LOAD DATA STOCK
if "df_atk_monitor" not in st.session_state:
    st.session_state.df_atk_monitor = get_supplies_stock_view()

if st.button("🔄 Refresh Data"):
    st.session_state.df_atk_monitor = get_supplies_stock_view()
    st.rerun()

df = st.session_state.df_atk_monitor

# --- [TAB SYSTEM] ---
tab_dash, tab_history = st.tabs(["📊 Dashboard Stock", "🗄️ Global Log History"])

# ==============================================================================
# TAB 1: DASHBOARD STOCK (EXISTING LOGIC)
# ==============================================================================
with tab_dash:
    if not df.empty:
        # Metrics
        df['status'] = df.apply(lambda x: '⚠️ LOW' if x['current_stock'] <= x['min_stock'] else '✅ OK', axis=1)
        total_low = len(df[df['status'] == '⚠️ LOW'])
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total SKU", f"{len(df)}", "Items")
        m2.metric("Perlu Restock", f"{total_low}", "Items", delta_color="inverse")
        m3.metric("Consumable", f"{len(df[df['item_category'] == 'CONSUMABLE'])}", "Items")
        m4.metric("Asset", f"{len(df[df['item_category'] == 'ASSET'])}", "Unit")

        if total_low > 0:
            st.error(f"🚨 Ada {total_low} barang stok menipis!")

        st.divider()

        # Filters (Yang kata loe usernya gak liat wkwk)
        c_filter1, c_filter2, c_filter3 = st.columns([2, 1, 1])
        search_txt = c_filter1.text_input("🔍 Cari Barang", placeholder="Nama / Spek...")
        
        # [REQUESTED FILTER] Filter User & Type ada disini
        filter_user = c_filter2.multiselect("Filter User (Allocation)", df['allocation_group'].unique() if not df.empty else [])
        filter_type = c_filter3.multiselect("Filter Tipe", df['item_category'].unique() if not df.empty else [])

        # Apply Filter
        df_show = df.copy()
        if search_txt:
            df_show = df_show[df_show['item_name'].str.contains(search_txt, case=False) | df_show['specification'].str.contains(search_txt, case=False)]
        if filter_user:
            df_show = df_show[df_show['allocation_group'].isin(filter_user)]
        if filter_type:
            df_show = df_show[df_show['item_category'].isin(filter_type)]

        # Tabel Stock
        st.dataframe(
            df_show,
            column_config={
                "item_name": "Nama Barang", "specification": "Spesifikasi",
                "allocation_group": "User", "item_category": "Tipe", "uom": "Satuan",
                "current_stock": st.column_config.ProgressColumn("Level Stok", format="%d", min_value=0, max_value=100),
                "min_stock": "Min", "total_in": "Tot In", "total_out": "Tot Out"
            },
            use_container_width=True, hide_index=True, height=400
        )
    else:
        st.info("Data Kosong.")

# ==============================================================================
# TAB 2: GLOBAL LOG HISTORY (EDITABLE & AUDITED)
# ==============================================================================
with tab_history:
    st.markdown("##### 📜 Riwayat Transaksi Global")
    
    # --- A. FILTER SECTION ---
    with st.expander("🔍 Filter Data", expanded=True):
        hc1, hc2, hc3, hc4 = st.columns(4)
        d_range = hc1.date_input("Periode", value=(date.today() - timedelta(days=30), date.today()))
        start_d, end_d = d_range if isinstance(d_range, tuple) and len(d_range) == 2 else (date.today(), date.today())
        
        # Ambil opsi filter dari session state
        user_opts = st.session_state.df_atk_monitor['allocation_group'].unique().tolist() if not st.session_state.df_atk_monitor.empty else []
        h_user = hc2.multiselect("Filter User", user_opts)
        
        h_type = hc3.multiselect("Tipe Transaksi", ["IN", "OUT"], default=["IN", "OUT"])
        
        if hc4.button("🔄 Refresh History", use_container_width=True):
            st.rerun()

    # --- B. FETCH DATA ---
    df_hist = get_global_supplies_history(start_d, end_d)
    
    # Filter Lokal
    if not df_hist.empty:
        # [FIX] Convert date string ke object date biar editor gak error
        df_hist['trx_date'] = pd.to_datetime(df_hist['trx_date']).dt.date
        
        # [NEW] Tambah kolom 'void' default False buat fitur hapus
        df_hist['is_void'] = False 

        if h_user: df_hist = df_hist[df_hist['allocation_group'].isin(h_user)]
        if h_type: df_hist = df_hist[df_hist['trx_type'].isin(h_type)]

    # --- C. MODE EDIT CONTROL ---
    st.divider()
    c_lock, c_alert = st.columns([1, 3])
    edit_mode = c_lock.toggle("🔓 Buka Mode Edit", value=False)
    
    if edit_mode:
        c_alert.warning("⚠️ **MODE EDIT AKTIF:** Centang kolom 'VOID' untuk menghapus data. Hati-hati, perubahan tercatat di Audit Trail.")
    else:
        c_alert.info("🔒 **MODE VIEW:** Data terkunci. Geser tombol untuk mengedit atau menghapus.")

    # --- D. PERSIAPAN EDITOR ---
    item_map_name_to_id, item_map_id_to_name, item_options = get_master_item_map()
    
    if not df_hist.empty:
        # 1. Bikin kolom Label buat Dropdown
        df_hist['item_label'] = df_hist['item_id'].map(item_map_id_to_name)

        # 2. [NEW] REORDER KOLOM BIAR VOID DI KIRI
        # Kita susun ulang urutan kolomnya secara manual
        # Kolom 'is_void' kita taruh paling depan
        target_order = [
            'is_void',       # <--- Juara 1 (Paling Kiri)
            'trx_date', 
            'trx_type', 
            'item_label', 
            'qty', 
            'uom', 
            'pic', 
            'notes', 
            'allocation_group', 
            # Sisanya (kolom hidden/id) taruh belakang aja
            'id', 'item_id', 'created_at', 'item_name', 'specification' 
        ]
        
        # Filter kolom biar gak error kalau ada nama kolom yg beda dikit
        final_cols = [c for c in target_order if c in df_hist.columns]
        df_hist = df_hist[final_cols]
    
    # --- E. TAMPILAN DATA ---
    if df_hist.empty:
        st.info("Tidak ada data history.")
    else:
        if not edit_mode:
            # === VIEW MODE ===
            # (Sama kayak sebelumnya)
            st.dataframe(
                df_hist[['trx_date', 'trx_type', 'item_name', 'specification', 'qty', 'uom', 'allocation_group', 'pic', 'notes']],
                column_config={
                    "trx_date": "Tanggal", "trx_type": "Tipe", "item_name": "Nama Barang",
                    "specification": "Spek", "qty": "Qty", "uom": "Sat",
                    "allocation_group": "User", "pic": "PIC", "notes": "Ket"
                },
                use_container_width=True, hide_index=True
            )
        else:
            # === EDIT MODE ===
            edited_df = st.data_editor(
                df_hist,
                key="history_editor",
                num_rows="fixed", 
                use_container_width=True,
                hide_index=True,
                column_config={
                    # [NEW] VOID COLUMN (Paling Kiri)
                    "is_void": st.column_config.CheckboxColumn(
                        "🔴 Hapus?", 
                        help="Centang untuk menghapus data ini",
                        default=False,
                        width="small" 
                    ),

                    # Editable Columns
                    "trx_date": st.column_config.DateColumn("Tanggal", required=True),
                    "trx_type": st.column_config.SelectboxColumn("Tipe", options=["IN", "OUT"], required=True, width="small"),
                    "item_label": st.column_config.SelectboxColumn("Nama Barang (Edit)", options=item_options, required=True, width="medium"),
                    "qty": st.column_config.NumberColumn("Qty", min_value=0.1, step=0.1, format="%.1f", required=True),
                    "pic": st.column_config.TextColumn("PIC", required=True),
                    "notes": st.column_config.TextColumn("Catatan"),
                    
                    # Read Only Info
                    "uom": st.column_config.TextColumn("Satuan", disabled=True),
                    "allocation_group": st.column_config.TextColumn("User Group", disabled=True),

                    # Hidden Columns
                    "id": None, "item_id": None, "created_at": None,
                    "item_name": None, "specification": None,
                },
                disabled=["uom", "allocation_group"]
            )

            # --- F. LOGIC SIMPAN & HAPUS ---
            st.caption("ℹ️ Untuk menghapus, centang kolom 'VOID?' lalu klik tombol di bawah.")
            
            # Kita pake Session State buat nampung konfirmasi hapus biar gak ilang pas refresh
            if "confirm_delete" not in st.session_state:
                st.session_state["confirm_delete"] = False
            if "payload_delete" not in st.session_state:
                st.session_state["payload_delete"] = []
            if "payload_update" not in st.session_state:
                st.session_state["payload_update"] = []

            # Tombol Utama
            if st.button("💾 PROSES PERUBAHAN", type="primary"):
                changes = st.session_state["history_editor"]
                edits = changes["edited_rows"]
                
                # Reset container
                to_delete = []
                to_update = []
                
                # Cek perubahan
                if edits:
                    for idx, new_vals in edits.items():
                        original_row = df_hist.iloc[idx]
                        
                        # Cek apakah user mencentang VOID/Hapus
                        # Logic: Kalau kolom 'is_void' diubah jadi True
                        if new_vals.get('is_void') == True:
                            to_delete.append(original_row)
                        else:
                            # Kalau bukan hapus, berarti update biasa
                            # Gabung data lama + data baru
                            final_data = original_row.to_dict()
                            final_data.update(new_vals)
                            
                            # Handle dropdown label -> item_id
                            if 'item_label' in new_vals:
                                label_baru = new_vals['item_label']
                                if label_baru in item_map_name_to_id:
                                    final_data['item_id'] = item_map_name_to_id[label_baru]
                            
                            to_update.append(final_data)

                # Simpan ke state untuk konfirmasi
                st.session_state["payload_delete"] = to_delete
                st.session_state["payload_update"] = to_update
                
                # Logic Trigger Konfirmasi
                if len(to_delete) > 0:
                    st.session_state["confirm_delete"] = True # Nyalakan mode konfirmasi
                    st.rerun()
                elif len(to_update) > 0:
                    # Kalau cuma update, langsung sikat tanpa warning seram
                    success_c = 0
                    for row in to_update:
                        ok, msg = update_log_transaction_safe(row['id'], row, st.session_state.current_user)
                        if ok: success_c += 1
                    
                    st.success(f"✅ Berhasil mengupdate {success_c} data!")
                    time.sleep(1.5)
                    st.rerun()
                else:
                    st.toast("Tidak ada perubahan.", icon="ℹ️")

            # --- G. POPUP KONFIRMASI HAPUS ---
            if st.session_state["confirm_delete"]:
                st.error(f"⚠️ **PERINGATAN KERAS!**")
                st.write(f"Anda akan menghapus **{len(st.session_state['payload_delete'])} data transaksi**.")
                st.write("Data yang dihapus akan hilang dari stok dan history, namun tercatat di Audit Trail.")
                
                col_confirm1, col_confirm2 = st.columns(2)
                
                if col_confirm1.button("✅ YA, HAPUS PERMANEN", type="primary"):
                    del_count = 0
                    # 1. Eksekusi Hapus
                    for row in st.session_state["payload_delete"]:
                        ok, msg = delete_log_transaction_safe(row['id'], st.session_state.current_user)
                        if ok: del_count += 1
                    
                    # 2. Eksekusi Update (kalau ada update barengan hapus)
                    upd_count = 0
                    for row in st.session_state["payload_update"]:
                        ok, msg = update_log_transaction_safe(row['id'], row, st.session_state.current_user)
                        if ok: upd_count += 1
                        
                    st.success(f"✅ Selesai! Dihapus: {del_count}, Diupdate: {upd_count}")
                    
                    # Reset State
                    st.session_state["confirm_delete"] = False
                    st.session_state["payload_delete"] = []
                    st.session_state["payload_update"] = []
                    time.sleep(2)
                    st.rerun()
                    
                if col_confirm2.button("❌ BATAL"):
                    st.session_state["confirm_delete"] = False
                    st.session_state["payload_delete"] = []
                    st.session_state["payload_update"] = []
                    st.rerun()