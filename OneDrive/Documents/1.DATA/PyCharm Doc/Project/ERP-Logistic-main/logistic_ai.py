import logging
import traceback
import html
import json
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode, ChatAction
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    MessageHandler, filters, ConversationHandler
)
from supabase import create_client, Client
import google.generativeai as genai

# ==========================================
# 1. KONFIGURASI (ISI DATA ASLI LOE!)
# ==========================================
SUPABASE_URL = "https://glwjceaehdtrbtocudcj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imdsd2pjZWFlaGR0cmJ0b2N1ZGNqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc2NjIxOTksImV4cCI6MjA4MzIzODE5OX0.TxlNQkoGfJ7m0sIWk_M73lB9lgiQQTg8lnykzWBLyco"
TELEGRAM_TOKEN = "8399172279:AAERnUxI0MshhGz0acw8AFmvlpI6-4yqRT0"
GEMINI_API_KEY = "AIzaSyDdpEUN9te2DbWHTFwB2tU5vjKh-vQosW4"
ALLOWED_USER_ID = 1104208558 # ID Telegram Loe

# ==========================================
# 2. SETUP LOGGING (BIAR GAK BISU)
# ==========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# Matikan log berisik dari library lain
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Init Systems
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-flash-lite-latest')
except Exception as e:
    logger.error(f"GAGAL INIT SYSTEM: {e}")

# STATES
CHOOSING_CATEGORY, INPUT_QTY, INPUT_PIC = range(3)

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def get_categories():
    try:
        res = supabase.table("products").select("part_name").eq("status", "ACTIVE").execute()
        items = [row['part_name'] for row in res.data]
        if not items: return []
        # Ambil kata depan
        categories = sorted(list(set([name.split(' ')[0].upper() for name in items])))
        return categories
    except Exception as e:
        logger.error(f"DB Error Categories: {e}")
        return []

def get_products_by_category(category):
    try:
        res = supabase.table("products").select("id, part_name, part_no").ilike("part_name", f"{category}%").eq("status", "ACTIVE").execute()
        return res.data
    except Exception as e:
        logger.error(f"DB Error Products: {e}")
        return []

def save_transfer_log(product, qty, pic_name):
    try:
        receiver_format = f"GUDANG FG ({pic_name.upper()})"
        payload = {
            "date_out": datetime.now().strftime("%Y-%m-%d"),
            "part_name": product['part_name'],
            "part_no": product['part_no'],
            "qty": int(qty),
            "doc_no": f"BOT-{int(datetime.now().timestamp())}", 
            "receiver": receiver_format,
            "notes": "Input via Telegram Bot"
        }
        supabase.table("wip_out").insert(payload).execute()
        return True
    except Exception as e:
        logger.error(f"Save Error: {e}")
        return False

def get_stock_overview():
    """
    Narik data stock LANGSUNG dari RPC (Sumber Kebenaran Streamlit).
    """
    try:
        # Kita set tanggal hari ini biar datanya realtime
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # PANGGIL FUNCTION SAKTI (RPC) YANG DIPAKE STREAMLIT
        res = supabase.rpc('get_fg_daily_report', {'target_date': today_str}).execute()
        
        if not res.data:
            return "Data Stock Kosong / Gagal Load RPC."
            
        stock_text = f"📊 **POSISI STOCK GUDANG ({today_str})**:\n"
        
        # Loop data dari RPC
        for row in res.data:
            name = row.get('part_name', 'Unknown')
            # Di RPC loe, nama kolom saldo akhir itu 'balance'
            qty = row.get('balance', 0)
            
            # Tampilkan cuma yang ada isinya (biar gak spam 0)
            if qty != 0:
                stock_text += f"- {name}: **{qty}** Pcs\n"
            
        return stock_text

    except Exception as e:
        logger.error(f"Error Get Stock Overview: {e}")
        return "Gagal mengambil data stock (RPC Error)."

# ==========================================
# 4. HANDLERS
# ==========================================

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buat ngetes bot idup apa nggak"""
    await update.message.reply_text(" PONG! Bot Online & Siap Bre.")

async def start_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"User {user.first_name} trigger /update_stock")
    
    if user.id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Loe gak punya akses bre.")
        return ConversationHandler.END

    categories = get_categories()
    if not categories:
        await update.message.reply_text("⚠️ Data Produk Kosong/Gagal Load. Cek Database (Pastikan status='ACTIVE').")
        return ConversationHandler.END
    
    keyboard = [categories[i:i + 2] for i in range(0, len(categories), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(" **TRANSFER FG**\nPilih Kategori:", reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    return CHOOSING_CATEGORY

async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    products = get_products_by_category(category)
    
    if not products:
        await update.message.reply_text("❌ Kategori salah.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    product_map = {str(i+1): p for i, p in enumerate(products)}
    context.user_data['product_map'] = product_map
    
    msg = f" Kategori: **{category}**\nFormat: `No=Qty` (Cth: `1=200`)\n\n"
    for idx, p in product_map.items():
        msg += f"*{idx}. {p['part_name']}*\n"
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove(), parse_mode=ParseMode.MARKDOWN)
    return INPUT_QTY

async def input_qty_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_text = update.message.text
    product_map = context.user_data.get('product_map')
    temp_trx_list = []
    preview_text = "Konfirmasi Transfer:\n"
    
    try:
        entries = [e.strip() for e in raw_text.split(',')]
        for entry in entries:
            if '=' not in entry: continue
            idx, qty = entry.split('=')
            idx = idx.strip(); qty = qty.strip()
            
            if idx in product_map and qty.isdigit():
                target = product_map[idx]
                temp_trx_list.append({"product": target, "qty": qty})
                preview_text += f"- {target['part_name']}: **{qty} Pcs**\n"
            else:
                await update.message.reply_text(f"❌ Input ngaco: {entry}. Ulangi ya.")
                return ConversationHandler.END
                
        if not temp_trx_list:
            await update.message.reply_text("❌ Gak ada data valid.")
            return ConversationHandler.END
            
        context.user_data['pending_transactions'] = temp_trx_list
        await update.message.reply_text(f"{preview_text}\n‍♂️ **Nama PIC?**", parse_mode=ParseMode.MARKDOWN)
        return INPUT_PIC

    except Exception as e:
        logger.error(f"Input Error: {e}")
        await update.message.reply_text("Error parsing data.")
        return ConversationHandler.END

async def input_pic_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pic_name = update.message.text
    pending_trx = context.user_data.get('pending_transactions')
    
    count = 0
    for trx in pending_trx:
        if save_transfer_log(trx['product'], trx['qty'], pic_name):
            count += 1
            
    await update.message.reply_text(f"✅ Mantap **{pic_name}**! {count} item masuk Gudang.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Batal bos.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

# AI HANDLER (Simple Version)
async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name
    
    # 1. Kasih feedback "Typing..." biar user tau bot lagi mikir
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # 2. Ambil "Context" Data Stock terbaru dari DB
        current_stock_data = get_stock_overview()
        
        # 3. Rakit System Prompt (Mantra AI)
        # Ini yang bikin dia pinter dan bisa baca stock
        system_instruction = f"""
        Role: Loe adalah "Logistic Bot", asisten gudang yang santai, gaul, tapi akurat. Loe ngomong pakai gaya "Gua/Loe" atau santai sopan.
        
        Tugas Loe:
        1. Menjawab pertanyaan seputar stock berdasarkan DATA STOCK di bawah ini.
        2. Kalau user nanya "paling dikit" atau "paling banyak", loe analisa dari angka di data.
        3. Kalau stock minus, kasih warning lucu (misal: "Waduh minus bre").
        4. Basa-basi sopan kalau disapa (Selamat pagi, dll).
        
        DATA STOCK GUDANG SAAT INI (Live):
        {current_stock_data}
        
        User Info: Nama user adalah {user_name}.
        """
        
        # 4. Kirim ke Gemini
        # Kita gabungin instruksi + pertanyaan user
        full_prompt = f"{system_instruction}\n\nUser nanya: {user_text}\nJawab:"
        
        response = model.generate_content(full_prompt)
        ai_reply = response.text
        
        # 5. Balas ke Telegram
        await update.message.reply_text(ai_reply, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"AI Error: {e}")
        await update.message.reply_text("Waduh, otak gua lagi error bre. Coba lagi ntar ya.")

# ERROR HANDLER (PENYELAMAT)
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# ==========================================
# 5. MAIN
# ==========================================
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Handler Percakapan (WAJIB DULUAN)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('update_stock', start_update)],
        states={
            CHOOSING_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_category)],
            INPUT_QTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_qty_process)],
            INPUT_PIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_pic_process)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(conv_handler)
    
    # Command Lain
    application.add_handler(CommandHandler("ping", ping_command))
    
    # Chat AI (Terakhir)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat))
    
    # Register Error Handler
    application.add_error_handler(error_handler)
    
    print(" BOT V3 FINAL - STARTED!")
    application.run_polling()