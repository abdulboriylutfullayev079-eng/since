from aiogram import Router, types, F
from ..db import db

router = Router()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    amount = message.successful_payment.total_amount
    telegram_charge_id = message.successful_payment.telegram_payment_charge_id
    user_id = message.from_user.id
    
    user = await db.get_user(user_id)
    current_donated = user.get("total_donated", 0) if user else 0
    new_donated = current_donated + amount
    
    await db.update_user(user_id, is_premium=True, total_donated=new_donated)
    await db.create_transaction(user_id, amount, telegram_charge_id)
    
    await message.answer(f"🎉 Спасибо за поддержку! Вы задонатили {amount} ⭐.\nТеперь у вас Premium статус!")
