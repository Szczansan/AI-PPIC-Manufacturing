import pandas as pd
import streamlit as st
import sys
import os

# Setup Path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from supabase_client import get_supabase
except Exception as e:
    st.error(f"System Path Error: {e}")

def get_material_requirements(period_ym: str) -> pd.DataFrame:
    """
    Mengambil data matang dari VIEW calculate_material.
    Gak ada hitungan lagi disini, cuma tarik data.
    """
    supabase = get_supabase()
    
    try:
        # Tarik data sesuai bulan yang dipilih
        response = supabase.table("calculate_material") \
            .select("*") \
            .eq("forecast_month", period_ym) \
            .execute()
        
        df = pd.DataFrame(response.data)
        return df

    except Exception as e:
        st.error(f"Gagal load view material: {e}")
        return pd.DataFrame()

def get_available_months() -> list:
    """Ambil list bulan yang tersedia di view (biar dropdown-nya akurat)"""
    supabase = get_supabase()
    try:
        # Ambil distinct month (trik pakai .select)
        # Note: Supabase JS client kadang butuh trik buat distinct, 
        # tapi cara paling aman kita ambil kolomnya lalu unique di pandas kalau datanya dikit.
        # Atau kalau mau query distinct langsung via rpc/query ribet. 
        # Kita pakai cara simple: Ambil kolom bulan aja, lalu unique di Python.
        res = supabase.table("calculate_material").select("forecast_month").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            return sorted(df['forecast_month'].unique().tolist(), reverse=True)
        return []
    except:
        return []