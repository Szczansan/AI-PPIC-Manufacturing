import logging
from supabase import create_client, Client
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# --- 1. CONFIG ---
SUPABASE_URL = "https://laxagfijnbcpzxjvwutq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxheGFnZmlqbmJjcHp4anZ3dXRxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjE0MDE1ODIsImV4cCI6MjA3Njk3NzU4Mn0.VkYg-4zu1SjNzv1RqzccHnKCMY0NDHsDrd6Il3paC6U"
TELEGRAM_TOKEN = "8208649184:AAF0viugACi1u8bWaRMv9IeP0DNbrUUUj8c"

# Koneksi ke Database
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"❌ Error Config Supabase: {e}")
    exit()

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 2. FUNGSI CEK DATABASE ---

# A. Cek Stock FG / WIP (Dari view v_alert_bot)
def get_critical_stock():
    try:
        response = supabase.table("v_alert_bot").select("*").execute()
        return response.data
    except Exception as e:
        print(f"❌ Error DB Alert: {e}")
        return []

# B. Cek Stock Material (Dari view v_material_balance)
def get_material_stock():
    try:
        # Kita filter yang balance <= 50 (Low Stock / Minus) biar bot gak spam semua item
        # Kalau mau munculin SEMUA, hapus bagian .lte("balance", 50)
        response = supabase.table("v_material_balance")\
            .select("*")\
            .lte("balance", 50)\
            .order("balance", desc=False)\
            .execute()
        return response.data
    except Exception as e:
        print(f"❌ Error DB Material: {e}")
        return []

# --- 3. LOGIC BALAS CHAT ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_user = update.message.text.lower()
    user_name = update.message.from_user.first_name
    
    print(f"📩 {user_name}: {text_user}")

    # --- LOGIC 1: CEK MATERIAL ---
    if "cek stock material" in text_user:
        await update.message.reply_text("Sebentar bre, lagi ngecek silo material...")
        
        data_material = get_material_stock()
        
        if not data_material:
            await update.message.reply_text(
                "✅ *STOCK MATERIAL AMAN*\nSemua material balance di atas 50.",
                parse_mode='Markdown'
            )
        else:
            # Header
            msg_lines = ["🚨 *ALERT MATERIAL LOW/MINUS!*"]
            
            for m in data_material:
                # Ambil data kolom (sesuai view v_material_balance)
                type_m = m.get('type_material', '-')
                grade_m = m.get('grade_material', '-')
                color_m = m.get('color_material', '-')
                bal = m.get('balance', 0)
                
                # Format: AS2 - GRADE - COLOR | Bal: -10
                msg_lines.append(f"⚠️ {type_m} {grade_m} ({color_m})\n    └ Stok: *{bal}*" )
            
            final_msg = "\n".join(msg_lines)
            final_msg += "\n\n👉 *Segera info Purchasing/Gudang!*"
            
            await update.message.reply_text(final_msg, parse_mode='Markdown')
            
        return # Stop disini biar gak lanjut ke logic bawah

    # --- LOGIC 2: CEK FG / WIP ---
    target_tipe = ""
    if "cek stock fg" in text_user:
        target_tipe = "FG"
    elif "cek stock wip" in text_user:
        target_tipe = "WIP"
    else:
        return # Kalau chat gak jelas, diem aja

    # Respon FG/WIP
    await update.message.reply_text(f"Sebentar bre, lagi narik data {target_tipe}...")
    all_critical_data = get_critical_stock()
    specific_data = [item for item in all_critical_data if item.get('tipe') == target_tipe]

    if not specific_data:
        await update.message.reply_text(
            f"✅ *STOCK {target_tipe} AMAN TERKENDALI*\nTidak ada item yang dibawah safety stock.", 
            parse_mode='Markdown'
        )
    else:
        msg_lines = [f"🚨 *STOCK {target_tipe} CRITICAL!*"]
        for item in specific_data:
            part_name = item.get('PART_NAME') or item.get('part_no')
            curr = item.get('current_stock', 0)
            min_s = int(item.get('min_stock', 0))
            msg_lines.append(f"⚠️ {part_name}\n    Stok: {curr} | Min: {min_s}")
            
        final_msg = "\n".join(msg_lines)
        final_msg += "\n\n👉 *Segera info tim produksi!*"
        await update.message.reply_text(final_msg, parse_mode='Markdown')

# --- 4. PROGRAM UTAMA ---
if __name__ == "__main__":
    if TELEGRAM_TOKEN == "ISI_TOKEN_DARI_BOTFATHER_DISINI":
        print("❌ TOKEN BELUM DIISI!")
        exit()

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Handle text biasa (bukan command /)
    chat_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(chat_handler)

    print("---------------------------------------")
    print("🚀 BOT PPIC V2 (FG + WIP + MATERIAL) ACTIVE")
    print("---------------------------------------")
    
    application.run_polling()