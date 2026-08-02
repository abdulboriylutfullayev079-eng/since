from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from .db import db

class UserRegisterMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler,
        event,
        data
    ):
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            
        if user and not user.is_bot:
            username = user.username or user.first_name
            await db.upsert_user(user.id, username)
            
        return await handler(event, data)
