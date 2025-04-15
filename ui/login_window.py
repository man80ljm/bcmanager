import sys
import resources
import hashlib
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QSpacerItem, 
                             QSizePolicy, QMessageBox, QCheckBox, QDialog, 
                             QTabWidget, QFileDialog, QFormLayout)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap, QIcon
from database.db_manager import DatabaseManager
import logging

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去掉疑问号
        self.db = parent.db
        self.settings = parent.settings
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()

        # Tab 1: 更换 Logo
        logo_tab = QWidget()
        logo_layout = QFormLayout()
        # 添加垂直 Spacer
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)  # 调整垂直间距
        logo_layout.addItem(spacer)
        self.logo_button = QPushButton("选择 Logo 图片")
        self.logo_button.clicked.connect(self.change_logo)
        logo_layout.addRow("更换 Logo:", self.logo_button)
        logo_tab.setLayout(logo_layout)
        tabs.addTab(logo_tab, "更换 Logo")

        # Tab 2: 更换窗口图标和标题
        title_tab = QWidget()
        title_layout = QFormLayout()
        # 添加垂直 Spacer
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)  # 调整垂直间距
        title_layout.addItem(spacer)
        self.icon_button = QPushButton("选择窗口图标")
        self.icon_button.clicked.connect(self.change_icon)
        self.title_input = QLineEdit()
        self.title_input.setText(self.parent().windowTitle())
        title_layout.addRow("窗口图标:", self.icon_button)
        title_layout.addRow("窗口标题:", self.title_input)
        title_tab.setLayout(title_layout)
        tabs.addTab(title_tab, "更换窗口图标与标题")

        # Tab 3: 更换账号密码（增加原用户名和原密码验证）
        account_tab = QWidget()
        account_layout = QFormLayout()
        # 添加垂直 Spacer
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)  # 调整垂直间距
        account_layout.addItem(spacer)
        # 原用户名和原密码
        self.old_username_input = QLineEdit()
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        # 新用户名、新密码和确认密码
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        # 添加到布局
        account_layout.addRow("原用户名:", self.old_username_input)
        account_layout.addRow("原密码:", self.old_password_input)
        account_layout.addRow("新用户名:", self.username_input)
        account_layout.addRow("新密码:", self.password_input)
        account_layout.addRow("确认密码:", self.confirm_password_input)
        account_tab.setLayout(account_layout)
        tabs.addTab(account_tab, "更换账号密码")

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("确认")
        confirm_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)

        layout.addWidget(tabs)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def change_logo(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择 Logo 图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.logo_path = file_name
            QMessageBox.information(self, "提示", "Logo 已选择，将在下次启动时应用")

    def change_icon(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择窗口图标", "", "Images (*.png *.ico *.jpg *.jpeg)")
        if file_name:
            self.icon_path = file_name
            QMessageBox.information(self, "提示", "窗口图标已选择，将在下次启动时应用")

    def save_settings(self):
        # 保存 Logo 和图标路径
        if hasattr(self, 'logo_path'):
            self.settings.setValue("logo_path", self.logo_path)
            logging.info(f"保存 Logo 路径: {self.logo_path}")
        if hasattr(self, 'icon_path'):
            self.settings.setValue("icon_path", self.icon_path)
            logging.info(f"保存图标路径: {self.icon_path}")


        # 保存窗口标题
        new_title = self.title_input.text().strip()
        if new_title:
            self.settings.setValue("window_title", new_title)
            self.parent().setWindowTitle(new_title)
            logging.info(f"保存窗口标题: {new_title}")

        # 更新账号密码（增加原账号密码验证）
        old_username = self.old_username_input.text().strip()
        old_password = self.old_password_input.text()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if username or password or confirm_password:  # 如果填写了新用户相关字段
        # 确保新用户字段都填写
            if not (username and password and confirm_password):
                QMessageBox.warning(self, "错误", "请填写所有新用户字段！")
                return

            # 验证新密码和确认密码是否一致
            if password != confirm_password:
                QMessageBox.warning(self, "错误", "两次输入的新密码不一致！")
                return

            # 检查 users 表是否为空（初次设置）
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                logging.info(f"用户表记录数: {user_count}")

                # 如果不是初次设置，需要验证原用户名和原密码
                if user_count > 0:
                    if not (old_username and old_password):
                        QMessageBox.warning(self, "错误", "请填写原用户名和原密码！")
                        return
                    hashed_old_password = hashlib.sha256(old_password.encode()).hexdigest()
                    success, _ = self.db.validate_user(old_username, hashed_old_password)
                    if not success:
                        QMessageBox.warning(self, "错误", "原用户名或密码错误，请重试！")
                        return

                # 更新或插入新用户
                try:
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    if user_count == 0:
                        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')",
                                    (username, hashed_password))
                        logging.info(f"插入新用户: {username}, 哈希密码: {hashed_password}")
                    else:
                        cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = 1",
                                    (username, hashed_password))
                        logging.info(f"更新用户记录，影响行数: {cursor.rowcount}, 新用户名: {username}, 哈希密码: {hashed_password}")
                    conn.commit()
                    QMessageBox.information(self, "成功", "账号密码已更新")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新账号密码失败: {str(e)}")
                    return

        self.accept()

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.settings = QSettings("MyCompany", "MyApp")
        self.check_initial_setup()
        self.initUI()
        self.load_saved_credentials()
        self.apply_custom_settings()

    def check_initial_setup(self):
        # 检查 users 表是否为空，若为空，强制要求设置账号密码
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                QMessageBox.information(self, "初次使用", "首次使用，请设置管理员账号和密码")
                dialog = SettingsDialog(self)
                if dialog.exec_() != QDialog.Accepted:
                    sys.exit(0)  # 如果用户取消设置，退出程序

    def initUI(self):
        self.setWindowTitle('本纯设计')
        self.setFixedSize(600, 400)

        main_layout = QHBoxLayout()

        # 左侧 logo 区域
        logo_layout = QVBoxLayout()
        self.logo_label = QLabel()
        logo_pixmap = QPixmap(':/logo.png')
        if logo_pixmap.isNull():
            print("警告：无法加载 logo 图片")
            logo_pixmap = QPixmap(147, 147)
            logo_pixmap.fill(Qt.transparent)
        self.logo_label.setPixmap(logo_pixmap.scaled(147, 147, Qt.KeepAspectRatio))
        self.logo_label.setAlignment(Qt.AlignTop)
        top_spacer = QSpacerItem(0, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        logo_layout.addItem(top_spacer)
        logo_layout.addWidget(self.logo_label)
        logo_layout.addStretch(1)
        main_layout.addLayout(logo_layout, 1)

        # 右侧输入区域
        input_layout = QVBoxLayout()

        # 用户名输入
        username_layout = QHBoxLayout()
        username_label = QLabel('用户名')
        username_label.setStyleSheet("font-size: 20px;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        input_layout.addLayout(username_layout)

        spacer = QSpacerItem(20, 10, QSizePolicy.Minimum)
        input_layout.addItem(spacer)

        # 密码输入
        password_layout = QHBoxLayout()
        password_label = QLabel('密  码')
        password_label.setStyleSheet("font-size: 20px;")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText('请输入密码')
        self.password_input.returnPressed.connect(self.handle_login)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        input_layout.addLayout(password_layout)

        # 记住我和设置按钮
        remember_layout = QHBoxLayout()
        self.remember_check = QCheckBox("记住我")
        self.remember_check.setStyleSheet("color: #666666;")
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(':/settings.png'))  # 需要一个 settings.png 资源
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.clicked.connect(self.open_settings)
        remember_layout.addWidget(self.remember_check)
        remember_layout.addWidget(self.settings_button)
        remember_layout.addStretch()
        input_layout.addLayout(remember_layout)

        # 登录按钮
        login_button = QPushButton('登录')
        login_button.setStyleSheet("background-color: #d3d3d3; padding: 2px;font-size: 20px;")
        login_button.clicked.connect(self.handle_login)
        input_layout.addWidget(login_button, alignment=Qt.AlignRight)
        login_button.setFixedSize(302, 40)

        main_layout.addLayout(input_layout, 2)
        self.setLayout(main_layout)

    def apply_custom_settings(self):
        # 应用自定义窗口标题
        custom_title = self.settings.value("window_title", "本纯设计")
        self.setWindowTitle(custom_title)
        logging.info(f"应用窗口标题: {custom_title}")

        # 应用自定义窗口图标
        icon_path = self.settings.value("icon_path", "")
        if icon_path and not QPixmap(icon_path).isNull():
            self.setWindowIcon(QIcon(icon_path))
            logging.info(f"应用窗口图标: {icon_path}")
        else:
            icon_pixmap = QPixmap(':/logo01.png')
            if not icon_pixmap.isNull():
                self.setWindowIcon(QIcon(icon_pixmap))
                logging.info("使用默认窗口图标: :/logo01.png")
            else:
                logging.warning("默认窗口图标加载失败: :/logo01.png")

        # 应用自定义 Logo
        logo_path = self.settings.value("logo_path", "")
        logging.info(f"读取 Logo 路径: {logo_path}")
        if logo_path and not QPixmap(logo_path).isNull():
            self.logo_label.setPixmap(QPixmap(logo_path).scaled(147, 147, Qt.KeepAspectRatio))
            logging.info(f"应用新 Logo: {logo_path}")
        else:
            logo_pixmap = QPixmap(':/logo.png')
            if not logo_pixmap.isNull():
                self.logo_label.setPixmap(logo_pixmap.scaled(147, 147, Qt.KeepAspectRatio))
                logging.info("使用默认 Logo: :/logo.png")
            else:
                logging.warning("默认 Logo 加载失败: :/logo.png")

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()
        self.apply_custom_settings()

    def load_saved_credentials(self):
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        remember = self.settings.value("remember", False, type=bool)

        if username and remember:
            self.username_input.setText(username)
            self.password_input.setText(password)
            self.remember_check.setChecked(True)
        else:
            self.remember_check.setChecked(False)
            self.username_input.setText("")
            self.password_input.setText("")

    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        remember = self.remember_check.isChecked()

        # 使用哈希密码验证
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        logging.info(f"登录尝试 - 用户名: {username}, 哈希密码: {hashed_password}")
        success, user = self.db.validate_user(username, hashed_password)
        logging.info(f"验证结果: {success}, 用户数据: {user}")

        if success:
            if remember:
                self.settings.setValue("username", username)
                self.settings.setValue("password", password)
                self.settings.setValue("remember", True)
            else:
                self.settings.remove("username")
                self.settings.remove("password")
                self.settings.remove("remember")

            print("登录成功！")
            from ui.year_window import YearWindow
            self.year_window = YearWindow()
            self.year_window.show()
            self.close()
        else:
            print("用户名或密码错误！")
            QMessageBox.warning(self, "登录失败", "用户名或密码错误，请重试！")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())