import pandas as pd
from supabase_client import supabase

try:
    from modules import get_master_products
except ImportError:
    pass

# =====================================================================
# [GLOBAL HELPERS] - FUNGSI TARIK DATA UMUM / MASTER DATA
# Dipakai di berbagai page untuk kebutuhan dropdown/list
# =====================================================================

def get_ppc_po_list():
    try:
        res = supabase.table("purchase_orders").select("po_number, customer_name").eq("status", "OPEN").order("created_at", desc=True).execute()
        return [f"{i['po_number']} | {i['customer_name']}" for i in res.data]
    except: return []

def get_po_items_details(po_number):
    try:
        po_res = supabase.table("purchase_orders").select("id").eq("po_number", po_number).execute()
        if not po_res.data: return pd.DataFrame()
        items_res = supabase.table("purchase_order_items").select("*").eq("po_id", po_res.data[0]['id']).execute()
        return pd.DataFrame(items_res.data)
    except: return pd.DataFrame()

def get_raw_materials_list():
    """ [NEW] Helper buat narik data Resin di dropdown Add Component """
    try:
        res = supabase.table("raw_materials").select("id, full_name").order("full_name").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()


# =====================================================================
# [PAGE: DASHBOARD PPC] - LOGIC TRACKING PRODUKSI vs PO
# =====================================================================

def get_daily_production_by_part(part_no, start_date, end_date):
    """
    [FIXED] Untuk Dashboard PPC: Tracking PO vs Realisasi.
    Menggunakan kolom 'qty' (Good Part Only), karena Sales jualnya barang OK.
    """
    try:
        res = supabase.table("wip_in")\
            .select("date_in, qty, part_no")\
            .eq("part_no", part_no)\
            .gte("date_in", str(start_date))\
            .lte("date_in", str(end_date))\
            .execute()
        
        df = pd.DataFrame(res.data)
        if df.empty: return pd.DataFrame(columns=['date_in', 'qty'])
        
        df['date_in'] = pd.to_datetime(df['date_in']).dt.date
        return df.groupby('date_in')['qty'].sum().reset_index()
    except Exception as e:
        return pd.DataFrame(columns=['date_in', 'qty'])


# =====================================================================
# [PAGE: RUNDOWN PART & BOM] - LOGIC MASTER BOM (TAB 1)
# =====================================================================

def get_bom_details_by_part_no(part_no_input):
    """
    Fungsi Utama Tarik BOM via Text Part Number.
    [UPDATED] Sekarang bisa narik Child Part DAN Resin sekaligus.
    """
    try:
        clean_no = str(part_no_input).strip()
        
        # 1. Cari Product ID berdasarkan Part No
        prod_res = supabase.table("products").select("*").eq("part_no", clean_no).execute()
        if not prod_res.data:
            return {"master": {}, "children": [], "error": f"Part No '{clean_no}' tidak ditemukan di Database."}
            
        prod_data = prod_res.data[0]
        real_uuid = prod_data['id'] 
        
        # 2. Ambil List Component (Join ke child_parts DAN raw_materials)
        # Hapus .eq("component_type", "CHILD") biar Resin ikut ketarik
        bom_res = supabase.table("master_bom")\
            .select("*, child_parts(part_name), raw_materials(full_name)")\
            .eq("product_id", real_uuid)\
            .execute()
            
        components = []
        for item in bom_res.data:
            comp_type = item.get('component_type', 'CHILD')
            
            # Filter penamaan berdasarkan tipe komponen
            if comp_type == 'RESIN':
                c_name = item['raw_materials']['full_name'] if item.get('raw_materials') else "Unknown Resin"
            else:
                c_name = item['child_parts']['part_name'] if item.get('child_parts') else "Unknown Part"
                
            components.append({
                "id": item['id'],
                "name": c_name,
                "usage": float(item['usage_qty']),
                "type": comp_type
            })
            
        return {
            "master": prod_data, 
            "children": components, # Frontend tetep pakai key 'children' biar ga error di tabel
            "error": None
        }
    except Exception as e:
        return {"master": {}, "children": [], "error": str(e)}

def add_bom_item(product_uuid, item_id, qty, component_type="CHILD"):
    """
    [UPDATED] Evolusi dari add_child_part_bom. 
    Sekarang jadi universal, bisa nambahin Child Part atau Resin.
    """
    try:
        # Cek duplikat & Set Payload sesuai tipe
        if component_type == "RESIN":
            cek = supabase.table("master_bom").select("*").eq("product_id", str(product_uuid)).eq("material_id", str(item_id)).execute()
            if cek.data: return False, "❌ Resin ini sudah ada di list!"
            payload = {"product_id": str(product_uuid), "component_type": "RESIN", "material_id": str(item_id), "usage_qty": qty}
            msg = "✅ Resin / Mix Berhasil Ditambahkan!"
        else:
            cek = supabase.table("master_bom").select("*").eq("product_id", str(product_uuid)).eq("child_part_id", str(item_id)).execute()
            if cek.data: return False, "❌ Part ini sudah ada di list!"
            payload = {"product_id": str(product_uuid), "component_type": "CHILD", "child_part_id": str(item_id), "usage_qty": qty}
            msg = "✅ Child Part Berhasil Ditambahkan!"

        supabase.table("master_bom").insert(payload).execute()
        return True, msg
    except Exception as e:
        return False, f"❌ Error Database: {e}"

def delete_bom_item(bom_id):
    try:
        supabase.table("master_bom").delete().eq("id", bom_id).execute()
        return True
    except: return False


# =====================================================================
# [PAGE: RUNDOWN PART & BOM] - LOGIC REPORTING & CCTV (TAB 2)
# =====================================================================

def get_daily_usage_analysis(product_id, part_no, start_date, end_date):
    """
    LOGIC TOTAL CONSUMPTION (Revisi: Total Qty = Good + NG)
    """
    try:
        res = supabase.table("wip_in").select("date_in, total_qty").eq("part_no", part_no)\
            .gte("date_in", str(start_date)).lte("date_in", str(end_date)).order("date_in").execute()
        
        df_prod = pd.DataFrame(res.data)
        if df_prod.empty: return pd.DataFrame(), {}
        
        df_prod['date_in'] = pd.to_datetime(df_prod['date_in']).dt.date
        df_daily = df_prod.groupby('date_in')['total_qty'].sum().reset_index()
        
        bom_data = get_bom_details_by_part_no(part_no)
        master = bom_data.get('master', {})
        children = bom_data.get('children', [])
        
        if not master: return df_daily, {}

        weight = float(master.get('part_weight', 0) or 0)
        
        try:
            raw_pct = master.get('composition_percentage', '0')
            mix_pct = float(str(raw_pct).replace('%', ''))
        except:
            mix_pct = 0
            
        summary_cols = [] 
        
        # 1. Material (Hitung dari master weight)
        mat_col_name = f"Mat: {master.get('material_type','-')} {master.get('material_grade','-')} ({master.get('material_color','-')})"
        df_daily[mat_col_name] = df_daily['total_qty'] * weight
        summary_cols.append({"name": mat_col_name, "type": "MATERIAL", "val": df_daily[mat_col_name].sum()})
        
        # 2. Masterbatch (Mix)
        mix_name = master.get('material_mix')
        if mix_name and mix_pct > 0:
            mb_col_name = f"Mix: {mix_name} ({mix_pct}%)"
            df_daily[mb_col_name] = (df_daily['total_qty'] * weight) * (mix_pct / 100)
            summary_cols.append({"name": mb_col_name, "type": "MIX", "val": df_daily[mb_col_name].sum()})
            
        # 3. Child Parts & Resin tambahan di BOM (Iterasi dinamis)
        for child in children:
            # Karena sekarang dict punya key 'type', kita bisa pisahin labelnya biar keren
            label_prefix = "Resin" if child.get('type') == 'RESIN' else "Part"
            c_col_name = f"{label_prefix}: {child['name']}"
            
            df_daily[c_col_name] = df_daily['total_qty'] * child['usage']
            summary_cols.append({"name": c_col_name, "type": child.get('type', 'CHILD'), "val": df_daily[c_col_name].sum()})
            
        return df_daily, summary_cols
        
    except Exception as e:
        print(f"Error PPC Report: {e}")
        return pd.DataFrame(), {}

def get_production_performance(part_no, start_date, end_date):
    """
    Fungsi SAKTI untuk Tab 2:
    1. Mengambil data harian (QTY OK, NG, PLAN).
    2. Mengambil data material (Berat Master vs Berat Aktual).
    """
    try:
        prod_res = supabase.table("products").select("part_weight, part_name").eq("part_no", part_no).execute()
        if not prod_res.data:
            return pd.DataFrame(), 0, 0
            
        master_weight = float(prod_res.data[0]['part_weight'] or 0)
        
        res = supabase.table("wip_in")\
            .select("date_in, qty, plan_qty, total_ng, total_qty, part_weight_act")\
            .eq("part_no", part_no)\
            .gte("date_in", str(start_date))\
            .lte("date_in", str(end_date))\
            .order("date_in")\
            .execute()
            
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return df, master_weight, 0

        df['date_in'] = pd.to_datetime(df['date_in']).dt.date
        df['qty'] = df['qty'].fillna(0).astype(int)            
        df['total_ng'] = df['total_ng'].fillna(0).astype(int)  
        df['plan_qty'] = df['plan_qty'].fillna(0).astype(int)  
        df['total_qty'] = df['total_qty'].fillna(0).astype(int) 
        df['part_weight_act'] = df['part_weight_act'].fillna(master_weight).astype(float) 

        df['mat_std_usage'] = df['total_qty'] * master_weight
        df['mat_act_usage'] = df['total_qty'] * df['part_weight_act']
        df['mat_variance'] = df['mat_act_usage'] - df['mat_std_usage']

        return df, master_weight, len(df) 

    except Exception as e:
        print(f"Error Performance: {e}")
        return pd.DataFrame(), 0, 0


# =====================================================================
# [PAGE: RUNDOWN PART & BOM] - LOGIC MRP CALCULATOR (TAB 2)
# =====================================================================

def get_po_mrp_breakdown(po_number):
    """
    MRP Calculator Updated
    """
    try:
        df_items = get_po_items_details(po_number)
        if df_items.empty: return []

        rundown_data = []

        for _, row in df_items.iterrows():
            part_no = row['part_no']
            qty_order = row['qty_order']
            
            prod_res = supabase.table("products").select("*").eq("part_no", part_no).execute()
            if not prod_res.data: continue
                
            prod = prod_res.data[0]
            
            # --- 1. PARAMETER WAKTU ---
            ct = float(prod.get('std_cycle_time', 0) or 0)
            weight = float(prod.get('part_weight', 0) or 0)
            cav = int(prod.get('cav', 1) or 1)
            eff = 0.90
            
            if cav < 1: cav = 1
            
            if ct > 0:
                total_seconds_machine = (qty_order * ct) / (cav * eff)
                est_hours = total_seconds_machine / 3600
            else:
                est_hours = 0
            
            # --- 2. PARAMETER MATERIAL (SPLIT LOGIC) ---
            base_total_kg = (qty_order * weight) / 1000
            total_req_kg = base_total_kg * 1.02 # Buffer 2%
            
            mix_name = prod.get('material_mix')
            raw_pct = str(prod.get('composition_percentage', '0')).replace('%', '').strip()
            
            try: mix_pct = float(raw_pct) if raw_pct else 0
            except: mix_pct = 0
                
            if mix_name and mix_pct > 0:
                mb_kg = total_req_kg * (mix_pct / 100)
                resin_kg = total_req_kg - mb_kg
            else:
                mb_kg = 0
                resin_kg = total_req_kg
                
            mat_type = prod.get('material_type', '-')
            mat_grade = prod.get('material_grade', '')
            mat_color = prod.get('material_color', '')
            full_mat_name = f"{mat_type} {mat_grade} ({mat_color})".strip()

            # --- 3. CHILD PARTS ---
            bom_data = get_bom_details_by_part_no(part_no)
            children = bom_data.get('children', [])
            
            child_needs = []
            for child in children:
                # Filter biar di MRP Breakdown cuma ngitung Child Part murni aja
                # (Karena Resin utama udah dihitung otomatis dari part_weight di atas)
                if child.get('type') == 'CHILD':
                    req_qty = qty_order * child['usage']
                    child_needs.append({
                        "name": child['name'],
                        "usage": child['usage'],
                        "total_req": req_qty
                    })

            rundown_data.append({
                "part_name": row['part_name'],
                "part_no": part_no,
                "qty_order": qty_order,
                "ct_sec": ct,
                "cav": cav,
                "est_hours": est_hours,
                "mat_full_name": full_mat_name,
                "resin_kg": resin_kg,
                "mb_name": mix_name,
                "mb_kg": mb_kg,
                "mb_pct": mix_pct,
                "child_parts": child_needs
            })
            
        return rundown_data

    except Exception as e:
        print(f"Error MRP Breakdown: {e}")
        return []