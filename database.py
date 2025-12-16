import sqlite3
import datetime
from typing import List, Dict, Optional


class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        """Создание подключения к БД"""
        return sqlite3.connect(self.db_name)

    def init_db(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registration_date TEXT,
                is_blocked INTEGER DEFAULT 0
            )
        """)

        # Таблица заявок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT,
                status TEXT DEFAULT 'new',
                created_at TEXT,
                updated_at TEXT,
                admin_comment TEXT,
                budget TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Таблица сообщений (переписка по заявке)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                message_text TEXT,
                is_from_admin INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (order_id) REFERENCES orders (order_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)

        # Таблица отзывов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                order_id INTEGER,
                rating INTEGER,
                comment TEXT,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (order_id) REFERENCES orders (order_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Добавление нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        registration_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registration_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, registration_date))

        conn.commit()
        conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        conn.close()

        if user:
            return {
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'registration_date': user[4],
                'is_blocked': user[5]
            }
        return None

    def create_order(self, user_id: int, description: str, budget: str = "") -> int:
        """Создание новой заявки"""
        conn = self.get_connection()
        cursor = conn.cursor()

        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO orders (user_id, description, status, created_at, updated_at, budget)
            VALUES (?, ?, 'new', ?, ?, ?)
        """, (user_id, description, created_at, created_at, budget))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return order_id

    def get_user_orders(self, user_id: int) -> List[Dict]:
        """Получение всех заявок пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT order_id, description, status, created_at, updated_at, admin_comment, budget
            FROM orders
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))

        orders = cursor.fetchall()
        conn.close()

        result = []
        for order in orders:
            result.append({
                'order_id': order[0],
                'description': order[1],
                'status': order[2],
                'created_at': order[3],
                'updated_at': order[4],
                'admin_comment': order[5],
                'budget': order[6]
            })

        return result

    def get_order(self, order_id: int) -> Optional[Dict]:
        """Получение информации о заявке"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT o.order_id, o.user_id, o.description, o.status, o.created_at,
                   o.updated_at, o.admin_comment, o.budget,
                   u.username, u.first_name, u.last_name
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            WHERE o.order_id = ?
        """, (order_id,))

        order = cursor.fetchone()
        conn.close()

        if order:
            return {
                'order_id': order[0],
                'user_id': order[1],
                'description': order[2],
                'status': order[3],
                'created_at': order[4],
                'updated_at': order[5],
                'admin_comment': order[6],
                'budget': order[7],
                'username': order[8],
                'first_name': order[9],
                'last_name': order[10]
            }
        return None

    def update_order_status(self, order_id: int, status: str, admin_comment: str = ""):
        """Обновление статуса заявки"""
        conn = self.get_connection()
        cursor = conn.cursor()

        updated_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            UPDATE orders
            SET status = ?, admin_comment = ?, updated_at = ?
            WHERE order_id = ?
        """, (status, admin_comment, updated_at, order_id))

        conn.commit()
        conn.close()

    def get_all_orders(self, status: str = None) -> List[Dict]:
        """Получение всех заявок (для админа)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.description, o.status, o.created_at,
                       o.updated_at, o.budget,
                       u.username, u.first_name
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                WHERE o.status = ?
                ORDER BY o.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT o.order_id, o.user_id, o.description, o.status, o.created_at,
                       o.updated_at, o.budget,
                       u.username, u.first_name
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                ORDER BY o.created_at DESC
            """)

        orders = cursor.fetchall()
        conn.close()

        result = []
        for order in orders:
            result.append({
                'order_id': order[0],
                'user_id': order[1],
                'description': order[2],
                'status': order[3],
                'created_at': order[4],
                'updated_at': order[5],
                'budget': order[6],
                'username': order[7],
                'first_name': order[8]
            })

        return result

    def add_message(self, order_id: int, user_id: int, message_text: str, is_from_admin: bool = False):
        """Добавление сообщения в переписку"""
        conn = self.get_connection()
        cursor = conn.cursor()

        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO messages (order_id, user_id, message_text, is_from_admin, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, user_id, message_text, 1 if is_from_admin else 0, created_at))

        conn.commit()
        conn.close()

    def get_order_messages(self, order_id: int) -> List[Dict]:
        """Получение всех сообщений по заявке"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_text, is_from_admin, created_at
            FROM messages
            WHERE order_id = ?
            ORDER BY created_at ASC
        """, (order_id,))

        messages = cursor.fetchall()
        conn.close()

        result = []
        for msg in messages:
            result.append({
                'message_text': msg[0],
                'is_from_admin': msg[1],
                'created_at': msg[2]
            })

        return result

    def add_review(self, user_id: int, order_id: int, rating: int, comment: str):
        """Добавление отзыва"""
        conn = self.get_connection()
        cursor = conn.cursor()

        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO reviews (user_id, order_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, order_id, rating, comment, created_at))

        conn.commit()
        conn.close()

    def get_statistics(self) -> Dict:
        """Получение статистики для админа"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Общее количество пользователей
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        # Общее количество заявок
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]

        # Новые заявки
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'new'")
        new_orders = cursor.fetchone()[0]

        # В работе
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'in_progress'")
        in_progress = cursor.fetchone()[0]

        # Завершенные
        cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
        completed = cursor.fetchone()[0]

        # Средняя оценка
        cursor.execute("SELECT AVG(rating) FROM reviews")
        avg_rating = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'total_users': total_users,
            'total_orders': total_orders,
            'new_orders': new_orders,
            'in_progress': in_progress,
            'completed': completed,
            'avg_rating': round(avg_rating, 2)
        }

    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, first_name, last_name, registration_date
            FROM users
            ORDER BY registration_date DESC
        """)

        users = cursor.fetchall()
        conn.close()

        result = []
        for user in users:
            result.append({
                'user_id': user[0],
                'username': user[1],
                'first_name': user[2],
                'last_name': user[3],
                'registration_date': user[4]
            })

        return result
