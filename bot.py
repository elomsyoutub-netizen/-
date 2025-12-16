#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram бот для продажи услуг по созданию ботов
"""

import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import BOT_TOKEN
from handlers_user import register_user_handlers
from handlers_admin import register_admin_handlers


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


# Установка команд бота
async def set_bot_commands():
    """Установка команд бота в меню"""
    commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="ℹ️ Помощь"),
        BotCommand(command="admin", description="🔧 Админ-панель (только для админа)")
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


# Функция запуска при старте бота
async def on_startup(dp):
    """Действия при запуске бота"""
    logger.info("Бот запускается...")
    await set_bot_commands()
    logger.info("Бот успешно запущен!")


# Функция при остановке бота
async def on_shutdown(dp):
    """Действия при остановке бота"""
    logger.info("Бот останавливается...")
    await dp.storage.close()
    await dp.storage.wait_closed()
    logger.info("Бот остановлен")


# Регистрация обработчиков
def register_all_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков"""
    # Сначала регистрируем админские обработчики (приоритет выше)
    register_admin_handlers(dp)
    # Затем пользовательские
    register_user_handlers(dp)


# Главная функция
def main():
    """Запуск бота"""
    logger.info("Инициализация обработчиков...")
    register_all_handlers(dp)

    try:
        logger.info("Запуск polling...")
        executor.start_polling(
            dp,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True  # Пропускаем накопившиеся обновления
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")


if __name__ == '__main__':
    main()
