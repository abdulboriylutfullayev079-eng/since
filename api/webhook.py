import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import asyncio
from http.server import BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from bot.config import BOT_TOKEN
from bot.middlewares import UserRegisterMiddleware
from bot.handlers.start import router as start_router
from bot.handlers.premium import router as premium_router
from bot.handlers.payments import router as payments_router
from bot.handlers.admin import router as admin_router

__all__ = ["handler"]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Register middleware
dp.update.outer_middleware(UserRegisterMiddleware())

# Register routers
dp.include_router(start_router)
dp.include_router(premium_router)
dp.include_router(payments_router)
dp.include_router(admin_router)

async def process_update(update_data: dict):
    update = types.Update(**update_data)
    await dp.feed_update(bot, update)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            update_data = json.loads(body)
            
            asyncio.run(process_update(update_data))
            
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        except Exception as e:
            print(f"Error in webhook: {e}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"Internal Server Error")
