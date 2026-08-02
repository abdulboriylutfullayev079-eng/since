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

_bot = None
_dp = None

def get_dispatcher():
    global _dp
    if _dp is None:
        _dp = Dispatcher()
        _dp.update.outer_middleware(UserRegisterMiddleware())
        _dp.include_router(start_router)
        _dp.include_router(premium_router)
        _dp.include_router(payments_router)
        _dp.include_router(admin_router)
    return _dp

async def process_update(update_data: dict):
    # In Vercel serverless, each request gets a new event loop with asyncio.run().
    # We MUST create a new Bot instance per request so its aiohttp session attaches to the current loop.
    bot = Bot(token=BOT_TOKEN)
    try:
        update = types.Update(**update_data)
        await get_dispatcher().feed_update(bot, update)
    finally:
        await bot.session.close()

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
            import traceback
            err_str = traceback.format_exc()
            print(f"Error in webhook:\n{err_str}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(err_str.encode('utf-8'))
