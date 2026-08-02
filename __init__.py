import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")
try:
    ADMIN_ID_RAW = os.environ.get("ADMIN_ID", "0")
    ADMIN_ID = int(ADMIN_ID_RAW) if ADMIN_ID_RAW.strip() else 0
except ValueError:
    ADMIN_ID = 0
CRON_SECRET = os.environ.get("CRON_SECRET", "")
