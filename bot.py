import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from database import init_db

# Настройки конфигурации напрямую в коде
TOKEN = "8500675415:AAGIa0rASikNPWld2j8WRERH7eFHaGgfJOA"
ADMIN_IDS = [1746547600, 5987383547]
CHANNEL_ID = -1003760722987
LOG_CHANNEL_ID = -1003894513411

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="orders", description="🔍 Найти заказы"),
        BotCommand(command="myprofile", description="⚙️ Мой профиль"),
    ]
    await bot.set_my_commands(commands)

async def main():
    await init_db()
    
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    from handlers import user_router, admin_router
    dp.include_router(admin_router)
    dp.include_router(user_router)

    await set_commands(bot)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    print("Бот запущен и готов к работе...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Бот остановлен")