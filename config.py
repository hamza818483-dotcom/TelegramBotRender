import os

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")

# Bot Owner (আপনার Telegram User ID - @userinfobot দিয়ে পান)
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

# Directories
CSV_DIR = "csv_files"
os.makedirs(CSV_DIR, exist_ok=True)

# Gemini Model
GEMINI_MODEL = "gemini-1.5-flash"

# CSV columns (Rayvila Quiz Maker format)
CSV_COLUMNS = [
    "questions", "option1", "option2", "option3", "option4", "option5",
    "answer", "explanation", "type", "section"
]
