# utils/file_manager.py

import os
import shutil
from datetime import datetime
import logging

class FileManager:
    def __init__(self, db_path="project_accounting.db", backup_dir="db_backup", base_dir="项目资料"):
        self.db_path = db_path
        self.backup_dir = backup_dir
        self.base_dir = base_dir  # 添加这一行
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
    
    def create_shortcut(self, year, month, project_name, stage, original_year):
        """创建项目文件夹快捷方式"""
        base_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月")
        original_path = os.path.join(self.base_dir, str(original_year), project_name)
        shortcut_name = f"{project_name}（{stage}）.lnk"
        shortcut_path = os.path.join(base_path, shortcut_name)

        try:
            # 确保目标路径（原始项目目录）存在
            if not os.path.exists(original_path):
                os.makedirs(original_path, exist_ok=True)
                logging.info(f"创建原始项目目录: {original_path}")
            # 确保快捷方式所在目录存在
            os.makedirs(base_path, exist_ok=True)
            if os.name == 'nt':  # Windows
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                # Windows 路径需要使用反斜杠
                shortcut.TargetPath = os.path.abspath(original_path).replace('/', '\\')
                shortcut.WorkingDirectory = os.path.dirname(shortcut.TargetPath)
                shortcut.save()
                logging.info(f"快捷方式创建成功: {shortcut_path}, 目标路径: {shortcut.TargetPath}")
            else:  # Linux/macOS，使用符号链接
                os.symlink(original_path, shortcut_path)
                logging.info(f"符号链接创建成功: {shortcut_path}")
            return True, shortcut_path
        except ImportError:
            logging.error("未安装 pywin32，Windows 快捷方式创建失败")
            return False, "请安装 pywin32 以支持 Windows 快捷方式"
        except Exception as e:
            logging.error(f"创建快捷方式失败: {str(e)}")
            return False, str(e)

    def create_project_folder(self, year, month, project_name):
        """创建项目文件夹结构"""
        base_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月", project_name)
        try:
            os.makedirs(os.path.join(base_path, "合同"), exist_ok=True)
            os.makedirs(os.path.join(base_path, "交付文件"), exist_ok=True)
            os.makedirs(os.path.join(base_path, "相关资料"), exist_ok=True)
            logging.info(f"文件夹创建成功: {base_path}")
            return True, base_path
        except Exception as e:
            logging.error(f"创建文件夹失败: {str(e)}")
            return False, str(e)