print("LOADING rules_service FROM:", __file__)

from supabase_client import get_supabase
supabase = get_supabase()

def get_rules():
    res = (
        supabase
        .table("rules")
        .select("*")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )

    if hasattr(res, "data") and res.data:
        return res.data[0]

    return {
        "shift_hours": 7,
        "shift_per_day": 3,
        "efficiency": 0.9,
        "dandory_min": 30,
        "startup_min": 15
    }
    