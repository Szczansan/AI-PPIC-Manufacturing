print(">>> LOADING forecast_service.py FROM:", __file__)

from supabase_client import get_supabase

supabase = get_supabase()

def get_forecast_by_month(month):
    """Ambil forecast berdasarkan month field (ex: 'November 2025')"""
    res = supabase.table("forcast").select("*").eq("month", month).execute()

    if hasattr(res, "data"):
        return res.data
    return res
