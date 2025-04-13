# main.py

import logging
import sys
from PyQt5.QtWidgets import QApplication
from ui.login_window import LoginWindow


# 初始化日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
