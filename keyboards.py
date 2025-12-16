from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


# Главное меню для пользователя
def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📋 Наши услуги"))
    keyboard.add(KeyboardButton("✍️ Оставить заявку"), KeyboardButton("👤 Личный кабинет"))
    keyboard.add(KeyboardButton("📞 Контакты"), KeyboardButton("ℹ️ О нас"))
    return keyboard


# Меню личного кабинета
def cabinet_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📝 Мои заявки"))
    keyboard.add(KeyboardButton("⭐ Оставить отзыв"))
    keyboard.add(KeyboardButton("🔙 Главное меню"))
    return keyboard


# Inline кнопки для заявки (для пользователя)
def order_inline_buttons(order_id: int):
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("💬 Написать сообщение", callback_data=f"message_{order_id}"),
        InlineKeyboardButton("📊 Статус", callback_data=f"status_{order_id}")
    )
    return keyboard


# Админское главное меню
def admin_main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Статистика"))
    keyboard.add(KeyboardButton("📋 Все заявки"), KeyboardButton("🆕 Новые заявки"))
    keyboard.add(KeyboardButton("👥 Пользователи"), KeyboardButton("📢 Рассылка"))
    keyboard.add(KeyboardButton("👤 Пользовательский режим"))
    return keyboard


# Inline кнопки для управления заявкой (для админа)
def admin_order_buttons(order_id: int, current_status: str):
    keyboard = InlineKeyboardMarkup(row_width=2)

    # Кнопки изменения статуса
    if current_status != "in_progress":
        keyboard.add(InlineKeyboardButton("🔄 В работу", callback_data=f"admin_status_{order_id}_in_progress"))

    if current_status != "completed":
        keyboard.add(InlineKeyboardButton("✅ Завершить", callback_data=f"admin_status_{order_id}_completed"))

    if current_status != "cancelled":
        keyboard.add(InlineKeyboardButton("❌ Отменить", callback_data=f"admin_status_{order_id}_cancelled"))

    # Кнопки действий
    keyboard.add(
        InlineKeyboardButton("💬 Написать клиенту", callback_data=f"admin_message_{order_id}"),
        InlineKeyboardButton("📝 Комментарий", callback_data=f"admin_comment_{order_id}")
    )
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_back_to_orders"))

    return keyboard


# Inline кнопки для фильтрации заявок
def admin_orders_filter():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🆕 Новые", callback_data="filter_new"),
        InlineKeyboardButton("🔄 В работе", callback_data="filter_in_progress")
    )
    keyboard.add(
        InlineKeyboardButton("✅ Завершенные", callback_data="filter_completed"),
        InlineKeyboardButton("❌ Отмененные", callback_data="filter_cancelled")
    )
    keyboard.add(InlineKeyboardButton("📋 Все", callback_data="filter_all"))
    return keyboard


# Inline кнопки для списка заявок
def admin_orders_list(orders: list, page: int = 0, per_page: int = 5):
    keyboard = InlineKeyboardMarkup(row_width=1)

    start = page * per_page
    end = start + per_page

    for order in orders[start:end]:
        status_emoji = {
            'new': '🆕',
            'in_progress': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }
        emoji = status_emoji.get(order['status'], '📋')

        text = f"{emoji} Заявка #{order['order_id']} от {order['first_name']}"
        keyboard.add(InlineKeyboardButton(text, callback_data=f"admin_order_{order['order_id']}"))

    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"page_{page-1}"))
    if end < len(orders):
        nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"page_{page+1}"))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    return keyboard


# Inline кнопки для подтверждения рассылки
def confirm_broadcast():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast_confirm"),
        InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
    )
    return keyboard


# Кнопка возврата в главное меню
def back_to_main():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Главное меню"))
    return keyboard


# Inline кнопки для оценки (звезды)
def rating_buttons(order_id: int):
    keyboard = InlineKeyboardMarkup(row_width=5)
    stars = []
    for i in range(1, 6):
        stars.append(InlineKeyboardButton(f"{'⭐' * i}", callback_data=f"rate_{order_id}_{i}"))
    keyboard.row(*stars)
    return keyboard


# Кнопки для списка заявок пользователя
def user_orders_buttons(orders: list):
    keyboard = InlineKeyboardMarkup(row_width=1)

    status_emoji = {
        'new': '🆕',
        'in_progress': '🔄',
        'completed': '✅',
        'cancelled': '❌'
    }

    for order in orders:
        emoji = status_emoji.get(order['status'], '📋')
        text = f"{emoji} Заявка #{order['order_id']} - {order['status']}"
        keyboard.add(InlineKeyboardButton(text, callback_data=f"view_order_{order['order_id']}"))

    return keyboard
