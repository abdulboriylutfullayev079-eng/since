import asyncio
from http.server import BaseHTTPRequestHandler
from aiogram import Bot
from bot.config import BOT_TOKEN, CRON_SECRET
from bot.notifications import send_countdown_notifications, send_habit_notifications, process_pending_broadcast

__all__ = ["handler"]

bot = Bot(token=BOT_TOKEN)

async def run_cron_jobs():
    await send_countdown_notifications(bot)
    await send_habit_notifications(bot)
    await process_pending_broadcast(bot)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        
        # Simple verification of CRON_SECRET
        if not auth_header or auth_header != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return
            
        try:
            asyncio.run(run_cron_jobs())
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Cron jobs executed successfully")
        except Exception as e:
            print(f"Error in cron: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")
