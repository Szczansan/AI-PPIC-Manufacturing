# pages/data_loader.py
import pandas as pd
import sys
import os
import streamlit as st

# Setup Path & Client
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from supabase_client import get_supabase
    supabase = get_supabase()
except Exception as e:
    st.error(f"FATAL: Gagal connect Supabase. {e}")
    supabase = None

def get_capacity_summary(period_ym: str) -> pd.DataFrame:
    """Mengambil Rekapitulasi Load per Mesin (Header)"""
    try:
        # Ambil dari View Summary
        response = supabase.table("view_machine_load_monthly") \
            .select("*") \
            .eq("forecast_month", period_ym) \
            .order("machine_id") \
            .execute()
        
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Error load summary: {e}")
        return pd.DataFrame()

def get_capacity_detail(period_ym: str) -> pd.DataFrame:
    """Mengambil Rincian Part per Mesin (Isi Tabel)"""
    try:
        # Ambil dari View Detail
        response = supabase.table("view_part_detail_monthly") \
            .select("*") \
            .eq("forecast_month", period_ym) \
            .execute()
        
        df = pd.DataFrame(response.data)
        return df
    except Exception as e:
        st.error(f"Error load details: {e}")
        return pd.DataFrame()

def get_rules_info() -> dict:
    """Mengambil info Rules buat ditampilkan di Header Dashboard"""
    try:
        response = supabase.table("rules").select("*").limit(1).execute()
        if response.data:
            return response.data[0]
        return {}
    except:
        return {}