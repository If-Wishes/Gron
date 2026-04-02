import re
import requests
import logging
import os
from telegram.ext import ApplicationBuilder, MessageHandler, filters

# 🔒 Disable ALL logging
logging.getLogger().setLevel(logging.CRITICAL)

# ENV VARIABLES (use Render env settings)
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

OTP_REGEX = r"\b\d{4,6}\b"

def extract(text):
    try:
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
    except:
        return {"otp": None, "phone_last3": None}

async def handle(update, context):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text

        data = extract(text)

        if data["otp"] and data["phone_last3"]:
            try:
                requests.post(
                    f"{SUPABASE_URL}/rest/v1/otp_logs",
                    headers=HEADERS,
                    json=data,
                    timeout=5
                )
            except:
                pass  # ignore request errors completely

    except:
        pass  # ignore everything

def main():
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle)
        )

        app.run_polling(
            drop_pending_updates=True,
            close_loop=False
        )
    except:
        pass  # no crash logs

if __name__ == "__main__":
    main()
