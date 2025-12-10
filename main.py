import sys
import os
import sqlite3
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox, QLineEdit, QPushButton, QLabel
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt

# Импортируем UserWindow из user_window.py
from user_window import UserWindow

# Путь к UI файлу приветственного экрана
WELCOME_UI = "QtCreator/welcomescreen.ui"
DB_PATH = "uchet.db"

class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.user_window = None  # Ссылка на окно пользователя
        
        print(f"🔧 Инициализация AuthWindow...")
        
        # Загружаем UI файл
        print(f"✅ Загружаю UI файл: {WELCOME_UI}")
        loadUi(WELCOME_UI, self)
        print("✅ UI файл загружен успешно")
        
        # Настраиваем интерфейс
        self.init_ui()
        
        self.setWindowTitle("Авторизация - Учет заявок на ремонт")
        self.setFixedSize(800, 600)
        
        print("✅ AuthWindow создан")
    
    def init_ui(self):
        """Инициализирует интерфейс"""
        print("🔧 Настройка интерфейса...")
        
        # Находим элементы
        self.login_input = self.findChild(QLineEdit, 'login_input')
        self.password_input = self.findChild(QLineEdit, 'password_input')
        self.login_button = self.findChild(QPushButton, 'LoginButton')
        self.error_label = self.findChild(QLabel, 'error_label')
        
        print(f"📝 Найдены элементы:")
        print(f"  login_input: {'Найден' if self.login_input else 'Не найден'}")
        print(f"  password_input: {'Найден' if self.password_input else 'Не найден'}")
        print(f"  LoginButton: {'Найден' if self.login_button else 'Не найден'}")
        print(f"  error_label: {'Найден' if self.error_label else 'Не найден'}")
        
        # Подключаем обработчик к кнопке
        if self.login_button:
            print(f"✅ Подключаю обработчик к кнопке: '{self.login_button.text()}'")
            self.login_button.clicked.connect(self.authenticate)
        else:
            print("❌ Кнопка входа не найдена!")
            
            # Пытаемся найти кнопку другим способом
            all_buttons = self.findChildren(QPushButton)
            print(f"🔍 Поиск всех кнопок: найдено {len(all_buttons)}")
            for i, btn in enumerate(all_buttons):
                print(f"  {i}: name='{btn.objectName()}', text='{btn.text()}'")
            
            if all_buttons:
                self.login_button = all_buttons[0]
                print(f"✅ Использую первую найденную кнопку: '{self.login_button.text()}'")
                self.login_button.clicked.connect(self.authenticate)
        
        # Устанавливаем фокус на поле логина
        if self.login_input:
            self.login_input.setFocus()
            print("✅ Фокус установлен на поле логина")
        
        print("✅ Интерфейс настроен")
    
    def authenticate(self):
        """Аутентификация пользователя"""
        print("=" * 50)
        print("🔐 НАЖАТА КНОПКА ВХОДА!")
        print("=" * 50)
        
        # Получаем значения из полей ввода
        login = self.login_input.text().strip() if self.login_input else ""
        password = self.password_input.text().strip() if self.password_input else ""
        
        print(f"📝 Логин: '{login}'")
        print(f"🔒 Пароль: '{'*' * len(password)}' (длина: {len(password)})")
        
        if not login:
            print("⚠️ Логин не введен")
            self.show_error('⚠️ Введите логин')
            return
        
        if not password:
            print("⚠️ Пароль не введен")
            self.show_error('⚠️ Введите пароль')
            return
        
        try:
            print("🔍 Проверка подключения к базе данных...")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Проверяем существует ли таблица users
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                print("❌ Таблица 'users' не найдена в базе данных")
                self.show_error('❌ Таблица пользователей не найдена')
                conn.close()
                return
            
            # ДОПОЛНИТЕЛЬНО: Проверяем структуру таблицы users
            cursor.execute("PRAGMA table_info(users)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            cursor.execute("""
                SELECT IDuser, fio, login, phone, typeID
                FROM users
                WHERE login = ? AND password = ?
            """, (login, password))
            
            user = cursor.fetchone()
            conn.close()
            
            if user:
                # Преобразуем результат в словарь
                user_data = {
                    'id': user[0],           # IDuser
                    'fio': user[1],          # fio
                    'login': user[2],        # login
                    'phone': user[3],        # phone
                    'type_id': user[4],      # typeID
                    # Добавляем название типа на основе номера
                    'type_name': self.get_type_name(user[4])
                }
                
                print(f"✅ Успешный вход:")
                print(f"  ID: {user_data['id']}")
                print(f"  ФИО: {user_data['fio']}")
                print(f"  Логин: {user_data['login']}")
                print(f"  Телефон: {user_data['phone']}")
                print(f"  Тип: {user_data['type_id']} - {user_data['type_name']}")
                
                self.show_error('')  # Очищаем ошибки
                
                # Закрываем окно авторизации
                print("🚪 Закрываю окно авторизации...")
                self.close()
                
                # Открываем главное окно пользователя
                self.open_user_window(user_data)
                
            else:
                print("❌ Неверный логин или пароль")
                self.show_error('❌ Неверный логин или пароль')
                
        except sqlite3.Error as e:
            error_msg = f'❌ Ошибка базы данных: {str(e)}'
            print(error_msg)
            self.show_error(error_msg)
        except Exception as e:
            error_msg = f'❌ Ошибка при авторизации: {str(e)}'
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.show_error('❌ Ошибка при авторизации')
    
    def get_type_name(self, type_id):
        """Возвращает название типа пользователя по его ID"""
        type_names = {
            1: "Менеджер",
            2: "Мастер",
            3: "Оператор",
            4: "Заказчик"
        }
        return type_names.get(type_id, f"Тип {type_id}")
    
    def show_error(self, message):
        """Показывает сообщение об ошибке"""
        print(f"🚨 Ошибка: {message}")
        if self.error_label:
            self.error_label.setText(message)
        else:
            # Если label не найден, показываем через QMessageBox
            if message:
                QMessageBox.warning(self, "Ошибка", message)
    
    def open_user_window(self, user_data):
        """Открывает главное окно пользователя"""
        print(f"🚀 Открываю главное окно для пользователя {user_data['fio']}")
        
        # Создаем и показываем окно пользователя
        self.user_window = UserWindow(user_data)
        self.user_window.show()

def main():
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль приложения
    app.setStyle('Fusion')
    
    print("🚀 Запуск приложения...")
    
    # Создаем и показываем окно авторизации
    auth_window = AuthWindow()
    auth_window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()