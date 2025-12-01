print("LOADING master_service.py FROM:", __file__)


from supabase_client import get_supabase

supabase = get_supabase()

def get_master_map():
    """Ambil seluruh MASTER dan kembalikan dict dengan key=part_no"""
    res = supabase.table("MASTER").select("*").execute()

    if hasattr(res, "data"):
        rows = res.data
    else:
        rows = res

    master_map = {}
    for row in rows:
        master_map[row["PART_NO"]] = {
            "part_no": row["PART_NO"],
            "part_name": row.get("PART_NAME", ""),
            "cycle_time": row.get("CYCLE_TIME", 0),
            "cavity": row.get("CAV", 1),
            "tonage": row.get("TONAGE", 0),
        }

    return master_map
