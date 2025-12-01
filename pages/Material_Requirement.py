import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
from datetime import datetime
from supabase_client import get_supabase
from components.navbar import show_navbar

# ===== INIT =====
supabase = get_supabase()
show_navbar()

# ===== PAGE HEADER =====
st.title("📦 Material Requirement")
st.caption("Monitor your forecast-based material demand.")
st.divider()

# ===== HELPER FUNCTION =====
def safe_execute(query):
    """Wrapper Supabase execution agar aman dari error"""
    res = query.execute()
    try:
        if hasattr(res, "status_code") and res.status_code not in [200, 201]:
            st.error(f"❌ Supabase Error {res.status_code}: {res.json()}")
            return None
        return res.data
    except Exception as e:
        st.error(f"⚠️ Unexpected response format: {e}")
        return None

def fetch_materials(customer=None, month=None, type_mat=None, grade=None, color=None, limit=2000):
    query = supabase.table("material_forecast").select("*")
    if customer and customer != "All":
        query = query.eq("customer_name", customer)
    if month and month != "All":
        query = query.eq("month", month)
    if type_mat and type_mat != "All":
        query = query.eq("type_material", type_mat)
    if grade and grade != "All":
        query = query.eq("grade_material", grade)
    if color and color != "All":
        query = query.eq("color_material", color)
    query = query.order("created_at", desc=True).limit(limit)
    data = safe_execute(query)
    return pd.DataFrame(data) if data else pd.DataFrame()

def summarize_material(df):
    if df.empty:
        return pd.DataFrame()
    return (
        df.groupby(["type_material", "grade_material", "color_material"], as_index=False)
        ["total_material_weight"].sum()
        .sort_values("total_material_weight", ascending=False)
    )

# ===== FILTER SECTION =====
df_all = fetch_materials(limit=5000)
if df_all.empty:
    st.info("No material forecast data found. Please generate material forecast first.")
    st.stop()

customers = ["All"] + sorted(df_all["customer_name"].dropna().unique().tolist())
months = ["All"] + sorted(df_all["month"].dropna().unique().tolist(), key=lambda x: datetime.strptime(x, "%B %Y"), reverse=True)
types = ["All"] + sorted(df_all["type_material"].dropna().unique().tolist())
grades = ["All"] + sorted(df_all["grade_material"].dropna().unique().tolist())
colors = ["All"] + sorted(df_all["color_material"].dropna().unique().tolist())

c1, c2, c3, c4, c5 = st.columns(5)
sel_customer = c1.selectbox("Customer", customers)
sel_month = c2.selectbox("Month", months)
sel_type = c3.selectbox("Type", types)
sel_grade = c4.selectbox("Grade", grades)
sel_color = c5.selectbox("Color", colors)

df_filtered = fetch_materials(
    customer=sel_customer if sel_customer != "All" else None,
    month=sel_month if sel_month != "All" else None,
    type_mat=sel_type if sel_type != "All" else None,
    grade=sel_grade if sel_grade != "All" else None,
    color=sel_color if sel_color != "All" else None,
)

st.divider()

# ===== MAIN TABLE =====
st.subheader("📋 Material Detail Data")

if df_filtered.empty:
    st.warning("No data available for selected filters.")
else:
    st.dataframe(
        df_filtered[
            [
                "customer_name",
                "part_no",
                "part_name",
                "type_material",
                "grade_material",
                "color_material",
                "forecast_qty",
                "total_material_weight",
                "uom",
                "month",
            ]
        ],
        use_container_width=True,
    )

    # ===== SUMMARY SECTION =====
    st.divider()
    st.subheader("📊 Summary of Material Usage")
    df_summary = summarize_material(df_filtered)
    if not df_summary.empty:
        st.dataframe(df_summary, use_container_width=True)
        total_sum = df_summary["total_material_weight"].sum()
        st.success(f"💡 Total Material Required: {total_sum:,.2f} kg")

    # ===== EXPORT SECTION =====
    st.divider()
    st.download_button(
        label="⬇️ Export to Excel",
        data=df_filtered.to_csv(index=False).encode("utf-8"),
        file_name=f"Material_Requirement_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
