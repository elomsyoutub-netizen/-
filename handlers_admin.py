from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from database import Database
from keyboards import *
from config import ADMIN_ID, DB_NAME


# Состояния для админа
class AdminStates(StatesGroup):
    waiting_for_comment = State()
    waiting_for_message = State()
    waiting_for_broadcast = State()


# Инициализация БД
db = Database(DB_NAME)


# Проверка, является ли пользователь админом
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# Команда /admin
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    admin_text = """
🔧 Админ-панель

Добро пожаловать в панель управления ботом!
Используйте меню ниже для навигации.
    """

    await message.answer(admin_text, reply_markup=admin_main_menu())


# Показать статистику
async def show_statistics(message: types.Message):
    if not is_admin(message.from_user.id):
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


# Показать все заявки
async def show_all_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    orders = db.get_all_orders()

    if not orders:
        await message.answer("Заявок пока нет.", reply_markup=admin_main_menu())
        return

    text = f"📋 Все заявки (всего: {len(orders)})\n\nВыберите заявку для просмотра:"

    await message.answer(text, reply_markup=admin_orders_list(orders))


# Показать новые заявки
async def show_new_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    orders = db.get_all_orders(status='new')

    if not orders:
        await message.answer("Новых заявок нет.", reply_markup=admin_main_menu())
        return

    text = f"🆕 Новые заявки (всего: {len(orders)})\n\nВыберите заявку для просмотра:"

    await message.answer(text, reply_markup=admin_orders_list(orders))


# Просмотр конкретной заявки (для админа)
async def admin_view_order(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

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

👤 Клиент: {order['first_name']} (@{order['username']})
🆔 User ID: {order['user_id']}

📅 Создана: {order['created_at']}
🔄 Обновлена: {order['updated_at']}
📊 Статус: {status_text.get(order['status'], order['status'])}

📝 Описание:
{order['description']}
    """

    if order['budget']:
        order_text += f"\n💰 Бюджет: {order['budget']}"

    if order['admin_comment']:
        order_text += f"\n\n💬 Ваш комментарий:\n{order['admin_comment']}"

    # Показываем историю сообщений
    messages = db.get_order_messages(order_id)
    if messages:
        order_text += "\n\n📨 История сообщений:\n"
        for msg in messages[-5:]:  # Последние 5 сообщений
            sender = "👨‍💼 Вы" if msg['is_from_admin'] else "👤 Клиент"
            order_text += f"\n{sender} ({msg['created_at']}):\n{msg['message_text']}\n"

    await callback.message.edit_text(
        order_text,
        reply_markup=admin_order_buttons(order_id, order['status'])
    )
    await callback.answer()


# Изменение статуса заявки
async def admin_change_status(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    data = callback.data.split("_")
    order_id = int(data[2])
    new_status = data[3]

    order = db.get_order(order_id)

    status_names = {
        'new': 'Новая',
        'in_progress': 'В работе',
        'completed': 'Завершена',
        'cancelled': 'Отменена'
    }

    # Обновляем статус
    db.update_order_status(order_id, new_status)

    await callback.answer(f"Статус изменен на: {status_names[new_status]}")

    # Уведомляем клиента
    try:
        status_messages = {
            'in_progress': f"🔄 Ваша заявка #{order_id} взята в работу!",
            'completed': f"✅ Ваша заявка #{order_id} выполнена! Спасибо за обращение!",
            'cancelled': f"❌ Ваша заявка #{order_id} была отменена."
        }

        if new_status in status_messages:
            from bot import bot
            await bot.send_message(order['user_id'], status_messages[new_status])
    except:
        pass

    # Обновляем сообщение
    await admin_view_order(callback)


# Написать комментарий к заявке
async def admin_add_comment(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[2])

    await state.update_data(order_id=order_id)
    await AdminStates.waiting_for_comment.set()

    await callback.message.answer("✍️ Напишите комментарий к заявке:")
    await callback.answer()


# Обработка комментария
async def process_admin_comment(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data.get('order_id')

    if not order_id:
        await state.finish()
        return

    comment = message.text
    order = db.get_order(order_id)

    # Обновляем комментарий
    db.update_order_status(order_id, order['status'], comment)

    await state.finish()

    await message.answer("✅ Комментарий добавлен!", reply_markup=admin_main_menu())

    # Уведомляем клиента
    try:
        from bot import bot
        await bot.send_message(
            order['user_id'],
            f"💬 Новый комментарий по заявке #{order_id}:\n\n{comment}"
        )
    except:
        pass


# Написать сообщение клиенту
async def admin_send_message(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    order_id = int(callback.data.split("_")[2])

    await state.update_data(order_id=order_id)
    await AdminStates.waiting_for_message.set()

    await callback.message.answer("✍️ Напишите сообщение клиенту:")
    await callback.answer()


# Обработка сообщения клиенту
async def process_admin_message(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    order_id = data.get('order_id')

    if not order_id:
        await state.finish()
        return

    message_text = message.text
    order = db.get_order(order_id)

    # Сохраняем сообщение
    db.add_message(order_id, ADMIN_ID, message_text, True)

    await state.finish()

    await message.answer("✅ Сообщение отправлено!", reply_markup=admin_main_menu())

    # Отправляем клиенту
    try:
        from bot import bot
        await bot.send_message(
            order['user_id'],
            f"💬 Сообщение от менеджера по заявке #{order_id}:\n\n{message_text}"
        )
    except:
        pass


# Показать список пользователей
async def show_users(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    users = db.get_all_users()

    if not users:
        await message.answer("Пользователей пока нет.", reply_markup=admin_main_menu())
        return

    text = f"👥 Пользователи (всего: {len(users)})\n\n"

    for user in users[:20]:  # Показываем первых 20
        text += f"👤 {user['first_name']} (@{user['username']})\n"
        text += f"🆔 ID: {user['user_id']}\n"
        text += f"📅 Регистрация: {user['registration_date']}\n\n"

    await message.answer(text, reply_markup=admin_main_menu())


# Начать рассылку
async def start_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    text = """
📢 Рассылка сообщений

Напишите текст сообщения, которое хотите отправить всем пользователям бота.

⚠️ Будьте осторожны! Сообщение будет отправлено всем зарегистрированным пользователям.
    """

    await message.answer(text, reply_markup=back_to_main())
    await AdminStates.waiting_for_broadcast.set()


# Обработка текста рассылки
async def process_broadcast_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if message.text == "🔙 Главное меню":
        await state.finish()
        await message.answer("Рассылка отменена", reply_markup=admin_main_menu())
        return

    broadcast_text = message.text

    await state.update_data(broadcast_text=broadcast_text)

    users_count = db.get_statistics()['total_users']

    confirm_text = f"""
📢 Подтверждение рассылки

Вы собираетесь отправить сообщение {users_count} пользователям:

---
{broadcast_text}
---

Подтвердите отправку:
    """

    await message.answer(confirm_text, reply_markup=confirm_broadcast())


# Подтверждение рассылки
async def confirm_broadcast_callback(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    if callback.data == "broadcast_cancel":
        await state.finish()
        await callback.message.edit_text("❌ Рассылка отменена")
        await callback.message.answer("Админ-панель", reply_markup=admin_main_menu())
        await callback.answer()
        return

    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')

    await state.finish()

    users = db.get_all_users()

    await callback.message.edit_text("📤 Начинаю рассылку...")

    success_count = 0
    fail_count = 0

    from bot import bot

    for user in users:
        try:
            await bot.send_message(user['user_id'], broadcast_text)
            success_count += 1
        except Exception as e:
            fail_count += 1

    result_text = f"""
✅ Рассылка завершена!

📊 Результаты:
• Успешно отправлено: {success_count}
• Не удалось отправить: {fail_count}
    """

    await callback.message.answer(result_text, reply_markup=admin_main_menu())
    await callback.answer()


# Переключение в пользовательский режим
async def switch_to_user_mode(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.finish()

    from handlers_user import cmd_start
    await cmd_start(message)


# Возврат к списку заявок
async def back_to_orders(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        return

    orders = db.get_all_orders()
    text = f"📋 Все заявки (всего: {len(orders)})\n\nВыберите заявку для просмотра:"

    await callback.message.edit_text(text, reply_markup=admin_orders_list(orders))
    await callback.answer()


# Регистрация админских обработчиков
def register_admin_handlers(dp: Dispatcher):
    # Команды
    dp.register_message_handler(cmd_admin, commands=['admin'], state='*')

    # Кнопки админ-панели
    dp.register_message_handler(show_statistics, text="📊 Статистика", state='*')
    dp.register_message_handler(show_all_orders, text="📋 Все заявки", state='*')
    dp.register_message_handler(show_new_orders, text="🆕 Новые заявки", state='*')
    dp.register_message_handler(show_users, text="👥 Пользователи", state='*')
    dp.register_message_handler(start_broadcast, text="📢 Рассылка", state='*')
    dp.register_message_handler(switch_to_user_mode, text="👤 Пользовательский режим", state='*')

    # FSM обработчики
    dp.register_message_handler(process_admin_comment, state=AdminStates.waiting_for_comment)
    dp.register_message_handler(process_admin_message, state=AdminStates.waiting_for_message)
    dp.register_message_handler(process_broadcast_text, state=AdminStates.waiting_for_broadcast)

    # Callback обработчики
    dp.register_callback_query_handler(admin_view_order, lambda c: c.data.startswith('admin_order_'))
    dp.register_callback_query_handler(admin_change_status, lambda c: c.data.startswith('admin_status_'))
    dp.register_callback_query_handler(admin_add_comment, lambda c: c.data.startswith('admin_comment_'))
    dp.register_callback_query_handler(admin_send_message, lambda c: c.data.startswith('admin_message_'))
    dp.register_callback_query_handler(back_to_orders, lambda c: c.data == 'admin_back_to_orders')
    dp.register_callback_query_handler(confirm_broadcast_callback, lambda c: c.data in ['broadcast_confirm', 'broadcast_cancel'])
