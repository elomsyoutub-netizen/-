#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram бот для продажи услуг (версия для aiogram 3.x)
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID
from database import Database
from keyboards import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация
db = Database("bot_database.db")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Состояния для FSM
class OrderForm(StatesGroup):
    waiting_for_description = State()
    waiting_for_message = State()


class ReviewForm(StatesGroup):
    waiting_for_comment = State()


class AdminStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_message = State()
    waiting_for_broadcast = State()


# === ОБРАБОТЧИКИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===

@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    db.add_user(user_id, username, first_name, last_name)

    from config import WELCOME_MESSAGE
    await message.answer(WELCOME_MESSAGE, reply_markup=main_menu())


@dp.message(F.text == "📋 Наши услуги")
async def show_services(message: types.Message):
    from config import SERVICES_MESSAGE
    await message.answer(SERVICES_MESSAGE, reply_markup=main_menu())


@dp.message(F.text == "ℹ️ О нас")
async def show_about(message: types.Message):
    about_text = """
ℹ️ О нас

Мы - команда профессиональных разработчиков Telegram ботов с опытом работы более 5 лет.

🏆 Наши достижения:
• Более 200 успешно реализованных проектов
• Клиенты из 15+ стран
• Средний рейтинг 4.9/5.0

💪 Почему выбирают нас:
• Индивидуальный подход к каждому проекту
• Соблюдение сроков
• Техническая поддержка после запуска
• Конкурентные цены
• Гарантия качества
    """
    await message.answer(about_text, reply_markup=main_menu())


@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: types.Message):
    contacts_text = """
📞 Контакты

💬 Telegram: @your_username
📧 Email: info@example.com

⏰ Режим работы:
Пн-Пт: 9:00 - 18:00 (МСК)

💡 Для быстрой связи - оставьте заявку через бота!
    """
    await message.answer(contacts_text, reply_markup=main_menu())


@dp.message(F.text == "✍️ Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    from config import ORDER_MESSAGE
    await message.answer(ORDER_MESSAGE, reply_markup=back_to_main())
    await state.set_state(OrderForm.waiting_for_description)


@dp.message(OrderForm.waiting_for_description)
async def process_order_description(message: types.Message, state: FSMContext):
    if message.text == "🔙 Главное меню":
        await state.clear()
        await message.answer("Главное меню", reply_markup=main_menu())
        return

    description = message.text
    user_id = message.from_user.id
    order_id = db.create_order(user_id, description)
    db.add_message(order_id, user_id, description, False)

    await state.clear()

    success_text = f"""
✅ Ваша заявка #{order_id} успешно принята!

Наш менеджер рассмотрит её в ближайшее время.

Вы можете отслеживать статус в личном кабинете.
    """
    await message.answer(success_text, reply_markup=main_menu())

    # Уведомление админу
    try:
        admin_notification = f"""
🆕 Новая заявка #{order_id}!

👤 От: {message.from_user.first_name}
🆔 ID: {user_id}
📝 Описание:
{description}
        """
        await bot.send_message(ADMIN_ID, admin_notification)
    except:
        pass


@dp.message(F.text == "👤 Личный кабинет")
async def show_cabinet(message: types.Message):
    user = db.get_user(message.from_user.id)
    orders = db.get_user_orders(message.from_user.id)

    cabinet_text = f"""
👤 Личный кабинет

📊 Ваша статистика:
• Всего заявок: {len(orders)}
• Дата регистрации: {user['registration_date']}

Выберите действие:
    """
    await message.answer(cabinet_text, reply_markup=cabinet_menu())


@dp.message(F.text == "📝 Мои заявки")
async def show_my_orders(message: types.Message):
    orders = db.get_user_orders(message.from_user.id)

    if not orders:
        await message.answer("У вас пока нет заявок.", reply_markup=cabinet_menu())
        return

    text = "📝 Ваши заявки:\n\n"
    await message.answer(text, reply_markup=user_orders_buttons(orders))


@dp.message(F.text == "🔙 Главное меню")
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=main_menu())


# === ОБРАБОТЧИКИ ДЛЯ АДМИНА ===

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    admin_text = """
🔧 Админ-панель

Добро пожаловать в панель управления ботом!
    """
    await message.answer(admin_text, reply_markup=admin_main_menu())


@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    stats = db.get_statistics()

    stats_text = f"""
📊 Статистика бота

👥 Пользователи: {stats['total_users']}

📋 Заявки:
• Всего: {stats['total_orders']}
• 🆕 Новые: {stats['new_orders']}
• 🔄 В работе: {stats['in_progress']}
• ✅ Завершенные: {stats['completed']}

⭐ Средняя оценка: {stats['avg_rating']}/5.0
    """
    await message.answer(stats_text, reply_markup=admin_main_menu())


@dp.message(F.text == "📋 Все заявки")
async def show_all_orders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    orders = db.get_all_orders()

    if not orders:
        await message.answer("Заявок пока нет.", reply_markup=admin_main_menu())
        return

    text = f"📋 Все заявки (всего: {len(orders)})\n\nВыберите заявку:"
    await message.answer(text, reply_markup=admin_orders_list(orders))


@dp.message(F.text == "🆕 Новые заявки")
async def show_new_orders(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    orders = db.get_all_orders(status='new')

    if not orders:
        await message.answer("Новых заявок нет.", reply_markup=admin_main_menu())
        return

    text = f"🆕 Новые заявки (всего: {len(orders)})"
    await message.answer(text, reply_markup=admin_orders_list(orders))


@dp.message(F.text == "👥 Пользователи")
async def show_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    users = db.get_all_users()

    if not users:
        await message.answer("Пользователей нет.", reply_markup=admin_main_menu())
        return

    text = f"👥 Пользователи (всего: {len(users)})\n\n"

    for user in users[:20]:
        text += f"👤 {user['first_name']} (@{user['username']})\n"
        text += f"🆔 ID: {user['user_id']}\n\n"

    await message.answer(text, reply_markup=admin_main_menu())


@dp.message(F.text == "👤 Пользовательский режим")
async def switch_to_user_mode(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()
    await cmd_start(message)


# Главная функция
async def main():
    logger.info("Бот запускается...")

    # Устанавливаем команды
    await bot.set_my_commands([
        types.BotCommand(command="start", description="🏠 Главное меню"),
        types.BotCommand(command="help", description="ℹ️ Помощь"),
        types.BotCommand(command="admin", description="🔧 Админ-панель")
    ])

    logger.info("Бот успешно запущен!")

    # Запускаем polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
