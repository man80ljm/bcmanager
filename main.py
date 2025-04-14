# main.py

import logging
import sys
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PyQt5.QtWidgets import QApplication
from ui.login_window import LoginWindow

def setup_logging():
    log_dir = "log"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as e:
            print(f"无法创建日志目录 {log_dir}: {e}")
            sys.exit(1)

    # 生成时间戳命名的日志文件
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{timestamp}.log")

    # 清空现有 handlers（防止追加）
    logging.getLogger().handlers.clear()

    # 配置 RotatingFileHandler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB 每文件
        backupCount=10  # 保留 10 个日志文件
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),  # 控制台输出
            handler  # 文件输出
        ]
    )
    logging.info(f"程序启动，日志文件：{log_file}")

if __name__ == '__main__':
    setup_logging()
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())