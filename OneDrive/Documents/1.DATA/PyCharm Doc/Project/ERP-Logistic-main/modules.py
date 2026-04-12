import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase_client import supabase
from fpdf import FPDF
import math
import io
import uuid

# ==============================================================================
# 0. GLOBAL UTILITIES & SECURITY (THEME, AUTH, PAGINATION)
# ==============================================================================
def inject_premium_theme():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
        .stApp { background-image: radial-gradient(circle at 10% 20%, rgba(124, 242, 212, 0.03), transparent 25%), radial-gradient(circle at 80% 0%, rgba(122, 165, 255, 0.03), transparent 30%); background-attachment: fixed; }
        .glass-panel { background: rgba(23, 33, 56, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2); }
        [data-testid="stDataFrame"] { background: rgba(16, 22, 39, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; }
        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div { background-color: rgba(10, 14, 23, 0.6); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 10px; color: #e8edf7; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True
    )

@st.cache_data(ttl=3600) 
def get_all_users():
    try:
        res = supabase.table("user_access").select("username").order("username").execute()
        return [item['username'] for item in res.data]
    except: return []

def check_user_access(username, module_name):
    # 1. GOD MODE (Super Admin) - Akses Jebol Semua
    god_mode_users = ['Dede', 'Fauzan', 'Aqil_N', 'Rudy_C']
    if username in god_mode_users: 
        return True

    # 2. DEFINISI PERMISSION PER USER
    permissions = {
        'Adit': ['production', 'master_data', 'control_po', 'scrap', 'atk'],
        'Rudy_L': ['warehouse', 'shipping', 'material', 'return', 'atk'],
        'E_Solihin': ['warehouse', 'shipping', 'material', 'return', 'atk']
    }

    # 3. CEK APAKAH MODULE ADA DI LIST USER
    user_perms = permissions.get(username, [])
    return module_name in user_perms

def protect_page(required_module):
    if "current_user" not in st.session_state or not st.session_state.current_user:
        st.warning("⚠️ Silakan Login Terlebih Dahulu!"); st.stop()
    user = st.session_state.current_user
    if not check_user_access(user, required_module):
        st.error(f"⛔ Akses Ditolak! Anda tidak memiliki izin modul: {required_module}"); st.stop()

def get_history_paginated(table_name, page, page_size, date_start, date_end, search_col=None, search_term=None):
    try:
        offset = (page - 1) * page_size
        limit = offset + page_size - 1 
        query = supabase.table(table_name).select("*", count='exact')\
            .gte("created_at", f"{date_start} 00:00:00")\
            .lte("created_at", f"{date_end} 23:59:59")
        if search_col and search_term:
            query = query.ilike(search_col, f"%{search_term}%")
        res = query.order("created_at", desc=True).range(offset, limit).execute()
        return pd.DataFrame(res.data), res.count
    except Exception as e:
        return pd.DataFrame(), 0

def generate_doc_number(trx_type='IN'):
    try:
        today = datetime.now(); date_str = today.strftime("%m-%d")
        prefix = "TRF-IN" if trx_type == 'IN' else "TRF-OUT"
        table = "wip_in" if trx_type == 'IN' else "wip_out"
        date_col = "date_in" if trx_type == 'IN' else "date_out"
        res = supabase.table(table).select("id", count="exact").eq(date_col, today.strftime("%Y-%m-%d")).execute()
        count = res.count if res.count else 0
        return f"{prefix}/{date_str}/{count + 1:04d}"
    except: return "DRAFT"

def save_log_audit(log_id, action, old_data, new_data, user):
    try:
        payload = {
            "log_id": log_id,
            "action_type": action,
            "old_data": old_data,
            "new_data": new_data,
            "changed_by": user
        }
        supabase.table("audit_log_supplies").insert(payload).execute()
    except Exception as e:
        print(f"Audit Error: {e}")

# ==============================================================================
# 1. production_entry
# ==============================================================================
@st.cache_data(ttl=60)
def get_ng_types():
    try:
        res = supabase.table("master_ng_types").select("*").order("ng_name").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def add_new_ng_type(ng_name):
    try:
        supabase.table("master_ng_types").insert({"ng_name": ng_name.upper()}).execute()
        st.cache_data.clear()
        return True
    except: return False

def submit_production_logsheet(header_data, ng_list, downtime_list):
    try:
        total_dt_min = sum([x['duration'] for x in downtime_list])
        payload = {
            "date_in": str(header_data['date']), "shift": header_data['shift'],
            "machine_no": header_data['machine'], "operator_name": header_data['operator'],
            "doc_no": header_data['doc_no'], "part_name": header_data['part_name'],
            "part_no": header_data['part_no'], "part_weight_act": header_data['part_weight_act'],
            "act_cycle_time": header_data['act_cycle_time'], "plan_qty": int(header_data['plan_qty']),
            "total_qty": int(header_data['total_qty']), "qty": int(header_data['qty_ok']),
            "total_ng": int(header_data['total_ng']), "ng_detail": ng_list,
            "total_downtime": total_dt_min, "downtime_detail": downtime_list,
            "problem_category": downtime_list[0]['category'] if downtime_list else None,
            "notes": header_data.get('notes', '-')
        }
        supabase.table("wip_in").insert(payload).execute()
        return True, "✅ Laporan Produksi Berhasil Disimpan!"
    except Exception as e: return False, f"❌ Error Database: {str(e)}"

# ==============================================================================
# 2. production_dashboard & 19. ppc_dashboard
# ==============================================================================
def get_wip_report_by_date(target_date):
    try: return pd.DataFrame(supabase.rpc('get_wip_daily_report', {'target_date': str(target_date)}).execute().data)
    except: return pd.DataFrame()

def get_fg_report_by_date(target_date):
    try: return pd.DataFrame(supabase.rpc('get_fg_daily_report', {'target_date': str(target_date)}).execute().data)
    except: return pd.DataFrame()

def get_material_report_by_date(target_date):
    try: return pd.DataFrame(supabase.rpc('get_material_daily_report', {'target_date': str(target_date)}).execute().data)
    except: return pd.DataFrame()

def get_child_report_by_date(target_date):
    try: return pd.DataFrame(supabase.rpc('get_child_daily_report', {'target_date': str(target_date)}).execute().data)
    except: return pd.DataFrame()

def generate_usage_report_pdf(start_date, end_date, include_resin, include_child, part_filter=None):
    """
    Fungsi Generate PDF Laporan Pemakaian
    [UPDATED] Added TOTAL SUMMARY for Child Parts at the Footer
    """
    try:
        # 1. Build Query WIP_IN
        query = supabase.table("wip_in")\
            .select("*")\
            .gte("date_in", str(start_date))\
            .lte("date_in", str(end_date))\
            .order("date_in", desc=False)
        
        # Filter Part Name
        if part_filter and part_filter != "All":
            query = query.eq("part_name", part_filter)
            
        res_wip = query.execute()
        
        data_wip = res_wip.data
        if not data_wip:
            return None, "❌ Tidak ada data produksi untuk filter tersebut."

        # 2. Manual Mapping & Cache BOM
        unique_part_nos = list(set([item['part_no'] for item in data_wip]))
        prod_map = {} 
        if unique_part_nos:
            res_prods = supabase.table("products").select("id, part_no").in_("part_no", unique_part_nos).execute()
            for p in res_prods.data: prod_map[p['part_no']] = p['id']

        bom_cache = {}
        if include_child and prod_map:
            all_uuids = list(prod_map.values())
            res_bom = supabase.table("master_bom")\
                .select("product_id, usage_qty, child_parts(part_name)")\
                .in_("product_id", all_uuids)\
                .not_.is_("child_part_id", "null")\
                .execute()
            
            for b in res_bom.data:
                pid = b['product_id']
                if pid not in bom_cache: bom_cache[pid] = []
                c_name = b['child_parts']['part_name'] if b['child_parts'] else "Unknown Component"
                bom_cache[pid].append({'name': c_name, 'usage': b['usage_qty']})

        # 3. Setup PDF
        pdf = FPDF(orientation='L', unit='mm', format='A4') 
        pdf.add_page()
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "PRODUCTION MATERIAL & COMPONENT USAGE REPORT", 0, 1, 'C')
        
        pdf.set_font("Arial", "", 10)
        filter_txt = f"Part: {part_filter}" if part_filter and part_filter != "All" else "Part: All Items"
        pdf.cell(0, 6, f"Period: {start_date} s/d {end_date} | {filter_txt}", 0, 1, 'C')
        pdf.ln(5)

        # 4. Header Table
        base_cols = [10, 25, 20, 20, 50, 15] 
        headers = ["NO", "DATE", "SHIFT", "M/C", "PART NAME", "SHOT"]
        
        if include_resin:
            base_cols.append(25); headers.append("RESIN (Kg)")
        if include_child:
            base_cols.append(80); headers.append("COMPONENTS USED (Pcs)")

        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(200, 220, 255)
        for i, h in enumerate(headers):
            pdf.cell(base_cols[i], 8, h, 1, 0, 'C', True)
        pdf.ln()

        # 5. Loop Data & Calculate Totals
        pdf.set_font("Arial", "", 8)
        total_resin_kg = 0
        
        # [NEW] Variable buat nampung Total Child Part
        # Format: {'Mur': 500, 'Baut': 200}
        total_child_summary = {} 
        
        for idx, row in enumerate(data_wip):
            row_height = 6
            qty_shot = row.get('total_qty', 0)
            
            # Logic Resin
            resin_txt = "-"
            if include_resin:
                weight_act = float(row.get('part_weight_act') or 0)
                used_kg = (qty_shot * weight_act) / 1000
                total_resin_kg += used_kg
                resin_txt = f"{used_kg:.2f}"

            # Logic Child Part
            child_txt = "-"
            if include_child:
                pid = prod_map.get(row['part_no'])
                if pid and pid in bom_cache:
                    lines = []
                    for c in bom_cache[pid]:
                        usage_per_shot = float(c['usage'])
                        total_usage = qty_shot * usage_per_shot
                        
                        # [NEW] Masukin ke Summary Global
                        c_name = c['name']
                        if c_name in total_child_summary:
                            total_child_summary[c_name] += total_usage
                        else:
                            total_child_summary[c_name] = total_usage
                            
                        lines.append(f"- {c_name}: {total_usage:,.0f}")
                    
                    child_txt = "\n".join(lines)
                elif not pid: child_txt = "(Master Missing)"
                else: child_txt = "-"

            # Handle Multiline
            line_count = child_txt.count('\n') + 1 if include_child and child_txt not in ["-", "(Master Missing)"] else 1
            final_h = row_height * line_count
            
            if pdf.get_y() + final_h > 180:
                pdf.add_page()
                pdf.set_font("Arial", "B", 8)
                for i, h in enumerate(headers): pdf.cell(base_cols[i], 8, h, 1, 0, 'C', True)
                pdf.ln(); pdf.set_font("Arial", "", 8)

            # Print Cells
            x_start, y_start = pdf.get_x(), pdf.get_y()
            
            pdf.cell(base_cols[0], final_h, str(idx+1), 1, 0, 'C')
            pdf.cell(base_cols[1], final_h, str(row['date_in']), 1, 0, 'C')
            pdf.cell(base_cols[2], final_h, str(row['shift']), 1, 0, 'C')
            pdf.cell(base_cols[3], final_h, str(row['machine_no']), 1, 0, 'C')
            
            x_nm = pdf.get_x()
            pdf.multi_cell(base_cols[4], row_height, str(row['part_name']), 1, 'L')
            pdf.set_xy(x_nm + base_cols[4], y_start)
            
            pdf.cell(base_cols[5], final_h, str(qty_shot), 1, 0, 'C')
            
            if include_resin: pdf.cell(base_cols[6], final_h, resin_txt, 1, 0, 'C')
            
            if include_child:
                x_ch = pdf.get_x()
                pdf.multi_cell(base_cols[-1], row_height, child_txt, 1, 'L')
                pdf.set_xy(x_ch + base_cols[-1], y_start)

            pdf.ln(final_h)
        
        # --- FOOTER SUMMARY ---
        pdf.ln(5)
        
        # 1. Total Resin
        if include_resin:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, f"TOTAL RESIN USAGE: {total_resin_kg:,.2f} Kg", 0, 1)
        
        # 2. Total Child Parts (Looping Dictionary)
        if include_child and total_child_summary:
            pdf.ln(2)
            pdf.set_font("Arial", "B", 10)
            pdf.cell(0, 6, "TOTAL COMPONENTS USAGE SUMMARY:", 0, 1)
            
            pdf.set_font("Arial", "", 9)
            # Sort biar rapi sesuai abjad
            for name in sorted(total_child_summary.keys()):
                qty = total_child_summary[name]
                pdf.cell(0, 5, f"  - {name}: {qty:,.0f} Pcs", 0, 1)
        
        return pdf.output(dest='S').encode('latin-1'), "✅ PDF Generated!"

    except Exception as e: return None, f"❌ Error: {str(e)}"

# ==============================================================================
# 3. stock_wip
# ==============================================================================
@st.cache_data(ttl=60)
def get_stockboard_view():
    try: return pd.DataFrame(supabase.table("view_stockboard").select("*").execute().data)
    except: return pd.DataFrame()

def get_wip_stock_balance(part_no):
    """Mengambil Saldo WIP saat ini dari view_stockboard"""
    try:
        res = supabase.table("view_stockboard")\
            .select("balance")\
            .eq("part_no", part_no)\
            .limit(1)\
            .execute()
        
        if res.data:
            return int(res.data[0]['balance'])
        return 0 
    except:
        return 0

# ==============================================================================
# 4. stock_fg
# ==============================================================================
@st.cache_data(ttl=60)
def get_stockboard_fg_view():
    """
    Fungsi ini narik data lengkap dari View. 
    Sekarang kolom part_name dan balance ikut ketarik buat keperluan DO System.
    """
    try:
        # [UPDATE]: Tarik semua kolom (*), jangan cuma part_no
        res = supabase.table("view_stockboard_fg").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # 1. Konversi ke Datetime
            df['last_stock_update'] = pd.to_datetime(df['last_stock_update'])
            
            # 2. Fix Timezone WIB (UTC+7)
            df['last_stock_update'] = df['last_stock_update'] + timedelta(hours=7)
            
            # 3. Format String untuk UI
            df['last_update_str'] = df['last_stock_update'].dt.strftime('%d %b, %H:%M')
            
        return df # Balikin semua kolom (termasuk part_name dan balance)
    except Exception as e:
        print(f"Error View Stockboard: {e}")
        return pd.DataFrame()

def submit_wip_out(date, part_name, part_no, qty, doc_no, sender, receiver, notes):
    """Fungsi submit satuan (tetap diupdate untuk kolom sender)"""
    try:
        data = {
            "date_out": str(date), 
            "part_name": part_name, 
            "part_no": part_no, 
            "qty": qty, 
            "doc_no": doc_no, 
            "sender": sender,    # <--- ADDED
            "receiver": receiver, 
            "notes": notes
        }
        supabase.table("wip_out").insert(data).execute(); return True, "✅ Saved!"
    except Exception as e: return False, f"❌ Error: {e}"

def submit_wip_out_cart(header_data, items_cart):
    """Submit Banyak Barang WIP Keluar (Transfer FG) sekaligus."""
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_out": str(header_data['date']),
                "doc_no": str(header_data['doc_no']),
                "sender": str(header_data.get('sender', '-')), # <--- ADDED
                "receiver": str(header_data['receiver']),
                "part_name": str(item['part_name']),
                "part_no": str(item['part_no']),
                "qty": int(item['qty']),
                "notes": str(item['notes']) 
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("wip_out").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} Item Berhasil Ditransfer ke FG."
        
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def get_wip_in_history_paged(page, page_size, d_start, d_end, search=None):
    return get_history_paginated("wip_in", page, page_size, d_start, d_end, "part_name", search)

def get_wip_out_history_paged(page, page_size, d_start, d_end, search=None):
    return get_history_paginated("wip_out", page, page_size, d_start, d_end, "part_name", search)

def get_wip_in_history(limit=50):
    try: return pd.DataFrame(supabase.table("wip_in").select("*").order("created_at", desc=True).limit(limit).execute().data)
    except: return pd.DataFrame()

def get_wip_out_history(limit=50):
    try: return pd.DataFrame(supabase.table("wip_out").select("*").order("created_at", desc=True).limit(limit).execute().data)
    except: return pd.DataFrame()

def update_wip_out_bulk(edited_df, master_product_df):
    """
    Fungsi sakti buat simpan perubahan massal riwayat transfer FG.
    edited_df: data hasil editan dari UI
    master_product_df: data master buat mapping part_name -> part_no
    """
    try:
        # Kita bikin mapping dulu biar kalau nama barang diganti, part_no ikut bener di DB
        name_to_no = dict(zip(master_product_df['part_name'], master_product_df['part_no']))
        
        for _, row in edited_df.iterrows():
            # Cari part_no yang sesuai sama part_name yang dipilih
            p_name = row['part_name']
            p_no = name_to_no.get(p_name, row.get('part_no')) # Fallback ke part_no lama kalau gak ketemu
            
            payload = {
                "date_out": str(row['date_out']),
                "doc_no": str(row['doc_no']),
                "part_name": str(p_name),
                "part_no": str(p_no),
                "qty": int(row['qty']),
                "sender": str(row.get('sender', '-')), # <--- ADDED
                "receiver": str(row['receiver']),
                "notes": str(row['notes'])
            }
            
            # Eksekusi Update ke tabel wip_out berdasarkan ID
            supabase.table("wip_out").update(payload).eq("id", row['id']).execute()
            
        return True, "✅ Perubahan Riwayat Transfer Berhasil Disimpan!"
    except Exception as e:
        return False, f"❌ Gagal Update Riwayat: {str(e)}"
# ==============================================================================
# 5. delivery_order
# ==============================================================================
def get_items_by_po_number(po_number):
    try:
        res = supabase.table("view_po_control")\
            .select("part_name, part_no, balance_qty")\
            .eq("po_number", po_number)\
            .gt("balance_qty", 0)\
            .execute() 
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def generate_custom_do_number(customer_name, trx_date):
    """Generate DO Number Format Baru: XXXX/SSP"""
    try:
        d = datetime.strptime(str(trx_date), "%Y-%m-%d") if isinstance(trx_date, str) else trx_date
        year = d.strftime("%Y")
        cust_code = "SSP"
        start, end = f"{year}-01-01", f"{year}-12-31"
        res = supabase.table("delivery_logs").select("do_number").gte("transaction_date", start).lte("transaction_date", end).execute()
        existing_dos = set(item['do_number'] for item in res.data)
        return f"{len(existing_dos) + 1:04d}/{cust_code}"
    except: 
        return "DRAFT-DO"

def submit_delivery_cart(header_data, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            qty_val = int(item['qty']); spq_val = int(item['spq']) if int(item['spq']) > 0 else 1
            box_val = math.ceil(qty_val / spq_val)
            row = {
                "transaction_date": str(header_data['date']), "do_number": str(header_data['do_no']),
                "po_number": str(header_data['po_no']), "customer_name": str(header_data['customer']),
                "prepared_by": str(header_data['prepared_by']), "transaction_type": "SALES",
                "part_name": str(item['part_name']), "part_no": str(item['part_no']),
                "inventory_id": str(item.get('inventory_id', '-')), 
                "qty": qty_val, "spq": spq_val, "total_box": int(box_val), 
                "notes": str(item.get('notes', '-')) 
            }
            data_to_insert.append(row)
        supabase.table("delivery_logs").insert(data_to_insert).execute()
        return True, "✅ Delivery Order Terbit (Verified)."
    except Exception as e: return False, f"❌ Gagal Simpan: {str(e)}"

def submit_general_delivery_cart(header_data, items_cart):
    """[UPDATED] Support UOM & Total Box Manual"""
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "transaction_date": str(header_data['date']), 
                "do_number": str(header_data['do_no']), 
                "transaction_type": "NON_COMMERCIAL",
                "customer_name": str(header_data['customer']), 
                "part_name": str(item['part_name']), 
                "part_no": str(item.get('part_no', 'GENERAL')), 
                "qty": int(item['qty']), 
                "uom": str(item.get('uom', 'PCS')), 
                "total_box": int(item.get('box', 1)), 
                "spq": 0, 
                "po_number": str(header_data.get('po_no', '-')), 
                "prepared_by": str(header_data['prepared_by']), 
                "notes": str(item.get('notes', '-'))
            }
            data_to_insert.append(row)
            
        supabase.table("delivery_logs").insert(data_to_insert).execute()
        return True, "✅ SJ Umum (Multi-Item) Terbit!"
    except Exception as e: 
        return False, f"❌ Error: {e}"

def update_delivery_log_advanced(row_id, new_data):
    """Fungsi Update DO Super Lengkap (Barang, Qty, PO, Notes, Date, Inventory ID, & Revision)"""
    try:
        current_data = supabase.table("delivery_logs").select("part_name, part_no, spq, rev_count").eq("id", row_id).execute().data[0]
        current_rev = int(current_data.get('rev_count') or 0)
        
        final_part_name = new_data.get('part_name', current_data['part_name'])
        final_qty = int(new_data.get('qty', 0))
        final_po = new_data.get('po_number', '-')
        final_notes = new_data.get('notes', '-')
        final_date = str(new_data.get('transaction_date')) 
        final_inv_id = str(new_data.get('inventory_id', '-'))

        update_payload = {
            "qty": final_qty, 
            "po_number": final_po, 
            "notes": final_notes,
            "transaction_date": final_date, 
            "inventory_id": final_inv_id,
            "rev_count": current_rev + 1  
        }
        
        if final_part_name != current_data['part_name']:
            master = supabase.table("products").select("part_no, spq").eq("part_name", final_part_name).execute()
            if master.data:
                new_master = master.data[0]
                new_spq = int(new_master['spq']) if new_master['spq'] > 0 else 1
                new_box = math.ceil(final_qty / new_spq)
                
                update_payload.update({
                    "part_name": final_part_name, 
                    "part_no": new_master['part_no'], 
                    "spq": new_spq, 
                    "total_box": new_box
                })
            else: 
                return False, f"❌ Gagal: Part '{final_part_name}' tidak ditemukan di Master!"
        else:
            spq_old = int(current_data.get('spq') or 1)
            spq_old = spq_old if spq_old > 0 else 1
            update_payload["total_box"] = math.ceil(final_qty / spq_old)

        supabase.table("delivery_logs").update(update_payload).eq("id", row_id).execute()
        return True, f"✅ Data Berhasil Direvisi menjadi Rev {current_rev + 1}!"
    except Exception as e: return False, f"❌ Error Update: {e}"

def get_delivery_history(limit=20):
    try: return pd.DataFrame(supabase.table("delivery_logs").select("*").order("created_at", desc=True).limit(limit).execute().data)
    except: return pd.DataFrame()

def get_delivery_history_paged(page, page_size, d_start, d_end, search=None):
    try:
        offset = (page - 1) * page_size
        limit = offset + page_size - 1
        query = supabase.table("delivery_logs").select("*", count='exact')\
            .gte("transaction_date", str(d_start))\
            .lte("transaction_date", str(d_end))
            
        if search: 
            query = query.or_(f"customer_name.ilike.%{search}%,do_number.ilike.%{search}%,part_name.ilike.%{search}%")
            
        res = query.order("created_at", desc=True).range(offset, limit).execute()
        return pd.DataFrame(res.data), res.count
    except: return pd.DataFrame(), 0

def get_do_items_by_number(do_number):
    try: return supabase.table("delivery_logs").select("*").eq("do_number", do_number).execute().data
    except: return []

def get_do_details(do_number):
    try: return supabase.table("delivery_logs").select("*").eq("do_number", do_number).execute().data
    except: return []

def void_delivery_item(row_id):
    """
    Hapus item spesifik dari DO secara permanen.
    """
    try:
        supabase.table("delivery_logs").delete().eq("id", row_id).execute()
        return True, "✅ Item berhasil dihapus selamanya!"
    except Exception as e:
        return False, f"❌ Gagal Void: {str(e)}"    

def create_pdf_do(header, items):
    pdf = FPDF(unit='mm', format=(215, 140)) 
    pdf.add_page()
    pdf.set_auto_page_break(auto=False, margin=0)
    
    # --- KOP ---
    pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 8); pdf.cell(90, 5, "PT SHIN SAM-PLUS INDUSTRY", 0, 1)
    pdf.set_font("Arial", "", 8); pdf.cell(90, 4, "JL PERMATA RAYA LOT E1 - KIIC", 0, 1); pdf.cell(90, 4, "KARAWANG (0267) 863 7292", 0, 1)
    
    # --- NOTE BOX ---
    x_note = 172; y_note = 8; w_note = 38
    pdf.set_xy(x_note, y_note); pdf.set_font("Arial", "B", 7); pdf.cell(w_note, 4, "NOTE:", 1, 1, 'L')
    pdf.set_x(x_note); pdf.cell(w_note, 22, "", 1, 1)
    
    pdf.set_xy(x_note + 1, y_note + 5); pdf.set_font("Arial", "", 6)
    for c in ["- Putih (Accounting)", "- Merah (PPIC)", "- Hijau (Customer)", "- Kuning (Logistic)", "- Biru (Security)"]:
        pdf.set_x(x_note + 1); pdf.cell(w_note-1, 3.2, c, 0, 1)

    # --- HEADER INFO ---
    x_mid = 95; y_mid = 8
    pdf.set_xy(x_mid, y_mid); pdf.set_font("Arial", "B", 9); pdf.cell(25, 5, "KEPADA YTH :", 0, 0)
    pdf.set_font("Arial", "", 9); pdf.set_xy(x_mid + 25, y_mid); pdf.multi_cell(50, 5, f"{header['customer']}", 0, 'L')
    
    y_curr = 20 
    pdf.set_xy(x_mid, y_curr)
    
    raw_po = str(header.get('po_no', '-'))
    label_po = "-" if raw_po in ['None', ''] else raw_po
    
    label_ref = "RO NO" if header.get('is_replacement') else "PO NO"
    pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, label_ref, 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, f": {label_po}", 0, 1)
    pdf.set_x(x_mid); pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, "DO NO", 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, f": {header['do_no']}", 0, 1)
    pdf.set_x(x_mid); pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, "DATE", 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, f": {header['date']}", 0, 1)

    # --- JUDUL ---
    rev_val = header.get('rev_count', 0)
    pdf.set_xy(10, 32); pdf.set_font("Arial", "B", 14); pdf.set_line_width(0.5); 
    pdf.cell(50, 9, "DELIVERY ORDER", 1, 0, 'C')
    
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(220, 53, 69) if rev_val > 0 else pdf.set_text_color(0, 0, 0) 
    pdf.cell(20, 9, f"REV {rev_val}", 1, 0, 'C')
    pdf.set_text_color(0, 0, 0) 
    
    pdf.set_line_width(0.2); pdf.line(5, 42, 210, 42)
    
    # --- DRIVER INFO ---
    notes_raw = header.get('notes', '')
    drv_txt, pol_txt = "..............................", ".............................."
    if '|' in notes_raw:
        parts = notes_raw.split('|')
        drv_txt = parts[0].strip() if len(parts) > 0 else drv_txt
        pol_txt = parts[1].strip() if len(parts) > 1 else pol_txt

    # --- TABEL ---
    pdf.set_xy(5, 44); col_w = [10, 35, 75, 20, 15, 15, 35]; headers = ["NO", "PART NO", "PART NAME / INV ID", "QTY", "UNIT", "BOX", "REMARKS"]
    pdf.set_font("Arial", "B", 9)
    for i, h in enumerate(headers): pdf.cell(col_w[i], 7, h, 1, 0, 'C') 
    pdf.ln(); pdf.set_font("Arial", "", 9); h_row = 7
    
    for idx, item in enumerate(items):
        pdf.set_x(5)
        uom_val = str(item.get('uom', 'PCS'))
        
        if item.get('total_box') is not None and int(item.get('total_box', 0)) > 0:
            box_val = str(item['total_box'])
        else:
            spq = int(item.get('spq', 1)); spq = spq if spq > 0 else 1
            qty = int(item['qty'])
            box_calc = math.ceil(qty / spq)
            box_val = str(box_calc)

        item_remark = item.get('notes', '')
        if item_remark == 'None' or item_remark == '-': item_remark = ''

        p_name = f"{item.get('part_name','-')[:38]}"
        inv_id = str(item.get('inventory_id', '-'))
        if inv_id not in ['-', 'None', '']:
             p_display = f"{p_name}\n(Inv ID: {inv_id})"
             final_h_row = 10 
        else:
             p_display = p_name
             final_h_row = 7

        x_start = pdf.get_x()
        y_start = pdf.get_y()
        
        pdf.cell(col_w[0], final_h_row, str(idx + 1), 1, 0, 'C')
        pdf.cell(col_w[1], final_h_row, f"{item.get('part_no','-')}", 1, 0, 'C')
        
        x_curr = pdf.get_x()
        pdf.multi_cell(col_w[2], final_h_row if inv_id in ['-','None',''] else 5, p_display, 1, 'L')
        pdf.set_xy(x_curr + col_w[2], y_start) 
        
        pdf.cell(col_w[3], final_h_row, f"{item['qty']}", 1, 0, 'C')
        pdf.cell(col_w[4], final_h_row, uom_val, 1, 0, 'C')
        pdf.cell(col_w[5], final_h_row, box_val, 1, 0, 'C')
        pdf.cell(col_w[6], final_h_row, item_remark, 1, 0, 'L')
        
        pdf.ln(final_h_row)
    
    # --- FOOTER ---
    y_foot = 97 
    pdf.set_xy(5, y_foot); pdf.set_font("Arial", "B", 8)
    
    x_lbl = 5; x_cln = 30
    pdf.set_x(x_lbl); pdf.cell(25, 4, "DRIVER", 0, 0); pdf.set_x(x_cln); pdf.cell(60, 4, f": {drv_txt}", 0, 1)
    pdf.set_x(x_lbl); pdf.cell(25, 4, "NO. POLISI", 0, 0); pdf.set_x(x_cln); pdf.cell(60, 4, f": {pol_txt}", 0, 1)
    
    y_ttd_head = y_foot + 10; headers_sig = ["PREPARED", "CHECKED", "APPROVED", "SECURITY", "RECIEVED BY"]
    x_pos = [5, 45, 85, 125, 165]; w_sig = 38
    
    for i, h in enumerate(headers_sig): pdf.set_xy(x_pos[i], y_ttd_head); pdf.cell(w_sig, 5, h, 1, 0, 'C')
    y_ttd_space = y_ttd_head + 5
    for i in range(5): pdf.set_xy(x_pos[i], y_ttd_space); pdf.cell(w_sig, 15, "", 1, 0) 
    
    y_ttd_nm = y_ttd_space + 15
    for i in range(5): pdf.set_xy(x_pos[i], y_ttd_nm); pdf.cell(w_sig, 5, "( ....................... )", 1, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

def create_blank_pdf_do():
    """Generate Surat Jalan (DO) Kosong untuk keperluan manual shift malam."""
    pdf = FPDF(unit='mm', format=(215, 140)) 
    pdf.add_page()
    pdf.set_auto_page_break(auto=False, margin=0)
    
    # --- KOP ---
    pdf.set_font("Arial", "B", 10); pdf.set_xy(10, 8); pdf.cell(90, 5, "PT SHIN SAM-PLUS INDUSTRY", 0, 1)
    pdf.set_font("Arial", "", 8); pdf.cell(90, 4, "JL PERMATA RAYA LOT E1 - KIIC", 0, 1); pdf.cell(90, 4, "KARAWANG (0267) 863 7292", 0, 1)
    
    # --- NOTE BOX ---
    x_note = 172; y_note = 8; w_note = 38
    pdf.set_xy(x_note, y_note); pdf.set_font("Arial", "B", 7); pdf.cell(w_note, 4, "NOTE:", 1, 1, 'L')
    pdf.set_x(x_note); pdf.cell(w_note, 22, "", 1, 1)
    
    pdf.set_xy(x_note + 1, y_note + 5); pdf.set_font("Arial", "", 6)
    for c in ["- Putih (Accounting)", "- Merah (PPIC)", "- Hijau (Customer)", "- Kuning (Logistic)", "- Biru (Security)"]:
        pdf.set_x(x_note + 1); pdf.cell(w_note-1, 3.2, c, 0, 1)

    # --- HEADER INFO (BLANK) ---
    x_mid = 95; y_mid = 8
    pdf.set_xy(x_mid, y_mid); pdf.set_font("Arial", "B", 9); pdf.cell(25, 5, "KEPADA YTH :", 0, 0)
    
    pdf.set_xy(x_mid + 25, y_mid)
    pdf.cell(50, 5, ".............................................................", 0, 1)
    pdf.set_xy(x_mid + 25, y_mid + 5)
    pdf.cell(50, 5, ".............................................................", 0, 1)
    
    y_curr = 20 
    pdf.set_xy(x_mid, y_curr)
    
    pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, "PO NO", 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, ": ...............................................", 0, 1)
    pdf.set_x(x_mid); pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, "DO NO", 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, ": ...............................................", 0, 1)
    pdf.set_x(x_mid); pdf.set_font("Arial", "B", 9); pdf.cell(15, 5, "DATE", 0, 0); pdf.set_font("Arial", "", 9); pdf.cell(45, 5, ": ...............................................", 0, 1)

    # --- JUDUL ---
    pdf.set_xy(10, 32); pdf.set_font("Arial", "B", 14); pdf.set_line_width(0.5); pdf.cell(50, 9, "DELIVERY ORDER", 1, 0, 'C'); pdf.set_line_width(0.2); pdf.line(5, 42, 210, 42)
    
    # --- TABEL ---
    pdf.set_xy(5, 44); col_w = [10, 35, 75, 20, 15, 15, 35]; headers = ["NO", "PART NO", "PART NAME / INV ID", "QTY", "UNIT", "BOX", "REMARKS"]
    pdf.set_font("Arial", "B", 9)
    for i, h in enumerate(headers): pdf.cell(col_w[i], 7, h, 1, 0, 'C') 
    pdf.ln(); pdf.set_font("Arial", "", 9); h_row = 7
    
    for i in range(5):
        pdf.set_x(5)
        pdf.cell(col_w[0], h_row, str(i + 1), 1, 0, 'C') 
        pdf.cell(col_w[1], h_row, "", 1, 0, 'C')         
        pdf.cell(col_w[2], h_row, "", 1, 0, 'L')         
        pdf.cell(col_w[3], h_row, "", 1, 0, 'C')         
        pdf.cell(col_w[4], h_row, "", 1, 0, 'C')         
        pdf.cell(col_w[5], h_row, "", 1, 0, 'C')         
        pdf.cell(col_w[6], h_row, "", 1, 0, 'L')         
        pdf.ln(h_row)
    
    # --- FOOTER ---
    y_foot = 97 
    pdf.set_xy(5, y_foot); pdf.set_font("Arial", "B", 8)
    
    x_lbl = 5; x_cln = 30
    pdf.set_x(x_lbl); pdf.cell(25, 4, "DRIVER", 0, 0); pdf.set_x(x_cln); pdf.cell(60, 4, ": .........................................", 0, 1)
    pdf.set_x(x_lbl); pdf.cell(25, 4, "NO. POLISI", 0, 0); pdf.set_x(x_cln); pdf.cell(60, 4, ": .........................................", 0, 1)
    
    y_ttd_head = y_foot + 10; headers_sig = ["PREPARED", "CHECKED", "APPROVED", "SECURITY", "RECIEVED BY"]
    x_pos = [5, 45, 85, 125, 165]; w_sig = 38
    
    for i, h in enumerate(headers_sig): pdf.set_xy(x_pos[i], y_ttd_head); pdf.cell(w_sig, 5, h, 1, 0, 'C')
    y_ttd_space = y_ttd_head + 5
    for i in range(5): pdf.set_xy(x_pos[i], y_ttd_space); pdf.cell(w_sig, 15, "", 1, 0) 
    
    y_ttd_nm = y_ttd_space + 15
    for i in range(5): pdf.set_xy(x_pos[i], y_ttd_nm); pdf.cell(w_sig, 5, "( ....................... )", 1, 0, 'C')
    
    return pdf.output(dest='S').encode('latin-1')

# ==============================================================================
# 6. material_in & 7. material_out & 8. material_stock (CLEAN VERSION)
# ==============================================================================
@st.cache_data(ttl=60)
def get_material_stock_view():
    try: 
        return pd.DataFrame(supabase.table("view_material_stock").select("*").execute().data)
    except: 
        return pd.DataFrame()

def submit_material_in(date, material_id, qty, input_by, doc_no, notes, supplier="-"):
    try:
        data = {
            "date_in": str(date), 
            "material_id": material_id, 
            "qty": qty, 
            "input_by": input_by, 
            "doc_no": doc_no, 
            "notes": notes,
            "supplier": supplier 
        }
        supabase.table("log_material_in").insert(data).execute()
        return True, "✅ Kedatangan Resin Tersimpan!"
    except Exception as e: 
        return False, f"❌ Error: {e}"

def submit_material_out(date, material_id, qty, input_by, notes):
    try:
        data = {"date_out": str(date), "material_id": material_id, "qty": qty, "input_by": input_by, "notes": notes}
        supabase.table("log_material_out").insert(data).execute()
        return True, "✅ Saved!"
    except Exception as e: 
        return False, f"❌ Error: {e}"

def submit_incoming_material_cart(header_data, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_in": str(header_data['date']),
                "doc_no": str(header_data['doc_no']),
                "supplier": str(header_data['supplier']),
                "input_by": str(header_data['input_by']),
                "po_number": header_data.get('po_no'), 
                "material_id": item['id'],
                "qty": float(item['qty']),
                "notes": str(item['notes']) if item.get('notes') else str(header_data.get('notes', '-'))
            }
            data_to_insert.append(row)
        
        if data_to_insert:
            supabase.table("log_material_in").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} Item Resin Berhasil Disimpan."
        return False, "❌ Keranjang Kosong!"
        
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def submit_outgoing_material_cart(header_data, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_out": str(header_data['date']),
                "input_by": str(header_data['input_by']), 
                "material_id": item['id'],
                "qty": float(item['qty']),
                "notes": f"Receiver: {header_data['receiver']} | {item.get('notes', '-')}" 
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("log_material_out").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} Item Resin Dikeluarkan."
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def get_material_in_history_paged(page, page_size, d_start, d_end, search=None):
    return get_history_paginated("log_material_in", page, page_size, d_start, d_end, "doc_no", search)

def get_material_out_history_paged(page, page_size, d_start, d_end, search=None):
    return get_history_paginated("log_material_out", page, page_size, d_start, d_end, "notes", search)

def get_material_in_history(limit=50):
    try:
        res = supabase.table("log_material_in").select("*, raw_materials(full_name)").order("created_at", desc=True).limit(limit).execute()
        df = pd.DataFrame(res.data)
        if not df.empty: 
            df['material_name'] = df['raw_materials'].apply(lambda x: x['full_name'] if x else "Unknown")
        return df
    except: 
        return pd.DataFrame()

def get_material_out_history(limit=50):
    try:
        res = supabase.table("log_material_out").select("*, raw_materials(full_name)").order("created_at", desc=True).limit(limit).execute()
        df = pd.DataFrame(res.data)
        if not df.empty: 
            df['material_name'] = df['raw_materials'].apply(lambda x: x['full_name'] if x else "Unknown")
        return df
    except: 
        return pd.DataFrame()

# [NEW HELPER FOR SYNC FILTER]
def get_products_for_filter():
    """Mengambil daftar produk aktif untuk dropdown filter"""
    try:
        res = supabase.table("products").select("part_name").eq("status", "ACTIVE").order("part_name").execute()
        return [row['part_name'] for row in res.data]
    except: return []

def get_bom_map_by_product(product_name):
    """Mendapatkan ID Material & Child Part yang terdaftar di BOM produk tertentu"""
    try:
        p_res = supabase.table("products").select("id").eq("part_name", product_name).execute()
        if not p_res.data: return [], []
        p_id = p_res.data[0]['id']
        
        b_res = supabase.table("master_bom").select("material_id, child_part_id").eq("product_id", p_id).execute()
        m_ids = [r['material_id'] for r in b_res.data if r['material_id']]
        c_ids = [r['child_part_id'] for r in b_res.data if r['child_part_id']]
        return m_ids, c_ids
    except: return [], []

def get_incoming_history_filtered(category, d_start, d_end, search_term=""):
    """
    Fungsi untuk narik riwayat masuk (Resin / Child Part) dengan filter canggih.
    """
    try:
        table = "log_material_in" if category == 'RESIN' else "log_child_in"
        join_table = "raw_materials(type_grade, material_grade, color_grade)" if category == 'RESIN' else "child_parts(part_name)"
        
        # 1. Start Query
        query = supabase.table(table).select(f"*, {join_table}")\
            .gte("date_in", str(d_start))\
            .lte("date_in", str(d_end))
        
        # 2. Apply Search (Jika ada kata kunci)
        if search_term:
            # Cari di PO, Surat Jalan, Supplier, atau Notes
            query = query.or_(f"po_number.ilike.%{search_term}%,doc_no.ilike.%{search_term}%,supplier.ilike.%{search_term}%,notes.ilike.%{search_term}%")
            
        res = query.order("created_at", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # 3. Merapikan Nama Barang hasil Join
            if category == 'RESIN':
                df['item_name'] = df['raw_materials'].apply(lambda x: f"{x['type_grade']} - {x['material_grade']} ({x['color_grade']})" if x else "Unknown")
            else:
                df['item_name'] = df['child_parts'].apply(lambda x: x['part_name'] if x else "Unknown")
        
        return df
    except Exception as e:
        print(f"Error Filter History: {e}")
        return pd.DataFrame()

def update_log_bulk(category, edited_df):
    """
    Fungsi Sakti buat simpan perubahan massal dari st.data_editor (Excel Style).
    """
    try:
        table = "log_material_in" if category == 'RESIN' else "log_child_in"
        id_col = "material_id" if category == 'RESIN' else "child_part_id"
        
        # Kita looping per baris yang ada di DataFrame hasil edit
        for _, row in edited_df.iterrows():
            payload = {
                "date_in": str(row['date_in']),
                "po_number": row['po_number'],
                "doc_no": row['doc_no'],
                "qty": float(row['qty']),
                "supplier": row['supplier'],
                "input_by": row['input_by'],
                "notes": row['notes'],
                "is_void": bool(row['is_void']),
                id_col: row[id_col] # Update ID barangnya kalau-kalau diganti di dropdown
            }
            
            # Eksekusi Update berdasarkan ID baris tersebut
            supabase.table(table).update(payload).eq("id", row['id']).execute()
            
        return True, "✅ Semua perubahan berhasil disimpan ke Database!"
    except Exception as e:
        return False, f"❌ Gagal Simpan Massal: {str(e)}"

# ==============================================================================
# 9. master_part
# ==============================================================================
@st.cache_data(ttl=3600)
def get_master_products():
    try: return pd.DataFrame(supabase.table("products").select("*").order("part_name").execute().data)
    except: return pd.DataFrame()

def manage_product(action, data_payload=None, target_id=None):
    try:
        if action == 'INSERT':
            cek = supabase.table("products").select("id").eq("part_no", data_payload['part_no']).execute()
            if cek.data: return False, f"❌ Part No {data_payload['part_no']} sudah ada!"
            supabase.table("products").insert(data_payload).execute()
            st.cache_data.clear()
            return True, "✅ Part berhasil ditambahkan!"
        elif action == 'UPDATE':
            if not target_id: return False, "Target ID Missing"
            supabase.table("products").update(data_payload).eq("id", target_id).execute()
            st.cache_data.clear()
            return True, "✅ Data Part berhasil di-update!"
        elif action == 'DELETE':
            cek = supabase.table("products").select("image_url").eq("id", target_id).execute()
            if cek.data and cek.data[0].get('image_url'):
                delete_part_image(cek.data[0]['image_url']) 
                
            supabase.table("products").delete().eq("id", target_id).execute()
            st.cache_data.clear()
            return True, "🗑️ Part dan gambarnya berhasil dihapus!"
    except Exception as e: return False, f"❌ Database Error: {str(e)}"

def upload_part_image(image_bytes, part_no):
    try:
        unique_id = str(uuid.uuid4())[:8]
        file_name = f"{part_no}_{unique_id}.webp"
        
        res = supabase.storage.from_("part_images").upload(
            path=file_name, 
            file=image_bytes, 
            file_options={"content-type": "image/webp"}
        )
        
        public_url = supabase.storage.from_("part_images").get_public_url(file_name)
        return True, public_url
    except Exception as e:
        return False, str(e)

def delete_part_image(image_url):
    try:
        if not image_url or image_url == '-' or image_url == 'None': 
            return True
        file_name = image_url.split('/')[-1]
        supabase.storage.from_("part_images").remove([file_name])
        return True
    except:
        return False

@st.cache_data(ttl=3600)
def get_machine_list():
    try:
        res = supabase.table("products").select("mc_id").execute()
        machines = sorted(list(set([item['mc_id'] for item in res.data if item['mc_id']])))
        return machines
    except:
        return []

# ==============================================================================
# 10. master_material
# ==============================================================================
@st.cache_data(ttl=3600)
def get_master_materials():
    try:
        df = pd.DataFrame(supabase.table("raw_materials").select("*").order("type_grade").execute().data)
        if not df.empty: df['full_name'] = df['type_grade'] + " - " + df['material_grade'] + " (" + df['color_grade'] + ")"
        return df
    except: return pd.DataFrame()

def add_new_material(type_g, mat_g, col_g):
    try: supabase.table("raw_materials").insert({"type_grade": type_g, "material_grade": mat_g, "color_grade": col_g}).execute(); return True, "✅ Saved!"
    except Exception as e: return False, f"❌ Error: {e}"

def update_raw_material(id, type_g, mat_g, col_g):
    try:
        supabase.table("raw_materials").update({
            "type_grade": type_g,
            "material_grade": mat_g,
            "color_grade": col_g
        }).eq("id", id).execute()
        return True, "✅ Material berhasil diupdate!"
    except Exception as e:
        return False, f"❌ Gagal Update: {str(e)}"

def delete_raw_material(id):
    try:
        supabase.table("raw_materials").delete().eq("id", id).execute()
        return True, "🗑️ Material berhasil dihapus (Void)!"
    except Exception as e:
        return False, f"❌ Gagal Hapus: {str(e)}"

# ==============================================================================
# 11. master_child
# ==============================================================================
@st.cache_data(ttl=3600)
def get_child_parts():
    try: return pd.DataFrame(supabase.table("child_parts").select("*").execute().data)
    except: return pd.DataFrame()

def add_new_child_part(part_name, part_no, uom, min_stock):
    try:
        payload = {
            "part_name": part_name, 
            "part_no": part_no,
            "uom": uom,
            "min_stock": int(min_stock)
        }
        supabase.table("child_parts").insert(payload).execute()
        return True, "✅ Child Part berhasil disimpan!"
    except Exception as e:
        return False, f"❌ Gagal Simpan: {str(e)}"

def update_child_part(id, part_name, part_no, uom, min_stock):
    try:
        payload = {
            "part_name": part_name, 
            "part_no": part_no,
            "uom": uom,
            "min_stock": int(min_stock)
        }
        supabase.table("child_parts").update(payload).eq("id", id).execute()
        return True, "✅ Data berhasil diupdate!"
    except Exception as e:
        return False, f"❌ Gagal Update: {str(e)}"

def delete_child_part(id):
    try:
        supabase.table("child_parts").delete().eq("id", id).execute()
        return True, "🗑️ Data berhasil dihapus (Void)!"
    except Exception as e:
        return False, f"❌ Gagal Hapus: {str(e)}"

@st.cache_data(ttl=60)
def get_child_stock_view():
    try: return pd.DataFrame(supabase.table("view_child_stock").select("*").execute().data)
    except: return pd.DataFrame()

def submit_child_in(date, child_id, qty, input_by, doc_no, notes, supplier="-"):
    try:
        data = {
            "date_in": str(date), 
            "child_part_id": child_id, 
            "qty": int(qty), 
            "input_by": input_by, 
            "doc_no": doc_no, 
            "notes": notes,
            "supplier": supplier 
        }
        supabase.table("log_child_in").insert(data).execute()
        return True, "✅ Kedatangan Komponen Tersimpan!"
    except Exception as e: 
        return False, f"❌ Error: {e}"

def submit_child_out(date, child_id, qty, input_by, notes):
    try:
        data = {"date_out": str(date), "child_part_id": child_id, "qty": int(qty), "input_by": input_by, "notes": notes}
        supabase.table("log_child_out").insert(data).execute(); return True, "✅ Saved!"
    except Exception as e: return False, f"❌ Error: {e}"

def submit_incoming_child_cart(header_data, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_in": str(header_data['date']),
                "doc_no": str(header_data['doc_no']),
                "supplier": str(header_data['supplier']),
                "input_by": str(header_data['input_by']),
                "po_number": header_data.get('po_no'),
                "child_part_id": item['id'],
                "qty": int(item['qty']),
                "notes": str(item['notes']) if item.get('notes') else str(header_data.get('notes', '-'))
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("log_child_in").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} Item Komponen Berhasil Disimpan."
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def submit_outgoing_child_cart(header_data, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_out": str(header_data['date']),
                "input_by": str(header_data['input_by']),
                "child_part_id": item['id'],
                "qty": int(item['qty']),
                "notes": f"Receiver: {header_data['receiver']} | {item.get('notes', '-')}"
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("log_child_out").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} Item Komponen Dikeluarkan."
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def get_child_in_history(limit=50):
    try:
        res = supabase.table("log_child_in").select("*, child_parts(part_name)").order("created_at", desc=True).limit(limit).execute()
        df = pd.DataFrame(res.data)
        if not df.empty: df['part_name'] = df['child_parts'].apply(lambda x: x['part_name'] if x else "-")
        return df
    except: return pd.DataFrame()

def get_child_out_history(limit=50):
    try:
        res = supabase.table("log_child_out").select("*, child_parts(part_name)").order("created_at", desc=True).limit(limit).execute()
        df = pd.DataFrame(res.data)
        if not df.empty: df['part_name'] = df['child_parts'].apply(lambda x: x['part_name'] if x else "-")
        return df
    except: return pd.DataFrame()

# ==============================================================================
# 12. wip_scrap
# ==============================================================================
# (Placeholder untuk modul wip_scrap jika diperlukan di masa depan)

# ==============================================================================
# 13. cust_return
# ==============================================================================
def submit_return_cart(header_data, items_cart):
    try:
        data = [{"date_return": str(header_data['date']), "customer_name": str(header_data['customer']), "doc_no": str(header_data['doc_no']), "original_do": str(header_data['original_do']), "reason": str(header_data['reason']), "status": "OPEN", "qty_replaced": 0, "part_name": str(i['part_name']), "part_no": str(i['part_no']), "qty": int(i['qty'])} for i in items_cart]
        supabase.table("returns_log").insert(data).execute(); return True, "✅ Data Retur Berhasil Disimpan!"
    except Exception as e: return False, f"❌ Error: {e}"

def get_open_return_docs():
    try:
        res = supabase.table("returns_log").select("doc_no, customer_name, original_do, status").neq("status", "CLOSED").execute()
        seen = set(); unique_docs = []
        for item in res.data:
            if item['doc_no'] not in seen:
                seen.add(item['doc_no']); unique_docs.append({"label": f"{item['customer_name']} | SJ: {item['doc_no']}", "doc_no": item['doc_no'], "customer": item['customer_name']})
        return unique_docs
    except: return []

def get_return_items_by_doc(doc_no):
    try: return supabase.table("returns_log").select("*").eq("doc_no", doc_no).neq("status", "CLOSED").execute().data
    except: return []

def generate_ro_number(trx_date):
    try:
        d = datetime.strptime(str(trx_date), "%Y-%m-%d") if isinstance(trx_date, str) else trx_date
        year, day, month = d.strftime("%Y"), d.strftime("%d"), d.strftime("%m")
        start, end = f"{year}-01-01", f"{year}-12-31"
        res = supabase.table("delivery_logs").select("id", count="exact").eq("transaction_type", "REPLACEMENT").gte("transaction_date", start).lte("transaction_date", end).execute()
        count = res.count if res.count else 0
        return f"{year}/RO-{count + 1:04d}/{month}/{day}"
    except: return "DRAFT-RO"

# ==============================================================================
# 14. so_wip & 15. so_fg & 21. material_sto (UPDATED WITH HEADER LOGIC)
# ==============================================================================
def generate_so_number(category):
    """Generate nomor dokumen SO otomatis"""
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"SO-{category}-{today_str}-"
    try:
        res = supabase.table("inventory_so_headers").select("so_number").ilike("so_number", f"{prefix}%").order("so_number", desc=True).limit(1).execute()
        if res.data:
            last_num = int(res.data[0]['so_number'].split('-')[-1])
            new_num = str(last_num + 1).zfill(3)
        else:
            new_num = "001"
        return f"{prefix}{new_num}"
    except: return f"{prefix}001"

def create_so_header(category, pic):
    """Buat record bapak/header SO"""
    try:
        so_no = generate_so_number(category)
        data = {"so_number": so_no, "category": category, "pic": pic, "status": "COMPLETED"}
        res = supabase.table("inventory_so_headers").insert(data).execute()
        return (True, res.data[0]) if res.data else (False, "Gagal buat header")
    except Exception as e: return False, str(e)

def submit_stock_adjustment(header_id, date_adj, category, adjustments_list, pic):
    try:
        data_audit = []
        for i in adjustments_list:
            diff_val = float(i['diff'])
            if diff_val != 0: 
                row = {
                    "header_id": header_id, # Foreign Key ke inventory_so_headers
                    "adjust_date": str(date_adj),
                    "category": category,
                    "part_no": str(i.get('part_no', '-')), 
                    "part_name": str(i['part_name']),
                    "type": 'IN' if diff_val > 0 else 'OUT',
                    "reason": "Stock Opname",
                    "pic": pic,
                    "qty_system": None, "qty_actual": None, "qty_adjust": None,
                    "qty_system_dec": None, "qty_actual_dec": None, "qty_adjust_dec": None
                }

                if category in ['RESIN', 'CHILD_PART']:
                    row["qty_system_dec"] = float(i['system'])
                    row["qty_actual_dec"] = float(i['actual'])
                    row["qty_adjust_dec"] = abs(diff_val)
                else:
                    row["qty_system"] = int(i['system'])
                    row["qty_actual"] = int(i['actual'])
                    row["qty_adjust"] = int(abs(diff_val))
                
                data_audit.append(row)
        
        if data_audit: 
            supabase.table("inventory_adjustments").insert(data_audit).execute()

        # LOGIC ASLI (RESIN/CHILD PART) - TIDAK DIRUBAH
        if category in ['RESIN', 'CHILD_PART']:
            log_in_data = []
            log_out_data = []
            for item in data_audit:
                matched_item = next((x for x in adjustments_list if x['part_name'] == item['part_name']), None)
                if matched_item and 'id' in matched_item:
                    obj_id = matched_item['id']
                    qty_abs = item['qty_adjust_dec'] 
                    note_sto = f"STO ADJ ({item['type']})"
                    if category == 'RESIN':
                        if item['type'] == 'IN':
                            log_in_data.append({"date_in": str(date_adj), "material_id": obj_id, "qty": qty_abs, "input_by": pic, "doc_no": "STO-ADJ", "notes": note_sto})
                        else:
                            log_out_data.append({"date_out": str(date_adj), "material_id": obj_id, "qty": qty_abs, "input_by": pic, "notes": note_sto})
                    elif category == 'CHILD_PART':
                         if item['type'] == 'IN':
                            supabase.table("log_child_in").insert({"date_in": str(date_adj), "child_part_id": obj_id, "qty": int(qty_abs), "input_by": pic, "doc_no": "STO-ADJ", "notes": note_sto}).execute()
                         else:
                            supabase.table("log_child_out").insert({"date_out": str(date_adj), "child_part_id": obj_id, "qty": int(qty_abs), "input_by": pic, "notes": note_sto}).execute()
            if log_in_data: supabase.table("log_material_in").insert(log_in_data).execute()
            if log_out_data: supabase.table("log_material_out").insert(log_out_data).execute()

        return True, f"✅ {len(data_audit)} Item disesuaikan!"
    except Exception as e: return False, f"❌ Error: {str(e)}"

def get_so_history(category, limit=20):
    """Ambil daftar sesi SO (Header)"""
    try: 
        res = supabase.table("inventory_so_headers") \
            .select("*") \
            .eq("category", category) \
            .order("created_at", desc=True) \
            .limit(limit).execute()
        return pd.DataFrame(res.data)
    except: 
        return pd.DataFrame()

# Jangan lupa fungsi detail buat Excel juga harus ada di modules.py
def get_so_details_for_excel(header_id):
    """Ambil semua item berdasarkan header_id untuk diconvert ke Excel"""
    try:
        res = supabase.table("inventory_adjustments") \
            .select("*") \
            .eq("header_id", header_id) \
            .execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# ==============================================================================
# 16. control_po
# ==============================================================================
def get_open_po_by_customer(customer_name):
    try:
        res = supabase.table("purchase_orders").select("po_number").eq("customer_name", customer_name).eq("status", "OPEN").execute()
        return [item['po_number'] for item in res.data]
    except: return []

def get_all_open_pos():
    try:
        res = supabase.table("purchase_orders").select("po_number, customer_name").eq("status", "OPEN").order("po_number", desc=True).execute()
        return pd.DataFrame(res.data) 
    except: return pd.DataFrame()

def submit_new_po_master(po_number, customer, items):
    try:
        if supabase.table("purchase_orders").select("id").eq("po_number", po_number).execute().data: return False, "PO Exists!"
        res_head = supabase.table("purchase_orders").insert({"po_number": po_number, "customer_name": customer, "status": "OPEN"}).execute()
        if not res_head.data: return False, "Fail Header"; 
        po_id = res_head.data[0]['id']
        supabase.table("purchase_order_items").insert([{"po_id": po_id, "part_name": i['part_name'], "part_no": i['part_no'], "qty_order": int(i['qty'])} for i in items]).execute()
        return True, "✅ PO Saved!"
    except Exception as e: return False, f"❌ Error: {e}"

def get_po_monitoring_data(customer_filter=None):
    try:
        query = supabase.table("view_po_control").select("*")
        if customer_filter and customer_filter != "All": 
            query = query.eq("customer_name", customer_filter)
        
        res_view = query.execute()
        df_view = pd.DataFrame(res_view.data)
        
        if df_view.empty: return pd.DataFrame()

        unique_pos = df_view['po_number'].unique().tolist()
        
        res_status = supabase.table("purchase_orders")\
            .select("po_number, status, created_at")\
            .in_("po_number", unique_pos)\
            .execute()
        
        status_map = {item['po_number']: item['status'] for item in res_status.data}
        date_map = {item['po_number']: item['created_at'] for item in res_status.data} 
        
        df_view['status_master'] = df_view['po_number'].map(status_map)
        df_view['po_date'] = df_view['po_number'].map(date_map) 
        
        df_final = df_view[df_view['status_master'] != 'CLOSED']
        
        return df_final
        
    except Exception as e:
        return pd.DataFrame()

def close_po_status(po_number):
    try: supabase.table("purchase_orders").update({"status": "CLOSED"}).eq("po_number", po_number).execute(); return True, "✅ PO Closed."
    except: return False, "Fail."

def get_closed_pos():
    try:
        res = supabase.table("purchase_orders").select("*").eq("status", "CLOSED").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def get_po_final_summary(po_number):
    try:
        clean_po = str(po_number).strip()
        
        res_header = supabase.table("purchase_orders").select("*").eq("po_number", clean_po).limit(1).execute()
        
        if not res_header.data:
            return None
            
        header = res_header.data[0] 
        
        items_res = supabase.table("purchase_order_items").select("*").eq("po_id", header['id']).execute()
        items_data = items_res.data

        logs_res = supabase.table("delivery_logs").select("*").eq("po_number", clean_po).order("transaction_date", desc=False).execute()
        logs_data = logs_res.data
        
        return {
            "header": header,
            "items": items_data,
            "logs": logs_data
        }
    except Exception as e:
        return None

def generate_po_closing_pdf(po_number):
    try:
        data = get_po_final_summary(po_number)
        if not data or not data['header']: return None, "❌ Data PO tidak ditemukan (Cek Spasi/Nomor)"

        header = data['header']
        items = data['items']
        logs = data['logs']

        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # --- TITLE ---
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "PO FULFILLMENT FINAL REPORT", 0, 1, 'C')
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 6, "Official Closing Document", 0, 1, 'C')
        pdf.ln(5)

        # --- INFO HEADER ---
        pdf.set_font("Arial", "B", 10)
        po_num_txt = str(header.get('po_number', '-'))
        cust_txt = str(header.get('customer_name', '-'))
        
        pdf.cell(30, 6, "PO Number", 0, 0); pdf.cell(5, 6, ":", 0, 0); pdf.set_font("Arial", "", 10); pdf.cell(0, 6, po_num_txt, 0, 1)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 6, "Customer", 0, 0); pdf.cell(5, 6, ":", 0, 0); pdf.set_font("Arial", "", 10); pdf.cell(0, 6, cust_txt, 0, 1)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(30, 6, "Status", 0, 0); pdf.cell(5, 6, ":", 0, 0); pdf.set_font("Arial", "B", 10); pdf.set_text_color(220, 53, 69); pdf.cell(0, 6, "CLOSED / COMPLETED", 0, 1)
        pdf.set_text_color(0, 0, 0) 
        pdf.ln(5)

        # --- SECTION 1: FULFILLMENT SUMMARY ---
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "1. FULFILLMENT SUMMARY (RINGKASAN)", 1, 1, 'L', True)
        
        cols = [10, 60, 40, 30, 30, 20]
        h_txt = ["NO", "PART NAME", "PART NO", "TARGET", "SENT", "VOID"]
        
        pdf.set_font("Arial", "B", 8)
        for i, t in enumerate(h_txt): pdf.cell(cols[i], 8, t, 1, 0, 'C')
        pdf.ln()

        pdf.set_font("Arial", "", 8)
        
        for idx, item in enumerate(items):
            p_name = str(item.get('part_name', '-'))
            p_no = str(item.get('part_no', '-'))
            target = int(item.get('qty_order') or 0) 
            
            total_sent = 0
            for d in logs:
                log_p_no = str(d.get('part_no', ''))
                log_qty = int(d.get('qty') or 0)
                if log_p_no == p_no:
                    total_sent += log_qty

            void_qty = target - total_sent
            if void_qty < 0: void_qty = 0
            
            h_row = 6
            pdf.cell(cols[0], h_row, str(idx+1), 1, 0, 'C')
            pdf.cell(cols[1], h_row, p_name[:35], 1, 0, 'L') 
            pdf.cell(cols[2], h_row, p_no, 1, 0, 'C')
            pdf.cell(cols[3], h_row, f"{target:,.0f}", 1, 0, 'C')
            pdf.cell(cols[4], h_row, f"{total_sent:,.0f}", 1, 0, 'C')
            
            if void_qty > 0: pdf.set_text_color(220, 53, 69)
            pdf.cell(cols[5], h_row, f"{void_qty:,.0f}", 1, 0, 'C')
            pdf.set_text_color(0, 0, 0)
            pdf.ln()

        pdf.ln(5)

        # --- SECTION 2: DELIVERY HISTORY LOG ---
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 8, "2. DELIVERY HISTORY LOG (RIWAYAT PENGIRIMAN)", 1, 1, 'L', True)
        
        if not logs:
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 10, "Tidak ada riwayat pengiriman (PO Closed tanpa delivery).", 1, 1, 'C')
        else:
            l_cols = [10, 30, 40, 60, 20, 30] 
            l_txt = ["NO", "DATE", "DO NUMBER", "PART NAME", "QTY", "REMARKS"]
            
            pdf.set_font("Arial", "B", 8)
            for i, t in enumerate(l_txt): pdf.cell(l_cols[i], 8, t, 1, 0, 'C')
            pdf.ln()
            
            pdf.set_font("Arial", "", 8)
            for idx, log in enumerate(logs):
                l_date = str(log.get('transaction_date', '-')) 
                l_do = str(log.get('do_number', '-'))
                l_pname = str(log.get('part_name', '-'))
                l_qty = int(log.get('qty') or 0)
                l_note = str(log.get('notes') or "-")

                h_row = 6
                pdf.cell(l_cols[0], h_row, str(idx+1), 1, 0, 'C')
                pdf.cell(l_cols[1], h_row, l_date, 1, 0, 'C')
                pdf.cell(l_cols[2], h_row, l_do, 1, 0, 'C')
                pdf.cell(l_cols[3], h_row, l_pname[:35], 1, 0, 'L')
                pdf.cell(l_cols[4], h_row, f"{l_qty:,.0f}", 1, 0, 'C')
                pdf.cell(l_cols[5], h_row, l_note[:15], 1, 0, 'L')
                pdf.ln()

        pdf.ln(5)
        pdf.set_font("Arial", "I", 7)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        pdf.cell(0, 5, f"Dicetak otomatis oleh system pada: {timestamp}", 0, 1)

        return pdf.output(dest='S').encode('latin-1'), "✅ PDF Report Ready!"

    except Exception as e:
        return None, f"❌ Error PDF Detail: {str(e)}"

# ==============================================================================
# 17. atk_supplies & 18. atk_stock
# ==============================================================================
def get_supplies_stock_view():
    try: 
        res = supabase.table("view_supplies_stock").select("*").order("item_name").execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return pd.DataFrame(columns=[
                'id', 'item_name', 'specification', 'allocation_group', 
                'item_category', 'uom', 'current_stock', 'min_stock', 
                'total_in', 'total_out', 'is_active'
            ])
            
        return df
    except: 
        return pd.DataFrame(columns=[
            'id', 'item_name', 'specification', 'allocation_group', 
            'item_category', 'uom', 'current_stock', 'min_stock', 
            'total_in', 'total_out', 'is_active'
        ])

def manage_supply_item(action, data_payload=None, item_id=None):
    try:
        if action == 'INSERT':
            existing = supabase.table("master_supplies").select("id").eq("item_name", data_payload['item_name']).eq("specification", data_payload['specification']).execute()
            if existing.data: return False, f"❌ Barang '{data_payload['item_name']}' dengan spek tersebut sudah ada!"
            
            supabase.table("master_supplies").insert(data_payload).execute()
            return True, "✅ Item ATK Berhasil Ditambah!"
            
        elif action == 'UPDATE':
            if not item_id: return False, "ID Missing"
            supabase.table("master_supplies").update(data_payload).eq("id", item_id).execute()
            return True, "✅ Data ATK Berhasil Diupdate!"
            
        elif action == 'DELETE':
            supabase.table("master_supplies").delete().eq("id", item_id).execute()
            return True, "🗑️ Item ATK Berhasil Dihapus!"
            
    except Exception as e: return False, f"❌ Database Error: {str(e)}"

def submit_supply_trx(item_id, trx_type, qty, pic, notes="-", custom_date=None):
    try:
        final_date = str(custom_date) if custom_date else str(datetime.now().date())

        payload = {
            "item_id": item_id,
            "trx_type": trx_type,   
            "qty": float(qty),
            "pic": pic,
            "notes": notes,
            "trx_date": final_date  
        }
        
        supabase.table("log_supplies").insert(payload).execute()
        return True, "✅ Transaksi Stok Tercatat!"
    except Exception as e: return False, f"❌ Error Log: {str(e)}"

def get_supply_history(item_id=None, limit=50):
    try:
        query = supabase.table("log_supplies").select("*, master_supplies(item_name, specification)").order("created_at", desc=True).limit(limit)
        if item_id:
            query = query.eq("item_id", item_id)
        
        res = query.execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            df['item_name'] = df['master_supplies'].apply(lambda x: x['item_name'] if x else '-')
            df['spec'] = df['master_supplies'].apply(lambda x: x['specification'] if x else '-')
            
        return df
    except: return pd.DataFrame()

def get_global_supplies_history(start_date, end_date):
    try:
        res = supabase.table("view_supplies_history")\
            .select("*")\
            .gte("trx_date", str(start_date))\
            .lte("trx_date", str(end_date))\
            .order("created_at", desc=True)\
            .execute()
        
        return pd.DataFrame(res.data)
    except Exception as e:
        return pd.DataFrame()

def get_combined_history_global(start_date, end_date):
    try:
        res = supabase.table("view_global_log_history")\
            .select("*")\
            .gte("trx_date", str(start_date))\
            .lte("trx_date", str(end_date))\
            .order("created_at", desc=True)\
            .execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def get_master_item_map():
    try:
        res = supabase.table("master_supplies").select("id, item_name, specification").eq("is_active", True).execute()
        mapping = {}
        reverse_mapping = {}
        options = []
        
        for item in res.data:
            label = f"{item['item_name']} | {item['specification'] or ''}"
            mapping[label] = item['id']
            reverse_mapping[item['id']] = label
            options.append(label)
            
        return mapping, reverse_mapping, sorted(options)
    except:
        return {}, {}, []

def update_log_transaction_safe(log_id, new_data, user_actor):
    try:
        res_old = supabase.table("log_supplies").select("*").eq("id", log_id).execute()
        if not res_old.data:
            return False, "❌ Data transaksi tidak ditemukan (mungkin sudah dihapus)."
        
        old_data = res_old.data[0]
        
        update_payload = {
            "trx_date": str(new_data['trx_date']),
            "trx_type": new_data['trx_type'],
            "qty": float(new_data['qty']),
            "item_id": new_data['item_id'], 
            "pic": new_data['pic'],
            "notes": new_data['notes']
        }
        
        res_upd = supabase.table("log_supplies").update(update_payload).eq("id", log_id).execute()
        
        save_log_audit(log_id, 'UPDATE', old_data, update_payload, user_actor)
        
        return True, "✅ Data berhasil diperbarui & tercatat di audit!"
        
    except Exception as e:
        return False, f"❌ Gagal Update: {str(e)}"

def delete_log_transaction_safe(log_id, user_actor):
    try:
        res_old = supabase.table("log_supplies").select("*").eq("id", log_id).execute()
        if not res_old.data:
            return False, "❌ Data sudah tidak ada."
            
        old_data = res_old.data[0]
        
        supabase.table("log_supplies").delete().eq("id", log_id).execute()
        
        save_log_audit(log_id, 'DELETE', old_data, None, user_actor)
        
        return True, "🗑️ Data berhasil dihapus (Audit Saved)."
        
    except Exception as e:
        return False, f"❌ Gagal Hapus: {str(e)}"

# ==============================================================================
# 20. rundown_part
# ==============================================================================
# (Placeholder untuk modul rundown_part)

# ==============================================================================
# 22. atk_so
# ==============================================================================
def get_atk_adjustment_history(limit=50):
    try:
        res = supabase.table("view_atk_adjustment_history").select("*").order("created_at", desc=True).limit(limit).execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def submit_atk_adjustment(adjust_date, items_cart, pic):
    try:
        audit_data = []
        log_injection = []
        
        for item in items_cart:
            qty_system = int(item['system'])
            qty_actual = int(item['actual'])
            diff = qty_actual - qty_system
            
            audit_row = {
                "adjust_date": str(adjust_date),
                "item_id": item['id'],
                "qty_system": qty_system,
                "qty_actual": qty_actual,
                "qty_diff": diff,
                "pic": pic,
                "notes": "Stock Opname"
            }
            audit_data.append(audit_row)
            
            if diff != 0:
                trx_type = 'IN' if diff > 0 else 'OUT'
                qty_abs = abs(diff) 
                
                log_row = {
                    "trx_date": str(adjust_date),
                    "item_id": item['id'],
                    "trx_type": trx_type,
                    "qty": qty_abs,
                    "pic": pic,
                    "notes": f"STO ADJ ({trx_type}) | Sys:{qty_system} -> Act:{qty_actual}"
                }
                log_injection.append(log_row)
        
        if audit_data:
            supabase.table("inventory_adjustments_atk").insert(audit_data).execute()
            
        if log_injection:
            supabase.table("log_supplies").insert(log_injection).execute()
            
        return True, f"✅ Sukses! {len(audit_data)} Item disesuaikan."

    except Exception as e:
        return False, f"❌ Error Database: {str(e)}"

def generate_atk_sto_pdf(start_date, end_date):
    try:
        res = supabase.table("view_atk_adjustment_history")\
            .select("*")\
            .gte("adjust_date", str(start_date))\
            .lte("adjust_date", str(end_date))\
            .order("adjust_date", desc=False)\
            .execute()
            
        data = res.data
        if not data:
            return None, "❌ Tidak ada data adjustment pada periode ini."

        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        # --- KOP / HEADER ---
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "LAPORAN STOCK OPNAME (STO) - ATK & SUPPLIES", 0, 1, 'C')
        
        pdf.set_font("Arial", "", 10)
        pdf.cell(0, 6, f"Periode: {start_date} s/d {end_date}", 0, 1, 'C')
        pdf.ln(5)
        
        # --- TABLE HEADER ---
        cols = [10, 25, 60, 50, 20, 20, 20, 20, 40] 
        headers = ["NO", "TANGGAL", "NAMA BARANG", "SPESIFIKASI", "SAT", "SYS", "FISIK", "DIFF", "PIC"]
        
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(200, 220, 255) 
        
        for i, h in enumerate(headers):
            pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
        pdf.ln()
        
        # --- TABLE BODY ---
        pdf.set_font("Arial", "", 8)
        
        for idx, row in enumerate(data):
            h_row = 6
            diff = row['qty_diff']
            
            pdf.set_text_color(0, 0, 0)
            pdf.cell(cols[0], h_row, str(idx+1), 1, 0, 'C')
            pdf.cell(cols[1], h_row, str(row['adjust_date']), 1, 0, 'C')
            pdf.cell(cols[2], h_row, str(row['item_name'])[:30], 1, 0, 'L') 
            pdf.cell(cols[3], h_row, str(row['specification'])[:25], 1, 0, 'L')
            pdf.cell(cols[4], h_row, str(row['uom']), 1, 0, 'C')
            pdf.cell(cols[5], h_row, str(row['qty_system']), 1, 0, 'C')
            pdf.cell(cols[6], h_row, str(row['qty_actual']), 1, 0, 'C')
            
            if diff < 0: pdf.set_text_color(220, 53, 69)   
            elif diff > 0: pdf.set_text_color(25, 135, 84) 
            else: pdf.set_text_color(0, 0, 0)              
            
            diff_txt = f"+{diff}" if diff > 0 else str(diff)
            pdf.cell(cols[7], h_row, diff_txt, 1, 0, 'C')
            
            pdf.set_text_color(0, 0, 0)
            pdf.cell(cols[8], h_row, str(row['pic'])[:20], 1, 0, 'L')
            
            pdf.ln()
            
        # --- SIGNATURE SECTION ---
        pdf.ln(10)
        y_sig = pdf.get_y()
        
        pdf.set_font("Arial", "", 9)
        pdf.set_xy(20, y_sig)
        pdf.cell(50, 5, "Dibuat Oleh (GA/Admin),", 0, 1, 'C')
        pdf.set_xy(20, y_sig + 25)
        pdf.cell(50, 5, "( ........................... )", 0, 1, 'C')
        
        pdf.set_xy(110, y_sig)
        pdf.cell(50, 5, "Diketahui (Dept Head),", 0, 1, 'C')
        pdf.set_xy(110, y_sig + 25)
        pdf.cell(50, 5, "( ........................... )", 0, 1, 'C')
        
        pdf.set_xy(200, y_sig)
        pdf.cell(50, 5, "Disetujui (Management),", 0, 1, 'C')
        pdf.set_xy(200, y_sig + 25)
        pdf.cell(50, 5, "( ........................... )", 0, 1, 'C')
        
        return pdf.output(dest='S').encode('latin-1'), "✅ PDF Ready!"
        
    except Exception as e:
        return None, f"❌ Error PDF: {str(e)}"

# ==============================================================================
# 23. master_box & 24. log_box_in_out & 25. stock_box
# ==============================================================================
def get_master_boxes():
    try:
        res = supabase.table("master_box").select("*").order("box_name").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def manage_master_box(action, payload=None, box_id=None):
    try:
        if action == 'INSERT':
            cek = supabase.table("master_box").select("id").eq("box_name", payload['box_name']).execute()
            if cek.data: return False, f"❌ Box dengan nama '{payload['box_name']}' sudah ada!"
            
            supabase.table("master_box").insert(payload).execute()
            return True, "✅ Master Box berhasil ditambah!"
            
        elif action == 'UPDATE':
            if not box_id: return False, "Missing ID"
            supabase.table("master_box").update(payload).eq("id", box_id).execute()
            return True, "✅ Master Box berhasil diupdate!"
            
        elif action == 'DELETE':
            supabase.table("master_box").delete().eq("id", box_id).execute()
            return True, "🗑️ Master Box berhasil dihapus!"
            
    except Exception as e:
        return False, f"❌ Database Error: {str(e)}"

def submit_box_transaction_cart(header, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            row = {
                "date_trans": str(header['date']),
                "sj_number": str(header.get('sj_number', '-')),
                "box_id": item['box_id'],
                "type": header['type'],
                "qty": int(item['qty']),
                "pic": str(header['pic'])
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("log_box_transactions").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} item berhasil dicatat ({header['type']})."
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Error Log Transaksi: {str(e)}"

def get_box_transaction_history(start_date, end_date, box_filter="All", status_filter="All"):
    try:
        res = supabase.table("log_box_transactions")\
            .select("date_trans, type, qty, pic, sj_number, master_box!inner(box_name, specification)")\
            .gte("date_trans", str(start_date))\
            .lte("date_trans", str(end_date))\
            .order("date_trans", desc=False)\
            .execute()
            
        df = pd.DataFrame(res.data)
        if df.empty: return pd.DataFrame()

        df['box_name'] = df['master_box'].apply(lambda x: x['box_name'] if x else '-')
        df['specification'] = df['master_box'].apply(lambda x: x['specification'] if x else '-')
        df = df.drop(columns=['master_box'])
        
        if box_filter != "All":
            df = df[df['box_name'] == box_filter]
            
        if status_filter != "All":
            df = df[df['type'] == status_filter]
            
        return df
    except Exception as e:
        print(f"Error History Box: {e}")
        return pd.DataFrame()

def generate_box_history_pdf(df_history, start_date, end_date, box_filter="All", status_filter="All"):
    try:
        from fpdf import FPDF
        
        pdf = FPDF(orientation='L', unit='mm', format='A4')
        pdf.add_page()
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "LOG TRANSACTION REPORT - PACKAGING BOX", 0, 1, 'C')
        
        pdf.set_font("Arial", "", 10)
        filter_text = f"Filter Box: {box_filter} | Status: {status_filter}"
        pdf.cell(0, 6, f"Period: {start_date} s/d {end_date} | {filter_text}", 0, 1, 'C')
        pdf.ln(5)
        
        cols = [10, 25, 75, 55, 20, 25, 35, 30] 
        headers = ["NO", "DATE", "BOX NAME", "SPECIFICATION", "STATUS", "QTY (Pcs)", "SJ NUMBER", "PIC"]
        
        pdf.set_font("Arial", "B", 9)
        pdf.set_fill_color(200, 220, 255)
        
        for i, h in enumerate(headers):
            pdf.cell(cols[i], 8, h, 1, 0, 'C', True)
        pdf.ln()
        
        pdf.set_font("Arial", "", 8)
        
        total_in = 0
        total_out = 0
        
        for idx, row in df_history.iterrows():
            h_row = 6
            qty = int(row['qty'])
            trx_type = row['type']
            sj_no = str(row['sj_number']) if str(row['sj_number']) not in ['None', ''] else "-"
            
            if trx_type == 'IN': total_in += qty
            elif trx_type == 'OUT': total_out += qty
            
            pdf.cell(cols[0], h_row, str(idx+1), 1, 0, 'C')
            pdf.cell(cols[1], h_row, str(row['date_trans']), 1, 0, 'C')
            pdf.cell(cols[2], h_row, str(row['box_name'])[:40], 1, 0, 'L')
            pdf.cell(cols[3], h_row, str(row['specification'])[:30], 1, 0, 'L')
            
            if trx_type == 'IN': pdf.set_text_color(25, 135, 84)
            else: pdf.set_text_color(220, 53, 69)
            
            pdf.cell(cols[4], h_row, trx_type, 1, 0, 'C')
            pdf.set_text_color(0, 0, 0)
            
            pdf.cell(cols[5], h_row, f"{qty:,}", 1, 0, 'C')
            pdf.cell(cols[6], h_row, sj_no[:20], 1, 0, 'C')
            pdf.cell(cols[7], h_row, str(row['pic'])[:15], 1, 0, 'L')
            pdf.ln()
            
        pdf.ln(5)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(0, 6, "SUMMARY TOTAL:", 0, 1)
        pdf.set_font("Arial", "", 9)
        
        if status_filter in ["All", "IN"]:
            pdf.cell(0, 5, f"- Total Box IN  (Masuk) : {total_in:,} Pcs", 0, 1)
        if status_filter in ["All", "OUT"]:
            pdf.cell(0, 5, f"- Total Box OUT (Keluar): {total_out:,} Pcs", 0, 1)

        return pdf.output(dest='S').encode('latin-1'), "✅ PDF Generate Sukses!"
    except Exception as e:
        return None, f"❌ Error PDF: {str(e)}"

def get_box_stock_as_of(target_date):
    try:
        t_date = str(target_date)
        
        df_master = get_master_boxes()
        if df_master.empty:
            return pd.DataFrame()
            
        res_trx = supabase.table("log_box_transactions").select("box_id, type, qty").lte("date_trans", t_date).execute()
        df_trx = pd.DataFrame(res_trx.data)
        
        res_so = supabase.table("log_box_so").select("box_id, variance").lte("date_so", t_date).execute()
        df_so = pd.DataFrame(res_so.data)
        
        stock_result = []
        for _, row in df_master.iterrows():
            b_id = row['id']
            
            total_in = 0
            total_out = 0
            total_variance = 0
            
            if not df_trx.empty:
                box_trx = df_trx[df_trx['box_id'] == b_id]
                total_in = box_trx[box_trx['type'] == 'IN']['qty'].sum()
                total_out = box_trx[box_trx['type'] == 'OUT']['qty'].sum()
                
            if not df_so.empty:
                total_variance = df_so[df_so['box_id'] == b_id]['variance'].sum()
                
            current_stock = (total_in - total_out) + total_variance
            
            stock_result.append({
                "box_id": b_id,
                "box_name": row['box_name'],
                "specification": row['specification'],
                "model": row['model'],
                "customer": row['customer'],
                "total_in": int(total_in),
                "total_out": int(total_out),
                "total_variance": int(total_variance),
                "current_stock": int(current_stock)
            })
            
        return pd.DataFrame(stock_result)

    except Exception as e:
        print(f"Error Stock As Of: {e}")
        return pd.DataFrame()

# ==============================================================================
# 26. so_box
# ==============================================================================
def submit_box_so_cart(header, items_cart):
    try:
        data_to_insert = []
        for item in items_cart:
            qty_sys = int(item['qty_system'])
            qty_act = int(item['qty_actual'])
            variance = qty_act - qty_sys
            
            row = {
                "date_so": str(header['date']),
                "box_id": item['box_id'],
                "qty_system": qty_sys,
                "qty_actual": qty_act,
                "variance": variance,
                "pic": str(header['pic']),
                "notes": str(header.get('notes', '-'))
            }
            data_to_insert.append(row)
            
        if data_to_insert:
            supabase.table("log_box_so").insert(data_to_insert).execute()
            return True, f"✅ Sukses! {len(data_to_insert)} item SO Box berhasil dicatat."
        return False, "❌ Keranjang Kosong!"
    except Exception as e:
        return False, f"❌ Error SO: {str(e)}"

# ==============================================================================
# 27. po_supplier
# ==============================================================================
def submit_vendor_po(po_number, supplier_name, po_date, items_cart):
    try:
        cek = supabase.table("vendor_orders").select("id").eq("po_number", po_number).execute()
        if cek.data: return False, "❌ Nomor PO sudah ada di sistem!"

        res_head = supabase.table("vendor_orders").insert({
            "po_number": po_number,
            "supplier_name": supplier_name,
            "order_date": str(po_date),
            "status": "OPEN"
        }).execute()
        
        if not res_head.data: return False, "❌ Gagal simpan header PO"
        po_id = res_head.data[0]['id']
        
        payload_items = []
        for item in items_cart:
            row = {
                "po_id": po_id,
                "category": item['category'],
                "target_qty": float(item['qty']),
                "uom": item['uom']
            }
            if item['category'] == 'RESIN':
                row['material_id'] = item['item_id']
            else:
                row['child_part_id'] = item['item_id']
            payload_items.append(row)
            
        supabase.table("vendor_order_items").insert(payload_items).execute()
        return True, "✅ PO Purchasing Berhasil Diterbitkan!"
    except Exception as e:
        return False, f"❌ Error Database: {str(e)}"

def get_all_vendor_pos():
    try:
        res = supabase.table("vendor_orders").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def get_vendor_po_details(po_number):
    try:
        res_head = supabase.table("vendor_orders").select("*").eq("po_number", po_number).execute()
        if not res_head.data: return None, []
        header = res_head.data[0]
        
        res_items = supabase.table("vendor_order_items").select(
            "*, raw_materials(type_grade, material_grade, color_grade), child_parts(part_name)"
        ).eq("po_id", header['id']).execute()
        items = res_items.data
        
        res_log_mat = supabase.table("log_material_in").select("material_id, qty").eq("po_number", po_number).execute()
        res_log_cp = supabase.table("log_child_in").select("child_part_id, qty").eq("po_number", po_number).execute()
        
        df_mat = pd.DataFrame(res_log_mat.data)
        df_cp = pd.DataFrame(res_log_cp.data)
        
        for item in items:
            received = 0
            if item['category'] == 'RESIN':
                item['item_name'] = f"{item['raw_materials']['type_grade']} - {item['raw_materials']['material_grade']} ({item['raw_materials']['color_grade']})" if item.get('raw_materials') else "Unknown Resin"
                if not df_mat.empty:
                    received = df_mat[df_mat['material_id'] == item['material_id']]['qty'].sum()
            else:
                item['item_name'] = item['child_parts']['part_name'] if item.get('child_parts') else "Unknown Part"
                if not df_cp.empty:
                    received = df_cp[df_cp['child_part_id'] == item['child_part_id']]['qty'].sum()
            
            item['received_qty'] = float(received)
            item['balance'] = float(item['target_qty']) - float(received)
            
        return header, items
    except Exception as e:
        return None, []

def close_vendor_po(po_id):
    try:
        supabase.table("vendor_orders").update({"status": "CLOSED"}).eq("id", po_id).execute()
        return True, "✅ PO Berhasil di-Close!"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def get_open_vendor_pos():
    try:
        res = supabase.table("vendor_orders").select("po_number, supplier_name").neq("status", "CLOSED").execute()
        return pd.DataFrame(res.data)
    except: 
        return pd.DataFrame()