import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from dotenv import load_dotenv
from aiohttp import web

from db.database import init_db
from handlers import common
from handlers import admin

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Перезапустить бота"),
        BotCommand(command="menu", description="📦 Открыть каталог товаров"),
        BotCommand(command="add_product", description="➕ Добавить новый товар (Админ)"),
        BotCommand(command="report", description="📊 Финансовый отчет (Админ)"),
        BotCommand(command="help", description="❓ Инструкция по работе"),
    ]
    await bot.set_my_commands(commands)


# --- Заглушка для Render (чтобы не падал по таймауту) ---
async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.router.add_get('/', handle)
# ----------------------------------------------------


async def main():
    await init_db()
    await setup_bot_commands(bot)

    # Подключаем наши Роутеры к Диспетчеру:
    dp.include_router(common.router)
    dp.include_router(admin.router)

    # Запускаем фоновый веб-сервер для Render:
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    print("Бот успешно запущен и ждет сообщений...")
    
    # Запускаем поллинг бота:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
