import asyncio
import datetime
import re
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter, TelegramForbiddenError, TelegramBadRequest
from .db import db


def parse_timezone_offset(tz_str: str) -> int:
    """Parse timezone string like 'UTC', 'UTC+5', 'UTC-3', 'UTC+5:30' into integer hour offset."""
    if not tz_str or tz_str == "UTC":
        return 0
    match = re.match(r"UTC([+-])(\d{1,2})(?::(\d{2}))?", tz_str)
    if match:
        sign = 1 if match.group(1) == "+" else -1
        hours = int(match.group(2))
        return sign * hours
    return 0


def get_user_local_hour(current_utc_hour: int, tz_str: str) -> int:
    """Get user's local hour given current UTC hour and their timezone."""
    offset = parse_timezone_offset(tz_str)
    local_hour = (current_utc_hour + offset) % 24
    return local_hour


async def send_countdown_notifications(bot: Bot, current_utc_hour: int):
    """Send countdown notifications to users whose notify_hour matches their local time."""
    countdowns = await db.get_users_for_countdown_notification(current_utc_hour)
    today = datetime.date.today()

    for c in countdowns:
        try:
            user_data = c.get("users", {})
            user_tz = user_data.get("timezone", "UTC")
            user_local_hour = get_user_local_hour(current_utc_hour, user_tz)
            notify_hour = c.get("notify_hour", 9)

            # Only notify if user's local hour matches the configured notify_hour
            if user_local_hour != notify_hour:
                continue

            target_date = datetime.date.fromisoformat(c["target_date"])
            created_at_str = c["created_at"]
            if "T" in created_at_str:
                created_at = datetime.datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                ).date()
            else:
                created_at = datetime.date.fromisoformat(created_at_str)

            days_remaining = (target_date - today).days
            days_since_creation = (today - created_at).days
            frequency = c.get("frequency", 1)

            if frequency > 0 and days_since_creation >= 0 and days_since_creation % frequency == 0:
                if days_remaining > 0:
                    text = f"⏳ {c['title']}\n{days_remaining} дней осталось"
                elif days_remaining == 0:
                    text = f"🎉 {c['title']}\nСобытие наступило сегодня!"
                else:
                    text = f"📅 {c['title']}\nСобытие было {abs(days_remaining)} дней назад"

                try:
                    await bot.send_message(c["user_id"], text)
                except TelegramForbiddenError:
                    await db.update_user(c["user_id"], status="deleted")
                except TelegramRetryAfter as e:
                    await asyncio.sleep(e.retry_after)
                    await bot.send_message(c["user_id"], text)

        except Exception as e:
            print(f"Failed to notify countdown {c.get('id')}: {e}")


async def send_habit_notifications(bot: Bot, current_utc_hour: int):
    """Send habit reminders to users who haven't logged today/yesterday.
    Sends at 20:00 local time (evening reminder)."""
    users = await db.get_users_for_habit_notification(current_utc_hour)
    today = datetime.date.today()
    today_str = today.isoformat()
    yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

    for user in users:
        habits = user.get("habits", [])
        if not habits:
            continue

        user_tz = user.get("timezone", "UTC")
        user_local_hour = get_user_local_hour(current_utc_hour, user_tz)

        # Send habit reminders at 20:00 user's local time
        if user_local_hour != 20:
            continue

        for habit in habits:
            try:
                logs = await db.get_habit_logs(habit["id"], yesterday_str, today_str)
                logged_dates = {log["date"] for log in logs}

                messages = []
                if yesterday_str not in logged_dates:
                    messages.append(f'📋 Не забудь отметить привычку "{habit["title"]}" за вчера!')
                if today_str not in logged_dates:
                    messages.append(f'📋 Не забудь отметить привычку "{habit["title"]}" за сегодня!')

                if messages:
                    text = "\n".join(messages)
                    try:
                        await bot.send_message(user["user_id"], text)
                    except TelegramForbiddenError:
                        await db.update_user(user["user_id"], status="deleted")
                        break  # Don't try more habits for deleted user
                    except TelegramRetryAfter as e:
                        await asyncio.sleep(e.retry_after)
                        await bot.send_message(user["user_id"], text)

            except Exception as e:
                print(f"Failed to notify habit {habit.get('id')}: {e}")


async def process_pending_broadcast(bot: Bot):
    """Process pending broadcast messages in batches, respecting Vercel time limits."""
    broadcast = await db.get_pending_broadcast()
    if not broadcast:
        return

    broadcast_id = broadcast["id"]
    sent = broadcast.get("sent", 0)
    failed = broadcast.get("failed", 0)
    offset = broadcast.get("offset_count", 0)

    users = await db.get_all_active_users()
    target_users = users[offset:]

    if not target_users:
        await db.update_broadcast_progress(broadcast_id, sent, failed, offset, status="completed")
        try:
            await bot.send_message(
                broadcast["admin_chat_id"],
                f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}"
            )
        except Exception:
            pass
        return

    start_time = asyncio.get_event_loop().time()
    batch_size = 25

    for i in range(0, len(target_users), batch_size):
        batch = target_users[i:i + batch_size]
        for user in batch:
            try:
                await bot.copy_message(
                    chat_id=user["user_id"],
                    from_chat_id=broadcast["message_chat_id"],
                    message_id=broadcast["message_id"]
                )
                sent += 1
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.copy_message(
                        chat_id=user["user_id"],
                        from_chat_id=broadcast["message_chat_id"],
                        message_id=broadcast["message_id"]
                    )
                    sent += 1
                except Exception:
                    failed += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                await db.update_user(user["user_id"], status="deleted")
                failed += 1
            except Exception:
                failed += 1

        offset += len(batch)

        # Check Vercel time limit (~8 seconds to be safe)
        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > 8.0:
            await db.update_broadcast_progress(broadcast_id, sent, failed, offset, status="in_progress")
            try:
                await bot.send_message(
                    broadcast["admin_chat_id"],
                    f"⏳ Рассылка в процессе...\nОтправлено: {sent}/{broadcast['total_users']}\nОшибок: {failed}\nПродолжение через cron..."
                )
            except Exception:
                pass
            return

        await asyncio.sleep(1)

    await db.update_broadcast_progress(broadcast_id, sent, failed, offset, status="completed")
    try:
        await bot.send_message(
            broadcast["admin_chat_id"],
            f"✅ Рассылка завершена!\nОтправлено: {sent}\nОшибок: {failed}"
        )
    except Exception:
        pass
