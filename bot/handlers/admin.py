from aiogram import Router, types, F
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from ..config import ADMIN_ID
from ..db import db

router = Router()

class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_ID

class SubscribersForm(StatesGroup):
    waiting_count = State()

class BroadcastForm(StatesGroup):
    waiting_content = State()

@router.message(Command("subs"), IsAdmin())
async def cmd_subs(message: types.Message):
    stats = await db.get_user_stats()
    
    text = f"""@since0bot
Active: {stats.get('active', 0)} ({stats.get('active', 0)}👤 + 0👥)
Muted: {stats.get('muted', 0)} ({stats.get('muted', 0)}👤 + 0👥)
Deleted: {stats.get('deleted', 0)} ({stats.get('deleted', 0)}👤 + 0👥)
Total: {stats.get('total', 0)} ({stats.get('total', 0)}👤 + 0👥)
👤 - users
👥 - group chats"""
    await message.answer(text)

@router.message(Command("subscribers"), IsAdmin())
async def cmd_subscribers(message: types.Message, state: FSMContext):
    await message.answer("Введите количество последних пользователей:")
    await state.set_state(SubscribersForm.waiting_count)

@router.message(SubscribersForm.waiting_count, IsAdmin())
async def process_subscribers_count(message: types.Message, state: FSMContext):
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите положительное число.")
        return
        
    users = await db.get_recent_users(count)
    if not users:
        await message.answer("Пользователи не найдены.")
    else:
        text = "\n".join([f"@{u.get('username') or 'NoUsername'} — ID: {u.get('user_id')}" for u in users])
        # Telegram max message length is 4096, handle it simply for now by slicing
        if len(text) > 4000:
            text = text[:4000] + "..."
        await message.answer(text)
        
    await state.clear()

@router.message(Command("send"), IsAdmin())
async def cmd_send(message: types.Message, state: FSMContext):
    await message.answer("Отправьте сообщение для рассылки (текст, фото, видео — что угодно):")
    await state.set_state(BroadcastForm.waiting_content)

@router.message(BroadcastForm.waiting_content, IsAdmin())
async def process_broadcast_content(message: types.Message, state: FSMContext):
    stats = await db.get_user_stats()
    total_users = stats.get('active', 0)
    
    await db.create_broadcast(
        admin_chat_id=message.chat.id,
        message_chat_id=message.chat.id,
        message_id=message.message_id,
        total_users=total_users
    )
    
    await message.answer(f"Рассылка запланирована для {total_users} пользователей.\nОна начнется немедленно и продолжится в фоне.")
    await state.clear()
    
    # The actual broadcasting should ideally be triggered here synchronously for the first 8 seconds, 
    # but to avoid blocking the webhook too long, we will let the cron take over, 
    # or optionally call process_pending_broadcast(message.bot) as requested, which checks time.
    from ..notifications import process_pending_broadcast
    import asyncio
    asyncio.create_task(process_pending_broadcast(message.bot))
