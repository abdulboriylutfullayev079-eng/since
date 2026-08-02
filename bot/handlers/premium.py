from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from ..db import db

router = Router()

@router.message(Command("premium"))
async def cmd_premium(message: types.Message):
    text = (
        "🌟 **Premium статус**\n\n"
        "Преимущества:\n"
        "• Безлимитные таймеры обратного отсчета\n"
        "• Безлимитные привычки\n"
        "• Поддержка разработчика\n\n"
        "Выберите действие:"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Донат", callback_data="donate")],
        [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="leaderboard")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "donate")
async def cb_donate(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 ⭐", callback_data="stars_1")],
        [InlineKeyboardButton(text="25 ⭐", callback_data="stars_25")],
        [InlineKeyboardButton(text="50 ⭐", callback_data="stars_50")],
        [InlineKeyboardButton(text="100 ⭐", callback_data="stars_100")]
    ])
    await callback.message.edit_text("Выберите сумму доната:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("stars_"))
async def cb_stars(callback: types.CallbackQuery):
    stars = int(callback.data.split("_")[1])
    prices = [LabeledPrice(label="Донат", amount=stars)]
    
    await callback.message.answer_invoice(
        title="Донат",
        description=f"Поддержка проекта на {stars} звезд",
        payload=f"donate_{stars}",
        provider_token="",  # Empty for Telegram Stars
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@router.callback_query(F.data == "leaderboard")
async def cb_leaderboard(callback: types.CallbackQuery):
    leaders = await db.get_leaderboard(10)
    if not leaders:
        await callback.message.answer("Таблица лидеров пуста.")
        await callback.answer()
        return
        
    text = "🏆 **Таблица лидеров**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, leader in enumerate(leaders):
        medal = medals[i] if i < 3 else f"{i+1}."
        username = leader.get("username") or f"User {leader.get('user_id')}"
        donated = leader.get("total_donated", 0)
        text += f"{medal} {username} — {donated} ⭐\n"
        
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()
