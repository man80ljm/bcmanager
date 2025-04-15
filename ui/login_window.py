import sys
import resources
from hashlib import sha256 as hashlib_sha256
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QSpacerItem, 
                             QSizePolicy, QMessageBox, QCheckBox, QDialog, 
                             QTabWidget, QFileDialog, QFormLayout, QComboBox)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap, QIcon
from database.db_manager import DatabaseManager
import logging

class RecoverPasswordDialog(QDialog):
    """密码找回对话框，用于通过安全问题找回密码并重置为默认值"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("找回密码")
        self.setFixedSize(400, 250)
        self.db = parent.db  # 获取父窗口的数据库实例
        self.security_question = None  # 存储安全问题
        self.initUI()

    def initUI(self):
        """初始化找回密码对话框的界面"""
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # 直接从数据库获取安全问题（假设只有一个用户，id = 1）
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT security_question FROM users WHERE id = 1")
            result = cursor.fetchone()
            if result and result[0]:
                self.security_question = result[0]
            else:
                self.security_question = "未设置安全问题"

        # 安全问题显示标签
        self.question_label = QLabel(self.security_question)
        form_layout.addRow("安全问题:", self.question_label)
        
        # 答案输入框
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("请输入答案")
        form_layout.addRow("答案:", self.answer_input)
        
        # 确认和取消按钮
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("确认")
        confirm_button.clicked.connect(self.verify_answer)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def verify_answer(self):
        """验证用户输入的答案，并重置密码为默认值"""
        answer = self.answer_input.text().strip()
        if not answer:
            QMessageBox.warning(self, "错误", "请输入答案！")
            return
        
        # 假设只有一个用户（id = 1），直接验证答案
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT security_answer, username FROM users WHERE id = 1")
            result = cursor.fetchone()
            if result:
                stored_answer_hash, current_username = result
                if not stored_answer_hash:
                    QMessageBox.warning(self, "错误", "未设置安全答案！")
                    return
                input_answer_hash = hashlib_sha256(answer.encode()).hexdigest()
                logging.info(f"验证安全答案 - 用户输入答案哈希: {input_answer_hash}, 数据库存储答案哈希: {stored_answer_hash}")
                if input_answer_hash == stored_answer_hash:
                    try:
                        default_username = "bc"
                        default_password_hash = "5dd2b2cbf23d7c2815e7100bcbef2325c1af832ae703b834e8508cbfc595a790"
                        # 检查当前用户名是否已经是 default_username
                        if current_username == default_username:
                            # 如果已经是 bc，只更新密码
                            cursor.execute(
                                "UPDATE users SET password = ? WHERE id = 1",
                                (default_password_hash,)
                            )
                        else:
                            # 如果不是 bc，更新用户名和密码
                            cursor.execute(
                                "UPDATE users SET username = ?, password = ? WHERE id = 1",
                                (default_username, default_password_hash)
                            )
                        conn.commit()
                        logging.info(f"用户 {current_username} 密码已重置为默认值")
                        QMessageBox.information(self, "成功", "用户密码重置成功！")
                        self.accept()
                    except Exception as e:
                        QMessageBox.warning(self, "错误", f"密码重置失败: {str(e)}")
                        logging.error(f"密码重置失败: {str(e)}")
                else:
                    QMessageBox.warning(self, "错误", "回答错误！")
            else:
                QMessageBox.warning(self, "错误", "用户不存在！")

class SettingsDialog(QDialog):
    """设置对话框，用于修改 Logo、窗口图标、标题和账号密码"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setFixedSize(600, 600)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.db = parent.db
        self.settings = parent.settings
        self.initUI()

    def initUI(self):
        """初始化设置对话框的界面"""
        layout = QVBoxLayout()
        tabs = QTabWidget()

        logo_tab = QWidget()
        logo_layout = QFormLayout()
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        logo_layout.addItem(spacer)
        self.logo_button = QPushButton("选择 Logo 图片")
        self.logo_button.clicked.connect(self.change_logo)
        logo_layout.addRow("更换 Logo:", self.logo_button)
        logo_tab.setLayout(logo_layout)
        tabs.addTab(logo_tab, "更换 Logo")

        title_tab = QWidget()
        title_layout = QFormLayout()
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        title_layout.addItem(spacer)
        self.icon_button = QPushButton("选择窗口图标")
        self.icon_button.clicked.connect(self.change_icon)
        self.title_input = QLineEdit()
        self.title_input.setText(self.parent().windowTitle())
        title_layout.addRow("窗口图标:", self.icon_button)
        title_layout.addRow("窗口标题:", self.title_input)
        title_tab.setLayout(title_layout)
        tabs.addTab(title_tab, "更换窗口图标与标题")

        account_tab = QWidget()
        account_layout = QFormLayout()
        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed)
        account_layout.addItem(spacer)
        self.old_username_input = QLineEdit()
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.security_question_combo = QComboBox()
        self.security_question_combo.addItems([
            "你的名字是什么？",
            "你的手机号是多少？",
            "你的公司全称是什么？",
            "你最喜欢的颜色是什么？",
            "你的出生地是哪里？",
            "你的第一所学校叫什么？",
            "你最喜欢的电影是什么？",
            "你的宠物名字是什么？",
            "你最喜欢的食物是什么？",
            "你的童年昵称是什么？"
        ])
        self.security_answer_input = QLineEdit()
        self.security_answer_input.setPlaceholderText("请输入答案")
        account_layout.addRow("原用户名:", self.old_username_input)
        account_layout.addRow("原密码:", self.old_password_input)
        account_layout.addRow("新用户名:", self.username_input)
        account_layout.addRow("新密码:", self.password_input)
        account_layout.addRow("确认密码:", self.confirm_password_input)
        account_layout.addRow("安全问题:", self.security_question_combo)
        account_layout.addRow("答案:", self.security_answer_input)
        account_tab.setLayout(account_layout)
        tabs.addTab(account_tab, "更换账号密码")

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
        """打开文件对话框，选择新的 Logo 图片"""
        file_name, _ = QFileDialog.getOpenFileName(self, "选择 Logo 图片", "", "Images (*.png *.jpg *.jpeg)")
        if file_name:
            self.logo_path = file_name
            QMessageBox.information(self, "提示", "Logo 已选择，将在下次启动时应用")

    def change_icon(self):
        """打开文件对话框，选择新的窗口图标"""
        file_name, _ = QFileDialog.getOpenFileName(self, "选择窗口图标", "", "Images (*.png *.ico *.jpg *.jpeg)")
        if file_name:
            self.icon_path = file_name
            QMessageBox.information(self, "提示", "窗口图标已选择，将在下次启动时应用")

    def save_settings(self):
        """保存设置，包括 Logo、图标、窗口标题和账号密码"""
        if hasattr(self, 'logo_path'):
            self.settings.setValue("logo_path", self.logo_path)
            logging.info(f"保存 Logo 路径: {self.logo_path}")
        if hasattr(self, 'icon_path'):
            self.settings.setValue("icon_path", self.icon_path)
            logging.info(f"保存图标路径: {self.icon_path}")

        new_title = self.title_input.text().strip()
        if new_title:
            self.settings.setValue("window_title", new_title)
            self.parent().setWindowTitle(new_title)
            logging.info(f"保存窗口标题: {new_title}")

        old_username = self.old_username_input.text().strip()
        old_password = self.old_password_input.text()
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        security_question = self.security_question_combo.currentText()
        security_answer = self.security_answer_input.text().strip()

        if security_question or security_answer:
            if not (username and password and confirm_password):
                QMessageBox.warning(self, "错误", "请填写所有新用户字段以保存安全问题！")
                return

        if username or password or confirm_password:
            if not (username and password and confirm_password):
                QMessageBox.warning(self, "错误", "请填写所有新用户字段！")
                return

            if password != confirm_password:
                QMessageBox.warning(self, "错误", "两次输入的新密码不一致！")
                return

            if not (security_question and security_answer):
                QMessageBox.warning(self, "错误", "请设置安全问题和答案！")
                return

            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                logging.info(f"用户表记录数: {user_count}")

                if user_count > 0:
                    if not (old_username and old_password):
                        QMessageBox.warning(self, "错误", "请填写原用户名和原密码！")
                        return
                    hashed_old_password = hashlib_sha256(old_password.encode()).hexdigest()
                    success, _ = self.db.validate_user(old_username, hashed_old_password)
                    if not success:
                        QMessageBox.warning(self, "错误", "原用户名或密码错误，请重试！")
                        return

                try:
                    hashed_password = hashlib_sha256(password.encode()).hexdigest()
                    hashed_answer = hashlib_sha256(security_answer.encode()).hexdigest()
                    logging.info(f"保存安全问题 - 问题: {security_question}, 答案哈希: {hashed_answer}")
                    if user_count == 0:
                        cursor.execute("INSERT INTO users (username, password, role, security_question, security_answer) VALUES (?, ?, 'admin', ?, ?)",
                                     (username, hashed_password, security_question, hashed_answer))
                        logging.info(f"插入新用户: {username}")
                    else:
                        cursor.execute("UPDATE users SET username = ?, password = ?, security_question = ?, security_answer = ? WHERE id = 1",
                                     (username, hashed_password, security_question, hashed_answer))
                        logging.info(f"更新用户记录，影响行数: {cursor.rowcount}, 新用户名: {username}")
                    conn.commit()
                    # 验证更新是否成功
                    cursor.execute("SELECT security_question, security_answer FROM users WHERE id = 1")
                    result = cursor.fetchone()
                    logging.info(f"验证更新 - 数据库安全问题: {result[0]}, 答案哈希: {result[1]}")
                    QMessageBox.information(self, "成功", "账号密码已更新")
                    QMessageBox.warning(self, "重要提示", "安全问题是你唯一找回账号密码的机会！请谨记！")
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"更新账号密码失败: {str(e)}")
                    logging.error(f"更新账号密码失败: {str(e)}")
                    return
        else:
            self.accept()
            return

        self.accept()

class LoginWindow(QWidget):
    """登录窗口，用于用户登录和基本设置"""
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.settings = QSettings("MyCompany", "MyApp")
        self.check_initial_setup()
        self.initUI()
        self.load_saved_credentials()
        self.apply_custom_settings()

    def check_initial_setup(self):
        """检查是否为首次使用，若 users 表为空，强制要求设置账号密码"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            if user_count == 0:
                QMessageBox.information(self, "初次使用", "首次使用，请设置管理员账号和密码")
                dialog = SettingsDialog(self)
                if dialog.exec_() != QDialog.Accepted:
                    sys.exit(0)

    def initUI(self):
        """初始化登录窗口的界面"""
        self.setWindowTitle('本纯设计')
        self.setFixedSize(600, 400)

        main_layout = QHBoxLayout()

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

        input_layout = QVBoxLayout()

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

        remember_layout = QHBoxLayout()
        self.remember_check = QCheckBox("记住我")
        self.remember_check.setStyleSheet("color: #666666;")
        self.settings_button = QPushButton()
        self.settings_button.setIcon(QIcon(':/settings.png'))
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.clicked.connect(self.open_settings)

        self.recover_button = QPushButton()
        icon = QIcon(':/help.png')
        if icon.isNull():
            print("警告：无法加载 help.png 图标")
            self.recover_button.setText("?")
        else:
            self.recover_button.setIcon(icon)
            print("help.png 图标加载成功")
        self.recover_button.setFixedSize(24, 24)
        self.recover_button.clicked.connect(self.open_recover_dialog)

        remember_layout.addWidget(self.remember_check)
        remember_layout.addWidget(self.settings_button)
        spacer = QSpacerItem(30, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        remember_layout.addItem(spacer)
        remember_layout.addWidget(self.recover_button)
        remember_layout.addStretch()
        input_layout.addLayout(remember_layout)

        login_button = QPushButton('登录')
        login_button.setStyleSheet("background-color: #d3d3d3; padding: 2px;font-size: 20px;")
        login_button.clicked.connect(self.handle_login)
        input_layout.addWidget(login_button, alignment=Qt.AlignRight)
        login_button.setFixedSize(302, 40)

        main_layout.addLayout(input_layout, 2)
        self.setLayout(main_layout)

    def apply_custom_settings(self):
        """应用自定义设置，包括窗口标题、图标和 Logo"""
        custom_title = self.settings.value("window_title", "本纯设计")
        self.setWindowTitle(custom_title)
        logging.info(f"应用窗口标题: {custom_title}")

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
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec_()
        self.apply_custom_settings()

    def open_recover_dialog(self):
        """打开找回密码对话框"""
        dialog = RecoverPasswordDialog(self)
        dialog.exec_()

    def load_saved_credentials(self):
        """加载保存的登录凭据（如果用户选择了‘记住我’）"""
        username = self.settings.value("username", "")
        password = self.settings.value("password", "")
        remember = self.settings.value("remember", False, type=bool)
        logging.info(f"加载保存的凭据 - 用户名: {username}, 记住我: {remember}")
        if username and remember:
            self.username_input.setText(username)
            self.password_input.setText(password)
            self.remember_check.setChecked(True)
        else:
            self.remember_check.setChecked(False)
            self.username_input.setText("")
            self.password_input.setText("")

    def handle_login(self):
        """处理用户登录逻辑，验证用户名和密码"""
        username = self.username_input.text()
        password = self.password_input.text()
        remember = self.remember_check.isChecked()
        hashed_password = hashlib_sha256(password.encode()).hexdigest()
        logging.info(f"登录尝试 - 用户名: {username}")
        success, user = self.db.validate_user(username, hashed_password)
        logging.info(f"验证结果: {success}")
        if success:
            if remember:
                self.settings.setValue("username", username)
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
    """程序入口，启动登录窗口"""
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())