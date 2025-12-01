from supabase_client import get_supabase

supabase = get_supabase()

def get_machines_by_tonage(tonage):
    """
    Ambil semua mesin dari table INFO.machine berdasarkan TONAGE.
    Return: list of machine_id (ex: ['MC 450T-1', 'MC 450T-2'])
    """
    res = supabase.table("machine").select("*").eq("tonage", tonage).order("machine_id").execute()

    if hasattr(res, "data"):
        rows = res.data
    else:
        rows = res

    return [r["machine_id"] for r in rows]
