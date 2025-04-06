# utils/file_manager.py

import os
import shutil
from datetime import datetime
import logging

class FileManager:
    def __init__(self, db_path="project_accounting.db", backup_dir="db_backup"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        # 确保备份目录存在
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        # 设置日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def backup_database(self):
        """备份数据库文件到 db_backup 文件夹"""
        try:
            # 生成备份文件名，格式：project_accounting_YYYYMMDDHHMMSS.db
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            backup_filename = f"project_accounting_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_filename)

            # 复制数据库文件到备份路径
            shutil.copy2(self.db_path, backup_path)
            logging.info(f"Database backed up to {backup_path}")
            return True, backup_path
        except Exception as e:
            logging.error(f"Backup failed: {str(e)}")
            return False, str(e)

    def get_backup_files(self):
        """获取 db_backup 文件夹中的所有备份文件"""
        try:
            backup_files = [f for f in os.listdir(self.backup_dir) if f.endswith('.db')]
            return backup_files
        except Exception as e:
            logging.error(f"Error listing backup files: {str(e)}")
            return []

    def restore_database(self, backup_filename):
        """从指定备份文件恢复数据库"""
        try:
            backup_path = os.path.join(self.backup_dir, backup_filename)
            if not os.path.exists(backup_path):
                return False, "备份文件不存在！"

            # 复制备份文件覆盖当前数据库文件
            shutil.copy2(backup_path, self.db_path)
            logging.info(f"Database restored from {backup_path}")
            return True, "数据库恢复成功！"
        except Exception as e:
            logging.error(f"Restore failed: {str(e)}")
            return False, str(e)
    #继续开发新的功能