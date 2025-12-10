import sys
import os
import sqlite3
from PyQt5.QtWidgets import (QApplication, QWidget, QMessageBox, QTableWidget, 
                             QTableWidgetItem, QVBoxLayout, QPushButton, QLabel,
                             QMainWindow, QHBoxLayout, QHeaderView, QDateEdit,
                             QComboBox, QLineEdit, QFormLayout, QDialog, QTextEdit,
                             QInputDialog, QSplitter, QFrame)
from PyQt5.uic import loadUi
from PyQt5.QtCore import Qt, QDate
from datetime import datetime

# Пути к UI файлам для разных ролей
USER_User = "QtCreator/user.ui"
USER_Manager = "QtCreator/manager.ui"
USER_Master = "QtCreator/master.ui"
USER_Operator = "QtCreator/operator.ui"
DB_PATH = "uchet.db"

def check_database_structure():
    """Проверяет структуру базы данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Проверяем таблицу requests
        cursor.execute("PRAGMA table_info(requests)")
        requests_columns = cursor.fetchall()
        print("=== Структура таблицы requests ===")
        for col in requests_columns:
            print(f"  {col}")
        
        # Проверяем таблицу users
        cursor.execute("PRAGMA table_info(users)")
        users_columns = cursor.fetchall()
        print("=== Структура таблицы users ===")
        for col in users_columns:
            print(f"  {col}")
        
        # Проверяем, есть ли записи в requests
        cursor.execute("SELECT COUNT(*) FROM requests")
        count = cursor.fetchone()[0]
        print(f"Количество записей в requests: {count}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка проверки структуры БД: {e}")

class RequestDialog(QDialog):
    """Диалоговое окно для создания/редактирования заявки"""
    def __init__(self, user_data, parent=None, request_id=None):
        super().__init__(parent)
        self.user_data = user_data
        self.request_id = request_id
        self.conn = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Новая заявка" if not self.request_id else "Редактирование заявки")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Поля формы
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        self.equipment_type = QComboBox()
        self.load_equipment_types()
        
        self.equipment_model = QLineEdit()
        self.problem_desc = QTextEdit()
        self.problem_desc.setMaximumHeight(100)
        
        # Определяем type_id из user_data
        type_id = self.user_data.get('type_id', self.user_data.get('typeID', 0))
        
        # Если это заказчик, заполняем его данные
        if type_id == 4:  # Заказчик
            self.client_name = QLabel(self.user_data['fio'])
            
            # Преобразуем телефон в строку
            phone = self.user_data.get('phone', '')
            phone_str = str(phone) if phone is not None else ''
            self.client_phone = QLabel(phone_str)
        else:
            self.client_name = QLineEdit()
            self.client_phone = QLineEdit()
        
        form_layout.addRow("Тип оборудования:", self.equipment_type)
        form_layout.addRow("Модель:", self.equipment_model)
        form_layout.addRow("Описание проблемы:", self.problem_desc)
        form_layout.addRow("ФИО клиента:", self.client_name)
        form_layout.addRow("Телефон:", self.client_phone)
        
        layout.addWidget(form_widget)
        
        # Кнопки
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        self.save_btn = QPushButton("Сохранить")
        self.cancel_btn = QPushButton("Отмена")
        
        self.save_btn.clicked.connect(self.save_request)
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(buttons_widget)
        
        self.setLayout(layout)
        
        # Если редактируем, загружаем данные
        if self.request_id:
            self.load_request_data()
    
    def closeEvent(self, event):
        """Закрываем соединение при закрытии диалога"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass
        super().closeEvent(event)
    
    def load_equipment_types(self):
        """Загружает типы оборудования из БД"""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT IDorgTechType, orgTechType FROM orgTechTypes ORDER BY orgTechType")
            types = cursor.fetchall()
            conn.close()
            
            for type_id, type_name in types:
                self.equipment_type.addItem(type_name, type_id)
        except Exception as e:
            print(f"❌ Ошибка загрузки типов оборудования: {e}")
            self.equipment_type.addItems(["Компьютер", "Ноутбук", "Принтер"])
    
    def save_request(self):
        """Сохраняет заявку в БД"""
        conn = None
        try:
            # Открываем соединение с таймаутом
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            # Получаем ID пользователя
            user_id = self.user_data.get('id', self.user_data.get('IDuser', 0))
            
            if not self.request_id:  # Новая заявка
                # Сначала пробуем вариант с автоинкрементом (без указания IDrequest)
                try:
                    query = """
                    INSERT INTO requests (startDate, orgTechTypeID, orgTechModel, problemDescryption, 
                                         requestStatusID, clientID)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """
                    values = (
                        datetime.now().strftime("%d.%m.%Y"),
                        self.equipment_type.currentData(),
                        self.equipment_model.text(),
                        self.problem_desc.toPlainText(),
                        3,  # Статус "Новая заявка"
                        user_id if self.user_data.get('type_id', 0) == 4 else None
                    )
                    
                    print(f"Пробуем вставить без IDrequest")
                    cursor.execute(query, values)
                    
                except sqlite3.IntegrityError as e:
                    if "NOT NULL constraint failed: requests.IDrequest" in str(e):
                        print(f"Автоинкремент не настроен, вычисляем следующий ID")
                        # Вычисляем следующий ID
                        cursor.execute("SELECT MAX(IDrequest) FROM requests")
                        max_id = cursor.fetchone()[0]
                        next_id = (max_id or 0) + 1
                        
                        query = """
                        INSERT INTO requests (IDrequest, startDate, orgTechTypeID, orgTechModel, problemDescryption, 
                                             requestStatusID, clientID)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """
                        values = (
                            next_id,
                            datetime.now().strftime("%d.%m.%Y"),
                            self.equipment_type.currentData(),
                            self.equipment_model.text(),
                            self.problem_desc.toPlainText(),
                            3,  # Статус "Новая заявка"
                            user_id if self.user_data.get('type_id', 0) == 4 else None
                        )
                        
                        cursor.execute(query, values)
                    else:
                        # Другая ошибка целостности
                        raise e
            
            conn.commit()
            print(f"Заявка успешно сохранена")
            self.accept()
            
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                QMessageBox.critical(self, "Ошибка", 
                    "База данных заблокирована другим процессом.\nПожалуйста, попробуйте через несколько секунд.")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить заявку: {e}")
        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка целостности данных: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить заявку: {e}")
        finally:
            # Всегда закрываем соединение
            if conn:
                try:
                    cursor.close()
                    conn.close()
                except:
                    pass

class UserWindow(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        
        print(f"🚀 Инициализация UserWindow...")
        print(f"👤 Пользователь: {user_data.get('fio', 'Unknown')}")
        print(f"🏷️ Роль: {user_data.get('type_name', 'Unknown')}")
        
        self.user_data = user_data
        
        # Определяем путь к UI файлу в зависимости от роли
        self.ui_path = self.get_ui_path_for_role()
        print(f"📁 Выбран UI файл: {self.ui_path}")
        
        # Инициализируем атрибуты
        self.table_widget = None
        self.status_label = None
        self.action_button = None
        self.logout_button = None
        self.new_request_btn = None
        self.table_visible = False
        self.table_frame = None
        
        # Создаем интерфейс с таблицей снизу
        self.create_interface_with_bottom_table()
        
        # Устанавливаем заголовок окна
        self.setWindowTitle(f"Учет заявок - {user_data['fio']} ({user_data['type_name']})")
        self.setMinimumSize(1200, 800)
        
        print("✅ UserWindow инициализирован успешно!")
    
    def execute_db_query(self, query, params=None, fetch=False):
        """Безопасное выполнение запроса к БД"""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
                
            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = None
                
            cursor.close()
            return result
            
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                print(f"⚠️ База данных заблокирована: {e}")
                QMessageBox.warning(self, "Ошибка БД", 
                    "База данных временно заблокирована.\nПожалуйста, подождите несколько секунд и попробуйте снова.")
            else:
                print(f"❌ Ошибка БД: {e}")
                QMessageBox.warning(self, "Ошибка БД", f"Ошибка доступа к базе данных: {e}")
            return None
        except Exception as e:
            print(f"❌ Ошибка при выполнении запроса: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def get_role_button_name(self):
        """Возвращает название кнопки в зависимости от роли"""
        role_id = self.user_data.get('type_id', self.user_data.get('typeID', 0))
        
        button_names = {
            1: "📊 Управление заявками",        # Менеджер
            2: "🔧 Мои задания на ремонт",      # Мастер
            3: "📝 Прием новых заявок",         # Оператор
            4: "📋 Мои заявки на ремонт"        # Заказчик
        }
        
        return button_names.get(role_id, "📊 Заявки")
    
    def get_user_type_id(self):
        """Безопасно получает type_id из user_data"""
        return self.user_data.get('type_id', self.user_data.get('typeID', 0))
    
    def get_user_id(self):
        """Безопасно получает ID пользователя"""
        return self.user_data.get('id', self.user_data.get('IDuser', 0))
    
    def get_ui_path_for_role(self):
        """Возвращает путь к UI файлу в зависимости от роли пользователя"""
        role_id = self.get_user_type_id()
        
        ui_map = {
            1: USER_Manager,      # Менеджер
            2: USER_Master,       # Мастер
            3: USER_Operator,     # Оператор
            4: USER_User          # Заказчик
        }
        
        return ui_map.get(role_id, USER_User)
    
    def create_interface_with_bottom_table(self):
        """Создает интерфейс с таблицей внизу для всех пользователей"""
        print("🛠️ Создаю интерфейс с таблицей снизу...")
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной вертикальный layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # === ВЕРХНЯЯ ЧАСТЬ: Панель информации и управления ===
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        top_layout = QVBoxLayout(top_frame)
        top_layout.setSpacing(15)
        
        # Заголовок с информацией о пользователе
        user_info_widget = QWidget()
        user_info_layout = QHBoxLayout(user_info_widget)
        user_info_layout.setContentsMargins(0, 0, 0, 0)
        
        avatar_label = QLabel("👤")
        avatar_label.setStyleSheet("font-size: 24px; padding-right: 10px;")
        
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        user_name = QLabel(self.user_data['fio'])
        user_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        
        role_name = QLabel(f"Роль: {self.user_data['type_name']}")
        role_name.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        
        info_layout.addWidget(user_name)
        info_layout.addWidget(role_name)
        
        user_info_layout.addWidget(avatar_label)
        user_info_layout.addWidget(info_widget)
        user_info_layout.addStretch()
        
        top_layout.addWidget(user_info_widget)
        
        # Разделительная линия
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setStyleSheet("background-color: #dee2e6;")
        top_layout.addWidget(separator1)
        
        # Кнопка главного действия
        self.action_button = QPushButton(self.get_role_button_name())
        self.action_button.setMinimumHeight(50)
        self.action_button.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                background-color: #3498db;
                color: white;
                border-radius: 6px;
                border: none;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1c6ea4;
            }
        """)
        self.action_button.clicked.connect(self.show_role_table)
        top_layout.addWidget(self.action_button)
        
        # Дополнительные кнопки в зависимости от роли
        type_id = self.get_user_type_id()
        if type_id == 3 or type_id == 4:
            btn_text = "➕ Новая заявка" if type_id == 4 else "➕ Принять новую заявку"
            self.new_request_btn = QPushButton(btn_text)
            self.new_request_btn.setMinimumHeight(40)
            self.new_request_btn.setStyleSheet("""
                QPushButton {
                    font-size: 14px;
                    background-color: #27ae60;
                    color: white;
                    border-radius: 6px;
                    border: none;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #219653;
                }
            """)
            self.new_request_btn.clicked.connect(self.create_new_request)
            top_layout.addWidget(self.new_request_btn)
        
        # Разделительная линия
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setStyleSheet("background-color: #dee2e6;")
        top_layout.addWidget(separator2)
        
        # Панель статуса
        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("font-size: 12px; color: #95a5a6; font-style: italic;")
        self.status_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.status_label)
        
        main_layout.addWidget(top_frame)
        
        # === НИЖНЯЯ ЧАСТЬ: Таблица заявок ===
        self.table_frame = QFrame()
        self.table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.table_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)
        
        table_layout = QVBoxLayout(self.table_frame)
        
        # Заголовок таблицы
        table_header = QLabel("📋 Таблица заявок")
        table_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50; padding: 5px;")
        table_header.setAlignment(Qt.AlignCenter)
        table_layout.addWidget(table_header)
        
        # Создаем таблицу
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
                gridline-color: #e9ecef;
                border: none;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: 1px solid #dee2e6;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #e9ecef;
            }
            QTableWidget::item:selected {
                background-color: #d6eaf8;
            }
        """)
        
        table_layout.addWidget(self.table_widget)
        main_layout.addWidget(self.table_frame, 1)  # 1 - коэффициент растяжения
        
        # === КНОПКА ВЫХОДА ===
        logout_widget = QWidget()
        logout_layout = QHBoxLayout(logout_widget)
        logout_layout.setContentsMargins(0, 0, 0, 0)
        
        logout_layout.addStretch()
        self.logout_button = QPushButton("🚪 Выход")
        self.logout_button.setFixedSize(100, 35)
        self.logout_button.setStyleSheet("""
            QPushButton {
                font-size: 13px;
                background-color: #e74c3c;
                color: white;
                border-radius: 5px;
                border: none;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.logout_button.clicked.connect(self.logout)
        logout_layout.addWidget(self.logout_button)
        
        main_layout.addWidget(logout_widget)
        
        # Настраиваем таблицу для текущей роли
        self.setup_role_table()
        
        # Скрываем таблицу при запуске (пока пользователь не нажмет кнопку)
        self.table_frame.setVisible(False)
        self.table_visible = False
    
    def setup_role_table(self):
        """Настраивает таблицу в зависимости от роли пользователя"""
        # Проверяем, что table_widget существует
        if self.table_widget is None:
            print("❌ table_widget is None, создаем...")
            return
            
        role_id = self.get_user_type_id()
        
        if role_id == 1:  # Менеджер
            self.setup_manager_table()
        elif role_id == 2:  # Мастер
            self.setup_master_table()
        elif role_id == 3:  # Оператор
            self.setup_operator_table()
        elif role_id == 4:  # Заказчик
            self.setup_client_table()
        else:
            self.setup_general_table()
    
    def setup_manager_table(self):
        """Настраивает таблицу для менеджера"""
        if self.table_widget is None:
            print("❌ table_widget is None в setup_manager_table")
            return
            
        headers = ["ID", "Дата", "Тип оборудования", "Модель", "Проблема", 
                  "Статус", "Мастер", "Дата завершения", "Запчасти", "Клиент"]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.style_table()
    
    def setup_master_table(self):
        """Настраивает таблицу для мастера"""
        if self.table_widget is None:
            print("❌ table_widget is None в setup_master_table")
            return
            
        headers = ["ID", "Дата", "Тип оборудования", "Модель", "Проблема", 
                  "Статус", "Дата завершения", "Запчасти", "Действия"]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.style_table()
    
    def setup_operator_table(self):
        """Настраивает таблицу для оператора"""
        if self.table_widget is None:
            print("❌ table_widget is None в setup_operator_table")
            return
            
        headers = ["ID", "Дата", "Тип оборудования", "Модель", "Проблема", 
                  "Статус", "Мастер", "Клиент", "Телефон", "Действия"]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.style_table()
    
    def setup_client_table(self):
        """Настраивает таблицу для заказчика"""
        if self.table_widget is None:
            print("❌ table_widget is None в setup_client_table")
            return
            
        headers = ["ID", "Дата", "Тип оборудования", "Модель", "Проблема", 
                  "Статус", "Мастер", "Дата завершения", "Комментарий"]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.style_table()
    
    def setup_general_table(self):
        """Настраивает общую таблицу"""
        if self.table_widget is None:
            print("❌ table_widget is None в setup_general_table")
            return
            
        headers = ["ID", "Дата", "Тип оборудования", "Проблема", "Статус"]
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.style_table()
    
    def style_table(self):
        """Стилизует таблицу"""
        if self.table_widget is None:
            print("❌ table_widget is None в style_table")
            return
            
        header = self.table_widget.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(120)
    
    def show_role_table(self):
        """Показывает/скрывает таблицу заявок"""
        print(f"📋 Загрузка таблицы для роли: {self.user_data['type_name']}")
        
        # Проверяем, что таблица существует
        if self.table_widget is None:
            print("❌ table_widget is None в show_role_table")
            return
            
        if not self.table_visible:
            # Показываем таблицу
            self.table_frame.setVisible(True)
            self.table_visible = True
            
            # Загружаем данные
            try:
                role_id = self.get_user_type_id()
                
                if role_id == 1:  # Менеджер
                    self.load_all_requests()
                elif role_id == 2:  # Мастер
                    self.load_master_requests()
                elif role_id == 3:  # Оператор
                    self.load_operator_requests()
                elif role_id == 4:  # Заказчик
                    self.load_client_requests()
                else:
                    self.load_general_requests()
                    
                if self.action_button:
                    self.action_button.setText("👁️ Скрыть таблицу")
                    
            except Exception as e:
                print(f"❌ Ошибка загрузки таблицы: {e}")
                import traceback
                traceback.print_exc()
        else:
            # Скрываем таблицу
            self.table_frame.setVisible(False)
            self.table_visible = False
            if self.action_button:
                self.action_button.setText(self.get_role_button_name())
    
    def get_user_name(self, user_id):
        """Получает ФИО пользователя по ID"""
        if not user_id:
            return "Не указан"
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT fio FROM users WHERE IDuser = ?", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else "Неизвестно"
        except:
            return "Неизвестно"
        finally:
            if conn:
                conn.close()
    
    def get_tech_type_name(self, type_id):
        """Получает название типа техники по ID"""
        if not type_id:
            return ""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT orgTechType FROM orgTechTypes WHERE IDorgTechType = ?", (type_id,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else str(type_id)
        except:
            return str(type_id)
        finally:
            if conn:
                conn.close()
    
    def get_status_name(self, status_id):
        """Получает название статуса по ID"""
        status_names = {
            1: "В процессе ремонта",
            2: "Готова к выдаче", 
            3: "Новая заявка"
        }
        return status_names.get(status_id, str(status_id))
    
    def get_client_phone(self, client_id):
        """Получает телефон клиента по ID"""
        if not client_id:
            return ""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT phone FROM users WHERE IDuser = ?", (client_id,))
            result = cursor.fetchone()
            cursor.close()
            if result and result[0]:
                return str(result[0])
            else:
                return ""
        except Exception as e:
            print(f"❌ Ошибка получения телефона для ID {client_id}: {e}")
            return ""
        finally:
            if conn:
                conn.close()
    
    def load_all_requests(self):
        """Загружает все заявки для менеджера"""
        if self.table_widget is None:
            print("❌ table_widget is None в load_all_requests")
            return
            
        try:
            query = """
            SELECT r.IDrequest, r.startDate, r.orgTechTypeID, r.orgTechModel, 
                   r.problemDescryption, r.requestStatusID, r.completionDate, 
                   r.repairParts, r.masterID, r.clientID
            FROM requests r
            ORDER BY r.startDate DESC
            """
            
            requests = self.execute_db_query(query, fetch=True)
            
            if requests is None:
                self.table_widget.setRowCount(0)
                if self.status_label:
                    self.status_label.setText("Не удалось загрузить данные")
                return
            
            self.table_widget.setRowCount(len(requests))
            
            for row, request in enumerate(requests):
                # ID
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(request[0])))
                # Дата
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(request[1])))
                # Тип оборудования
                type_name = self.get_tech_type_name(request[2])
                self.table_widget.setItem(row, 2, QTableWidgetItem(type_name))
                # Модель
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(request[3])))
                # Проблема
                self.table_widget.setItem(row, 4, QTableWidgetItem(str(request[4])))
                # Статус
                status_name = self.get_status_name(request[5])
                self.table_widget.setItem(row, 5, QTableWidgetItem(status_name))
                # Мастер
                master_name = self.get_user_name(request[8])
                self.table_widget.setItem(row, 6, QTableWidgetItem(master_name))
                # Дата завершения
                self.table_widget.setItem(row, 7, QTableWidgetItem(str(request[6] if request[6] else "")))
                # Запчасти
                self.table_widget.setItem(row, 8, QTableWidgetItem(str(request[7] if request[7] else "")))
                # Клиент
                client_name = self.get_user_name(request[9])
                self.table_widget.setItem(row, 9, QTableWidgetItem(client_name))
        
            self.table_widget.resizeColumnsToContents()
            if self.status_label:
                self.status_label.setText(f"Загружено записей: {len(requests)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки всех заявок: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {e}")
    
    def load_master_requests(self):
        """Загружает заявки для мастера"""
        if self.table_widget is None:
            print("❌ table_widget is None в load_master_requests")
            return
            
        try:
            user_id = self.get_user_id()
            
            query = """
            SELECT r.IDrequest, r.startDate, r.orgTechTypeID, r.orgTechModel,
                   r.problemDescryption, r.requestStatusID, r.completionDate, r.repairParts
            FROM requests r
            WHERE r.masterID = ?
            ORDER BY r.startDate DESC
            """
            
            requests = self.execute_db_query(query, (user_id,), fetch=True)
            
            if requests is None:
                self.table_widget.setRowCount(0)
                if self.status_label:
                    self.status_label.setText("Не удалось загрузить данные")
                return
            
            self.table_widget.setRowCount(len(requests))
            
            for row, request in enumerate(requests):
                # ID
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(request[0])))
                # Дата
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(request[1])))
                # Тип оборудования
                type_name = self.get_tech_type_name(request[2])
                self.table_widget.setItem(row, 2, QTableWidgetItem(type_name))
                # Модель
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(request[3])))
                # Проблема
                self.table_widget.setItem(row, 4, QTableWidgetItem(str(request[4])))
                # Статус
                status_name = self.get_status_name(request[5])
                self.table_widget.setItem(row, 5, QTableWidgetItem(status_name))
                # Дата завершения
                self.table_widget.setItem(row, 6, QTableWidgetItem(str(request[6] if request[6] else "")))
                # Запчасти
                self.table_widget.setItem(row, 7, QTableWidgetItem(str(request[7] if request[7] else "")))
                
                # Кнопка действий
                action_btn = QPushButton("Изменить")
                action_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f39c12;
                        color: white;
                        border-radius: 4px;
                        padding: 3px 8px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #e67e22;
                    }
                """)
                action_btn.clicked.connect(lambda checked, req_id=request[0]: self.change_request_status(req_id))
                self.table_widget.setCellWidget(row, 8, action_btn)
            
            self.table_widget.resizeColumnsToContents()
            if self.status_label:
                self.status_label.setText(f"Загружено заданий: {len(requests)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки заявок мастера: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {e}")
    
    def load_operator_requests(self):
        """Загружает заявки для оператора"""
        if self.table_widget is None:
            print("❌ table_widget is None в load_operator_requests")
            return
            
        try:
            query = """
            SELECT r.IDrequest, r.startDate, r.orgTechTypeID, r.orgTechModel,
                   r.problemDescryption, r.requestStatusID, r.masterID, r.clientID
            FROM requests r
            ORDER BY r.startDate DESC
            """
            
            requests = self.execute_db_query(query, fetch=True)
            
            if requests is None:
                self.table_widget.setRowCount(0)
                if self.status_label:
                    self.status_label.setText("Не удалось загрузить данные")
                return
            
            print(f"📊 Найдено заявок: {len(requests)}")
            
            self.table_widget.setRowCount(len(requests))
            
            # Проверяем количество столбцов
            column_count = self.table_widget.columnCount()
            print(f"📊 Количество столбцов в таблице: {column_count}")
            
            for row, request in enumerate(requests):
                # ID (колонка 0)
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(request[0])))
                
                # Дата (колонка 1)
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(request[1])))
                
                # Тип оборудования (колонка 2)
                type_name = self.get_tech_type_name(request[2])
                self.table_widget.setItem(row, 2, QTableWidgetItem(type_name))
                
                # Модель (колонка 3)
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(request[3])))
                
                # Проблема (колонка 4)
                self.table_widget.setItem(row, 4, QTableWidgetItem(str(request[4])))
                
                # Статус (колонка 5)
                status_name = self.get_status_name(request[5])
                self.table_widget.setItem(row, 5, QTableWidgetItem(status_name))
                
                # Мастер (колонка 6)
                master_name = self.get_user_name(request[6])
                self.table_widget.setItem(row, 6, QTableWidgetItem(master_name))
                
                # Клиент (колонка 7)
                client_name = self.get_user_name(request[7])
                self.table_widget.setItem(row, 7, QTableWidgetItem(client_name))
                
                # Телефон клиента (колонка 8)
                client_phone = self.get_client_phone(request[7])
                print(f"Телефон для клиента ID={request[7]}: '{client_phone}'")
                
                # Создаем QTableWidgetItem с телефоном
                phone_item = QTableWidgetItem(str(client_phone) if client_phone else "")
                self.table_widget.setItem(row, 8, phone_item)
                
                # Кнопка действий (колонка 9)
                if column_count > 9:  # Проверяем, есть ли 10-я колонка
                    action_btn = QPushButton("Назначить")
                    action_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #9b59b6;
                            color: white;
                            border-radius: 4px;
                            padding: 3px 8px;
                            font-size: 11px;
                        }
                        QPushButton:hover {
                            background-color: #8e44ad;
                        }
                    """)
                    action_btn.clicked.connect(lambda checked, req_id=request[0]: self.assign_master(req_id))
                    self.table_widget.setCellWidget(row, 9, action_btn)
                else:
                    print(f"⚠️ Нет 10-й колонки для кнопки действий")
            
            self.table_widget.resizeColumnsToContents()
            if self.status_label:
                self.status_label.setText(f"Загружено заявок: {len(requests)}")
            
        except Exception as e:
            print(f"❌ Ошибка в load_operator_requests: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить заявки: {e}")
    
    def load_client_requests(self):
        """Загружает заявки для заказчика"""
        if self.table_widget is None:
            print("❌ table_widget is None в load_client_requests")
            return
            
        try:
            user_id = self.get_user_id()
            
            query = """
            SELECT r.IDrequest, r.startDate, r.orgTechTypeID, r.orgTechModel,
                   r.problemDescryption, r.requestStatusID, r.masterID, r.completionDate
            FROM requests r
            WHERE r.clientID = ?
            ORDER BY r.startDate DESC
            """
            
            requests = self.execute_db_query(query, (user_id,), fetch=True)
            
            if requests is None:
                self.table_widget.setRowCount(0)
                if self.status_label:
                    self.status_label.setText("Не удалось загрузить данные")
                return
            
            self.table_widget.setRowCount(len(requests))
            
            for row, request in enumerate(requests):
                # ID
                self.table_widget.setItem(row, 0, QTableWidgetItem(str(request[0])))
                # Дата
                self.table_widget.setItem(row, 1, QTableWidgetItem(str(request[1])))
                # Тип оборудования
                type_name = self.get_tech_type_name(request[2])
                self.table_widget.setItem(row, 2, QTableWidgetItem(type_name))
                # Модель
                self.table_widget.setItem(row, 3, QTableWidgetItem(str(request[3])))
                # Проблема
                self.table_widget.setItem(row, 4, QTableWidgetItem(str(request[4])))
                # Статус
                status_name = self.get_status_name(request[5])
                self.table_widget.setItem(row, 5, QTableWidgetItem(status_name))
                # Мастер
                master_name = self.get_user_name(request[6])
                self.table_widget.setItem(row, 6, QTableWidgetItem(master_name))
                # Дата завершения
                self.table_widget.setItem(row, 7, QTableWidgetItem(str(request[7] if request[7] else "")))
                
                # Комментарии
                comments = self.get_request_comments(request[0])
                self.table_widget.setItem(row, 8, QTableWidgetItem(comments))
            
            self.table_widget.resizeColumnsToContents()
            if self.status_label:
                self.status_label.setText(f"Загружено ваших заявок: {len(requests)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки заявок клиента: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {e}")
    
    def get_request_comments(self, request_id):
        """Получает комментарии к заявке"""
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT message FROM comments WHERE requestID = ?", (request_id,))
            comments = cursor.fetchall()
            cursor.close()
            
            if comments:
                return "; ".join([c[0] for c in comments])
            return "Нет комментариев"
        except:
            return "Нет комментариев"
        finally:
            if conn:
                conn.close()
    
    def load_general_requests(self):
        """Загружает общие заявки"""
        if self.table_widget is None:
            print("❌ table_widget is None в load_general_requests")
            return
            
        try:
            query = """
            SELECT IDrequest, startDate, orgTechTypeID, problemDescryption, requestStatusID
            FROM requests
            ORDER BY startDate DESC
            LIMIT 50
            """
            
            requests = self.execute_db_query(query, fetch=True)
            
            if requests is None:
                self.table_widget.setRowCount(0)
                if self.status_label:
                    self.status_label.setText("Не удалось загрузить данные")
                return
            
            self.table_widget.setRowCount(len(requests))
            
            for row, request in enumerate(requests):
                for col, value in enumerate(request):
                    if col == 2:  # Тип оборудования
                        value = self.get_tech_type_name(value)
                    elif col == 4:  # Статус
                        value = self.get_status_name(value)
                    
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.table_widget.setItem(row, col, item)
            
            self.table_widget.resizeColumnsToContents()
            if self.status_label:
                self.status_label.setText(f"Загружено записей: {len(requests)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки общих заявок: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {e}")
    
    def change_request_status(self, request_id):
        """Изменяет статус заявки (для мастера)"""
        statuses = ["В процессе ремонта", "Готова к выдаче", "Новая заявка"]
        status, ok = QInputDialog.getItem(self, "Изменение статуса", 
                                         "Выберите новый статус:", statuses, 0, False)
        
        if ok and status:
            try:
                # Находим ID статуса
                status_id = statuses.index(status) + 1
                
                query = "UPDATE requests SET requestStatusID = ? WHERE IDrequest = ?"
                
                # Если статус "Готова к выдаче", ставим дату завершения
                if status_id == 2:
                    query = """
                    UPDATE requests 
                    SET requestStatusID = ?, completionDate = ?
                    WHERE IDrequest = ?
                    """
                    result = self.execute_db_query(query, (status_id, datetime.now().strftime("%d.%m.%Y"), request_id))
                else:
                    result = self.execute_db_query(query, (status_id, request_id))
                
                if result is None:
                    QMessageBox.warning(self, "Ошибка", "Не удалось обновить статус")
                else:
                    QMessageBox.information(self, "Успех", "Статус обновлен!")
                    self.show_role_table()  # Обновляем таблицу
                
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось обновить статус: {e}")
    
    def assign_master(self, request_id):
        """Назначает мастера на заявку (для оператора)"""
        # Получаем список мастеров
        try:
            query = "SELECT IDuser, fio FROM users WHERE typeID = 2"
            masters = self.execute_db_query(query, fetch=True)
            
            if masters is None:
                QMessageBox.warning(self, "Предупреждение", "Нет доступных мастеров")
                return
            
            master_names = [f"{m[0]} - {m[1]}" for m in masters]
            master_name, ok = QInputDialog.getItem(self, "Назначение мастера", 
                                                  "Выберите мастера:", master_names, 0, False)
            
            if ok and master_name:
                master_id = int(master_name.split(" - ")[0])
                
                query = "UPDATE requests SET masterID = ?, requestStatusID = 1 WHERE IDrequest = ?"
                result = self.execute_db_query(query, (master_id, request_id))
                
                if result is None:
                    QMessageBox.warning(self, "Ошибка", "Не удалось назначить мастера")
                else:
                    QMessageBox.information(self, "Успех", "Мастер назначен!")
                    self.show_role_table()  # Обновляем таблицу
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось назначить мастера: {e}")
    
    def create_new_request(self):
        """Создает новую заявку"""
        dialog = RequestDialog(self.user_data, self)
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, "Успех", "Заявка создана!")
            self.show_role_table()  # Обновляем таблицу
    
    def logout(self):
        """Выход из системы"""
        reply = QMessageBox.question(
            self, "Выход",
            "Вы уверены, что хотите выйти из системы?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print("🚪 Выход из системы...")
            self.close()

if __name__ == "__main__":
    # Сначала проверяем структуру БД
    check_database_structure()
    
    # Тестирование
    app = QApplication(sys.argv)
    
    test_user = {
        'id': 2,
        'IDuser': 2,
        'fio': 'Ильин Александр Андреевич',
        'type_id': 2,
        'type_name': 'Мастер',
        'phone': '89535078985'
    }
    
    window = UserWindow(test_user)
    window.show()
    sys.exit(app.exec_())