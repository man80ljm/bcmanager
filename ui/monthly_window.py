from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QVBoxLayout, QWidget,
                             QMenu, QInputDialog, QComboBox, QMessageBox,QHBoxLayout)
from PyQt5.QtGui import QIcon,QColor
from PyQt5.QtCore import Qt  # 添加这一行，导入 Qt
from database.db_manager import DatabaseManager
from utils.file_manager import FileManager
from ui.dialogs import EditTransactionDialog
from PyQt5.QtWidgets import QMenu, QAction
import logging
import os
from datetime import datetime

class MonthlyWindow(QMainWindow):
    def __init__(self, year, month):
        super().__init__()
        self.year = year
        self.month = month
        self.db = DatabaseManager()
        self.file_manager = FileManager()  # 初始化 FileManager
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'{self.year}年{self.month}月详情')
        self.setMinimumSize(1300, 550)
        self.setWindowIcon(QIcon(r'D:\bcmanager\logo01.png'))  # 设置窗口图标

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["创建时间", "项目名称", "金额", "类型", "支付方式", "备注", "修改", "删除"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁用编辑
        
        # 功能按钮
        button_layout = QHBoxLayout()
        create_button = QPushButton("创建")
        create_button.clicked.connect(self.show_create_dialog)  # 修复：连接信号
        filter_button = QPushButton("筛选")
        button_layout.addWidget(create_button)
        button_layout.addWidget(filter_button)
        layout.addLayout(button_layout)

        # 汇总信息
        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        # 先加载数据
        self.load_transactions()

        # 再设置上下文菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)


    def load_transactions(self):
        try:
            transactions = self.db.get_monthly_transactions(self.year, self.month)
            logging.info(f"Loaded {len(transactions)} transactions for {self.year}-{self.month}")
            for t in transactions:
                logging.info(f"Transaction: {t}")  # 打印每条交易记录
            self.table.setRowCount(len(transactions))
            for row, (id, created_at, name, amount, trans_type, payment_method, stage, status) in enumerate(transactions):
                created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                formatted_time = created_at_dt.strftime("%Y年%m月%d日%H时%M分")
                self.table.setItem(row, 0, QTableWidgetItem(formatted_time))
                display_name = f"{name}（{stage}）" if stage else name
                name_item = QTableWidgetItem(display_name)
                if trans_type == "收入" and status == "已结项":
                    name_item.setBackground(QColor("lightgreen"))
                self.table.setItem(row, 1, name_item)
                self.table.setItem(row, 2, QTableWidgetItem(str(amount)))
                self.table.setItem(row, 3, QTableWidgetItem(trans_type))
                self.table.setItem(row, 4, QTableWidgetItem(payment_method))
                remark_button = QPushButton("备注")
                self.table.setCellWidget(row, 5, remark_button)
                edit_button = QPushButton("修改")
                edit_button.clicked.connect(lambda checked, r=row: self.edit_transaction(r))
                self.table.setCellWidget(row, 6, edit_button)
                delete_button = QPushButton("删除")
                delete_button.clicked.connect(lambda checked, r=row: self.delete_transaction(r))
                self.table.setCellWidget(row, 7, delete_button)

            total_income, total_expense, balance = self.db.get_monthly_summary(self.year, self.month)
            self.summary_label.setText(f"总收入: {total_income} | 总支出: {total_expense} | 结余: {balance}")
        except Exception as e:
            logging.error(f"Failed to load transactions for {self.year}-{self.month}: {str(e)}")
            QMessageBox.warning(self, "错误", f"加载交易记录失败: {str(e)}")

    def show_context_menu(self, pos):
        """显示右键菜单"""
        logging.info(f"Right-click detected at position: {pos}")
        # 获取点击的单元格
        item = self.table.itemAt(pos)
        if not item:
            return

        row = item.row()
        col = item.column()
        logging.info(f"Clicked on row {row}, column {col}")
        # 只在“项目名称”列（第 1 列）且类型为“收入”时显示菜单
        if col != 1:
            return

        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        trans_type = transaction[4]  # 类型
        logging.info(f"Transaction type: {trans_type}")
        if trans_type != "收入":
            logging.info("Transaction type is not '收入'")
            return

        # 创建上下文菜单
        menu = QMenu(self)
        action_unsettled = QAction("未结项", self)
        action_settled = QAction("已结项", self)
        menu.addAction(action_unsettled)
        menu.addAction(action_settled)

        # 绑定动作
        action_unsettled.triggered.connect(lambda: self.set_transaction_status(row, "未结项"))
        action_settled.triggered.connect(lambda: self.set_transaction_status(row, "已结项"))

        # 显示菜单
        logging.info("Showing context menu")
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def set_transaction_status(self, row, status):
        """设置交易状态并更新显示"""
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        transaction_id = transaction[0]
        success = self.db.update_transaction_status(transaction_id, status)
        if success:
            # 更新单元格背景色
            name_item = self.table.item(row, 1)
            if status == "已结项":
                name_item.setBackground(QColor("lightgreen"))
            else:
                name_item.setBackground(QColor("white"))  # 恢复默认背景
            QMessageBox.information(self, "成功", f"状态已更新为: {status}")
        else:
            QMessageBox.warning(self, "失败", "状态更新失败！")

    def edit_transaction(self, row):
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        id, created_at, name, amount, trans_type, payment_method, stage, status = transaction
        old_project_name = name
        dialog = EditTransactionDialog(transaction, self.db, parent=self)  # 传递 self.db
        if dialog.exec_():
            updated_data = dialog.get_updated_data()
            success = self.db.update_transaction(
                updated_data["id"],
                updated_data["amount"],
                updated_data["type"],
                updated_data["payment_method"]
            )
            if success and old_project_name != updated_data["name"]:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT project_id, p.year_id, p.month 
                    FROM transactions t 
                    JOIN projects p ON t.project_id = p.id 
                    WHERE t.id = ?
                """, (updated_data["id"],))
                project_id, year_id, project_month = cursor.fetchone()
                cursor.execute("SELECT year FROM years WHERE id = ?", (year_id,))
                project_year = cursor.fetchone()[0]
                conn.close()

                success = self.db.update_project_name(project_id, updated_data["name"])
                if success:
                    rename_success, result = self.file_manager.rename_project_folder(
                        project_year, project_month, old_project_name, updated_data["name"]
                    )
                    if not rename_success:
                        QMessageBox.warning(self, "警告", f"项目文件夹重命名失败: {result}")
                    else:
                        update_success, update_result = self.file_manager.update_shortcuts(
                            old_project_name, updated_data["name"], project_year, project_month
                        )
                        if not update_success:
                            QMessageBox.warning(self, "警告", f"快捷方式更新失败: {update_result}")
            if success:
                QMessageBox.information(self, "成功", "收支记录修改成功！")
                self.load_transactions()
            else:
                QMessageBox.warning(self, "失败", "收支记录修改失败！")

    def delete_transaction(self, row):
        """删除指定行的收支记录"""
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        id, created_at, name, amount, trans_type, payment_method, stage, status = transaction
        transaction_id = id
        project_name = name
        # 弹出确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 '{project_name}' 的这条收支记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # 检查该项目是否是该月份的唯一项目
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) 
                FROM transactions 
                WHERE year_id = (SELECT id FROM years WHERE year = ?) AND month = ?
            """, (self.year, self.month))
            total_transactions = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) 
                FROM transactions 
                WHERE project_id = (SELECT project_id FROM transactions WHERE id = ?) 
                AND year_id = (SELECT id FROM years WHERE year = ?) 
                AND month = ?
            """, (transaction_id, self.year, self.month))
            project_transactions = cursor.fetchone()[0]
            conn.close()

            # 如果该项目在该月份只有一条记录，则认为是唯一项目
            is_only_project_in_month = (project_transactions == 1 and total_transactions == 1)

            # 删除数据库记录
            success = self.db.delete_transaction(transaction_id)
            if success:
                # 删除项目文件夹，并根据条件删除月份文件夹
                delete_success, result = self.file_manager.delete_project_folder(
                    self.year, self.month, project_name, is_only_project_in_month
                )
                if not delete_success:
                    QMessageBox.warning(self, "警告", f"项目文件夹删除失败: {result}")
                QMessageBox.information(self, "成功", "收支记录删除成功！")
                # 刷新表格
                self.load_transactions()
            else:
                QMessageBox.warning(self, "失败", "收支记录删除失败！")

    def show_create_dialog(self):
        """显示创建方式选择对话框"""
        choice, ok = QInputDialog.getItem(self, "创建收支记录", "请选择创建方式：", 
                                         ["创建新项目", "选择已有项目"], 0, False)
        if not ok:
            print("取消创建选择")
            return
        if choice == "创建新项目":
            self.create_new_project_transaction()
        elif choice == "选择已有项目":
            self.create_existing_project_transaction()  

    def create_new_project_transaction(self):
        # 检查目标月份是否晚于当前时间
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        transaction_year = int(self.year)
        transaction_month = int(self.month)

        if transaction_year > current_year or (transaction_year == current_year and transaction_month > current_month):
            QMessageBox.warning(self, "错误", f"不能为未来的月份创建项目！当前日期：{current_year}年{current_month}月")
            return
        
        # 步骤 1: 输入项目名称
        project_name, ok = QInputDialog.getText(self, "创建新项目", "请输入项目名称：")
        if not ok or not project_name:
            print("取消输入项目名称")
            return

        # 步骤 2: 输入金额
        amount, ok = QInputDialog.getDouble(self, "输入金额", "请输入金额：", value=0.0, min=0.01, max=9999999.99, decimals=2)
        if not ok:
            print("取消输入金额")
            return

        # 步骤 3: 选择收支类型
        trans_type, ok = QInputDialog.getItem(self, "选择类型", "请选择收支类型：", ["收入", "支出"], 0, False)
        if not ok:
            print("取消选择收支类型")
            return

        # 步骤 4: 选择支付方式
        payment_method, ok = QInputDialog.getItem(self, "选择支付方式", "请选择支付方式：",
                                                ["微信", "支付宝", "对公账户", "对私账户", "现金"], 0, False)
        if not ok:
            print("取消选择支付方式")
            return

        # 步骤 5: 确认对话框
        confirm_msg = f"项目名称: {project_name}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
        reply = QMessageBox.question(self, "确认创建", confirm_msg, QMessageBox.Ok | QMessageBox.Cancel)
        if reply != QMessageBox.Ok:
            print("取消确认")
            return

        # 步骤 6: 保存到数据库
        print(f"创建项目: name={project_name}, year={self.year}")
        success, project_id = self.db.add_project(project_name, self.year, self.month)
        if success and project_id is not None:
            print(f"项目 {project_name} 创建成功，ID: {project_id}")
            year_int = int(self.year)
            month_int = int(self.month)
            print(f"保存收支记录: project_id={project_id}, amount={amount}, trans_type={trans_type}, payment_method={payment_method}, month={month_int}, year={year_int}")
            success = self.db.add_transaction(project_id, amount, trans_type, payment_method, month_int, year_int)
            if success:
                # 使用 FileManager 创建文件夹
                folder_success, result = self.file_manager.create_project_folder(self.year, self.month, project_name)
                if not folder_success:
                    QMessageBox.warning(self, "失败", f"创建文件夹失败: {result}")
                else:
                    print(f"文件夹创建成功: {result}")
                    QMessageBox.information(self, "成功", "收支记录创建成功！")
                    self.load_transactions()
            else:
                QMessageBox.warning(self, "失败", "保存收支记录失败！")
        else:
            QMessageBox.warning(self, "失败", f"创建项目失败！请确保年份 {self.year} 已存在。")

    def create_existing_project_transaction(self):
        """选择已有项目创建收支记录"""
        # 步骤 1: 选择年份
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month

        transaction_year = int(self.year)
        transaction_month = int(self.month)

        if transaction_year > current_year or (transaction_year == current_year and transaction_month > current_month):
            QMessageBox.warning(self, "错误", f"不能为未来的月份创建收支记录！当前日期：{current_year}年{current_month}月")
            return
        
        all_years = self.db.get_years()
        years = [year for year in all_years if int(year) <= current_year]
        if not years:
            QMessageBox.warning(self, "错误", "数据库中没有年份记录，请先创建年份！")
            return
        selected_year, ok = QInputDialog.getItem(self, "选择年份", "请选择项目所属年份：", years, 0, False)
        if not ok:
            print("取消选择年份")
            return

        # 步骤 2: 选择项目（确保显示最新名称）
        projects = self.db.get_projects_by_year(selected_year)
        
        # 定义当前窗口的月份
        current_window_month = int(self.month)  # 提前定义，避免 NameError
        
        # 过滤掉创建月份晚于当前窗口月份的项目
        filtered_projects = [p for p in projects if p[2] is not None and p[2] <= current_window_month]
        print(f"Filtered projects (month <= {current_window_month}): {filtered_projects}")

        if not filtered_projects:
            QMessageBox.warning(self, "错误", f"{selected_year} 年没有创建月份在 {current_window_month} 月及之前的项目！")
            return
        
        # 显示项目名称时包含创建月份
        project_names = [p[1] for p in filtered_projects]  # 只使用过滤后的项目
        project_ids = {p[1]: p[0] for p in filtered_projects}
        project_months = {p[1]: p[2] for p in filtered_projects}  # 映射项目名称到创建月份
        project_name, ok = QInputDialog.getItem(self, "选择项目", "请选择已有项目：", project_names, 0, False)
        if not ok:
            print("取消选择项目")
            return
        project_id = project_ids[project_name]
        project_month = project_months[project_name]  # 获取项目的创建月份

        # 确保 project_month 不为 None（已经通过过滤确保）
        if project_month is None:
            QMessageBox.critical(self, "错误", f"项目 {project_name} 的创建月份未定义，请联系管理员检查数据库！")
            return

        # 步骤 3: 选择项目阶段
        stages = ["第二阶段", "第三阶段", "第四阶段"]
        stage, ok = QInputDialog.getItem(self, "选择阶段", "请选择项目阶段：", stages, 0, False)
        if not ok:
            print("取消选择阶段")
            return

        # 步骤 4: 输入金额
        amount, ok = QInputDialog.getDouble(self, "输入金额", "请输入金额（正数）：", value=0.0, min=0.01, max=9999999.99, decimals=2)
        if not ok:
            print("取消输入金额")
            return

        # 步骤 5: 选择收支类型
        trans_type, ok = QInputDialog.getItem(self, "选择类型", "请选择收支类型：", ["收入", "支出"], 0, False)
        if not ok:
            print("取消选择收支类型")
            return

        # 步骤 6: 选择支付方式
        payment_method, ok = QInputDialog.getItem(self, "选择支付方式", "请选择支付方式：",
                                                ["微信", "支付宝", "对公账户", "对私账户", "现金"], 0, False)
        if not ok:
            print("取消选择支付方式")
            return

        # 步骤 7: 确认对话框
        confirm_msg = f"项目名称: {project_name}\n阶段: {stage}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
        reply = QMessageBox.question(self, "确认创建", confirm_msg, QMessageBox.Ok | QMessageBox.Cancel)
        if reply != QMessageBox.Ok:
            print("取消确认")
            return

        # 步骤 8: 保存到数据库并创建快捷方式
        success = self.db.add_transaction(project_id, amount, trans_type, payment_method, self.month, self.year, stage)
        if success:
            # 创建快捷方式
            print(f"创建快捷方式: year={self.year}, month={self.month}, project_name={project_name}, stage={stage}, original_year={selected_year}, project_month={project_month}")
            shortcut_success, result = self.file_manager.create_shortcut(self.year, self.month, project_name, stage, selected_year, project_month)
            if not shortcut_success:
                QMessageBox.warning(self, "提示", f"快捷方式创建失败: {result}")
            else:
                print(f"快捷方式创建成功: {result}")
            QMessageBox.information(self, "成功", "收支记录创建成功！")
            self.load_transactions()
        else:
            QMessageBox.warning(self, "失败", "保存收支记录失败！")

    def closeEvent(self, event):
        self.deleteLater()  # 确保窗口被销毁，触发 destroyed 信号
        super().closeEvent(event)

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MonthlyWindow("2025", 4)
    window.show()
    sys.exit(app.exec_())