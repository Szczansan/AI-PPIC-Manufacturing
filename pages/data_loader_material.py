# pages/data_loader_material.py
# Logika Perhitungan Kebutuhan Material (Kg)

import pandas as pd
from supabase import Client
import time
import sys
import os

# --- IMPORT DARI ROOT (supabase_client) & DATA LOADER UTAMA ---
# Memastikan akses ke root directory dan fungsi data umum
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_client import get_supabase
# Asumsi: get_filtered_forecast ada di pages/data_loader.py
from pages.data_loader import get_filtered_forecast 

# --- KONEKSI SUPABASE ---
supabase: Client = get_supabase()

# =========================================================================
# 1. GETTER: Mengambil Data MASTER untuk BOM
# =========================================================================
def get_master_bom_data() -> pd.DataFrame:
    """
    Mengambil data BOM spesifik (GROSS, Material Specs) dari tabel 'MASTER'.
    """
    print("-> Mengambil data MASTER untuk BOM...")
    try:
        # Mengambil kolom yang dikonfirmasi: part_no, GROSS, TYPE_MATERIAL, GRADE_MATERIAL, COLOR_MATERIAL
        response = supabase.table("MASTER").select("part_no, GROSS, TYPE_MATERIAL, GRADE_MATERIAL, COLOR_MATERIAL").execute() 
        
        df_master = pd.DataFrame(response.data)
        
        if df_master.empty:
            print("   [INFO] Tabel MASTER BOM kosong.")
            return pd.DataFrame()
            
        # FIX: Paksa semua nama kolom di DataFrame menjadi lowercase
        df_master.columns = [col.lower() for col in df_master.columns]

        # Bersihkan part_no
        df_master['part_no'] = df_master['part_no'].astype(str).str.strip().str.upper()
        
        print(f"   [SUKSES] {len(df_master)} data MASTER BOM dimuat.")
        return df_master
    except Exception as e:
        print(f"ERROR saat mengambil data MASTER BOM: {e}")
        return pd.DataFrame() 

# =========================================================================
# 2. FUNGSI PENYIMPANAN MATERIAL REPORT
# =========================================================================

def save_material_report(report_df: pd.DataFrame, year_month: str) -> None:
    """
    Menyimpan hasil perhitungan kebutuhan material ke tabel MATERIAL_REPORT.
    """
    print(f"-> Menyimpan report material untuk {year_month}...")
    # ... (Logika penyimpanan sama seperti sebelumnya)
    data_to_insert = report_df[[
        'material_id_unique', 'material_type', 'material_grade', 
        'material_color', 'total_required_kg'
    ]].copy()
    
    data_to_insert['period_ym'] = year_month
    
    # Rename untuk mencocokkan skema DB
    data_to_insert.rename(columns={'material_type': 'material_type', 
                                    'material_grade': 'material_grade', 
                                    'material_color': 'material_color'}, inplace=True)
    try:
        supabase.table("MATERIAL_REPORT").upsert(
            data_to_insert.to_dict('records'), 
            on_conflict='period_ym,material_id_unique' 
        ).execute()
        print(f"   [SUKSES] Report material berhasil disimpan/diperbarui.")
        
    except Exception as e:
        print(f"ERROR saat menyimpan report material: {e}")


# =========================================================================
# 3. FUNGSI UTAMA PERHITUNGAN MATERIAL
# =========================================================================

def calculate_material_report(year_month: str) -> pd.DataFrame:
    """
    Menghitung kebutuhan material (Kg) berdasarkan forecast dan data MASTER (GROSS / 1000).
    """
    print(f"\n--- Memulai Perhitungan Material untuk {year_month} ---")
    try:
        # 1. Ambil data forecast (QTY)
        # Mengimpor dari file data_loader.py yang sudah ada
        forecast_df = get_filtered_forecast(year_month) 
        if forecast_df.empty:
            return pd.DataFrame()

        # 2. Ambil data MASTER (BOM/GROSS)
        master_df = get_master_bom_data()
        if master_df.empty:
            print("ERROR: Data MASTER BOM kosong.")
            return pd.DataFrame()

        # 3. Join Forecast (QTY) dengan MASTER (GROSS/Material Specs)
        forecast_df['part_no'] = forecast_df['part_no'].astype(str).str.strip().str.upper() # Clean part_no forecast
        
        material_needs = pd.merge(
            forecast_df,
            master_df,
            on='part_no',
            how='left'
        )
        
        # Hapus baris yang gagal di-join atau GROSS/QTY-nya NULL
        material_needs.dropna(subset=['gross'], inplace=True) 

        # 4. Pembersihan Data & Tipe Data
        material_needs['forecast_qty'] = pd.to_numeric(material_needs['forecast_qty'], errors='coerce').fillna(0)
        material_needs['gross'] = pd.to_numeric(material_needs['gross'], errors='coerce').fillna(0)
        
        # 5. Hitung Kebutuhan Total (Kg)
        # Total Kg = (forecast_qty * gross (gram)) / 1000
        material_needs['required_kg'] = (material_needs['forecast_qty'] * material_needs['gross']) / 1000
        
        # 6. Buat Material ID Unik (Concatenation, Tahan NULL/Kosong)
        cols_to_combine = ['type_material', 'grade_material', 'color_material']
        
        for col in cols_to_combine:
            # Isi NULL dengan string kosong dan konversi ke UPPERCASE untuk konsistensi grouping
            material_needs[col] = material_needs.get(col, pd.Series([''] * len(material_needs))).fillna('').astype(str).str.strip().str.upper()
                
        # Concatenate: Gabungkan semua kolom dengan pemisah '-'
        material_needs['material_id_unique'] = material_needs[cols_to_combine].apply(
            lambda row: '-'.join(row.values), axis=1
        )
        
        # 7. Rangkum Total Kebutuhan per Material
        material_report = material_needs.groupby([
            'material_id_unique', 
            'type_material', 
            'grade_material', 
            'color_material'
        ]).agg(
            total_required_kg=('required_kg', 'sum'),
            total_forecast_parts=('forecast_qty', 'sum') 
        ).reset_index()
        
        material_report.rename(columns={
            'type_material': 'material_type',
            'grade_material': 'material_grade',
            'color_material': 'material_color'
        }, inplace=True)
        
        material_report['unit'] = 'Kg'

        # 8. Simpan Hasil ke DB dan Kembalikan DataFrame
        save_material_report(material_report, year_month)
        
        print("   [SELESAI] Perhitungan Material Berhasil.")
        return material_report.sort_values(by='total_required_kg', ascending=False)

    except Exception as e:
        print(f"ERROR: calculate_material_report gagal: {e}")
        return pd.DataFrame()