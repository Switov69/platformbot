from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_reg_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Столичное")], [KeyboardButton(text="Антегриевское")]],
        resize_keyboard=True, one_time_keyboard=True 
    )

def main_menu_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile"))
    return builder.as_markup()

def profile_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💳 Изменить счёт", callback_data="edit_bank"))
    builder.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="to_main"))
    return builder.as_markup()

def vacancy_player_kb(v_id, current_index, total_active):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="☑️ Выполнил", callback_data=f"job_done_{v_id}"))
    builder.row(InlineKeyboardButton(text="❌ Отказаться", callback_data=f"job_refuse_{v_id}"))
    if total_active > 1:
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"active_jobs_{current_index-1}"))
        if current_index < total_active - 1:
            nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"active_jobs_{current_index+1}"))
        if nav_buttons:
            builder.row(*nav_buttons)
    return builder.as_markup()

def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Создать заказ", callback_data="adm_create_job"))
    builder.row(InlineKeyboardButton(text="📋 Список заказов", callback_data="adm_jobs_list_0"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"))
    return builder.as_markup()

def admin_job_manage_kb(v_id, assigned_user_id):
    builder = InlineKeyboardBuilder()
    if assigned_user_id:
        builder.row(InlineKeyboardButton(text="💬 Исполнитель", url=f"tg://user?id={assigned_user_id}"))
    builder.row(InlineKeyboardButton(text="🗑 Удалить заказ", callback_data=f"adm_del_{v_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ К списку", callback_data="adm_jobs_list_0"))
    return builder.as_markup()

def admin_stats_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏆 Рейтинг", callback_data="adm_rating"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back"))
    return builder.as_markup()

def admin_back_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="adm_back"))
    return builder.as_markup()

def get_priority_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Легкий", callback_data="set_priority:Легкий"))
    builder.row(InlineKeyboardButton(text="Средний", callback_data="set_priority:Средний"))
    builder.row(InlineKeyboardButton(text="Высокий", callback_data="set_priority:Высокий"))
    return builder.as_markup()

def get_category_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Ресурсы", callback_data="set_category:Ресурсы"))
    builder.row(InlineKeyboardButton(text="Строительство", callback_data="set_category:Строительство"))
    return builder.as_markup()