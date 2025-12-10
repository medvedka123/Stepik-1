import sqlite3
from typing import Optional, Dict, Any
from contextlib import contextmanager


@contextmanager
def get_db_connection():
    """Контекстный менеджер для подключения к БД"""
    conn = sqlite3.connect('uchet.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    """Простой класс для работы с БД"""
    
    @staticmethod
    def get_user_by_credentials(login: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по логину и паролю.
        Проверяет точное совпадение.
        """
        login = login.strip()
        password = password.strip()
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # Ищем точное совпадение логина и пароля
                cursor.execute(
                    "SELECT * FROM users WHERE login = ? AND password = ?",
                    (login, password)
                )
                user = cursor.fetchone()
                
                if user:
                    return dict(user)
                else:
                    # Пробуем найти без учета пробелов
                    cursor.execute(
                        "SELECT * FROM users WHERE TRIM(login) = ? AND TRIM(password) = ?",
                        (login, password)
                    )
                    user = cursor.fetchone()
                    
                    if user:
                        return dict(user)
                    
                return None
                
        except sqlite3.Error as e:
            print(f"❌ Ошибка БД: {e}")
            return None
    
    @staticmethod
    def get_all_users() -> list:
        """Получает всех пользователей"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY IDuser")
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"❌ Ошибка БД: {e}")
            return []
    
    @staticmethod
    def get_user_type_name(type_id: int) -> str:
        """Получает название типа пользователя"""
        type_mapping = {
            1: "Менеджер",
            2: "Мастер",
            3: "Оператор",
            4: "Заказчик"
        }
        return type_mapping.get(type_id, f"Тип {type_id}")