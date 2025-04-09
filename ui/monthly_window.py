from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QVBoxLayout, QWidget,
                             QMenu, QInputDialog, QComboBox, QMessageBox, QHBoxLayout, QDialog, QTextEdit,
                             QTableWidgetItem, QHeaderView,QApplication, QLineEdit,QAction)
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt,QTimer
from database.db_manager import DatabaseManager
from utils.file_manager import FileManager
from ui.dialogs import EditTransactionDialog
import logging
import os
import sys
from datetime import datetime

# 定义收入类型的详情对话框
class DetailTextDialog(QDialog):
    def __init__(self, transaction, db_manager, file_manager, year, month, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.db = db_manager
        self.file_manager = file_manager
        self.year = year
        self.month = month
        self.setWindowTitle("文本记录")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(400, 300)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM remarks WHERE transaction_id = ?", (self.transaction[0],))
        remark = cursor.fetchone()
        conn.close()
        if remark:
            self.text_edit.setText(remark[0])
        layout.addWidget(self.text_edit)

        folder_button = QPushButton("项目资料")
        folder_button.clicked.connect(self.open_project_folder)
        layout.addWidget(folder_button)

        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_remark)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def open_project_folder(self):
        project_name = self.transaction[2]
        folder_path = os.path.join("项目资料", f"{self.year}年", f"{str(self.month).zfill(2)}月", project_name)
        if not os.path.exists(folder_path):
            shortcut_path = None
            base_path = os.path.join("项目资料", f"{self.year}年", f"{str(self.month).zfill(2)}月")
            for item in os.listdir(base_path):
                if item.startswith(project_name) and item.endswith(".lnk"):
                    shortcut_path = os.path.join(base_path, item)
                    break
            if shortcut_path and os.path.exists(shortcut_path):
                try:
                    if os.name == 'nt':
                        import win32com.client
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortCut(shortcut_path)
                        folder_path = shortcut.TargetPath
                    else:
                        folder_path = os.readlink(shortcut_path)
                except Exception as e:
                    QMessageBox.warning(self, "错误", f"无法解析快捷方式：{str(e)}")
                    return
        if os.path.exists(folder_path):
            if os.name == 'nt':
                os.startfile(folder_path)
            else:
                os.system(f"open {folder_path}")
        else:
            QMessageBox.warning(self, "错误", "项目文件夹不存在！")

    def save_remark(self):
        content = self.text_edit.toPlainText()
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO remarks (transaction_id, content, updated_at) VALUES (?, ?, ?)",
                       (self.transaction[0], content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        self.accept()

# 定义支出类型的详情对话框
class DetailExpenseDialog(QDialog):
    def __init__(self, transaction, db_manager, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.db = db_manager
        self.setWindowTitle("收支详情")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(1000, 1000)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["项目名称", "类型", "金额"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 500)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 250)
        # 设置编辑触发器：只允许双击或程序触发的编辑
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.resizeEvent = self.adjust_column_widths
        self.load_sub_transactions()
        layout.addWidget(self.table)
        self.table.itemChanged.connect(self.on_item_changed)  # 连接信号
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        add_button = QPushButton("新增项")
        add_button.clicked.connect(self.add_row)
        layout.addWidget(add_button)
        self.total_label = QLabel("总金额：0元")
        layout.addWidget(self.total_label)
        self.update_total()
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_details)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        menu = QMenu(self)
        delete_action = QAction("删除行", self)
        delete_action.triggered.connect(lambda: self.delete_row(row))
        menu.addAction(delete_action)
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def delete_row(self, row):
        self.table.removeRow(row)
        self.update_total()

    def save_details(self):
        # 首先保存数据
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expense_details WHERE transaction_id = ?", (self.transaction[0],))
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            if not name:
                QMessageBox.warning(self, "错误", "项目名称不能为空！")
                conn.close()
                return
            trans_type = self.table.cellWidget(row, 1).currentText()
            try:
                amount = float(self.table.item(row, 2).text() or 0)
                if amount <= 0:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "错误", "金额必须为正数！")
                conn.close()
                return
            cursor.execute("INSERT INTO expense_details (transaction_id, name, type, amount) VALUES (?, ?, ?, ?)",
                           (self.transaction[0], name, trans_type, amount))
        
        # 获取 initial_amount 并更新 amount    
        cursor.execute("SELECT initial_amount FROM transactions WHERE id = ?", (self.transaction[0],))
        initial_amount = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        # 在新连接中重新计算 details_total 并更新 amount
        conn = self.db.connect()
        cursor = conn.cursor()
        details_total = self.db.get_expense_details_total(self.transaction[0])
        new_amount = initial_amount + details_total
        cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amount, self.transaction[0]))
        conn.commit()
        conn.close()
        
        # 添加日志验证
        logging.info(f"Saving details: transaction_id={self.transaction[0]}, initial_amount={initial_amount}, details_total={details_total}, new_amount={new_amount}")
        
        # 通知父窗口刷新列表
        if self.parent() and hasattr(self.parent(), 'load_transactions'):
            logging.info("Calling parent.load_transactions()")
            self.parent().load_transactions()
        else:
            logging.warning("Parent or load_transactions not available")

        self.accept()

    def adjust_column_widths(self, event):
        total_width = self.table.viewport().width()
        self.table.setColumnWidth(0, int(total_width * 0.5))
        self.table.setColumnWidth(1, int(total_width * 0.25))
        self.table.setColumnWidth(2, int(total_width * 0.25))

    def load_sub_transactions(self):
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name, type, amount FROM expense_details WHERE transaction_id = ?", (self.transaction[0],))
        rows = cursor.fetchall()
        conn.close()
        self.table.setRowCount(len(rows))
        for row, (name, trans_type, amount) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            combo = QComboBox()
            combo.addItems(["收入", "支出"])
            combo.setCurrentText(trans_type)
            self.table.setCellWidget(row, 1, combo)
            self.table.setItem(row, 2, QTableWidgetItem(str(amount)))

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        self.table.setItem(row_count, 0, QTableWidgetItem("")) # 项目名称
        combo = QComboBox()
        combo.addItems(["收入", "支出"])
        self.table.setCellWidget(row_count, 1, combo) # 类型
        self.table.setItem(row_count, 2, QTableWidgetItem("0")) # 金额

    def update_total(self):
        total = 0
        for row in range(self.table.rowCount()):
            amount_item = self.table.item(row, 2)
            if amount_item is None or not amount_item.text():
                amount = 0
            else:
                try:
                    amount = float(amount_item.text())
                except ValueError:
                    amount = 0
            trans_type = self.table.cellWidget(row, 1).currentText()
            if trans_type == "收入":
                total += amount
            elif trans_type == "支出":
                total -= amount
        self.total_label.setText(f"总金额：{total}元")

    def on_item_changed(self, item):
        logging.info(f"Item changed: row={item.row()}, column={item.column()}, text={item.text()}")
        if item.column() == 2:  # 仅在金额列（第 2 列）发生变化时更新总金额
            self.update_total()

class EditTransactionDialog(QDialog):
    def __init__(self, transaction, db, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.db = db
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        self.amount_input = QLineEdit(str(self.transaction[8]))  # 显示 initial_amount
        self.type_combo = QComboBox()
        self.type_combo.addItems(["收入", "支出"])
        self.type_combo.setCurrentText(self.transaction[4])
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["微信", "支付宝", "对公账户", "对私账户", "现金"])
        self.payment_combo.setCurrentText(self.transaction[5])
        layout.addWidget(QLabel("金额（初始金额）："))
        layout.addWidget(self.amount_input)
        layout.addWidget(QLabel("类型："))
        layout.addWidget(self.type_combo)
        layout.addWidget(QLabel("支付方式："))
        layout.addWidget(self.payment_combo)
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.accept)
        layout.addWidget(save_button)
        self.setLayout(layout)

    def get_updated_data(self):
        return {
            "id": self.transaction[0],
            "amount": float(self.amount_input.text()),
            "type": self.type_combo.currentText(),
            "payment_method": self.payment_combo.currentText(),
            "name": self.transaction[2]  # 假设项目名称不变，若需修改需添加输入框
        }

class MonthlyWindow(QMainWindow):
    def __init__(self, year, month, parent=None):
        super().__init__(parent)
        self.year = year
        self.month = month
        self.db = DatabaseManager()
        self.file_manager = FileManager()
        # 记录初始列宽比例
        self.column_width_ratios = [2, 3, 1, 1, 1, 1, 1, 1]  # 创建时间:项目名称:金额:类型:支付方式:详情:修改:删除
        self.base_width = 100  # 基准宽度
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'{self.year}年{self.month}月详情')
        self.setMinimumSize(1800, 550)
        self.setWindowIcon(QIcon(r'D:\bcmanager\logo01.png'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["创建时间", "项目名称", "金额", "类型", "支付方式", "详情", "修改", "删除"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 设置初始列宽（临时值，避免挤在一起）
        for col, ratio in enumerate(self.column_width_ratios):
            self.table.setColumnWidth(col, int(self.base_width * ratio))

        # 允许手动拖动调整列宽
        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        
        button_layout = QHBoxLayout()
        create_button = QPushButton("创建")
        create_button.clicked.connect(self.show_create_dialog)
        filter_button = QPushButton("筛选")
        button_layout.addWidget(create_button)
        button_layout.addWidget(filter_button)
        layout.addLayout(button_layout)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.load_transactions()

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.table)

        # 延迟调整列宽，确保布局完成
        QTimer.singleShot(0, self.update_column_widths)

    def update_column_widths(self):
            total_width = self.table.viewport().width()
            # 确保最小总宽度，防止列宽过窄
            min_total_width = sum(ratio * self.base_width for ratio in self.column_width_ratios)
            total_width = max(total_width, min_total_width)
            
            total_ratio = sum(self.column_width_ratios)
            unit_width = total_width / total_ratio
            for col, ratio in enumerate(self.column_width_ratios):
                new_width = int(unit_width * ratio)
                # 确保每列至少有最小宽度
                new_width = max(new_width, 50)  # 最小宽度 50 像素
                self.table.setColumnWidth(col, new_width)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 窗口大小变化时，按比例调整列宽
        self.update_column_widths()

    def load_transactions(self):
        try:
            transactions = self.db.get_monthly_transactions(self.year, self.month)
            logging.info(f"Loaded {len(transactions)} transactions for {self.year}-{self.month}")
            for t in transactions:
                logging.info(f"Transaction: {t}")
            
            # 按类型排序：收入在前，支出在后   
            transactions = sorted(transactions, key=lambda x: (x[4] != "收入", x[1]))  # 按类型排序后，再按创建时间排序

            self.table.setRowCount(len(transactions))
            for row, (id, created_at, name, amount, trans_type, payment_method, stage, status, initial_amount) in enumerate(transactions):
                created_at_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                formatted_time = created_at_dt.strftime("%Y年%m月%d日%H时%M分")
                # 创建时间居中
                time_item = QTableWidgetItem(formatted_time)
                time_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, time_item)

                display_name = f"{name}（{stage}）" if stage else name
                name_item = QTableWidgetItem(display_name)
                if trans_type == "收入" and status == "已结项":
                    name_item.setBackground(QColor("lightgreen"))
                # 项目名称居中
                name_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, name_item)    
                
                # 金额居中
                amount_item = QTableWidgetItem(str(amount))
                amount_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, amount_item)
                # 类型居中
                type_item = QTableWidgetItem(trans_type)
                type_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, type_item)
                # 支付方式居中
                payment_item = QTableWidgetItem(payment_method)
                payment_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 4, payment_item)

                detail_button = QPushButton("详情")
                detail_button.clicked.connect(lambda checked, r=row: self.show_detail_dialog(r))
                self.table.setCellWidget(row, 5, detail_button)

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
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        col = item.column()
        if col != 1:
            return
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        trans_type = transaction[4]
        if trans_type != "收入":
            return
        menu = QMenu(self)
        action_unsettled = QAction("未结项", self)
        action_settled = QAction("已结项", self)
        menu.addAction(action_unsettled)
        menu.addAction(action_settled)
        action_unsettled.triggered.connect(lambda: self.set_transaction_status(row, "未结项"))
        action_settled.triggered.connect(lambda: self.set_transaction_status(row, "已结项"))
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def set_transaction_status(self, row, status):
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        transaction_id = transaction[0]
        success = self.db.update_transaction_status(transaction_id, status)
        if success:
            name_item = self.table.item(row, 1)
            if status == "已结项":
                name_item.setBackground(QColor("lightgreen"))
            else:
                name_item.setBackground(QColor("white"))
            QMessageBox.information(self, "成功", f"状态已更新为: {status}")
        else:
            QMessageBox.warning(self, "失败", "状态更新失败！")

    def edit_transaction(self, row):
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        old_project_name = transaction[2]
        dialog = EditTransactionDialog(transaction, self.db, parent=self)
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
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        transaction_id = transaction[0]
        project_name = transaction[2]
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除项目 '{project_name}' 的这条收支记录吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
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
            is_only_project_in_month = (project_transactions == 1 and total_transactions == 1)
            success = self.db.delete_transaction(transaction_id)
            if success:
                delete_success, result = self.file_manager.delete_project_folder(
                    self.year, self.month, project_name, is_only_project_in_month
                )
                if not delete_success:
                    QMessageBox.warning(self, "警告", f"项目文件夹删除失败: {result}")
                QMessageBox.information(self, "成功", "收支记录删除成功！")
                self.load_transactions()
            else:
                QMessageBox.warning(self, "失败", "收支记录删除失败！")

    def show_detail_dialog(self, row):
        transaction = self.db.get_monthly_transactions(self.year, self.month)[row]
        if transaction[4] == "收入":
            dialog = DetailTextDialog(transaction, self.db, self.file_manager, self.year, self.month, parent=self)
            dialog.exec_()
        else:
            dialog = DetailExpenseDialog(transaction, self.db, parent=self)
            dialog.exec_()

    def show_create_dialog(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("创建收支记录")
        dialog.setLabelText("请选择创建方式：")
        dialog.setComboBoxItems(["创建新项目", "选择已有项目"])
        dialog.setOption(QInputDialog.NoButtons, False)
        dialog.setComboBoxEditable(False)
        dialog.resize(400, 250)
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowTitleHint)
        dialog.setFixedSize(500, 350)
        if dialog.exec_():
            choice = dialog.textValue()
            if choice == "创建新项目":
                self.create_new_project_transaction()
            elif choice == "选择已有项目":
                self.create_existing_project_transaction()

    def create_new_project_transaction(self):
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        transaction_year = int(self.year)
        transaction_month = int(self.month)
        if transaction_year > current_year or (transaction_year == current_year and transaction_month > current_month):
            QMessageBox.warning(self, "错误", f"不能为未来的月份创建项目！当前日期：{current_year}年{current_month}月")
            return
        project_name, ok = QInputDialog.getText(self, "创建新项目", "请输入项目名称：")
        if not ok or not project_name:
            return
        amount, ok = QInputDialog.getDouble(self, "输入金额", "请输入金额：", value=0.0, min=0.01, max=9999999.99, decimals=2)
        if not ok:
            return
        trans_type, ok = QInputDialog.getItem(self, "选择类型", "请选择收支类型：", ["收入", "支出"], 0, False)
        if not ok:
            return
        payment_method, ok = QInputDialog.getItem(self, "选择支付方式", "请选择支付方式：",
                                                  ["微信", "支付宝", "对公账户", "对私账户", "现金"], 0, False)
        if not ok:
            return
        confirm_msg = f"项目名称: {project_name}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
        reply = QMessageBox.question(self, "确认创建", confirm_msg, QMessageBox.Ok | QMessageBox.Cancel)
        if reply != QMessageBox.Ok:
            return
        success, project_id = self.db.add_project(project_name, self.year, self.month)
        if success and project_id:
            year_int = int(self.year)
            month_int = int(self.month)
            success = self.db.add_transaction(project_id, amount, trans_type, payment_method, month_int, year_int)
            if success:
                folder_success, result = self.file_manager.create_project_folder(self.year, self.month, project_name)
                if not folder_success:
                    QMessageBox.warning(self, "失败", f"创建文件夹失败: {result}")
                else:
                    QMessageBox.information(self, "成功", "收支记录创建成功！")
                    self.load_transactions()
            else:
                QMessageBox.warning(self, "失败", "保存收支记录失败！")
        else:
            QMessageBox.warning(self, "失败", f"创建项目失败！请确保年份 {self.year} 已存在。")

    def create_existing_project_transaction(self):
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        transaction_year = int(self.year)
        transaction_month = int(self.month)
        if transaction_year > current_year or (transaction_year == current_year and transaction_month > current_month):
            QMessageBox.warning(self, "错误", f"不能为未来的月份创建收支记录！当前日期：{current_year}年{current_month}月")
            return
        # 获取所有年份
        all_years = self.db.get_years()
        years = [year for year in all_years if int(year) <= current_year]
        if not years:
            QMessageBox.warning(self, "错误", "数据库中没有年份记录，请先创建年份！")
            return
        # 选择年份
        selected_year, ok = QInputDialog.getItem(self, "选择年份", "请选择项目所属年份：", years, 0, False)
        if not ok:
            return
        
        # 获取指定年份的非阶段性收入项目
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT p.id, p.name, p.month
            FROM projects p
            JOIN transactions t ON p.id = t.project_id
            WHERE p.year_id = (SELECT id FROM years WHERE year = ?)
            AND t.type = '收入'
            AND t.stage IS NULL
        """, (selected_year,))
        projects = cursor.fetchall()
        conn.close()

        if not projects:
            QMessageBox.warning(self, "错误", f"{selected_year} 年没有非阶段性的收入类型项目！")
            return
        project_names = [p[1] for p in projects]
        project_ids = {p[1]: p[0] for p in projects}
        project_months = {p[1]: p[2] for p in projects}  # 保存项目的创建月份

        # 选择项目
        project_name, ok = QInputDialog.getItem(self, "选择项目", "请选择已有收入项目（非阶段性）：", project_names, 0, False)
        if not ok:
            return
        project_id = project_ids[project_name]
        project_month = project_months[project_name]  # 获取项目的创建月份
        if project_month is None:
            QMessageBox.critical(self, "错误", f"项目 {project_name} 的创建月份未定义，请联系管理员检查数据库！")
            return

        # 选择阶段
        stages = ["第二阶段", "第三阶段", "第四阶段"]
        stage, ok = QInputDialog.getItem(self, "选择阶段", "请选择项目阶段：", stages, 0, False)
        if not ok:
            return
        
        # 输入金额
        amount, ok = QInputDialog.getDouble(self, "输入金额", "请输入金额（正数）：", value=0.0, min=0.01, max=9999999.99, decimals=2)
        if not ok:
            return
        # 选择类型
        trans_type, ok = QInputDialog.getItem(self, "选择类型", "请选择收支类型：", ["收入", "支出"], 0, False)
        if not ok:
            return
        # 选择支付方式
        payment_method, ok = QInputDialog.getItem(self, "选择支付方式", "请选择支付方式：",
                                                  ["微信", "支付宝", "对公账户", "对私账户", "现金"], 0, False)
        if not ok:
            return
        # 确认创建
        confirm_msg = f"项目名称: {project_name}\n阶段: {stage}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
        reply = QMessageBox.question(self, "确认创建", confirm_msg, QMessageBox.Ok | QMessageBox.Cancel)
        if reply != QMessageBox.Ok:
            return
        # 保存交易记录
        success = self.db.add_transaction(project_id, amount, trans_type, payment_method, self.month, self.year, stage)
        if success:
            if trans_type == "收入":  # 如果是收入类型，创建快捷方式
                shortcut_success, result = self.file_manager.create_shortcut(self.year, self.month, project_name, stage, selected_year, project_month)
                if not shortcut_success:
                    QMessageBox.warning(self, "提示", f"快捷方式创建失败: {result}")
            QMessageBox.information(self, "成功", "收支记录创建成功！")
            self.load_transactions()
        else:
            QMessageBox.warning(self, "失败", "保存收支记录失败！")

    def closeEvent(self, event):
        self.deleteLater()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MonthlyWindow("2025", 4)
    window.show()
    sys.exit(app.exec_())