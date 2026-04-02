import re
import requests
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import threading

# CONFIG
BOT_TOKEN = "YOUR_BOT_TOKEN"
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_ANON_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# REGEX
OTP_REGEX = r"\b\d{4,6}\b"
LAST3_REGEX = r"(\d{3})\s*$"

def extract_data(text):
    otp = None
    last3 = None
    country = None
    service = None
    time_raw = None
    parsed_time = None

    # OTP
    otp_match = re.search(OTP_REGEX, text)
    if otp_match:
        otp = otp_match.group()

    # Number
    number_line = re.search(r"Number:\s*(.+)", text)
    if number_line:
        last3_match = re.search(LAST3_REGEX, number_line.group(1))
        if last3_match:
            last3 = last3_match.group(1)

    # Country
    country_match = re.search(r"Country:\s*(.+)", text)
    if country_match:
        country = country_match.group(1).strip()

    # Service
    service_match = re.search(r"Service:\s*(.+)", text)
    if service_match:
        service = service_match.group(1).strip()

    # Time
    time_match = re.search(r"Time:\s*(.+)", text)
    if time_match:
        time_raw = time_match.group(1).strip()
        try:
            parsed_time = datetime.strptime(time_raw, "%Y-%m-%d %H:%M:%S").isoformat()
        except:
            pass

    return {
        "otp": otp,
        "phone_last3": last3,
        "country": country,
        "service": service,
        "time_raw": time_raw,
        "message_time": parsed_time
    }

def send_to_supabase(data):
    if not data["otp"] or not data["phone_last3"]:
        return

    requests.post(
        f"{SUPABASE_URL}/rest/v1/otp_logs",
        headers=HEADERS,
        json=data
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    data = extract_data(text)
    send_to_supabase(data)

# Flask health check
app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}

def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
