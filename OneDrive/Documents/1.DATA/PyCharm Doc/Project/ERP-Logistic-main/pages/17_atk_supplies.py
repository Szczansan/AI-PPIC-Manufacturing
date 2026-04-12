import streamlit as st
import pandas as pd
import time
from datetime import date
from modules import (
    inject_premium_theme, protect_page, 
    get_supplies_stock_view, manage_supply_item, submit_supply_trx
)

# 1. SETUP PAGE
st.set_page_config(page_title="ATK & Supplies", page_icon="✏️", layout="wide")
inject_premium_theme()
protect_page('warehouse') 

st.title("✏️ ATK & General Supplies Management")
st.caption("Mode: Excel View (Master Data & Transaksi Harian)")

# 2. LOAD DATA
if "df_atk" not in st.session_state:
    st.session_state.df_atk = get_supplies_stock_view()

# Tombol Refresh Manual
if st.button("🔄 Refresh Data"):
    st.session_state.df_atk = get_supplies_stock_view()
    st.rerun()

# 3. FITUR ADD NEW ITEM (Expander)
with st.expander("➕ Tambah Barang Baru (Master Data)"):
    with st.form("add_atk_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_name = st.text_input("Nama Barang", placeholder="Contoh: Pulpen Standard")
            new_spec = st.text_input("Spesifikasi", placeholder="Contoh: AE7 Hitam")
        with c2:
            new_user = st.selectbox("User / Allocation", ["Produksi", "Office", "Logistik", "Maintenance", "General Affair"])
            new_type = st.selectbox("Type", ["CONSUMABLE", "TOOLS", "ASSET"])
        with c3:
            uom_opts = ["PCS", "PACK", "BOX", "SET", "KG", "LITER", "TUBE", "UNIT", "LEMBAR", "METER", "ROLL"]
            new_uom = st.selectbox("Satuan (UOM)", uom_opts)
            new_min = st.number_input("Min. Stock Alert", min_value=0, value=5)
        
        submitted = st.form_submit_button("Simpan Barang Baru")
        
        if submitted:
            if not new_name:
                st.error("Nama Barang wajib diisi!")
            else:
                payload = {
                    "item_name": new_name,
                    "specification": new_spec,
                    "allocation_group": new_user,
                    "item_category": new_type,
                    "uom": new_uom,
                    "min_stock": new_min
                }
                success, msg = manage_supply_item('INSERT', data_payload=payload)
                if success:
                    st.success(msg)
                    time.sleep(1)
                    st.session_state.df_atk = get_supplies_stock_view()
                    st.rerun()
                else:
                    st.error(msg)

# 4. TABEL UTAMA (EDITOR)
st.markdown("### 📦 Stock Monitor (Edit Mode)")
df_current = get_supplies_stock_view()

edited_df = st.data_editor(
    df_current,
    key="atk_editor",
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
        "item_name": st.column_config.TextColumn("Nama Barang", required=True),
        "specification": st.column_config.TextColumn("Spesifikasi"),
        "allocation_group": st.column_config.SelectboxColumn("User", options=["Produksi", "Office", "Logistik", "Maintenance", "General Affair"]),
        "item_category": st.column_config.SelectboxColumn("Type", options=["CONSUMABLE", "TOOLS", "ASSET"]),
        "uom": st.column_config.SelectboxColumn("Satuan", options=["PCS", "PACK", "BOX", "SET", "KG", "LITER", "TUBE", "UNIT", "LEMBAR", "METER", "ROLL"]), 
        "current_stock": st.column_config.NumberColumn("Stok Aktif", disabled=True, help="Stok dihitung dari History IN-OUT"),
        "total_in": st.column_config.NumberColumn("Tot Masuk", disabled=True),
        "total_out": st.column_config.NumberColumn("Tot Keluar", disabled=True),
        "is_active": st.column_config.CheckboxColumn("Active?", default=True)
    },
    hide_index=True
)

if st.button("💾 Simpan Perubahan Master Data"):
    try:
        changes_count = 0
        for index, row in edited_df.iterrows():
            payload = {
                "item_name": row['item_name'],
                "specification": row['specification'],
                "allocation_group": row['allocation_group'],
                "item_category": row['item_category'],
                "uom": row['uom'],
                "is_active": row['is_active']
            }
            manage_supply_item('UPDATE', data_payload=payload, item_id=row['id'])
            changes_count += 1
            
        st.success(f"✅ Berhasil update {changes_count} data!")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"Gagal update: {e}")

# 5. TRANSAKSI STOCK (IN / OUT)
st.divider()
st.subheader("🔄 Transaksi Keluar Masuk (IN/OUT)")

c_in, c_out = st.columns(2)

# Siapkan list barang buat dropdown
item_map = {} 
item_list = []

if not df_current.empty:
    for idx, row in df_current.iterrows():
        spec_txt = row['specification'] if row['specification'] else ""
        display_name = f"{row['item_name']} | {spec_txt}"
        item_list.append(display_name)
        item_map[display_name] = row

# === LOGIC BARANG MASUK ===
with c_in:
    st.info("⬇️ Barang Masuk (Pembelian/Restock)")
    
    # 1. Selectbox Barang (Diluar Form)
    selected_str_in = st.selectbox("Pilih Barang Masuk", item_list, key="sel_in", index=None, placeholder="Cari Barang...")
    
    uom_val_in = "-"
    if selected_str_in and selected_str_in in item_map:
        uom_val_in = item_map[selected_str_in]['uom']
        
    with st.form("trx_in_form"):
        # Tanggal (Default Hari Ini)
        tgl_in = st.date_input("Tanggal Masuk", value=date.today())
        
        # UOM Display
        st.text_input("Satuan (UOM)", value=uom_val_in, disabled=True)
        
        # Qty
        qty_in = st.number_input("Qty Masuk", min_value=0.1, step=0.1, format="%.1f", key="qty_in")
        
        # [NEW] Nama Penerima (Default: User Login)
        receiver_in = st.text_input("Diterima Oleh (PIC)", value=st.session_state.current_user, placeholder="Nama staff gudang...")
        
        # Notes
        note_in = st.text_input("Catatan / No PO", key="note_in")
        
        if st.form_submit_button("Submit Masuk"):
            if not selected_str_in:
                st.error("Pilih barang dulu!")
            elif not receiver_in:
                st.error("Nama Penerima wajib diisi!")
            else:
                item_row = item_map[selected_str_in]
                
                # Kita gabungin user system ke notes, PIC diisi nama penerima
                final_note = f"{note_in} (System Input: {st.session_state.current_user})"
                
                ok, msg = submit_supply_trx(
                    item_id=int(item_row['id']), 
                    trx_type='IN', 
                    qty=qty_in, 
                    pic=receiver_in, # <--- Masuk kolom PIC
                    notes=final_note, 
                    custom_date=tgl_in
                )
                if ok: st.success(msg); time.sleep(1); st.rerun()
                else: st.error(msg)

# === LOGIC BARANG KELUAR ===
with c_out:
    st.warning("⬆️ Barang Keluar (Pakai/Ambil)")
    
    # Selectbox Barang (Diluar Form)
    selected_str_out = st.selectbox("Pilih Barang Keluar", item_list, key="sel_out", index=None, placeholder="Cari Barang...")
    
    uom_val_out = "-"
    stok_val_out = "0"
    if selected_str_out and selected_str_out in item_map:
            uom_val_out = item_map[selected_str_out]['uom']
            # Tampilkan float biar user tau sisa 0.5
            stok_val_out = str(float(item_map[selected_str_out]['current_stock']))
        
    with st.form("trx_out_form"):
        # Tanggal
        tgl_out = st.date_input("Tanggal Pengambilan", value=date.today())
        
        # Info UOM & Stok
        c_info1, c_info2 = st.columns(2)
        with c_info1:
            st.text_input("Satuan (UOM)", value=uom_val_out, disabled=True)
        with c_info2:
            st.text_input("Sisa Stok Sistem", value=stok_val_out, disabled=True)
            
        qty_out = st.number_input("Qty Keluar", min_value=0.1, step=0.1, format="%.1f", key="qty_out")
        
        # Nama Pengambil
        taker_name = st.text_input("Nama Pengambil (PIC)", placeholder="Contoh: Rudy / Pak Budi", key="pic_out") 
        
        note_out = st.text_input("Keperluaan", placeholder="Contoh: Meeting / Stok Ruangan", key="note_out")
        
        if st.form_submit_button("Submit Keluar"):
            if not selected_str_out:
                st.error("Data Barang Kosong!")
            elif not taker_name:
                st.error("⚠️ Nama Pengambil (PIC) wajib diisi!")
            else:
                item_row = item_map[selected_str_out]
                curr_qty = float(item_row['current_stock']) # <--- PENTING: Ganti int() jadi float()
                
                if qty_out > curr_qty:
                    # Tampilkan pesan error yang lebih presisi
                    st.error(f"⛔ Stok tidak cukup! Sisa cuma {curr_qty} {uom_val_out}")
                else:
                    final_note = f"{note_out} (System Input: {st.session_state.current_user})"
                    
                    ok, msg = submit_supply_trx(
                        item_id=int(item_row['id']), 
                        trx_type='OUT', 
                        qty=qty_out, 
                        pic=taker_name,
                        notes=final_note,
                        custom_date=tgl_out
                    )
                    
                    if ok: st.success(msg); time.sleep(1); st.rerun()
                    else: st.error(msg)