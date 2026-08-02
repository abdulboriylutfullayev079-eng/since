import aiohttp
from typing import Dict, Any, List, Optional
from .config import SUPABASE_URL, SUPABASE_KEY

class SupabaseClient:
    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    async def _request(self, method: str, table: str, params: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{self.base_url}/{table}"
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.request(method, url, params=params, json=json_data) as response:
                response.raise_for_status()
                text = await response.text()
                if text:
                    import json
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        pass
                return None

    async def upsert_user(self, user_id: int, username: Optional[str] = None) -> None:
        data = {"user_id": user_id}
        if username:
            data["username"] = username
        params = {"on_conflict": "user_id"}
        # Prefer: resolution=merge-duplicates ensures update on conflict
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates,return=representation"}
        async with aiohttp.ClientSession(headers=headers) as session:
            url = f"{self.base_url}/users"
            async with session.post(url, params=params, json=data) as response:
                response.raise_for_status()

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        result = await self._request("GET", "users", params={"user_id": f"eq.{user_id}", "select": "*"})
        return result[0] if result else None

    async def update_user(self, user_id: int, **fields) -> None:
        await self._request("PATCH", "users", params={"user_id": f"eq.{user_id}"}, json_data=fields)

    async def get_all_active_users(self) -> List[Dict[str, Any]]:
        return await self._request("GET", "users", params={"status": "eq.active", "select": "*"})

    async def get_user_stats(self) -> Dict[str, int]:
        # Perform aggregate queries, or just get all and count. Getting all might be large, but let's assume it's okay for now.
        # Alternatively, perform HEAD requests with Prefer: count=exact, but we'll fetch and count to keep it simple.
        users = await self._request("GET", "users", params={"select": "status"})
        active = sum(1 for u in users if u.get("status") == "active")
        muted = sum(1 for u in users if u.get("status") == "muted")
        deleted = sum(1 for u in users if u.get("status") == "deleted")
        return {"active": active, "muted": muted, "deleted": deleted, "total": len(users)}

    async def get_recent_users(self, limit: int) -> List[Dict[str, Any]]:
        return await self._request("GET", "users", params={"select": "*", "order": "created_at.desc", "limit": limit})

    async def create_countdown(self, user_id: int, title: str, target_date: str, frequency: int, notify_hour: int) -> Dict[str, Any]:
        data = {
            "user_id": user_id,
            "title": title,
            "target_date": target_date,
            "frequency": frequency,
            "notify_hour": notify_hour
        }
        res = await self._request("POST", "countdowns", json_data=data)
        return res[0] if res else {}

    async def get_countdowns(self, user_id: int) -> List[Dict[str, Any]]:
        return await self._request("GET", "countdowns", params={"user_id": f"eq.{user_id}", "select": "*"})

    async def delete_countdown(self, countdown_id: int, user_id: int) -> None:
        await self._request("DELETE", "countdowns", params={"id": f"eq.{countdown_id}", "user_id": f"eq.{user_id}"})

    async def count_countdowns(self, user_id: int) -> int:
        res = await self._request("GET", "countdowns", params={"user_id": f"eq.{user_id}", "select": "id"})
        return len(res)

    async def create_habit(self, user_id: int, title: str) -> Dict[str, Any]:
        data = {"user_id": user_id, "title": title}
        res = await self._request("POST", "habits", json_data=data)
        return res[0] if res else {}

    async def get_habits(self, user_id: int) -> List[Dict[str, Any]]:
        return await self._request("GET", "habits", params={"user_id": f"eq.{user_id}", "select": "*"})

    async def delete_habit(self, habit_id: int, user_id: int) -> None:
        await self._request("DELETE", "habits", params={"id": f"eq.{habit_id}", "user_id": f"eq.{user_id}"})

    async def count_habits(self, user_id: int) -> int:
        res = await self._request("GET", "habits", params={"user_id": f"eq.{user_id}", "select": "id"})
        return len(res)

    async def log_habit(self, habit_id: int, date: str, status: str) -> None:
        data = {"habit_id": habit_id, "date": date, "status": status}
        params = {"on_conflict": "habit_id,date"}
        headers = {**self.headers, "Prefer": "resolution=merge-duplicates"}
        async with aiohttp.ClientSession(headers=headers) as session:
            url = f"{self.base_url}/habit_logs"
            async with session.post(url, params=params, json=data) as response:
                response.raise_for_status()

    async def get_habit_logs(self, habit_id: int, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        # PostgREST requires 'and' syntax for multiple conditions on the same column
        params = {
            "habit_id": f"eq.{habit_id}",
            "and": f"(date.gte.{start_date},date.lte.{end_date})",
            "select": "*",
            "order": "date.asc"
        }
        return await self._request("GET", "habit_logs", params=params)

    async def create_transaction(self, user_id: int, amount: int, telegram_charge_id: str) -> None:
        data = {"user_id": user_id, "amount": amount, "telegram_charge_id": telegram_charge_id}
        await self._request("POST", "transactions", json_data=data)

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        return await self._request("GET", "users", params={"select": "user_id,username,total_donated", "order": "total_donated.desc", "limit": limit})

    async def get_users_for_countdown_notification(self, current_utc_hour: int) -> List[Dict[str, Any]]:
        """Fetch countdowns joined with user data, filtering active users.
        Timezone offset is handled in the notification logic."""
        params = {
            "select": "*,users!inner(user_id,username,status,timezone)",
            "users.status": "eq.active"
        }
        res = await self._request("GET", "countdowns", params=params)
        return res if res else []

    async def get_users_for_habit_notification(self, current_utc_hour: int) -> List[Dict[str, Any]]:
        """Get active users with their habits for notification checks."""
        params = {
            "status": "eq.active",
            "select": "user_id,username,timezone,habits(id,title,created_at)"
        }
        return await self._request("GET", "users", params=params)

    async def get_pending_broadcast(self) -> Optional[Dict[str, Any]]:
        res = await self._request("GET", "broadcasts", params={"status": "in.('pending','in_progress')", "select": "*", "limit": 1})
        return res[0] if res else None

    async def create_broadcast(self, admin_chat_id: int, message_chat_id: int, message_id: int, total_users: int) -> Dict[str, Any]:
        data = {
            "admin_chat_id": admin_chat_id,
            "message_chat_id": message_chat_id,
            "message_id": message_id,
            "total_users": total_users,
            "status": "pending"
        }
        res = await self._request("POST", "broadcasts", json_data=data)
        return res[0] if res else {}

    async def update_broadcast_progress(self, broadcast_id: int, sent: int, failed: int, offset_count: int, status: str = "in_progress") -> None:
        data = {
            "sent": sent,
            "failed": failed,
            "offset_count": offset_count,
            "status": status
        }
        await self._request("PATCH", "broadcasts", params={"id": f"eq.{broadcast_id}"}, json_data=data)

db = SupabaseClient()
