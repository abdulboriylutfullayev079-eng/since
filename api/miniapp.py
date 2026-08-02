import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import urllib.parse
import hmac
import hashlib
import asyncio
import aiohttp
import aiogram
from http.server import BaseHTTPRequestHandler
from bot.config import BOT_TOKEN
from bot.db import db

__all__ = ["handler"]

def validate_telegram_data(init_data: str) -> bool:
    try:
        parsed_data = urllib.parse.parse_qsl(init_data)
        data_dict = dict(parsed_data)
        
        hash_value = data_dict.pop('hash', None)
        if not hash_value:
            return False
            
        sorted_data = sorted(data_dict.items())
        data_check_string = '\n'.join([f"{k}={v}" for k, v in sorted_data])
        
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        
        return calculated_hash == hash_value
    except Exception:
        return False

def get_user_id_from_init_data(init_data: str) -> int:
    parsed_data = urllib.parse.parse_qsl(init_data)
    data_dict = dict(parsed_data)
    user_data = json.loads(data_dict.get('user', '{}'))
    return user_data.get('id', 0)

class handler(BaseHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()

    def handle_request(self, method: str):
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            query_params = dict(urllib.parse.parse_qsl(parsed_path.query))
            action = query_params.get("action")
            
            auth_header = self.headers.get('Authorization', '')
            if not auth_header.startswith('tma '):
                self.send_response(401)
                self.send_cors_headers()
                self.wfile.write(b"Unauthorized")
                return
                
            init_data = auth_header[4:]
            if not validate_telegram_data(init_data):
                self.send_response(401)
                self.send_cors_headers()
                self.wfile.write(b"Invalid initData")
                return
                
            user_id = get_user_id_from_init_data(init_data)
            if not user_id:
                self.send_response(400)
                self.send_cors_headers()
                self.wfile.write(b"User ID not found")
                return
                
            body_data = {}
            if method in ["POST", "DELETE"] and int(self.headers.get('Content-Length', 0)) > 0:
                content_length = int(self.headers['Content-Length'])
                body = self.rfile.read(content_length)
                body_data = json.loads(body)

            response_data = asyncio.run(self.process_action(method, action, user_id, query_params, body_data))
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors_headers()
            self.wfile.write(json.dumps(response_data).encode())
            
        except Exception as e:
            print(f"Error in miniapp API: {e}")
            self.send_response(500)
            self.send_cors_headers()
            self.wfile.write(b'{"error": "Internal Server Error"}')

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")
        
    def do_DELETE(self):
        self.handle_request("DELETE")

    async def process_action(self, method: str, action: str, user_id: int, query_params: dict, body_data: dict) -> dict:
        user = await db.get_user(user_id)
        if not user:
            return {"error": "User not found"}
            
        is_premium = user.get("is_premium", False)

        if action == "user" and method == "GET":
            return user
            
        elif action == "countdowns":
            if method == "GET":
                return await db.get_countdowns(user_id)
            elif method == "POST":
                count = await db.count_countdowns(user_id)
                if not is_premium and count >= 3:
                    return {"error": "Limit reached"}
                res = await db.create_countdown(
                    user_id, 
                    body_data.get("title"), 
                    body_data.get("target_date"), 
                    body_data.get("frequency"), 
                    body_data.get("notify_hour")
                )
                return res
            elif method == "DELETE":
                countdown_id = query_params.get("id") or body_data.get("id")
                await db.delete_countdown(int(countdown_id), user_id)
                return {"success": True}
                
        elif action == "habits":
            if method == "GET":
                return await db.get_habits(user_id)
            elif method == "POST":
                count = await db.count_habits(user_id)
                if not is_premium and count >= 1:
                    return {"error": "Limit reached"}
                res = await db.create_habit(user_id, body_data.get("title"))
                return res
            elif method == "DELETE":
                habit_id = query_params.get("id") or body_data.get("id")
                await db.delete_habit(int(habit_id), user_id)
                return {"success": True}
                
        elif action == "habit_logs":
            if method == "GET":
                habit_id = query_params.get("habit_id")
                start = query_params.get("start")
                end = query_params.get("end")
                return await db.get_habit_logs(int(habit_id), start, end)
            elif method == "POST":
                await db.log_habit(
                    body_data.get("habit_id"), 
                    body_data.get("date"), 
                    body_data.get("status")
                )
                return {"success": True}
                
        elif action == "timezone" and method == "POST":
            await db.update_user(user_id, timezone=body_data.get("timezone"))
            return {"success": True}
            
        return {"error": "Invalid action"}
