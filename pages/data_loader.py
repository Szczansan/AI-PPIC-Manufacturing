# pages/data_loader.py

import pandas as pd
from supabase import Client
import calendar
from datetime import datetime
import sys
import os
import time

# --- PENYESUAIAN PATH UNTUK IMPORT DARI ROOT ---
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from supabase_client import get_supabase
except ImportError as e:
    print(f"FATAL ERROR: Gagal import supabase_client. Menggunakan Mock Data. Detail: {e}")
    # (Kode Mock Client yang diperlukan jika koneksi gagal harus ada di sini)
    class MockClient:
        def table(self, table_name):
            class MockTable:
                def select(self, columns):
                    class MockResponse:
                        def execute(self):
                            if table_name == "rules":
                                return type('obj', (object,), {'data' : [{'id': 1, 'shift_hours': 8, 'shift_per_day': 3, 'efficiency': 0.85, 'dandory_min': 30, 'startup_min': 15, 'weekend_overtime': 4, 'created_at': '...'}]})
                            elif table_name == "MASTER":
                                # Menggunakan nama kolom yang benar: part_no, tonage, cycle_time
                                return type('obj', (object,), {'data' : [{'part_no': 'A101', 'tonage': '250 T', 'cycle_time': 30}, {'part_no': 'B202', 'tonage': '450 T', 'cycle_time': 45}]})
                            elif table_name == "forcast":
                                # Mock data forecast
                                period = datetime.now().strftime("%Y-%m")
                                return type('obj', (object,), {'data' : [{'delivery_date': f'{period}-10 08:00:00', 'part_name': 'Handle', 'part_no': 'A101', 'forecast_qty': 5000}, {'delivery_date': f'{period}-11 12:00:00', 'part_name': 'Cover', 'part_no': 'B202', 'forecast_qty': 8000}, {'delivery_date': f'{period}-11 15:00:00', 'part_name': 'Handle', 'part_no': 'A101', 'forecast_qty': 3000}]})
                            return type('obj', (object,), {'data' : []})
                def upsert(self, data, on_conflict):
                    print(f"DEBUG: Mock Supabase UPSERT to {table_name} executed.")
                    return type('obj', (object,), {'data' : data})
            return MockTable()
        
    def get_supabase():
        return MockClient()


# --- KONEKSI SUPABASE ---
supabase: Client = get_supabase()

# FUNGSI GETTER (get_rules_params, get_master_data, get_filtered_forecast)
# =========================================================================

def get_rules_params() -> dict:
    """Mengambil parameter aturan produksi dari tabel 'rules' di Supabase."""
    print("-> Mengambil parameter dari tabel 'rules'...")
    try:
        response = supabase.table("rules").select("*").limit(1).execute()
        rules_data = response.data
        if not rules_data:
            print("ERROR: Tabel 'rules' kosong!")
            return {}
        return rules_data[0]
    except Exception as e:
        print(f"ERROR saat mengambil data rules: {e}")
        return {}

def get_master_data() -> pd.DataFrame:
    """Mengambil data penting (part_no, tonage, cycle_time) dari tabel 'MASTER'."""
    print("-> Mengambil data spesifikasi dari tabel 'MASTER'...")
    try:
        # Panggil kolom dengan nama yang benar di DB (misal: "part_no", "TONAGE", "CYCLE_TIME")
        response = supabase.table("MASTER").select("part_no, TONAGE, CYCLE_TIME").execute() 
        
        df_master = pd.DataFrame(response.data)
        
        if df_master.empty:
            print("   [INFO] Tabel MASTER kosong.")
            return pd.DataFrame()
            
        df_master.columns = [col.lower() for col in df_master.columns] # Paksa lowercase
        
        df_master = df_master.set_index('part_no')
        df_master.index = df_master.index.astype(str).str.strip().str.upper() # Pembersihan part_no index

        print(f"   [SUKSES] {len(df_master)} data MASTER dimuat.")
        return df_master
    except Exception as e:
        print(f"ERROR saat mengambil data MASTER: {e}")
        return pd.DataFrame() 

def get_filtered_forecast(year_month: str) -> pd.DataFrame:
    """Mengambil data dari tabel 'forcast' berdasarkan 'YYYY-MM'."""
    print(f"-> Mengambil data 'forcast' untuk periode {year_month}...")
    try:
        year, month = map(int, year_month.split('-'))
        _, last_day = calendar.monthrange(year, month)
        
        start_date = f"{year_month}-01"
        end_date = f"{year_month}-{last_day} 23:59:59" # FIX TIMESTAMP
        
        response = supabase.table("forcast") \
                           .select("delivery_date, part_name, part_no, forecast_qty") \
                           .gte("delivery_date", start_date) \
                           .lte("delivery_date", end_date) \
                           .execute()
        
        df_forecast = pd.DataFrame(response.data)
        if df_forecast.empty:
            print(f"   [INFO] Tidak ada data 'forcast' untuk periode {year_month}.")
            return df_forecast

        df_forecast['forecast_qty'] = pd.to_numeric(df_forecast['forecast_qty'], errors='coerce')
        return df_forecast
        
    except Exception as e:
        print(f"ERROR saat mengambil data forcast: {e}")
        return pd.DataFrame() 

# FUNGSI SAVE REPORT
# =========================================================================

def save_capacity_report(report_data: dict, year_month: str) -> None:
    """Menyimpan hasil perhitungan kapasitas ke tabel CAPACITY_REPORT."""
    print(f"-> Menyimpan report kapasitas untuk {year_month}...")
    data_to_insert = []
    
    for tonage, data in report_data.items():
        if 'total_sum_day' in data and 'total_changes' in data and 'total_noa_hours' in data:
            row = {
                'period_ym': year_month,
                'tonage': tonage,
                'total_sum_day': round(data['total_sum_day'], 4),
                'total_changes': data['total_changes'],
                'total_noa_hours': round(data['total_noa_hours'], 4),
            }
            data_to_insert.append(row)

    if not data_to_insert:
        return

    try:
        supabase.table("CAPACITY_REPORT").upsert(data_to_insert, on_conflict='period_ym,tonage').execute()
    except Exception as e:
        print(f"ERROR saat menyimpan report kapasitas ke DB: {e}")

# FUNGSI UTAMA PERHITUNGAN
# =========================================================================
def calculate_capacity_report(year_month: str) -> dict:
    """Fungsi utama untuk menggabungkan data, menghitung kapasitas, dan menyimpan hasilnya."""
    print("\n--- Memulai Perhitungan Kapasitas ---")
    
    df_forecast = get_filtered_forecast(year_month)
    df_master = get_master_data()
    rules = get_rules_params()
    
    if df_forecast.empty or df_master.empty or not rules:
        print("PERINGATAN: Data tidak lengkap. Perhitungan dibatalkan.")
        return {}
    
    # 1. PEMBERSIHAN DATA & JOIN
    df_forecast['part_no'] = df_forecast['part_no'].astype(str).str.strip().str.upper() # Fix case & whitespace
    df_joined = df_forecast.merge(df_master.reset_index(), on='part_no', how='left')

    # 2. FILTRASI DATA
    df_joined = df_joined[df_joined['tonage'].notna() & df_joined['cycle_time'].notna()]
    
    if df_joined.empty:
        print("PERINGATAN: Semua data dibuang karena tidak ada pasangan part_no di MASTER.")
        return {}

    # --- LANJUTAN PERHITUNGAN (Sama seperti sebelumnya) ---
    CT_IN_HOURS = df_joined['cycle_time'] / 3600
    df_joined['total_hours'] = df_joined['forecast_qty'] * CT_IN_HOURS
    
    df_joined.sort_values(by=['tonage', 'delivery_date'], inplace=True)
    df_joined['is_change'] = (df_joined['part_no'] != df_joined.groupby('tonage')['part_no'].shift(1))
    total_changes = df_joined[df_joined['is_change'] == True].groupby('tonage')['part_no'].count().reset_index(name='total_changes')
    
    df_report = df_joined.groupby(['tonage', 'part_name', 'part_no', 'cycle_time']).agg(total_hours=('total_hours', 'sum')).reset_index()
    
    rules['dandory_hours'] = rules.get('dandory_min', 0) / 60
    rules['startup_hours'] = rules.get('startup_min', 0) / 60
    
    POTENTIAL_HOURS_PER_DAY = rules.get('shift_hours', 8) * rules.get('shift_per_day', 3) * rules.get('efficiency', 0.85)
    
    final_report = {}
    
    for tonase, df_group in df_report.groupby('tonage'):
        changes_row = total_changes[total_changes['tonage'] == tonase]
        change_count = changes_row['total_changes'].iloc[0] if not changes_row.empty else 0
        total_noa_hours = change_count * (rules['dandory_hours'] + rules['startup_hours'])
        df_group['total_day'] = df_group['total_hours'] / POTENTIAL_HOURS_PER_DAY
        total_sum_day = df_group['total_day'].sum()
        
        final_report[tonase] = {
            'data_detail': df_group.to_dict(orient='records'),
            'total_changes': change_count,
            'total_noa_hours': total_noa_hours,
            'potential_hours_per_day': POTENTIAL_HOURS_PER_DAY,
            'total_sum_day': total_sum_day
        }
        
    print(f"   [SELESAI] Perhitungan kapasitas berhasil.")
    save_capacity_report(final_report, year_month)
    
    return final_report