import os
import streamlit as st
from supabase import create_client, Client

# Pakai cache_resource biar koneksi gak dibuat berulang-ulang (Hemat resource & Cepat)
@st.cache_resource
def init_supabase() -> Client:
    """
    Inisialisasi koneksi Supabase.
    Prioritas 1: Environment Variables (Buat Railway/Server)
    Prioritas 2: Streamlit Secrets (Buat Local/Streamlit Cloud)
    """
    
    # 1. Coba ambil dari Environment Variable (Settingan Railway)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. Kalau di Env kosong, coba ambil dari secrets.toml (Local)
    if not url or not key:
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        except FileNotFoundError:
            st.error("🚨 Kritis: File .streamlit/secrets.toml gak ketemu!")
            st.stop()
        except KeyError:
            st.error("🚨 Kritis: Config 'supabase' (url/key) belum diset di secrets/env!")
            st.stop()

    # Buat Client
    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        st.error(f"🚨 Gagal connect ke Supabase: {e}")
        st.stop()

# Bikin satu instance client biar bisa di-import langsung
supabase = init_supabase()
