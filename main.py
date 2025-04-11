# main.py
import os
import logging
import sys
import configparser
from PyQt5.QtWidgets import QApplication
from ui.login_window import LoginWindow
# 导入 DatabaseManager
from database.db_manager import DatabaseManager

# 初始化日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
# 临时设置 data_dir，测试用
    DATA_DIR = os.path.expanduser("~") + "\\bcmanager"
    # 创建 DatabaseManager 实例，传递 data_dir
    db_manager = DatabaseManager(data_dir=DATA_DIR)

    app = QApplication(sys.argv)
    window = LoginWindow(db_manager)  # 假设 LoginWindow 需要 db_manager
    window.show()
    sys.exit(app.exec_())
