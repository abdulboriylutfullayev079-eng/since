from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from ..config import WEBAPP_URL
from ..db import db

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await db.upsert_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    
    text = (
        "Привет! Я бот для отслеживания привычек и таймеров обратного отсчета.\n\n"
        "Открой Mini App, чтобы начать!\n\n"
        "Разработчик: @mynus_x"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть приложение", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    await message.answer(text, reply_markup=keyboard)
