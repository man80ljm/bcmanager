import sys
import resources
from PyQt5.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QSpacerItem, 
                             QSizePolicy,QMessageBox, QCheckBox)
from PyQt5.QtCore import Qt,QSettings
from PyQt5.QtGui import QPixmap,QIcon
from database.db_manager import DatabaseManager  # 导入数据库管理类


class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()  # 初始化数据库
        self.settings = QSettings("MyCompany", "MyApp")  # 初始化设置存储
        # 临时清除所有设置（仅用于调试）
        # self.settings.clear()
        self.initUI()
        self.load_saved_credentials()  # 加载保存的凭证
        # 设置窗口图标
        icon_pixmap = QPixmap(':/logo01.png')
        if icon_pixmap.isNull():
            print("警告：无法加载窗口图标 logo01.png")
        self.setWindowIcon(QIcon(icon_pixmap))
        # 设置光标默认聚焦在密码输入框
        self.password_input.setFocus()

    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('本纯设计')
        self.setFixedSize(600, 400)  # 设置固定大小，防止窗口调整

        # 创建主布局（水平布局：左侧 logo，右侧输入区域）
        main_layout = QHBoxLayout()

        # 左侧 logo 区域
        logo_layout = QVBoxLayout()  # 垂直布局用于 logo
        logo_label = QLabel()
        logo_pixmap = QPixmap(':/logo.png')  # 确保提供正确的路径
        if logo_pixmap.isNull():
            print("警告：无法加载 logo 图片")
            logo_pixmap = QPixmap(147, 147)  # 备用空白图片
            logo_pixmap.fill(Qt.transparent)
        logo_label.setPixmap(logo_pixmap.scaled(147, 147, Qt.KeepAspectRatio))  # 调整图像大小
        logo_label.setAlignment(Qt.AlignTop)

        # 添加一个固定大小的 spacer 在顶部
        top_spacer = QSpacerItem(0, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)  # 20 表示离顶部的距离
        logo_layout.addItem(top_spacer)

        # 添加 logo
        logo_layout.addWidget(logo_label)

        # 在底部添加一个伸缩项，推到顶部
        logo_layout.addStretch(1)

        # 将 logo_layout 添加到主布局中
        main_layout.addLayout(logo_layout, 1)  # 占用 1 份空间

        # 右侧输入区域（垂直布局）
        input_layout = QVBoxLayout()

        # 用户名输入
        username_layout = QHBoxLayout()
        username_label = QLabel('用户名')
        username_label.setStyleSheet("font-size: 20px;")  # 设置用户名字体大小为 20px
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText('请输入用户名')
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        input_layout.addLayout(username_layout)

        # 增加行间距
        spacer = QSpacerItem(20, 10, QSizePolicy.Minimum)
        input_layout.addItem(spacer)

        # 密码输入
        password_layout = QHBoxLayout()
        password_label = QLabel('密  码')
        password_label.setStyleSheet("font-size: 20px;")  # 设置密码字体大小为 20px
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)  # 密码模式，输入显示为星号
        self.password_input.setPlaceholderText('请输入密码')
        # 绑定回车键到 handle_login
        self.password_input.returnPressed.connect(self.handle_login)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        input_layout.addLayout(password_layout)

        # 在密码输入框后添加"记住我"复选框
        remember_layout = QHBoxLayout()
        self.remember_check = QCheckBox("记住我")
        self.remember_check.setStyleSheet("color: #666666;")
        remember_layout.addWidget(self.remember_check)
        remember_layout.addStretch()  # 让复选框靠左
        input_layout.addLayout(remember_layout)

        # 登录按钮
        login_button = QPushButton('登录')
        login_button.setStyleSheet("background-color: #d3d3d3; padding: 2px;font-size: 20px;")  # 设置按钮样式，与图片一致
        login_button.clicked.connect(self.handle_login)  # 绑定登录按钮的点击事件
        input_layout.addWidget(login_button, alignment=Qt.AlignRight)
        login_button.setFixedSize(302, 40)  # 设置按钮的宽度和高度

        # 将输入区域添加到主布局
        main_layout.addLayout(input_layout, 2)  # 占用 2 份空间

        # 设置主布局到窗口
        self.setLayout(main_layout)

    def load_saved_credentials(self):
        """加载保存的用户名和密码"""
        username = self.settings.value("username", "bc") # 默认 bc
        password = self.settings.value("password", "")
        remember = self.settings.value("remember", False, type=bool)

        # 设置用户名（优先使用保存的用户名，否则为 bc）
        self.username_input.setText(username)
        
        # 仅当明确保存了用户名且 remember 为 True 时加载凭证
        if username and remember:
            self.username_input.setText(username)
            self.password_input.setText(password)
            self.remember_check.setChecked(True)
        else:
            # 确保复选框未勾选，且不加载密码
            self.remember_check.setChecked(False)
            self.username_input.setText(username)  # 可选择保留用户名
            self.password_input.setText("")

    # ui/login_window.py（仅修改 handle_login 方法）
    def handle_login(self):
        username = self.username_input.text()
        password = self.password_input.text()
        remember = self.remember_check.isChecked()

        success, user = self.db.validate_user(username, password)

        if success:
            # 保存凭证（如果勾选了记住我）
            if remember:
                self.settings.setValue("username", username)
                self.settings.setValue("password", password)
                self.settings.setValue("remember", True)
            else:
                # 清除保存的凭证
                self.settings.remove("username")
                self.settings.remove("password")
                self.settings.remove("remember")

            print("登录成功！")
            # 修复跳转问题 - 延迟导入
            print("准备跳转到year_window")  # 调试用
            from ui.year_window import YearWindow
            self.year_window = YearWindow()  # 创建年份管理窗口
            self.year_window.show()          # 显示年份管理窗口
            self.close()                     # 关闭登录窗口
        else:
            print("用户名或密码错误！")
            QMessageBox.warning(self, "登录失败", "用户名或密码错误，请重试！")

# 测试代码
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
