import re
import requests
from telegram.ext import ApplicationBuilder, MessageHandler, filters

BOT_TOKEN = "YOUR_BOT_TOKEN"
SUPABASE_URL = "YOUR_SUPABASE_URL"
SUPABASE_KEY = "YOUR_ANON_KEY"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

OTP_REGEX = r"\b\d{4,6}\b"

def extract(text):
    otp = re.search(OTP_REGEX, text)
    number = re.search(r"Number:\s*(.+)", text)

    last3 = None
    if number:
        last3_match = re.search(r"(\d{3})$", number.group(1))
        if last3_match:
            last3 = last3_match.group(1)

    return {
        "otp": otp.group() if otp else None,
        "phone_last3": last3
    }

async def handle(update, context):
    text = update.message.text
    if not text:
        return

    data = extract(text)

    if data["otp"] and data["phone_last3"]:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/otp_logs",
            headers=HEADERS,
            json=data
        )

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle))
app.run_polling()
