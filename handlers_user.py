from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database import Database
from keyboards import *
from config import *


# Состояния для FSM
class OrderForm(StatesGroup):
    waiting_for_description = State()
    waiting_for_message = State()


class ReviewForm(StatesGroup):
    waiting_for_order = State()
    waiting_for_rating = State()
    waiting_for_comment = State()


# Инициализация БД
db = Database(DB_NAME)


# Команда /start
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""

    # Регистрируем пользователя
    db.add_user(user_id, username, first_name, last_name)

    await message.answer(WELCOME_MESSAGE, reply_markup=main_menu())


# Обработка кнопки "Наши услуги"
async def show_services(message: types.Message):
    await message.answer(SERVICES_MESSAGE, reply_markup=main_menu())


# Обработка кнопки "О нас"
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

🎯 Специализация:
• Боты для интернет-магазинов
• Системы автоматизации
• Боты для образования
• CRM-системы
• Интеграции с API

📞 Свяжитесь с нами и получите бесплатную консультацию!
    """
    await message.answer(about_text, reply_markup=main_menu())


# Обработка кнопки "Контакты"
async def show_contacts(message: types.Message):
    contacts_text = """
📞 Контакты

💬 Telegram: @your_username
📧 Email: info@example.com
🌐 Website: www.example.com

⏰ Режим работы:
Пн-Пт: 9:00 - 18:00 (МСК)
Сб-Вс: Выходной

💡 Для быстрой связи - оставьте заявку через бота!
    """
    await message.answer(contacts_text, reply_markup=main_menu())


# Начало оформления заявки
async def start_order(message: types.Message):
    await message.answer(ORDER_MESSAGE, reply_markup=back_to_main())
    await OrderForm.waiting_for_description.set()


# Обработка текста заявки
async def process_order_description(message: types.Message, state: FSMContext):
    description = message.text

    if description == "🔙 Главное меню":
        await state.finish()
        await message.answer("Главное меню", reply_markup=main_menu())
        return

    user_id = message.from_user.id
    order_id = db.create_order(user_id, description)

    # Сохраняем сообщение в историю
    db.add_message(order_id, user_id, description, False)

    await state.finish()

    success_text = f"""
✅ Ваша заявка #{order_id} успешно принята!

Наш менеджер рассмотрит её в ближайшее время и свяжется с вами.

Вы можете отслеживать статус заявки в личном кабинете.
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
        from bot import bot
        await bot.send_message(ADMIN_ID, admin_notification)
    except:
        pass


# Личный кабинет
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


# Показать мои заявки
async def show_my_orders(message: types.Message):
    orders = db.get_user_orders(message.from_user.id)

    if not orders:
        await message.answer("У вас пока нет заявок.", reply_markup=cabinet_menu())
        return

    text = "📝 Ваши заявки:\n\n"

    await message.answer(text, reply_markup=user_orders_buttons(orders))


# Просмотр конкретной заявки
async def view_order_callback(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[2])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    status_text = {
        'new': '🆕 Новая',
        'in_progress': '🔄 В работе',
        'completed': '✅ Завершена',
        'cancelled': '❌ Отменена'
    }

    order_text = f"""
📋 Заявка #{order['order_id']}

📅 Создана: {order['created_at']}
🔄 Обновлена: {order['updated_at']}
📊 Статус: {status_text.get(order['status'], order['status'])}

📝 Описание:
{order['description']}
    """

    if order['admin_comment']:
        order_text += f"\n💬 Комментарий менеджера:\n{order['admin_comment']}"

    await callback.message.edit_text(order_text, reply_markup=order_inline_buttons(order_id))
    await callback.answer()


# Написать сообщение по заявке
async def message_order_callback(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])

    await state.update_data(order_id=order_id)
    await OrderForm.waiting_for_message.set()

    await callback.message.answer("✍️ Напишите ваше сообщение:")
    await callback.answer()


# Обработка сообщения по заявке
async def process_order_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')

    if not order_id:
        await state.finish()
        return

    user_id = message.from_user.id
    message_text = message.text

    # Сохраняем сообщение
    db.add_message(order_id, user_id, message_text, False)

    await state.finish()

    await message.answer("✅ Сообщение отправлено менеджеру!", reply_markup=cabinet_menu())

    # Уведомление админу
    try:
        order = db.get_order(order_id)
        admin_notification = f"""
💬 Новое сообщение по заявке #{order_id}

👤 От: {message.from_user.first_name}
📝 Сообщение:
{message_text}
        """
        from bot import bot
        await bot.send_message(ADMIN_ID, admin_notification)
    except:
        pass


# Просмотр статуса заявки
async def status_order_callback(callback: types.CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    order = db.get_order(order_id)

    if not order:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    status_text = {
        'new': '🆕 Новая - ваша заявка принята и ожидает обработки',
        'in_progress': '🔄 В работе - менеджер работает над вашей заявкой',
        'completed': '✅ Завершена - работа выполнена',
        'cancelled': '❌ Отменена'
    }

    await callback.answer(status_text.get(order['status'], order['status']), show_alert=True)


# Оставить отзыв
async def start_review(message: types.Message):
    orders = db.get_user_orders(message.from_user.id)
    completed_orders = [o for o in orders if o['status'] == 'completed']

    if not completed_orders:
        await message.answer(
            "У вас нет завершенных заказов для оценки.",
            reply_markup=cabinet_menu()
        )
        return

    text = "⭐ Выберите заказ для оценки:\n\n"
    keyboard = InlineKeyboardMarkup(row_width=1)

    for order in completed_orders:
        keyboard.add(
            InlineKeyboardButton(
                f"Заказ #{order['order_id']}",
                callback_data=f"review_{order['order_id']}"
            )
        )

    await message.answer(text, reply_markup=keyboard)


# Выбор заказа для отзыва
async def select_order_for_review(callback: types.CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])

    await state.update_data(order_id=order_id)

    await callback.message.edit_text(
        "⭐ Оцените качество выполненной работы:",
        reply_markup=rating_buttons(order_id)
    )
    await callback.answer()


# Обработка оценки
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data.split("_")
    order_id = int(data[1])
    rating = int(data[2])

    await state.update_data(order_id=order_id, rating=rating)
    await ReviewForm.waiting_for_comment.set()

    await callback.message.edit_text(
        f"Вы поставили оценку: {'⭐' * rating}\n\n"
        "💬 Напишите комментарий к вашему отзыву:"
    )
    await callback.answer()


# Обработка комментария к отзыву
async def process_review_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get('order_id')
    rating = data.get('rating')
    comment = message.text

    # Сохраняем отзыв
    db.add_review(message.from_user.id, order_id, rating, comment)

    await state.finish()

    await message.answer(
        "✅ Спасибо за ваш отзыв! Он очень важен для нас.",
        reply_markup=cabinet_menu()
    )

    # Уведомление админу
    try:
        admin_notification = f"""
⭐ Новый отзыв!

📋 Заказ: #{order_id}
👤 От: {message.from_user.first_name}
⭐ Оценка: {rating}/5
💬 Комментарий:
{comment}
        """
        from bot import bot
        await bot.send_message(ADMIN_ID, admin_notification)
    except:
        pass


# Возврат в главное меню
async def back_to_main_menu(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Главное меню", reply_markup=main_menu())


# Регистрация обработчиков
def register_user_handlers(dp: Dispatcher):
    # Команды
    dp.register_message_handler(cmd_start, commands=['start', 'help'], state='*')

    # Кнопки главного меню
    dp.register_message_handler(show_services, text="📋 Наши услуги", state='*')
    dp.register_message_handler(show_about, text="ℹ️ О нас", state='*')
    dp.register_message_handler(show_contacts, text="📞 Контакты", state='*')
    dp.register_message_handler(start_order, text="✍️ Оставить заявку", state='*')
    dp.register_message_handler(show_cabinet, text="👤 Личный кабинет", state='*')

    # Кнопки личного кабинета
    dp.register_message_handler(show_my_orders, text="📝 Мои заявки", state='*')
    dp.register_message_handler(start_review, text="⭐ Оставить отзыв", state='*')
    dp.register_message_handler(back_to_main_menu, text="🔙 Главное меню", state='*')

    # FSM обработчики для заявки
    dp.register_message_handler(process_order_description, state=OrderForm.waiting_for_description)
    dp.register_message_handler(process_order_message, state=OrderForm.waiting_for_message)

    # FSM обработчики для отзыва
    dp.register_message_handler(process_review_comment, state=ReviewForm.waiting_for_comment)

    # Callback обработчики
    dp.register_callback_query_handler(view_order_callback, lambda c: c.data.startswith('view_order_'))
    dp.register_callback_query_handler(message_order_callback, lambda c: c.data.startswith('message_'))
    dp.register_callback_query_handler(status_order_callback, lambda c: c.data.startswith('status_'))
    dp.register_callback_query_handler(select_order_for_review, lambda c: c.data.startswith('review_'))
    dp.register_callback_query_handler(process_rating, lambda c: c.data.startswith('rate_'))
