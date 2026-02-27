import aiosqlite
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Router, F, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import DB, DB_PATH
from states import Registration, CreateVacancy, JobAction, EditProfile
from keyboards import *
import utils

load_dotenv()

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

user_router = Router()
admin_router = Router()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def send_main_menu_logic(event, user, index=0, just_took=False):
    active_jobs = await DB.get_active_jobs(user['id'])
    
    if not active_jobs:
        text = "👋 Добро пожаловать!\n\nУ вас нет активных заказов. Актуальные задачи можно найти в канале профсоюза."
        reply_markup = main_menu_kb()
    else:
        if index >= len(active_jobs): index = 0
        job = active_jobs[index]
        job_card = utils.format_vacancy_text(job)
        
        if just_took:
            # Пункт 4: Убраны кнопки, только текст инструкции
            if job['category'] == "Строительство":
                text = (f"✅ Заказ #id{job['id']:03} взят!\n"
                        f"ℹ️ Ждите сообщение от куратора.")
            else:
                text = (f"✅ Заказ #id{job['id']:03} взят!\n"
                        f"ℹ️ Добудьте ресурсы, отправьте /start и нажмите «Выполнил», после укажите координаты где оставили ресурсы.")
            reply_markup = None
        else:
            text = f"🏃 **ВАШ АКТИВНЫЙ ЗАКАЗ ({index + 1} из {len(active_jobs)})**\n\n" + job_card
            reply_markup = vacancy_player_kb(job['id'], index, len(active_jobs))
    
    if isinstance(event, Message):
        await event.answer(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        except:
            await event.message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

async def render_admin_jobs_list(callback: CallbackQuery, page: int = 0):
    jobs = await DB.get_all_vacancies()
    if not jobs:
        await callback.message.edit_text("Заказов пока нет.", reply_markup=admin_back_kb())
        return
    text = "📋 **Список всех заказов:**"
    builder = InlineKeyboardBuilder()
    start_idx = page * 10
    end_idx = start_idx + 10
    for j in jobs[start_idx:end_idx]:
        status_emoji = "✅" if j['status'] == 'completed' else "⏳" if j['status'] == 'in_progress' else "🗑" if j['status'] == 'deleted' else "🆕"
        builder.row(InlineKeyboardButton(text=f"{status_emoji} #{j['id']:03} | {j['salary']} кбк", callback_data=f"adm_view_{j['id']}"))
    nav = []
    if page > 0: nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"adm_jobs_list_p_{page-1}"))
    if len(jobs) > end_idx: nav.append(InlineKeyboardButton(text="➡️", callback_data=f"adm_jobs_list_p_{page+1}"))
    if nav: builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="adm_back"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

# --- ОБЩИЕ КОМАНДЫ ---

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user = await DB.get_user(message.from_user.id)
    if not user:
        await message.answer("🧱 Добро пожаловать!\nВведите Ваш игровой ник:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(Registration.nickname)
        return
    
    # Обработка глубокой ссылки (взятие заказа из канала)
    args = message.text.split()
    if len(args) > 1 and args[1].startswith('job_'):
        try:
            job_id = int(args[1].replace('job_', ''))
            job = await DB.get_vacancy_by_id(job_id)
            if job and job['status'] == 'not_completed':
                active_jobs = await DB.get_active_jobs(message.from_user.id)
                if not active_jobs:
                    await DB.assign_vacancy(job_id, message.from_user.id)
                    await utils.update_channel_post(bot, CHANNEL_ID, job_id, DB)
                    await utils.send_log(bot, LOG_CHANNEL_ID, f"Взял заказ #id_{job_id:03}", user['id'], user['nickname'])
                    try: await message.delete()
                    except: pass
                    await send_main_menu_logic(message, user, just_took=True)
                    return 
                else:
                    await message.answer("❌ У вас уже есть активный заказ.")
                    return
            else:
                await message.answer("⚠️ Заказ уже кем-то взят или удален.")
                return
        except Exception as e: logging.error(f"Ошибка в cmd_start: {e}")
    
    await send_main_menu_logic(message, user)

# Пункт 2: Команда /orders
@user_router.message(Command("orders"))
async def cmd_orders(message: Message):
    text = (
        "💼 Все актуальные заказы публикуются в тгк профсоюза.\n\n"
        "🔗 [Перейти в канал профсоюза](https://t.me/+k677H-MfrDsxMmMy)"
    )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

# Пункт 3: Команда /myprofile
@user_router.message(Command("myprofile"))
async def cmd_myprofile(message: Message):
    user = await DB.get_user(message.from_user.id)
    if not user:
        await message.answer("Вы не зарегистрированы. Напишите /start")
        return
    text = (f"👤 **Профиль: {utils.escape_md(user['nickname'])}**\n"
            f"🌍 Гражданство: {user['citizenship']}\n"
            f"💳 Счет: `{user['bank_account']}`\n"
            f"🏆 Выполнено: {user['completed_jobs']}\n"
            f"💰 Заработано: {user['total_earned']} кбк")
    await message.answer(text, reply_markup=profile_kb(), parse_mode="Markdown")

# --- РЕГИСТРАЦИЯ ---

@user_router.message(Registration.nickname)
async def reg_nick(message: Message, state: FSMContext):
    if not utils.validate_nickname(message.text):
        await message.answer("❌ Неверный формат ника. Используйте только латиницу, цифры и нижнее подчеркивание.")
        return
    await state.update_data(nickname=message.text)
    await message.answer("Выберите Ваше гражданство:", reply_markup=get_reg_keyboard())
    await state.set_state(Registration.citizenship)

@user_router.message(Registration.citizenship, F.text.in_(["Столичное", "Антегрии", "Антегриевское"]))
async def reg_citiz(message: Message, state: FSMContext):
    await state.update_data(citizenship=message.text)
    await message.answer("Введите номер Вашего банковского счета:")
    await state.set_state(Registration.bank_account)

@user_router.message(Registration.bank_account)
async def reg_bank(message: Message, state: FSMContext):
    data = await state.get_data()
    await DB.register_user(message.from_user.id, data['nickname'], data['citizenship'], message.text)
    await state.clear()
    user = await DB.get_user(message.from_user.id)
    await message.answer("✅ Регистрация завершена!", reply_markup=ReplyKeyboardRemove())
    await send_main_menu_logic(message, user)

# --- ЛОГИКА ИГРОКА ---

@user_router.callback_query(F.data.startswith("active_jobs_"))
async def switch_active_job(callback: CallbackQuery):
    index = int(callback.data.split("_")[2])
    user = await DB.get_user(callback.from_user.id)
    await send_main_menu_logic(callback, user, index=index)

@user_router.callback_query(F.data.startswith("job_done_"))
async def job_done_start(callback: CallbackQuery, state: FSMContext):
    job_id = int(callback.data.split("_")[2])
    await state.update_data(temp_job_id=job_id)
    await callback.message.answer("📍 Отправьте координаты, где вы оставили ресурсы/выполнили работу:")
    await state.set_state(JobAction.waiting_for_coords)
    await callback.answer()

@user_router.message(JobAction.waiting_for_coords)
async def job_done_finish(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    job_id = data['temp_job_id']
    coords = message.text
    
    # Сохраняем в БД (в БД экранировать не нужно)
    await DB.update_vacancy_status(job_id, 'completed', coords)
    await utils.update_channel_post(bot, CHANNEL_ID, job_id, DB)
    
    user = await DB.get_user(message.from_user.id)
    await DB.update_user_stats(user['id'], 1, 0) 
   
    # Экранируем ник и координаты перед отправкой в лог-канал
    safe_nickname = utils.escape_md(user['nickname'])
    safe_coords = utils.escape_md(coords)
    
    log_text = f"Выполнил заказ #id_{job_id:03}\nКоординаты: {safe_coords}"
    
    await utils.send_log(bot, LOG_CHANNEL_ID, log_text, user['id'], safe_nickname)
    # ------------------------------
    
    await state.clear()
    await message.answer("✅ Отчет отправлен! Заказ отмечен как выполненный.")
    await send_main_menu_logic(message, user)

@user_router.callback_query(F.data.startswith("job_refuse_"))
async def job_refuse(callback: CallbackQuery, bot: Bot):
    job_id = int(callback.data.split("_")[2])
    await DB.update_vacancy_status(job_id, 'not_completed')
    await DB.assign_vacancy(job_id, None)
    await utils.update_channel_post(bot, CHANNEL_ID, job_id, DB)
    user = await DB.get_user(callback.from_user.id)
    await utils.send_log(bot, LOG_CHANNEL_ID, f"Отказался от заказа #id_{job_id:03}", user['id'], user['nickname'])
    await callback.answer("Вы отказались от заказа")
    await send_main_menu_logic(callback, user)

@user_router.callback_query(F.data == "my_profile")
async def view_profile(callback: CallbackQuery):
    user = await DB.get_user(callback.from_user.id)
    text = (f"👤 **Профиль: {utils.escape_md(user['nickname'])}**\n"
            f"🌍 Гражданство: {user['citizenship']}\n"
            f"💳 Счет: `{user['bank_account']}`\n"
            f"🏆 Выполнено: {user['completed_jobs']}\n"
            f"💰 Заработано: {user['total_earned']} кбк")
    await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="Markdown")

# Пункт 1: Обработка изменения счета
@user_router.callback_query(F.data == "edit_bank")
async def edit_bank_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите новый номер банковского счета:")
    await state.set_state(EditProfile.new_bank)
    await callback.answer()

@user_router.message(EditProfile.new_bank)
async def edit_bank_finish(message: Message, state: FSMContext):
    await DB.update_user_bank(message.from_user.id, message.text)
    await state.clear()
    await message.answer("✅ Номер счета успешно изменен!")
    user = await DB.get_user(message.from_user.id)
    text = (f"👤 **Профиль: {utils.escape_md(user['nickname'])}**\n"
            f"🌍 Гражданство: {user['citizenship']}\n"
            f"💳 Счет: `{user['bank_account']}`\n"
            f"🏆 Выполнено: {user['completed_jobs']}\n"
            f"💰 Заработано: {user['total_earned']} кбк")
    await message.answer(text, reply_markup=profile_kb(), parse_mode="Markdown")

@user_router.callback_query(F.data == "to_main")
async def back_to_main(callback: CallbackQuery):
    user = await DB.get_user(callback.from_user.id)
    await send_main_menu_logic(callback, user)

# --- АДМИН-ПАНЕЛЬ ---

@admin_router.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(message: Message):
    await message.answer("🛠 Панель управления профсоюзом", reply_markup=admin_main_kb())

@admin_router.callback_query(F.data == "adm_jobs_list_0")
async def adm_jobs_list_root(callback: CallbackQuery):
    await render_admin_jobs_list(callback, 0)

@admin_router.callback_query(F.data.startswith("adm_jobs_list_p_"))
async def adm_jobs_pagination(callback: CallbackQuery):
    page = int(callback.data.split("_")[4])
    await render_admin_jobs_list(callback, page)

@admin_router.callback_query(F.data.startswith("adm_view_"))
async def adm_view_job(callback: CallbackQuery):
    job_id = int(callback.data.split("_")[2])
    job = await DB.get_vacancy_by_id(job_id)
    assigned_user = await DB.get_user(job['assigned_user_id']) if job['assigned_user_id'] else None
    text = utils.format_vacancy_text(job, is_admin=True, user_data=assigned_user)
    
    # Кнопки управления заказом для админа
    builder = InlineKeyboardBuilder()
    if job['status'] == 'completed':
        builder.row(InlineKeyboardButton(text="💰 Подтвердить выплату", callback_data=f"adm_pay_{job_id}"))
    if job['assigned_user_id']:
        builder.row(InlineKeyboardButton(text="💬 Исполнитель", url=f"tg://user?id={job['assigned_user_id']}"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"adm_del_{job_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data="adm_jobs_list_0"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@admin_router.callback_query(F.data.startswith("adm_pay_"))
async def adm_pay_confirm(callback: CallbackQuery, bot: Bot):
    job_id = int(callback.data.split("_")[2])
    job = await DB.get_vacancy_by_id(job_id)
    if job and job['status'] == 'completed':
        await DB.update_user_stats(job['assigned_user_id'], 0, job['salary'])
        await DB.update_vacancy_status(job_id, 'paid')
        await callback.answer("Выплата подтверждена!", show_alert=True)
        # Уведомляем пользователя
        try:
            await bot.send_message(job['assigned_user_id'], f"💰 Вам начислена выплата за заказ #id{job_id:03} в размере {job['salary']} кбк!")
        except: pass
        await render_admin_jobs_list(callback, 0)
    else:
        await callback.answer("Ошибка: заказ не в статусе выполнения.")

@admin_router.callback_query(F.data.startswith("adm_del_"))
async def adm_delete_job(callback: CallbackQuery, bot: Bot):
    v_id = int(callback.data.split("_")[2])
    await DB.delete_vacancy(v_id)
    await utils.update_channel_post(bot, CHANNEL_ID, v_id, DB)
    await callback.answer("Заказ удален", show_alert=True)
    await render_admin_jobs_list(callback, 0)

@admin_router.callback_query(F.data == "adm_back")
async def adm_back(callback: CallbackQuery):
    await callback.message.edit_text("🛠 Панель управления профсоюзом", reply_markup=admin_main_kb())

@admin_router.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    users = await DB.get_all_users_detailed()
    text = f"📊 **Статистика**\n👥 Всего пользователей: {len(users)}"
    await callback.message.edit_text(text, reply_markup=admin_stats_kb(), parse_mode="Markdown")

@admin_router.callback_query(F.data == "adm_rating")
async def adm_rating(callback: CallbackQuery):
    users = await DB.get_all_users_detailed()
    users = sorted(users, key=lambda x: x['total_earned'], reverse=True)
    text = "🏆 **Топ по заработку:**\n\n"
    for i, u in enumerate(users[:10], 1):
        text += f"{i}. {utils.escape_md(u['nickname'])} — {u['total_earned']} кбк\n"
    await callback.message.edit_text(text, reply_markup=admin_back_kb(), parse_mode="Markdown")

# --- СОЗДАНИЕ ЗАКАЗА ---

@admin_router.callback_query(F.data == "adm_create_job")
async def adm_create_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📝 Введите описание заказа:")
    await state.set_state(CreateVacancy.description)

@admin_router.message(CreateVacancy.description)
async def adm_create_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Выберите приоритет:", reply_markup=get_priority_kb())
    await state.set_state(CreateVacancy.priority)

@admin_router.callback_query(CreateVacancy.priority, F.data.startswith("set_priority:"))
async def adm_create_priority(callback: CallbackQuery, state: FSMContext):
    priority = callback.data.split(":")[1]
    await state.update_data(priority=priority)
    await callback.message.edit_text("Выберите категорию:", reply_markup=get_category_kb())
    await state.set_state(CreateVacancy.category)

@admin_router.callback_query(CreateVacancy.category, F.data.startswith("set_category:"))
async def adm_create_cat(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]
    await state.update_data(category=category)
    await callback.message.edit_text("Введите сумму оплаты (только число):")
    await state.set_state(CreateVacancy.salary)

@admin_router.message(CreateVacancy.salary)
async def adm_create_salary(message: Message, state: FSMContext, bot: Bot):
    try:
        salary = float(message.text.replace(',', '.'))
        data = await state.get_data()
        job_id = await DB.add_vacancy(data['description'], data['priority'], data['category'], salary, message.from_user.id)
        job = await DB.get_vacancy_by_id(job_id)
        text = utils.format_vacancy_text(job, is_admin=False)
        me = await bot.get_me()
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📥 Взять заказ", url=f"https://t.me/{me.username}?start=job_{job_id}"))
        msg = await bot.send_message(CHANNEL_ID, text, reply_markup=builder.as_markup(), parse_mode="Markdown")
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE vacancies SET channel_message_id = ? WHERE id = ?", (msg.message_id, job_id))
            await db.commit()
        await state.clear()
        await message.answer(f"✅ Заказ #id{job_id:03} успешно создан!")
        await admin_panel(message)
    except ValueError:
        await message.answer("❌ Ошибка! Введите число")