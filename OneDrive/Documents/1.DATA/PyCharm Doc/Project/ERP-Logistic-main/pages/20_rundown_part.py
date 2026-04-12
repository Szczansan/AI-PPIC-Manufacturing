import streamlit as st
import pandas as pd
from datetime import date
import time
from supabase_client import supabase 
import textwrap # Library buat ngerapihin HTML

# Import Backend
from modules_ppc import (
    get_ppc_po_list, 
    get_po_items_details,
    get_bom_details_by_part_no, 
    add_bom_item,            # [UPDATED] Fungsi universal baru
    delete_bom_item,
    get_daily_usage_analysis,
    get_raw_materials_list   # [NEW] Fungsi tarik data Resin
)
from modules import inject_premium_theme, protect_page, get_child_parts
from modules import generate_usage_report_pdf

# SETUP
st.set_page_config(page_title="Rundown & Usage", page_icon="🧩", layout="wide")
inject_premium_theme()
protect_page('production')

st.title("🧩 Rundown Part & Usage Control")

def load_part_numbers():
    try:
        res = supabase.table("products").select("part_no, part_name").order("part_name").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

# === TAB NAVIGATION ===
tab1, tab2 = st.tabs(["📝 Register Rundown (BOM)", "🔍 Monitor Usage (Report)"])

# ============================================
# TAB 1: UI BARU "IDENTITY CARD"
# ============================================
with tab1:
    st.markdown("#### Step 1: Cari Identitas Produk (Part Number)")
    df_prods = load_part_numbers()
    
    if not df_prods.empty:
        prod_options = [f"{row['part_no']} | {row['part_name']}" for i, row in df_prods.iterrows()]
        selected_option = st.selectbox("Pilih Produk:", prod_options, placeholder="Ketik Part Number atau Nama...")
        
        if selected_option:
            selected_part_no = selected_option.split(" | ")[0].strip()
            
            st.markdown("---")
            st.markdown("#### Step 2: Spesifikasi & BOM")
            
            # CALL BACKEND
            data = get_bom_details_by_part_no(selected_part_no)
            
            if data.get('error'):
                st.error(f"❌ Error Database: {data['error']}")
                st.stop()
            
            master = data['master']
            children = data['children']
            real_uuid = master.get('id')
            
            has_specs = master.get('material_type') and master.get('part_weight') and float(master.get('part_weight') or 0) > 0
            
            card_color = "#1f2937" 
            status_icon = "⚠️"
            status_text = "Data Spek Belum Lengkap (Cek Master Data)"
            
            if has_specs:
                card_color = "rgba(16, 185, 129, 0.1)" 
                status_icon = "✅"
                status_text = "Data Spesifikasi Lengkap"

            # UI CARD
            card_html = f"""
<div style="background-color: {card_color}; padding: 20px; border-radius: 10px; border: 1px solid #374151; margin-bottom: 20px;">
<h3 style="margin:0; color:white;">{master.get('part_name')}</h3>
<p style="color:#9ca3af; font-family:monospace; margin-bottom: 15px;">PART NO: {selected_part_no}</p>

<div style="display:flex; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
<div style="min-width: 140px;">
<span style="color:#6b7280; font-size:12px;">MATERIAL TYPE</span><br>
<span style="font-size:18px; font-weight:bold; color:#f3f4f6;">{master.get('material_type') or '-'}</span>
</div>
<div style="min-width: 140px;">
<span style="color:#6b7280; font-size:12px;">COLOR</span><br>
<span style="font-size:18px; font-weight:bold; color:#f3f4f6;">{master.get('material_color') or '-'}</span>
</div>
<div style="min-width: 140px;">
<span style="color:#6b7280; font-size:12px;">WEIGHT (NET)</span><br>
<span style="font-size:18px; font-weight:bold; color:#34d399;">{master.get('part_weight') or 0} Gr</span>
</div>
<div style="min-width: 100px;">
<span style="color:#6b7280; font-size:12px;">CAVITY</span><br>
<span style="font-size:18px; font-weight:bold; color:#f3f4f6;">{master.get('cav') or '-'}</span>
</div>
</div>
<hr style="border-color:#374151; margin-top: 15px; margin-bottom: 15px;">
<small style="color:#d1d5db;">{status_icon} Status: {status_text}</small>
</div>
"""
            st.markdown(textwrap.dedent(card_html), unsafe_allow_html=True)
            
            # CONFIG INPUT BOM
            c_input, c_table = st.columns([1, 2])
            
            with c_input:
                st.subheader("➕ Add Component")
                
                # [NEW] RADIO BUTTON SELECTOR
                comp_type = st.radio("Tipe Komponen:", ["Child Part", "Resin / Masterbatch"], horizontal=True)
                
                # Fetch Data berdasarkan pilihan Radio
                if comp_type == "Child Part":
                    df_master = get_child_parts()
                    type_flag = "CHILD"
                else:
                    df_master = get_raw_materials_list()
                    type_flag = "RESIN"
                
                if not df_master.empty:
                    # Tentukan kolom nama yang mau diambil (part_name untuk Part, full_name untuk Resin)
                    name_col = 'part_name' if type_flag == "CHILD" else 'full_name'
                    
                    item_opts = {f"{r[name_col]}": r['id'] for i, r in df_master.iterrows()}
                    sel_item = st.selectbox("Pilih Item:", list(item_opts.keys()))
                    
                    qty_usage = st.number_input(
                        "Qty Usage per Pcs/Unit (Kg/Pcs):", 
                        min_value=0.0, 
                        step=0.01, 
                        format="%.3f", 
                        help="Support Desimal (Contoh: 0.5 atau 0.05)"
                    )
                    
                    if st.button(f"Simpan {comp_type}"):
                        ok, msg = add_bom_item(real_uuid, item_opts[sel_item], qty_usage, type_flag)
                        if ok: 
                            st.success(msg)
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error(msg)
                else:
                    st.warning(f"Data Master {comp_type} Masih Kosong!")
            
            with c_table:
                st.subheader("📋 Component List")
                if children:
                    df_view = pd.DataFrame(children)
                    st.dataframe(
                         df_view[['name', 'usage']], 
                         use_container_width=True,
                         column_config={
                             "name": "Component Name", 
                             "usage": st.column_config.NumberColumn("Qty/Unit", format="%.2f") 
                         }
                    )
                    
                    del_id = st.selectbox("Hapus ID:", [c['id'] for c in children], format_func=lambda x: "Select to Delete...")
                    if st.button("🗑️ Remove Component"):
                         if delete_bom_item(del_id): st.rerun()
                else:
                    st.info("Belum ada komponen dalam BOM.")

# ============================================
# TAB 2: MONITORING USAGE & REPORT
# ============================================
with tab2:
    # --- [BAGIAN 1: FITUR REPORT PDF] ---
    st.header("🖨️ Production Report Center")
    
    with st.expander("📄 MENU DOWNLOAD LAPORAN (PDF)", expanded=True):
        c_rep1, c_rep2, c_rep3 = st.columns([2, 2, 1])
        
        with c_rep1:
            pdf_start = st.date_input("Dari Tanggal", date.today().replace(day=1), key="pdf_d1")
            pdf_end = st.date_input("Sampai Tanggal", date.today(), key="pdf_d2")
            
            # [NEW] Dropdown Filter Part Name
            df_parts_avail = load_part_numbers()
            part_opts = ["All"] + df_parts_avail['part_name'].unique().tolist() if not df_parts_avail.empty else ["All"]
            sel_part_filter = st.selectbox("Filter Part Name:", part_opts, key="pdf_part_filter")
        
        with c_rep2:
            st.write("<b>Filter Kolom Data:</b>", unsafe_allow_html=True)
            show_resin = st.checkbox("Include Raw Material (Resin)", value=True, key="chk_res")
            show_child = st.checkbox("Include Components (Child Part)", value=True, key="chk_child")
        
        with c_rep3:
            st.write("") 
            st.write("") 
            st.write("") # Spacer extra biar sejajar sama input date yang numpuk
            if st.button("🚀 Generate PDF", use_container_width=True, key="btn_pdf"):
                if not show_resin and not show_child:
                    st.warning("⚠️ Pilih minimal satu filter data!")
                else:
                    with st.spinner("Sedang menarik data & hitung usage..."):
                        # [NEW] Pass sel_part_filter ke backend
                        pdf_file, msg = generate_usage_report_pdf(pdf_start, pdf_end, show_resin, show_child, sel_part_filter)
                        
                        if pdf_file:
                            st.success(msg)
                            filename = f"Report_{sel_part_filter}_{pdf_start}.pdf" if sel_part_filter != "All" else f"Report_All_{pdf_start}.pdf"
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_file,
                                file_name=filename,
                                mime="application/pdf",
                                type="primary"
                            )
                        else:
                            st.error(msg)
    
    st.markdown("---")

    # --- [BAGIAN 2: FITUR CCTV MONITORING (LAMA)] ---
    # (Biarkan code CCTV loe yang di bawah ini tetap utuh seperti sebelumnya)
    st.header("🕵️ Production Usage CCTV (Total Shot)")
    st.info("💡 Note: Perhitungan Material & Komponen berdasarkan TOTAL SHOT (Good + NG).")
    
    po_list = get_ppc_po_list()
    sel_po = st.selectbox("Pilih PO Active:", po_list, key="cctv_po")
    
    if sel_po:
        po_no = sel_po.split(" | ")[0]
        df_items = get_po_items_details(po_no)
        
        if not df_items.empty:
            target_part_name = st.selectbox("Pilih Item PO:", df_items['part_name'].unique())
            target_part_no = df_items[df_items['part_name'] == target_part_name].iloc[0]['part_no']
            target_qty_po = df_items[df_items['part_name'] == target_part_name].iloc[0]['qty_order']
            
            c_d1, c_d2 = st.columns(2)
            start_d = c_d1.date_input("Mulai:", date.today().replace(day=1))
            end_d = c_d2.date_input("Sampai:", date.today())
            st.markdown("---")
            
            prod_info = get_bom_details_by_part_no(target_part_no)
            if not prod_info.get('error'):
                 real_id_for_report = prod_info['master'].get('id')
                 
                 df_daily, summary_data = get_daily_usage_analysis(real_id_for_report, target_part_no, start_d, end_d)
                 
                 if not df_daily.empty:
                     real_total_shot = df_daily['total_qty'].sum() 
                     
                     st.markdown("##### 🏁 Statistik Pemakaian")
                     m1, m2 = st.columns(2)
                     m1.metric("Target PO (Good Part)", f"{target_qty_po:,.0f} Pcs")
                     m2.metric("Total Shot (Input Basis)", f"{real_total_shot:,.0f} Cycle")
                     
                     st.write("")
                     with st.expander("📅 Rincian Harian"):
                        st.dataframe(
                            df_daily, 
                            use_container_width=True,
                            column_config={
                                "date_in": "Tanggal", 
                                "total_qty": st.column_config.NumberColumn("Total Shot", format="%d")
                            }
                        )

                     st.markdown("---")
                     st.subheader("📊 Consumption Summary & Forecast")
                     
                     if summary_data:
                         mat_list = []
                         child_list = []
                         
                         for item in summary_data:
                             rem_target = target_qty_po - real_total_shot 
                             if rem_target < 0: rem_target = 0
                             
                             avg_usage = item['val'] / real_total_shot if real_total_shot > 0 else 0
                             est_need = rem_target * avg_usage
                             
                             if item['type'] in ['MATERIAL', 'MIX']:
                                 mat_list.append({
                                     "Item Material": item['name'],
                                     "Total Used": f"{item['val']/1000:,.2f} Kg",
                                     "Forecast (Sisa PO)": f"{est_need/1000:,.2f} Kg"
                                 })
                             else:
                                 child_list.append({
                                     "Item Component": item['name'],
                                     "Total Used": f"{item['val']:,.2f} Unit", 
                                     "Forecast (Sisa PO)": f"{est_need:,.2f} Unit"
                                 })
                         
                         c_mat, c_child = st.columns(2)
                         with c_mat:
                             st.markdown("###### 🛢️ Material Consumption (Kg)")
                             if mat_list: st.table(pd.DataFrame(mat_list))
                             else: st.info("No Material Data.")
                                 
                         with c_child:
                             st.markdown("###### 🔧 Components / Fluid Consumption")
                             if child_list: st.table(pd.DataFrame(child_list))
                             else: st.info("No Components Data.")
                     else:
                         st.info("Belum ada data produksi.")
            else:
                st.error("Data BOM Missing.")