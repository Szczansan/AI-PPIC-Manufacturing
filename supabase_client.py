from supabase import create_client, Client

SUPABASE_URL = "https://laxagfijnbcpzxjvwutq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxheGFnZmlqbmJjcHp4anZ3dXRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDE1ODIsImV4cCI6MjA3Njk3NzU4Mn0.VkYg-4zu1SjNzv1RqzccHnKCMY0NDHsDrd6Il3paC6U"

def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)
    