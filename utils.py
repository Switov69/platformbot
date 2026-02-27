import re
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def validate_nickname(nickname: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9_]+$', nickname))

def escape_md(text: str) -> str:
    if not text: return ""
    special_chars = ['_', '*', '`', '[']
    for char in special_chars:
        text = str(text).replace(char, f'\\{char}')
    return text

def get_citizenship_label(citizenship: str) -> str:
    if citizenship == "Антегриевское":
        return "Антегрии"
    elif citizenship == "Столичное":
        return "Столицы"
    return citizenship

def get_status_text(status: str) -> str:
    mapping = {
        'not_completed': 'Доступен',
        'in_progress': 'В работе',
        'completed': 'Выполнен',
        'failed': 'Отказался',
        'deleted': 'Удален'
    }
    return mapping.get(status, status)

def format_vacancy_text(job, is_admin=False, user_data=None) -> str:
    try:
        j = dict(job)
        
        j_id = j.get('id', 0)
        description = j.get('description', 'Нет описания')
        priority = j.get('priority', 'Обычный')
        category = j.get('category', 'Общее')
        salary = j.get('salary', 0.0)
        status = j.get('status', 'not_completed')
        coords = j.get('coords')
        assigned_id = j.get('assigned_user_id')

        status_emoji = "🆕"
        if status == 'in_progress':
            status_emoji = "⏳"
        elif status == 'completed':
            status_emoji = "✅"
        elif status == 'deleted':
            status_emoji = "🗑"
        elif status == 'failed':
            status_emoji = "❌"

        status_text = get_status_text(status)

        text = (
            f"📢 **ЗАКАЗ | #id{j_id:03}**\n"
            f"{status_emoji} Статус: {escape_md(status_text)}\n"
            f"🔥 Приоритет: {escape_md(priority)}\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
            f"📝 Описание: {escape_md(description)}\n"
            f"📂 Категория: {escape_md(category)}\n"
            f"💰 Зарплата: {salary} кбк\n"
            f"⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n"
        )

        if is_admin and coords:
            text += f"📍 **Координаты:** `{escape_md(coords)}`\n"

        if is_admin:
            if assigned_id:
                text += f"👤 **Исполнитель ID:** `{assigned_id}`\n"
                if user_data:
                    text += f"💳 **Счет исполнителя:** `{escape_md(user_data['bank_account'])}`\n"
            text += f"🛠 **Создан:** {j.get('created_at', 'Неизвестно')}\n"
            
        return text

    except Exception as e:
        logging.error(f"Ошибка при форматировании вакансии: {e}")
        return "⚠️ _Ошибка отображения данных заказа._"

async def update_channel_post(bot: Bot, channel_id: int, job_id: int, db_module):
    job = await db_module.get_vacancy_by_id(job_id)
    if not job or not job['channel_message_id']:
        return

    text = format_vacancy_text(job, is_admin=False)
    builder = InlineKeyboardBuilder()
    
    if job['status'] == 'not_completed':
        me = await bot.get_me()
        builder.row(InlineKeyboardButton(text="📥 Взять заказ", url=f"https://t.me/{me.username}?start=job_{job_id}"))
    
    try:
        await bot.edit_message_text(
            chat_id=channel_id,
            message_id=job['channel_message_id'],
            text=text,
            reply_markup=builder.as_markup() if job['status'] == 'not_completed' else None,
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Ошибка обновления поста: {e}")

async def send_log(bot: Bot, log_channel_id: int, action: str, user_id: int, nickname: str = "Неизвестно"):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # action и nickname уже должны приходить экранированными или экранироваться здесь
    text = f"🕒 {time_str}\n👤 Пользователь: {nickname} (ID: {user_id})\n📝 Действие: {action}"
    try:
        await bot.send_message(log_channel_id, text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка логов: {e}")