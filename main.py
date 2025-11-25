import sys
import pymysql
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QComboBox,
                             QTextEdit, QMessageBox, QHeaderView, QDialog,
                             QFormLayout, QDialogButtonBox, QStackedWidget)
from PyQt6.QtCore import Qt
import hashlib


class LoginWindow(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Авторизация менеджера")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Вход в систему управления партнерами")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Форма авторизации
        form_layout = QFormLayout()

        self.login_edit = QLineEdit()
        self.login_edit.setPlaceholderText("Введите логин")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Введите пароль")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        form_layout.addRow("Логин:", self.login_edit)
        form_layout.addRow("Пароль:", self.password_edit)

        layout.addLayout(form_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self.authenticate)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(login_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def authenticate(self):
        login = self.login_edit.text().strip()
        password = self.password_edit.text().strip()

        if not login or not password:
            QMessageBox.warning(self, "Ошибка", "Введите логин и пароль")
            return

        # Хешируем пароль для проверки
        password_hash = hashlib.md5(password.encode()).hexdigest()

        conn = self.db_manager.get_connection()
        if not conn:
            QMessageBox.critical(self, "Ошибка", "Ошибка подключения к базе данных")
            return

        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT id_manager, login, full_name, role 
                    FROM managers 
                    WHERE login = %s AND password_hash = %s AND is_active = TRUE
                ''', (login, password_hash))
                manager = cursor.fetchone()

                if manager:
                    self.manager_data = manager
                    self.accept()
                else:
                    QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")
        except pymysql.Error as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка базы данных: {e}")
        finally:
            conn.close()


class DatabaseManager:
    def __init__(self):
        self.host = "localhost"
        self.user = "root"
        self.password = "root"
        self.database = "vcxvxcvxc"
        self.port = 3306

    def get_connection(self):
        try:
            connection = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return connection
        except pymysql.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
            return None

    def get_all_partners(self):
        conn = self.get_connection()
        if not conn:
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    SELECT p.id_partner, p.name_partner, tp.type_name, p.director, 
                           p.email, p.phone_number, p.legal_address, p.inn, 
                           p.current_rating, p.logo
                    FROM partners p
                    LEFT JOIN type_partners tp ON p.id_type_partner = tp.id_type_partner
                    ORDER BY p.name_partner
                ''')
                partners = cursor.fetchall()
            return partners
        except pymysql.Error as e:
            print(f"Ошибка при получении партнеров: {e}")
            return []
        finally:
            conn.close()

    def get_partner_types(self):
        conn = self.get_connection()
        if not conn:
            return []

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id_type_partner, type_name FROM type_partners")
                types = cursor.fetchall()
            return types
        except pymysql.Error as e:
            print(f"Ошибка при получении типов партнеров: {e}")
            return []
        finally:
            conn.close()

    def add_partner(self, name, type_id, director, email, phone, address, inn, rating):
        conn = self.get_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    INSERT INTO partners 
                    (name_partner, id_type_partner, director, email, phone_number, 
                     legal_address, inn, current_rating)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (name, type_id, director, email, phone, address, inn, rating))
                conn.commit()
            return True
        except pymysql.Error as e:
            print(f"Ошибка при добавлении партнера: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def update_partner(self, partner_id, name, type_id, director, email,
                       phone, address, inn, rating):
        conn = self.get_connection()
        if not conn:
            return False

        try:
            with conn.cursor() as cursor:
                cursor.execute('''
                    UPDATE partners 
                    SET name_partner=%s, id_type_partner=%s, director=%s, email=%s,
                        phone_number=%s, legal_address=%s, inn=%s, current_rating=%s
                    WHERE id_partner=%s
                ''', (name, type_id, director, email, phone, address, inn, rating, partner_id))
                conn.commit()
            return True
        except pymysql.Error as e:
            print(f"Ошибка при обновлении партнера: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_partner_sales_stats(self, partner_id):
        """Получить статистику продаж для партнера"""
        conn = self.get_connection()
        if not conn:
            return {}

        try:
            with conn.cursor() as cursor:
                # Общий объем продаж
                cursor.execute('''
                    SELECT SUM(sh.amount_product) as total_quantity,
                           SUM(sh.total_sale_amount) as total_amount
                    FROM sales_history sh
                    WHERE sh.id_partner = %s
                ''', (partner_id,))
                total_stats = cursor.fetchone()

                # Продажи по продуктам
                cursor.execute('''
                    SELECT p.name_product, SUM(sh.amount_product) as quantity,
                           SUM(sh.total_sale_amount) as amount
                    FROM sales_history sh
                    JOIN products p ON sh.id_product = p.id_product
                    WHERE sh.id_partner = %s
                    GROUP BY p.id_product, p.name_product
                    ORDER BY amount DESC
                ''', (partner_id,))
                product_stats = cursor.fetchall()

                return {
                    'total_quantity': total_stats['total_quantity'] or 0,
                    'total_amount': total_stats['total_amount'] or 0,
                    'products': product_stats
                }
        except pymysql.Error as e:
            print(f"Ошибка при получении статистики: {e}")
            return {}
        finally:
            conn.close()


class PartnerAddDialog(QDialog):
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Добавление нового партнера")
        self.setModal(True)
        self.resize(500, 400)

        layout = QFormLayout()

        # Поля формы
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.director_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(80)
        self.inn_edit = QLineEdit()
        self.rating_edit = QLineEdit()
        self.rating_edit.setText("5")

        # Заполняем комбобокс типами партнеров
        partner_types = self.db_manager.get_partner_types()
        for type_data in partner_types:
            self.type_combo.addItem(type_data['type_name'], type_data['id_type_partner'])

        # Добавляем поля в форму
        layout.addRow("Наименование партнера*:", self.name_edit)
        layout.addRow("Тип партнера*:", self.type_combo)
        layout.addRow("Директор*:", self.director_edit)
        layout.addRow("Электронная почта*:", self.email_edit)
        layout.addRow("Телефон*:", self.phone_edit)
        layout.addRow("Юридический адрес*:", self.address_edit)
        layout.addRow("ИНН*:", self.inn_edit)
        layout.addRow("Рейтинг*:", self.rating_edit)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(QLabel("* - обязательные поля"))
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def validate_and_accept(self):
        """Проверка заполнения обязательных полей"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите наименование партнера")
            return

        if not self.director_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО директора")
            return

        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите электронную почту")
            return

        if not self.inn_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ИНН")
            return

        try:
            rating = int(self.rating_edit.text())
            if rating < 1 or rating > 10:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Рейтинг должен быть числом от 1 до 10")
            return

        self.accept()

    def get_partner_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'type_id': self.type_combo.currentData(),
            'director': self.director_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'address': self.address_edit.toPlainText().strip(),
            'inn': self.inn_edit.text().strip(),
            'rating': int(self.rating_edit.text())
        }


class PartnerEditDialog(QDialog):
    def __init__(self, partner_data=None, db_manager=None, parent=None):
        super().__init__(parent)
        self.partner_data = partner_data
        self.db_manager = db_manager
        self.partner_id = partner_data['id_partner'] if partner_data else None
        self.setup_ui()

        if partner_data:
            self.load_partner_data()

    def setup_ui(self):
        self.setWindowTitle("Редактирование партнера")
        self.setModal(True)
        self.resize(500, 400)

        layout = QFormLayout()

        # Поля формы
        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.director_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(80)
        self.inn_edit = QLineEdit()
        self.rating_edit = QLineEdit()

        # Заполняем комбобокс типами партнеров
        partner_types = self.db_manager.get_partner_types()
        for type_data in partner_types:
            self.type_combo.addItem(type_data['type_name'], type_data['id_type_partner'])

        # Добавляем поля в форму
        layout.addRow("Наименование партнера*:", self.name_edit)
        layout.addRow("Тип партнера*:", self.type_combo)
        layout.addRow("Директор*:", self.director_edit)
        layout.addRow("Электронная почта*:", self.email_edit)
        layout.addRow("Телефон*:", self.phone_edit)
        layout.addRow("Юридический адрес*:", self.address_edit)
        layout.addRow("ИНН*:", self.inn_edit)
        layout.addRow("Рейтинг*:", self.rating_edit)

        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                      QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addWidget(QLabel("* - обязательные поля"))
        main_layout.addWidget(button_box)

        self.setLayout(main_layout)

    def load_partner_data(self):
        if self.partner_data:
            self.name_edit.setText(self.partner_data['name_partner'])
            # Устанавливаем правильный тип партнера в комбобоксе
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == self.partner_data.get('id_type_partner'):
                    self.type_combo.setCurrentIndex(i)
                    break
            self.director_edit.setText(self.partner_data['director'])
            self.email_edit.setText(self.partner_data['email'])
            self.phone_edit.setText(self.partner_data['phone_number'])
            self.address_edit.setText(self.partner_data['legal_address'])
            self.inn_edit.setText(self.partner_data['inn'])
            self.rating_edit.setText(str(self.partner_data['current_rating']))

    def validate_and_accept(self):
        """Проверка заполнения обязательных полей"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите наименование партнера")
            return

        if not self.director_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ФИО директора")
            return

        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите электронную почту")
            return

        if not self.inn_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите ИНН")
            return

        try:
            rating = int(self.rating_edit.text())
            if rating < 1 or rating > 10:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Рейтинг должен быть числом от 1 до 10")
            return

        self.accept()

    def get_updated_data(self):
        return {
            'name': self.name_edit.text().strip(),
            'type_id': self.type_combo.currentData(),
            'director': self.director_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'address': self.address_edit.toPlainText().strip(),
            'inn': self.inn_edit.text().strip(),
            'rating': int(self.rating_edit.text())
        }


class PartnerDetailDialog(QDialog):
    def __init__(self, partner_data, db_manager, parent=None):
        super().__init__(parent)
        self.partner_data = partner_data
        self.db_manager = db_manager
        self.setup_ui()
        self.load_partner_details()

    def setup_ui(self):
        self.setWindowTitle(f"Детальная информация: {self.partner_data['name_partner']}")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Основная информация
        info_group = QWidget()
        info_layout = QFormLayout(info_group)

        self.name_label = QLabel(self.partner_data['name_partner'])
        self.type_label = QLabel(self.partner_data['type_name'])
        self.director_label = QLabel(self.partner_data['director'])
        self.email_label = QLabel(self.partner_data['email'])
        self.phone_label = QLabel(self.partner_data['phone_number'])
        self.address_label = QLabel(self.partner_data['legal_address'])
        self.inn_label = QLabel(self.partner_data['inn'])
        self.rating_label = QLabel(str(self.partner_data['current_rating']))

        info_layout.addRow("Наименование:", self.name_label)
        info_layout.addRow("Тип партнера:", self.type_label)
        info_layout.addRow("Директор:", self.director_label)
        info_layout.addRow("Электронная почта:", self.email_label)
        info_layout.addRow("Телефон:", self.phone_label)
        info_layout.addRow("Юридический адрес:", self.address_label)
        info_layout.addRow("ИНН:", self.inn_label)
        info_layout.addRow("Рейтинг:", self.rating_label)

        # Статистика продаж
        stats_group = QWidget()
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.addWidget(QLabel("<b>Статистика продаж:</b>"))

        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(["Продукция", "Количество", "Сумма"])
        stats_layout.addWidget(self.stats_table)

        layout.addWidget(info_group)
        layout.addWidget(stats_group)

        # Кнопки
        button_layout = QHBoxLayout()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_partner_details(self):
        stats = self.db_manager.get_partner_sales_stats(self.partner_data['id_partner'])

        if stats:
            total_quantity = stats['total_quantity']
            total_amount = stats['total_amount']

            # Добавляем итоговую строку
            self.stats_table.setRowCount(len(stats['products']) + 1)

            # Заполняем данные по продуктам
            for row, product in enumerate(stats['products']):
                self.stats_table.setItem(row, 0, QTableWidgetItem(product['name_product']))
                self.stats_table.setItem(row, 1, QTableWidgetItem(str(product['quantity'])))
                self.stats_table.setItem(row, 2, QTableWidgetItem(f"{product['amount']:,.2f} руб."))

            # Итоговая строка
            self.stats_table.setItem(len(stats['products']), 0, QTableWidgetItem("ВСЕГО:"))
            self.stats_table.setItem(len(stats['products']), 1, QTableWidgetItem(str(total_quantity)))
            self.stats_table.setItem(len(stats['products']), 2, QTableWidgetItem(f"{total_amount:,.2f} руб."))

            self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


class PartnersViewWindow(QMainWindow):
    def __init__(self, manager_data):
        super().__init__()
        self.manager_data = manager_data
        self.db_manager = DatabaseManager()
        self.setup_ui()
        self.load_partners()

    def setup_ui(self):
        self.setWindowTitle(
            f"Система управления партнерами - Производственная компания 'Мастер пол' (Менеджер: {self.manager_data['full_name']})")
        self.setGeometry(100, 100, 1200, 700)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        layout = QVBoxLayout(central_widget)

        # Заголовок и информация о менеджере
        header_layout = QHBoxLayout()

        title_label = QLabel("Список партнеров")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")

        manager_label = QLabel(f"Менеджер: {self.manager_data['full_name']} ({self.manager_data['role']})")
        manager_label.setStyleSheet("color: gray;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(manager_label)

        layout.addLayout(header_layout)

        # Панель кнопок
        button_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_partners)

        self.add_btn = QPushButton("Добавить партнера")
        self.add_btn.clicked.connect(self.add_partner)

        button_layout.addWidget(self.refresh_btn)
        button_layout.addWidget(self.add_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Таблица партнеров
        self.partners_table = QTableWidget()
        self.partners_table.setColumnCount(8)
        self.partners_table.setHorizontalHeaderLabels([
            "ID", "Наименование", "Тип", "Директор", "Email",
            "Телефон", "Рейтинг", "Действия"
        ])

        self.partners_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.partners_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.partners_table)

    def load_partners(self):
        partners = self.db_manager.get_all_partners()
        self.partners_table.setRowCount(len(partners))

        for row, partner in enumerate(partners):
            # Заполняем данные
            self.partners_table.setItem(row, 0, QTableWidgetItem(str(partner['id_partner'])))
            self.partners_table.setItem(row, 1, QTableWidgetItem(partner['name_partner']))
            self.partners_table.setItem(row, 2, QTableWidgetItem(partner['type_name']))
            self.partners_table.setItem(row, 3, QTableWidgetItem(partner['director']))
            self.partners_table.setItem(row, 4, QTableWidgetItem(partner['email']))
            self.partners_table.setItem(row, 5, QTableWidgetItem(partner['phone_number']))
            self.partners_table.setItem(row, 6, QTableWidgetItem(str(partner['current_rating'])))

            # Кнопки действий
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(5, 5, 5, 5)

            edit_btn = QPushButton("Редактировать")
            edit_btn.clicked.connect(lambda checked, p=partner: self.edit_partner(p))

            details_btn = QPushButton("Детали")
            details_btn.clicked.connect(lambda checked, p=partner: self.show_partner_details(p))

            actions_layout.addWidget(edit_btn)
            actions_layout.addWidget(details_btn)
            actions_layout.addStretch()

            self.partners_table.setCellWidget(row, 7, actions_widget)

    def add_partner(self):
        dialog = PartnerAddDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            partner_data = dialog.get_partner_data()
            success = self.db_manager.add_partner(
                partner_data['name'],
                partner_data['type_id'],
                partner_data['director'],
                partner_data['email'],
                partner_data['phone'],
                partner_data['address'],
                partner_data['inn'],
                partner_data['rating']
            )

            if success:
                QMessageBox.information(self, "Успех", "Партнер успешно добавлен!")
                self.load_partners()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить партнера")

    def edit_partner(self, partner_data):
        dialog = PartnerEditDialog(partner_data, self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_updated_data()
            success = self.db_manager.update_partner(
                partner_data['id_partner'],
                updated_data['name'],
                updated_data['type_id'],
                updated_data['director'],
                updated_data['email'],
                updated_data['phone'],
                updated_data['address'],
                updated_data['inn'],
                updated_data['rating']
            )

            if success:
                QMessageBox.information(self, "Успех", "Данные партнера успешно обновлены!")
                self.load_partners()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить данные партнера")

    def show_partner_details(self, partner_data):
        dialog = PartnerDetailDialog(partner_data, self.db_manager, self)
        dialog.exec()


class MainApplication:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.db_manager = DatabaseManager()
        self.current_manager = None

    def run(self):
        # Проверка подключения к базе данных
        if not self.db_manager.get_connection():
            QMessageBox.critical(None, "Ошибка",
                                 "Не удалось подключиться к базе данных.\n"
                                 "Проверьте настройки подключения в классе DatabaseManager.")
            return

        # Показываем окно авторизации
        login_window = LoginWindow(self.db_manager)
        if login_window.exec() == QDialog.DialogCode.Accepted:
            self.current_manager = login_window.manager_data
            # Запускаем главное окно
            main_window = PartnersViewWindow(self.current_manager)
            main_window.show()
            sys.exit(self.app.exec())
        else:
            # Пользователь отменил авторизацию
            sys.exit(0)


def main():
    application = MainApplication()
    application.run()


if __name__ == "__main__":
    main()