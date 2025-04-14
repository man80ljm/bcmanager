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
        try:
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir, exist_ok=True)
            logging.debug(f"备份目录已确认: {self.backup_dir}")
        except OSError as e:
            logging.error(f"无法创建备份目录 {self.backup_dir}: {str(e)}")
            raise RuntimeError(f"无法创建备份目录: {str(e)}")

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
    
    def create_shortcut(self, year, month, project_name, stage, original_year, original_month):
        """创建项目文件夹快捷方式"""
        base_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月")
        original_path = os.path.join(self.base_dir, f"{original_year}年", f"{str(original_month).zfill(2)}月", project_name)
        shortcut_name = f"{project_name}（{stage}）.lnk"
        shortcut_path = os.path.join(base_path, shortcut_name)
        logging.info(f"创建快捷方式: project_name={project_name}, original_path={original_path}")
        try:
            # 确保快捷方式所在目录存在
            os.makedirs(base_path, exist_ok=True)
            logging.info(f"Ensured base_path exists: {base_path}")
            # 检查原始项目目录是否存在
            if not os.path.exists(original_path):
                logging.error(f"原始项目目录不存在: {original_path}")
                return False, f"原始项目目录不存在: {original_path}"
            
            # 如果快捷方式已存在，记录日志但不中断
            if os.path.exists(shortcut_path):
                logging.warning(f"快捷方式已存在: {shortcut_path}，跳过创建")
                return True, f"快捷方式已存在: {shortcut_path}"

            if os.name == 'nt':  # Windows
                try:
                    import win32com.client
                except ImportError:
                    logging.error("未安装 pywin32，Windows 快捷方式创建失败")
                    return False, "请安装 pywin32 以支持 Windows 快捷方式"
                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(shortcut_path)
                target_path = os.path.abspath(original_path).replace('/', '\\')
                shortcut.TargetPath = target_path
                shortcut.WorkingDirectory = os.path.dirname(target_path)
                shortcut.save()
                logging.info(f"快捷方式创建成功: {shortcut_path}, 目标路径: {target_path}")
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
        
    def rename_project_folder(self, year, month, old_project_name, new_project_name):
        """重命名项目文件夹"""
        old_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月", old_project_name)
        new_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月", new_project_name)
        try:
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                logging.info(f"项目文件夹重命名成功: {old_path} -> {new_path}")
                return True, new_path
            else:
                logging.warning(f"项目文件夹不存在: {old_path}")
                return False, f"项目文件夹不存在: {old_path}"
        except Exception as e:
            logging.error(f"重命名项目文件夹失败: {str(e)}")
            return False, str(e)

    def delete_project_folder(self, year, month, project_name, is_only_project_in_month):
        """删除项目文件夹，并根据条件删除月份文件夹"""
        project_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月", project_name)
        month_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月")
        try:
            # 删除项目文件夹
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
                logging.info(f"项目文件夹删除成功: {project_path}")
            else:
                logging.warning(f"项目文件夹不存在: {project_path}")

            # 如果是该月份的唯一项目，删除月份文件夹
            if is_only_project_in_month and os.path.exists(month_path):
                # 检查月份文件夹是否为空（除了系统文件）
                remaining_items = [item for item in os.listdir(month_path) if not item.startswith('.')]
                if not remaining_items:  # 月份文件夹为空
                    shutil.rmtree(month_path)
                    logging.info(f"月份文件夹删除成功: {month_path}")
                else:
                    logging.info(f"月份文件夹不为空，保留: {month_path}")
            return True, "删除成功"
        except Exception as e:
            logging.error(f"删除项目文件夹失败: {str(e)}")
            return False, str(e)
        
    def update_shortcuts(self, old_project_name, new_project_name, project_year, project_month):
        """更新所有指向该项目的快捷方式"""
        try:
            # 遍历所有年份和月份，查找包含该项目名称的快捷方式
            base_year_path = os.path.join(self.base_dir, f"{project_year}年")
            if not os.path.exists(base_year_path):
                return True, "无快捷方式需要更新"

            for month in range(1, 13):
                month_path = os.path.join(base_year_path, f"{str(month).zfill(2)}月")
                if not os.path.exists(month_path):
                    continue

                for item in os.listdir(month_path):
                    if item.startswith(old_project_name) and item.endswith(".lnk"):
                        # 提取阶段信息（例如 "（微商）.lnk"）
                        stage_part = item[len(old_project_name):]
                        new_shortcut_name = f"{new_project_name}{stage_part}"
                        old_shortcut_path = os.path.join(month_path, item)
                        new_shortcut_path = os.path.join(month_path, new_shortcut_name)
                        # 重命名快捷方式
                        os.rename(old_shortcut_path, new_shortcut_path)
                        logging.info(f"快捷方式重命名成功: {old_shortcut_path} -> {new_shortcut_path}")

                        # 更新快捷方式的目标路径
                        if os.name == 'nt':  # Windows
                            try:
                                import win32com.client
                            except ImportError:
                                logging.error("未安装 pywin32，Windows 快捷方式创建失败")
                                return False, "请安装 pywin32 以支持 Windows 快捷方式"
                            shell = win32com.client.Dispatch("WScript.Shell")
                            shortcut = shell.CreateShortCut(new_shortcut_path)
                            new_target_path = os.path.join(self.base_dir, f"{project_year}年", f"{str(project_month).zfill(2)}月", new_project_name)
                            shortcut.TargetPath = new_target_path
                            shortcut.WorkingDirectory = os.path.dirname(new_target_path)
                            shortcut.save()
                            logging.info(f"快捷方式目标路径更新成功: {new_shortcut_path} -> {new_target_path}")

            return True, "快捷方式更新成功"
        except Exception as e:
            logging.error(f"更新快捷方式失败: {str(e)}")
            return False, str(e)
        
    def delete_shortcut(self, year, month, project_name, stage):
        """删除指定项目的快捷方式"""
        base_path = os.path.join(self.base_dir, f"{year}年", f"{str(month).zfill(2)}月")
        shortcut_name = f"{project_name}（{stage}）.lnk"
        shortcut_path = os.path.join(base_path, shortcut_name)
        try:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                logging.info(f"快捷方式删除成功: {shortcut_path}")
                return True, f"快捷方式删除成功: {shortcut_path}"
            else:
                logging.info(f"快捷方式不存在，无需删除: {shortcut_path}")
                return True, f"快捷方式不存在: {shortcut_path}"
        except Exception as e:
            logging.error(f"删除快捷方式失败: {str(e)}")
            return False, str(e)