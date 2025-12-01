# pages/input_plan_inj.py
import streamlit as st
import pandas as pd
from datetime import date
from streamlit_option_menu import option_menu

# --- PAGE CONFIG ---
st.set_page_config(page_title="Input Plan Injection", layout="wide")

# --- NAVBAR ---
with st.container():
    selected = option_menu(
        menu_title=None,
        options=[
            "🏠 Home",
            "📋 Plan Delivery",
            "🏭 Plan Production Control",
            "🚚 Monitor Delivery",
            "📦 Stock FG",
        ],
        icons=[
            "house",
            "calendar-check",
            "building",
            "truck",
            "archive",
        ],
        default_index=2,  # posisi aktif di halaman ini
        orientation="horizontal",
    )

# --- PAGE SWITCH ---
if selected == "🏠 Home":
    st.switch_page("Home.py")
elif selected == "📋 Plan Delivery":
    st.switch_page("pages/plan_delivery.py")
elif selected == "🚚 Monitor Delivery":
    st.switch_page("pages/monitor_delivery.py")
elif selected == "📦 Stock FG":
    st.switch_page("pages/monitor_fg.py")

# --- TITLE ---
st.markdown(
    """
    <h1 style='text-align:center; color:#010044;'>📅 Input Plan Injection</h1>
    <p style='text-align:center; font-size:16px; color:gray;'>
        Tambahkan rencana produksi harian per mesin injection untuk 1 bulan penuh.
    </p>
    """,
    unsafe_allow_html=True
)
st.markdown("---")

# --- MACHINE LIST ---
MACHINES = [
    "250T",
    "450T",
    "600T",
    "850T (1)",
    "850T (2)",
    "1500T"
]

# --- SESSION STATE ---
if "plan_rows" not in st.session_state:
    st.session_state.plan_rows = []

# --- HELPER FUNCTION ---
def get_df():
    if len(st.session_state.plan_rows) == 0:
        return pd.DataFrame(columns=["Date", "Machine", "Product", "Operation", "Shift", "Qty", "Notes"])
    return pd.DataFrame(st.session_state.plan_rows)

# --- FORM INPUT ---
col1, col2 = st.columns([2, 1])

with col1:
    with st.form("form_add_plan"):
        st.subheader("📝 Tambah Plan Baru")
        c_date = st.date_input("Tanggal", value=date.today())
        c_machine = st.selectbox("Mesin", MACHINES)
        c_product = st.text_input("Produk / Part", placeholder="Contoh: Cover, Assy, Fin Foglamp")
        c_operation = st.text_input("Operation / Keterangan", placeholder="Contoh: Running, Setup, Trial")
        c_shift = st.selectbox("Shift", ["Shift 1", "Shift 2", "Shift 3", "All Day"])
        c_qty = st.number_input("Qty (target)", min_value=0, step=1)
        c_notes = st.text_input("Notes (opsional)", placeholder="Catatan tambahan")
        submitted = st.form_submit_button("➕ Tambah ke list")

        if submitted:
            new_row = {
                "Date": pd.to_datetime(c_date).strftime("%Y-%m-%d"),
                "Machine": c_machine,
                "Product": c_product.strip(),
                "Operation": c_operation.strip(),
                "Shift": c_shift,
                "Qty": int(c_qty),
                "Notes": c_notes.strip()
            }
            st.session_state.plan_rows.append(new_row)
            st.success("✅ Berhasil ditambahkan ke list.")

    st.markdown("---")
    st.subheader("📂 Import / Export CSV")
    uploaded = st.file_uploader("Upload file CSV (kolom: Date,Machine,Product,Operation,Shift,Qty,Notes)", type=["csv"])
    if uploaded:
        try:
            df_up = pd.read_csv(uploaded)
            required = {"Date", "Machine", "Product", "Operation", "Shift", "Qty"}
            if not required.issubset(set(df_up.columns)):
                st.error(f"⚠️ CSV harus memiliki kolom: {', '.join(sorted(required))}")
            else:
                for _, r in df_up.iterrows():
                    st.session_state.plan_rows.append({
                        "Date": pd.to_datetime(r["Date"]).strftime("%Y-%m-%d"),
                        "Machine": str(r["Machine"]),
                        "Product": str(r.get("Product", "")).strip(),
                        "Operation": str(r.get("Operation", "")).strip(),
                        "Shift": str(r.get("Shift", "")).strip(),
                        "Qty": int(r.get("Qty", 0)),
                        "Notes": str(r.get("Notes", "")).strip(),
                    })
                st.success(f"✅ Berhasil import {len(df_up)} baris data.")
        except Exception as e:
            st.error(f"Gagal import CSV: {e}")

with col2:
    st.subheader("⚙️ Aksi Cepat")
    if st.button("🗑️ Hapus Semua Data"):
        st.session_state.plan_rows = []
        st.experimental_rerun()

    if st.button("💾 Simpan ke File Lokal (plans_snapshot.csv)"):
        df = get_df()
        if df.empty:
            st.warning("Belum ada data untuk disimpan.")
        else:
            df.to_csv("plans_snapshot.csv", index=False)
            st.success("✅ File tersimpan di server (plans_snapshot.csv).")

# --- PREVIEW TABLE ---
st.markdown("---")
st.subheader("📊 Preview Plan Injection")

df = get_df()
if df.empty:
    st.info("Belum ada plan yang dimasukkan.")
else:
    st.dataframe(df.sort_values(["Date", "Machine"]).reset_index(drop=True), use_container_width=True)

    # Hapus baris spesifik
    st.markdown("### ✂️ Hapus Baris Tertentu")
    idx_to_delete = st.number_input("Masukkan index baris yang ingin dihapus:", min_value=0, max_value=len(df)-1, step=1)
    if st.button("Hapus Baris"):
        try:
            st.session_state.plan_rows.pop(int(idx_to_delete))
            st.success("✅ Baris dihapus.")
            st.experimental_rerun()
        except:
            st.error("Gagal menghapus baris.")

# --- DOWNLOAD BUTTON ---
st.markdown("---")
st.subheader("⬇️ Download Plan Sebagai CSV")
csv = df.to_csv(index=False).encode("utf-8")
st.download_button("Download Plan CSV", csv, "plan_injection.csv", "text/csv")

st.markdown("---")
st.info("💡 Tips: Buat plan satu bulan sekaligus menggunakan Excel, lalu upload lewat fitur Import CSV di atas.")
