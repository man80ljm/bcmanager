from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QVBoxLayout, QWidget,
                             QMenu, QInputDialog, QComboBox, QMessageBox, QHBoxLayout, QDialog, QTextEdit,
                             QTableWidgetItem, QHeaderView,QApplication, QLineEdit,QAction, QCheckBox,)
from PyQt5.QtGui import QIcon, QColor,QFont, QFontMetrics
from PyQt5.QtCore import Qt,QTimer
from database.db_manager import DatabaseManager
from utils.file_manager import FileManager
from ui.dialogs import EditTransactionDialog
import logging
import os
import sys
from datetime import datetime
import resources


# 定义收入类型的详情对话框
class DetailTextDialog(QDialog):
    def __init__(self, transaction, db_manager, file_manager, year, month, parent=None):
        super().__init__(parent)
        self.transaction = transaction
        self.db = db_manager
        self.file_manager = file_manager
        self.year = year
        self.month = month
        self.base_dir = file_manager.base_dir  # 使用 FileManager 的 base_dir
        # 修改标题，包含项目名称
        project_name = self.transaction[2]  # 项目名称在 transaction 的第 3 个字段
        stage = self.transaction[6]  # stage 在 transaction 的第 7 个字段
        # 如果 stage 不为空，显示阶段信息；否则只显示项目名称
        title = f"{project_name}（{stage}） - 文本记录" if stage else f"{project_name} - 文本记录"
        self.setWindowTitle(title)
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
        # stage = self.transaction[6]  # 阶段信息
        folder_path = os.path.join(self.base_dir, f"{self.year}年", f"{str(self.month).zfill(2)}月", project_name)
        # 如果文件夹不存在，尝试查找快捷方式
        if not os.path.exists(folder_path):
            shortcut_path = None
            base_path = os.path.join(self.base_dir, f"{self.year}年", f"{str(self.month).zfill(2)}月")
            # 检查 base_path 是否存在
            if not os.path.exists(base_path):
                QMessageBox.warning(self, "错误", f"月份文件夹不存在：{base_path}")
                return
            # 查找以 project_name 开头的快捷方式
            try:
                for item in os.listdir(base_path):
                    if item.startswith(project_name) and item.endswith(".lnk"):
                        shortcut_path = os.path.join(base_path, item)
                        break
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法访问月份文件夹：{str(e)}")
                return
            # 如果找到快捷方式，解析其目标路径
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
        # 最后检查 folder_path 是否存在并打开
        if os.path.exists(folder_path):
            try:
                if os.name == 'nt':
                    os.startfile(folder_path)
                else:
                    os.system(f"open {folder_path}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开文件夹：{str(e)}")
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
        # 修改标题，包含项目名称和阶段信息
        project_name = self.transaction[2]  # 项目名称在 transaction 的第 3 个字段
        stage = self.transaction[6]  # stage 在 transaction 的第 7 个字段
        # 如果 stage 不为空，显示阶段信息；否则只显示项目名称
        title = f"{project_name}（{stage}） - 收支详情" if stage else f"{project_name} - 收支详情"
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setMinimumSize(600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # 设置字体为 Microsoft YaHei，20 号，带备选字体
        font = QFont()
        font.setFamily("Microsoft YaHei, SimSun, Arial")
        font.setPointSize(20)

        # 初始化表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["项目名称", "类型", "金额"])
        
        # 设置表格列名字体
        header = self.table.horizontalHeader()
        header.setFont(font)  # 列名字体设置为 20 号
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 500)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 250)
        
        # 设置表格内容字体
        self.table.setFont(font)  # 表格单元格内容字体设置为 20 号
        
        # 设置编辑触发器
        self.table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.table.resizeEvent = self.adjust_column_widths
        self.load_sub_transactions()
        layout.addWidget(self.table)
        
        # 连接信号
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        # 新增项按钮
        add_button = QPushButton("新增项")
        add_button.setFont(font)  # 按钮字体设置为 20 号
        add_button.clicked.connect(self.add_row)
        layout.addWidget(add_button)
        
        # 总金额标签
        self.total_label = QLabel("总金额：0元")
        self.total_label.setFont(font)  # 标签字体设置为 20 号
        layout.addWidget(self.total_label)
        self.update_total()
        
        # 保存按钮
        save_button = QPushButton("保存")
        save_button.setFont(font)  # 按钮字体设置为 20 号
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
            combo.setFont(QFont("Microsoft YaHei, SimSun, Arial", 20))  # 组合框字体设置为 20 号
            self.table.setCellWidget(row, 1, combo)
            self.table.setItem(row, 2, QTableWidgetItem(str(amount)))

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        self.table.setItem(row_count, 0, QTableWidgetItem("")) # 项目名称
        combo = QComboBox()
        combo.addItems(["收入", "支出"])
        combo.setFont(QFont("Microsoft YaHei, SimSun, Arial", 20))  # 组合框字体设置为 20 号
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
            # 修改标题，包含项目名称和阶段信息
            project_name = self.transaction[2]  # 项目名称在 transaction 的第 3 个字段
            stage = self.transaction[6]  # stage 在 transaction 的第 7 个字段
            # 如果 stage 不为空，显示阶段信息；否则只显示项目名称
            title = f"修改 - {project_name}（{stage}）" if stage else f"修改 - {project_name}"
            self.setWindowTitle(title)
            self.setWindowIcon(QIcon(':/logo01.png'))  # 设置窗口图标
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
            self.setMinimumSize(400, 300)
            self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 项目名称输入框
        self.name_label = QLabel("项目名称:")
        stage = self.transaction[6]  # stage 在 transaction 的第 7 个字段
        display_name = f"{self.transaction[2]}（{stage}）" if stage else self.transaction[2]
        self.name_input = QLineEdit(display_name)  # 显示项目名称和阶段信息
        self.name_input.setPlaceholderText("请输入项目名称")
        
        # 检查该项目是否为阶段性项目
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions 
            WHERE project_id = (SELECT project_id FROM transactions WHERE id = ?)
        """, (self.transaction[0],))
        transaction_count = cursor.fetchone()[0]
        conn.close()

        # 如果该项目有超过一条记录，且当前记录有 stage，禁用名称编辑
        if transaction_count > 1 and self.transaction[6]:  # transaction[6] 是 stage
            self.name_input.setEnabled(False)
            self.name_input.setToolTip("已有项目的后续阶段不可修改名称")
        
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        # 阶段选择（仅对阶段性项目显示）
        self.stage_label = QLabel("阶段:")
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["第二阶段", "第三阶段", "第四阶段"])  # 可根据需求扩展
        if self.transaction[6]:  # 如果是阶段性项目
            self.stage_combo.setCurrentText(self.transaction[6])
        else:
            self.stage_combo.setEnabled(False)  # 非阶段性项目禁用
            self.stage_combo.setToolTip("仅阶段性项目可修改阶段")
        layout.addWidget(self.stage_label)
        layout.addWidget(self.stage_combo)

        # 金额输入框
        self.amount_input = QLineEdit(str(self.transaction[8]))  # 显示 initial_amount
        self.amount_input.setPlaceholderText("请输入金额（正数）")
        layout.addWidget(QLabel("金额（初始金额）："))
        layout.addWidget(self.amount_input)

        # 类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems(["收入", "支出"])
        self.type_combo.setCurrentText(self.transaction[4])
        layout.addWidget(QLabel("类型："))
        layout.addWidget(self.type_combo)

        # 支付方式选择
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["微信", "支付宝", "对公账户", "对私账户", "现金"])
        self.payment_combo.setCurrentText(self.transaction[5])
        layout.addWidget(QLabel("支付方式："))
        layout.addWidget(self.payment_combo)

        # 保存按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.validate_and_accept)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def validate_and_accept(self):
        """验证输入并接受修改"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "项目名称不能为空！")
            return
        
        # 验证金额
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                QMessageBox.warning(self, "错误", "金额必须为正数！")
                return
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的金额（数字）！")
            return

        self.accept()

    def get_updated_data(self):
        # 去掉名称中的阶段信息（如果有）
        name = self.name_input.text().strip()
        stage = self.transaction[6]
        # 循环去掉所有可能的阶段信息
        while stage and name.endswith(f"（{stage}）"):
            name = name[:-len(f"（{stage}）")]
        return {
            "id": self.transaction[0],
            "amount": float(self.amount_input.text()),
            "type": self.type_combo.currentText(),
            "payment_method": self.payment_combo.currentText(),
            "name": name,  # 使用去掉阶段信息的名称
            "stage": self.stage_combo.currentText() if self.stage_combo.isEnabled() else None  # 返回新阶段
        }

class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("筛选")
        self.setFixedSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去掉疑问号
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 状态筛选
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("未结项"))
        self.status_unsettled = QCheckBox()
        status_layout.addWidget(self.status_unsettled)
        status_layout.addWidget(QLabel("已结项"))
        self.status_settled = QCheckBox()
        status_layout.addWidget(self.status_settled)
        layout.addLayout(status_layout)

        # 阶段筛选
        stage_layout = QHBoxLayout()
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["", "第二阶段", "第三阶段", "第四阶段"])
        stage_layout.addWidget(QLabel("阶段"))
        stage_layout.addWidget(self.stage_combo)
        layout.addLayout(stage_layout)

        # 类型筛选
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("收入"))
        self.type_income = QCheckBox()
        type_layout.addWidget(self.type_income)
        type_layout.addWidget(QLabel("支出"))
        self.type_expense = QCheckBox()
        type_layout.addWidget(self.type_expense)
        layout.addLayout(type_layout)

        # 支付方式筛选
        payment_layout = QHBoxLayout()
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["", "微信", "支付宝", "对公账户", "对私账户", "现金"])
        payment_layout.addWidget(QLabel("支付方式"))
        payment_layout.addWidget(self.payment_combo)
        layout.addLayout(payment_layout)

        # 金额筛选
        amount_layout = QHBoxLayout()
        self.amount_min = QLineEdit()
        self.amount_max = QLineEdit()
        amount_layout.addWidget(QLabel("现金额"))
        amount_layout.addWidget(self.amount_min)
        amount_layout.addWidget(QLabel("至"))
        amount_layout.addWidget(self.amount_max)
        layout.addLayout(amount_layout)

        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("CANCEL")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_filters(self):
        filters = {}
        # 状态
        statuses = []
        if self.status_unsettled.isChecked():
            statuses.append("未结项")
        if self.status_settled.isChecked():
            statuses.append("已结项")
        if statuses:
            filters["status"] = statuses

        # 阶段
        stage = self.stage_combo.currentText()
        if stage:
            filters["stage"] = stage

        # 类型
        types = []
        if self.type_income.isChecked():
            types.append("收入")
        if self.type_expense.isChecked():
            types.append("支出")
        if types:
            filters["type"] = types

        # 支付方式
        payment_method = self.payment_combo.currentText()
        if payment_method:
            filters["payment_method"] = payment_method

        # 金额范围
        amount_min = self.amount_min.text()
        amount_max = self.amount_max.text()
        if amount_min:
            try:
                filters["amount_min"] = float(amount_min)
            except ValueError:
                pass
        if amount_max:
            try:
                filters["amount_max"] = float(amount_max)
            except ValueError:
                pass

        return filters

class MonthlyWindow(QMainWindow):
    def __init__(self, year, month, parent=None):
            super().__init__(parent)
            self.year = year
            self.month = month
            self.db = DatabaseManager()
            self.file_manager = FileManager()
            # 缓存 year_id
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM years WHERE year = ?", (self.year,))
            self.year_id = cursor.fetchone()[0]
            conn.close()
            # 记录初始列宽比例
            self.column_width_ratios = [2, 3, 1, 1, 1, 1, 1, 1]  # 创建时间:项目名称:金额:类型:支付方式:详情:修改:删除
            self.base_width = 100  # 基准宽度
            self.initUI()

    def create_styled_message_box(self, title, text, buttons=QMessageBox.Ok):
        """创建样式统一的 QMessageBox"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setStandardButtons(buttons)
        # 设置字体为 Microsoft YaHei，20 号，带备选字体
        font = QFont()
        font.setFamily("Microsoft YaHei, SimSun, Arial")
        font.setPointSize(20)
        msg.setFont(font)
        # 设置样式表：仅调整文本间距（按钮样式已通过全局样式表设置）
        msg.setStyleSheet("QLabel { font-family: 'Microsoft YaHei, SimSun, Arial'; font-size: 20pt; padding: 10px; }")
        # 根据文本长度动态调整宽度
        width = 500 if len(text) > 20 else 400
        msg.setFixedWidth(width)
        # 添加日志记录
        logging.info(f"Created styled message box: title={title}, text={text}, width={width}")
        return msg

    def initUI(self):
        self.setWindowTitle(f'{self.year}年{self.month}月详情')
        self.setMinimumSize(1800, 550)
        self.setWindowIcon(QIcon(':/logo01.png'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 按钮布局（创建和筛选按钮）
        button_layout = QHBoxLayout()
        create_button = QPushButton("创建")
        create_button.clicked.connect(self.show_create_dialog)
        filter_button = QPushButton("筛选")
        filter_button.clicked.connect(self.show_filter_dialog)
        button_layout.addWidget(create_button)
        button_layout.addWidget(filter_button)
        layout.addLayout(button_layout)

        # 初始化表格
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["创建时间", "项目名称", "金额", "类型", "支付方式", "详情", "修改", "删除"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        # 设置表格内容字体（20 号）
        content_font = QFont()
        content_font.setPointSize(20)
        self.table.setFont(content_font)

        # 设置表头字体（20 号）
        header_font = QFont()
        header_font.setPointSize(20)
        self.table.horizontalHeader().setFont(header_font)

        # 设置初始列宽
        for col, ratio in enumerate(self.column_width_ratios):
            self.table.setColumnWidth(col, int(self.base_width * ratio))

        # 设置初始行高（动态计算，适应 20 号字体）
        row_height = QFontMetrics(content_font).height() + 20  # 字体高度加 20 像素余量
        self.table.verticalHeader().setDefaultSectionSize(row_height)

        # 允许手动拖动调整列宽
        header = self.table.horizontalHeader()
        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.Interactive)

        # 添加表格到布局
        layout.addWidget(self.table)

        # 初始化并设置 summary_label（移到表格下方）
        self.summary_label = QLabel()
        summary_font = QFont()
        summary_font.setPointSize(20)
        self.summary_label.setFont(summary_font)
        layout.addWidget(self.summary_label)

        # 加载交易记录（会更新 summary_label 内容）
        self.load_transactions()

        # 设置右键菜单
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # 延迟调整列宽
        QTimer.singleShot(0, self.update_column_widths)

    def show_filter_dialog(self):
        logging.info("Showing filter dialog")  # 添加日志
        dialog = FilterDialog(self)
        if dialog.exec_():
            filters = dialog.get_filters()
            logging.info(f"Filters applied: {filters}")  # 添加日志
            self.apply_filters(filters)

    def apply_filters(self, filters):
        logging.info("Applying filters")  # 添加日志
        self.filters = filters  # 保存筛选条件
        self.load_transactions()  # 重新加载表格

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
                # 构建动态查询
                query = """
                    SELECT t.id, t.created_at, p.name, t.amount, t.type, t.payment_method, t.stage, t.status, t.initial_amount
                    FROM transactions t
                    LEFT JOIN projects p ON t.project_id = p.id
                    WHERE t.year_id = (SELECT id FROM years WHERE year = ?) AND t.month = ?
                """
                params = [self.year, self.month]

                # 添加筛选条件
                conditions = []
                if hasattr(self, 'filters'):
                    if "status" in self.filters:
                        conditions.append("t.status IN ({})".format(",".join("?" for _ in self.filters["status"])))
                        params.extend(self.filters["status"])
                    if "stage" in self.filters:
                        conditions.append("t.stage = ?")
                        params.append(self.filters["stage"])
                    if "type" in self.filters:
                        conditions.append("t.type IN ({})".format(",".join("?" for _ in self.filters["type"])))
                        params.extend(self.filters["type"])
                    if "payment_method" in self.filters:
                        conditions.append("t.payment_method = ?")
                        params.append(self.filters["payment_method"])
                    if "amount_min" in self.filters:
                        conditions.append("t.amount >= ?")
                        params.append(self.filters["amount_min"])
                    if "amount_max" in self.filters:
                        conditions.append("t.amount <= ?")
                        params.append(self.filters["amount_max"])

                if conditions:
                    query += " AND " + " AND ".join(conditions)

                # 执行查询
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute(query, params)
                transactions = cursor.fetchall()
                conn.close()
                
                # 按类型排序：收入在前，支出在后
                transactions = sorted(transactions, key=lambda x: (x[4] != "收入", x[1]))  # 按类型排序后，再按创建时间排序
                
                # 更新表格
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

                    # 直接传递 transaction_id，而不是行号
                    detail_button = QPushButton("详情")
                    detail_button.setProperty("transaction_id", id)  # 存储 transaction_id
                    detail_button.clicked.connect(lambda checked, tid=id: self.show_detail_dialog(tid))
                    self.table.setCellWidget(row, 5, detail_button)

                    edit_button = QPushButton("修改")
                    edit_button.setProperty("transaction_id", id)  # 存储 transaction_id
                    edit_button.clicked.connect(lambda checked, tid=id: self.edit_transaction(tid))
                    self.table.setCellWidget(row, 6, edit_button)

                    delete_button = QPushButton("删除")
                    delete_button.setProperty("transaction_id", id)  # 存储 transaction_id
                    delete_button.clicked.connect(lambda checked, tid=id: self.delete_transaction(tid))
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
            if col != 1:  # 只在项目名称列显示菜单
                return
            # 获取排序后的交易记录
            transactions = self.db.get_monthly_transactions(self.year, self.month)
            transactions = sorted(transactions, key=lambda x: (x[4] != "收入", x[1]))
            transaction = transactions[row]
            trans_type = transaction[4]
            if trans_type != "收入":  # 仅对收入项目显示状态菜单
                return
            menu = QMenu(self)
            action_unsettled = QAction("未结项", self)
            action_settled = QAction("已结项", self)
            menu.addAction(action_unsettled)
            menu.addAction(action_settled)
            action_unsettled.triggered.connect(lambda: self.set_transaction_status(transaction[0], "未结项"))
            action_settled.triggered.connect(lambda: self.set_transaction_status(transaction[0], "已结项"))
            menu.exec_(self.table.viewport().mapToGlobal(pos))

    def set_transaction_status(self, transaction_id, status):
        logging.info(f"Setting transaction status: transaction_id={transaction_id}, status={status}")
        success = self.db.update_transaction_status(transaction_id, status)
        if success:
            # 找到对应的行并更新背景颜色
            for row in range(self.table.rowCount()):
                # 从详情按钮的属性中获取 transaction_id
                detail_button = self.table.cellWidget(row, 5)
                tid = detail_button.property("transaction_id")
                if tid == transaction_id:
                    name_item = self.table.item(row, 1)
                    trans_type = self.table.item(row, 3).text()  # 获取类型
                    # 仅对收入项目更新颜色
                    if status == "已结项": 
                        name_item.setBackground(QColor("lightgreen"))
                    else:
                        name_item.setBackground(QColor("white"))
                    break
            logging.info(f"Transaction {transaction_id} status updated to {status}, UI updated")
            QMessageBox.information(self, "成功", f"状态已更新为: {status}")
        else:
            logging.error(f"Failed to update transaction {transaction_id} status to {status}")
            QMessageBox.warning(self, "失败", "状态更新失败！")

    def edit_transaction(self, transaction_id):
        logging.info(f"Editing transaction with id {transaction_id}")
        # 第一次查询：加载记录以显示在对话框中
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.created_at, p.name, t.amount, t.type, t.payment_method, t.stage, t.status, t.initial_amount
            FROM transactions t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.id = ?
        """, (transaction_id,))
        transaction = cursor.fetchone()
        conn.close()

        if not transaction:
            logging.error(f"Transaction with id {transaction_id} not found before showing dialog")
            error_dialog = self.create_styled_message_box("错误", "交易记录不存在！")
            error_dialog.exec_()
            return

        old_project_name = transaction[2]
        dialog = EditTransactionDialog(transaction, self.db, parent=self)
        if dialog.exec_():
            updated_data = dialog.get_updated_data()
            
            # 第二次查询：在更新之前再次验证记录是否存在
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM transactions WHERE id = ?", (updated_data["id"],))
            exists = cursor.fetchone()
            conn.close()

            if not exists:
                logging.error(f"Transaction with id {updated_data['id']} not found before update")
                error_dialog = self.create_styled_message_box("错误", "交易记录已被删除，无法更新！")
                error_dialog.exec_()
                self.load_transactions()
                return

            logging.info(f"Calling update_transaction with: id={updated_data['id']}, amount={updated_data['amount']}, type={updated_data['type']}, payment_method={updated_data['payment_method']}, stage={updated_data['stage']}")
            result = self.db.update_transaction(
                updated_data["id"], updated_data["amount"], updated_data["type"], 
                updated_data["payment_method"], updated_data["stage"]
            )
            logging.info(f"update_transaction result: {result}")
            if not isinstance(result, tuple) or len(result) != 4:
                logging.error(f"Unexpected result from update_transaction: {result}")
                error_dialog = self.create_styled_message_box("错误", "更新收支记录失败：返回值格式错误")
                error_dialog.exec_()
                return
            success, old_type, new_type, old_stage = result

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
                        warning_dialog = self.create_styled_message_box("警告", f"项目文件夹重命名失败: {result}")
                        warning_dialog.exec_()
                    else:
                        update_success, update_result = self.file_manager.update_shortcuts(
                            old_project_name, updated_data["name"], project_year, project_month
                        )
                        if not update_success:
                            warning_dialog = self.create_styled_message_box("警告", f"快捷方式更新失败: {update_result}")
                            warning_dialog.exec_()
            if success:
                if old_stage != updated_data["stage"] and updated_data["stage"]:
                    shortcut_success, shortcut_result = self.file_manager.delete_shortcut(
                        self.year, self.month, old_project_name, old_stage
                    )
                    if not shortcut_success:
                        warning_dialog = self.create_styled_message_box("警告", f"旧快捷方式删除失败: {shortcut_result}")
                        warning_dialog.exec_()
                    
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT p.year_id, p.month 
                        FROM transactions t 
                        JOIN projects p ON t.project_id = p.id 
                        WHERE t.id = ?
                    """, (updated_data["id"],))
                    year_id, original_month = cursor.fetchone()
                    cursor.execute("SELECT year FROM years WHERE id = ?", (year_id,))
                    original_year = cursor.fetchone()[0]
                    conn.close()
                    
                    shortcut_success, shortcut_result = self.file_manager.create_shortcut(
                        self.year, self.month, updated_data["name"], updated_data["stage"], 
                        original_year, original_month
                    )
                    if not shortcut_success:
                        warning_dialog = self.create_styled_message_box("提示", f"快捷方式创建失败: {shortcut_result}")
                        warning_dialog.exec_()

                if old_type == "收入" and new_type == "支出":
                    if updated_data["stage"]:
                        shortcut_success, shortcut_result = self.file_manager.delete_shortcut(
                            self.year, self.month, old_project_name, updated_data["stage"]
                        )
                        if not shortcut_success:
                            warning_dialog = self.create_styled_message_box("警告", f"快捷方式删除失败: {shortcut_result}")
                            warning_dialog.exec_()
                    else:
                        delete_success, delete_result = self.file_manager.delete_project_folder(
                            self.year, self.month, old_project_name, is_only_project_in_month=True
                        )
                        if not delete_success:
                            warning_dialog = self.create_styled_message_box("警告", f"项目文件夹删除失败: {delete_result}")
                            warning_dialog.exec_()
                elif old_type == "支出" and new_type == "收入":
                    if updated_data["stage"]:
                        conn = self.db.connect()
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT p.year_id, p.month 
                            FROM transactions t 
                            JOIN projects p ON t.project_id = p.id 
                            WHERE t.id = ?
                        """, (updated_data["id"],))
                        year_id, original_month = cursor.fetchone()
                        cursor.execute("SELECT year FROM years WHERE id = ?", (year_id,))
                        original_year = cursor.fetchone()[0]
                        conn.close()
                        shortcut_success, shortcut_result = self.file_manager.create_shortcut(
                            self.year, self.month, updated_data["name"], updated_data["stage"],
                            original_year, original_month
                        )
                        if not shortcut_success:
                            warning_dialog = self.create_styled_message_box("提示", f"快捷方式创建失败: {shortcut_result}")
                            warning_dialog.exec_()
                    else:
                        folder_success, folder_result = self.file_manager.create_project_folder(
                            self.year, self.month, updated_data["name"]
                        )
                        if not folder_success:
                            warning_dialog = self.create_styled_message_box("失败", f"创建文件夹失败: {folder_result}")
                            warning_dialog.exec_()

                info_dialog = self.create_styled_message_box("成功", "收支记录修改成功！")
                info_dialog.exec_()
                self.load_transactions()
            else:
                warning_dialog = self.create_styled_message_box("失败", "收支记录修改失败！")
                warning_dialog.exec_()
                
    def delete_transaction(self, transaction_id):
        # 通过 transaction_id 获取交易记录
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, p.name, t.stage, t.type
            FROM transactions t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.id = ?
        """, (transaction_id,))
        transaction = cursor.fetchone()
        conn.close()

        if not transaction:
            error_dialog = self.create_styled_message_box("错误", "交易记录不存在！")
            error_dialog.exec_()
            return

        transaction_id, project_name, stage, trans_type = transaction
        confirm_dialog = self.create_styled_message_box(
            "确认删除",
            f"确定要删除项目 '{project_name}' 的这条收支记录吗？",
            buttons=QMessageBox.Yes | QMessageBox.No
        )
        reply = confirm_dialog.exec_()

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
            # 删除数据库记录
            success = self.db.delete_transaction(transaction_id)
            if success:
                # 根据类型和阶段决定是否删除文件夹/快捷方式
                if trans_type == "收入":
                    if stage:  # 阶段性项目，删除快捷方式
                        shortcut_success, shortcut_result = self.file_manager.delete_shortcut(
                            self.year, self.month, project_name, stage
                        )
                        if not shortcut_success:
                            warning_dialog = self.create_styled_message_box("警告", f"快捷方式删除失败: {shortcut_result}")
                            warning_dialog.exec_()
                    else:  # 新项目，删除项目文件夹
                        delete_success, result = self.file_manager.delete_project_folder(
                            self.year, self.month, project_name, is_only_project_in_month
                        )
                        if not delete_success:
                            warning_dialog = self.create_styled_message_box("警告", f"项目文件夹删除失败: {result}")
                            warning_dialog.exec_()
                else:  # 支出项目，理论上没有文件夹，但仍检查并清理
                    if stage:  # 阶段性项目，检查并删除可能的快捷方式
                        shortcut_success, shortcut_result = self.file_manager.delete_shortcut(
                            self.year, self.month, project_name, stage
                        )
                        if not shortcut_success:
                            warning_dialog = self.create_styled_message_box("警告", f"快捷方式删除失败: {shortcut_result}")
                            warning_dialog.exec_()
                    else:  # 新项目，检查并删除可能的项目文件夹
                        delete_success, result = self.file_manager.delete_project_folder(
                            self.year, self.month, project_name, is_only_project_in_month
                        )
                        if not delete_success:
                            warning_dialog = self.create_styled_message_box("警告", f"项目文件夹删除失败: {result}")
                            warning_dialog.exec_()

                info_dialog = self.create_styled_message_box("成功", "收支记录删除成功！")
                info_dialog.exec_()
                self.load_transactions()
            else:
                warning_dialog = self.create_styled_message_box("失败", "收支记录删除失败！")
                warning_dialog.exec_()

    def show_detail_dialog(self, transaction_id):
            # 通过 transaction_id 获取交易记录
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.created_at, p.name, t.amount, t.type, t.payment_method, t.stage, t.status, t.initial_amount
                FROM transactions t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.id = ?
            """, (transaction_id,))
            transaction = cursor.fetchone()
            conn.close()

            if not transaction:
                QMessageBox.warning(self, "错误", "交易记录不存在！")
                return

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
            error_dialog = self.create_styled_message_box(
                "错误", f"不能为未来的月份创建项目！当前日期：{current_year}年{current_month}月"
            )
            error_dialog.exec_()
            return

        # 输入项目名称
        project_name, ok = QInputDialog.getText(self, "创建新项目", "请输入项目名称：")
        if not ok or not project_name:
            return
        
        # 输入金额
        amount, ok = QInputDialog.getDouble(self, "输入金额", "请输入金额：", value=0.0, min=0.01, max=9999999.99, decimals=2)
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
        
        # 确认项目创建信息弹窗
        confirm_msg = f"项目名称: {project_name}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
        confirm_dialog = self.create_styled_message_box(
            "确认创建", confirm_msg, buttons=QMessageBox.Ok | QMessageBox.Cancel
        )
        reply = confirm_dialog.exec_()
        
        if reply != QMessageBox.Ok:
            return
        
        success, project_id = self.db.add_project(project_name, self.year, self.month)
        if success and project_id:
            year_int = int(self.year)
            month_int = int(self.month)
            success = self.db.add_transaction(project_id, amount, trans_type, payment_method, month_int, year_int)
            if success:
                if trans_type == "收入":
                    folder_success, result = self.file_manager.create_project_folder(self.year, self.month, project_name)
                    if not folder_success:
                        error_dialog = self.create_styled_message_box("失败", f"创建文件夹失败: {result}")
                        error_dialog.exec_()
                
                # 创建成功弹窗
                success_dialog = self.create_styled_message_box("成功", "收支记录创建成功！")
                success_dialog.exec_()
                
                self.load_transactions()
            else:
                error_dialog = self.create_styled_message_box("失败", "保存收支记录失败！")
                error_dialog.exec_()
        else:
            error_dialog = self.create_styled_message_box(
                "失败", f"创建项目失败！请确保年份 {self.year} 已存在。"
            )
            error_dialog.exec_()

    def create_existing_project_transaction(self):
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        transaction_year = int(self.year)
        transaction_month = int(self.month)
        if transaction_year > current_year or (transaction_year == current_year and transaction_month > current_month):
            msg = self.create_styled_message_box(
                "错误", f"不能为未来的月份创建收支记录！当前日期：{current_year}年{current_month}月"
            )
            msg.exec_()
            return
        
        # 获取年份
        all_years = self.db.get_years()
        years = [year for year in all_years if int(year) <= current_year]
        if not years:
            msg = self.create_styled_message_box("错误", "数据库中没有年份记录，请先创建年份！")
            msg.exec_()
            return
        
        # 设置字体为 Microsoft YaHei，20 号（用于 QInputDialog）
        font = QFont()
        font.setFamily("Microsoft YaHei, SimSun, Arial")
        font.setPointSize(20)
        
        # 选择年份
        dialog = QInputDialog(self)
        dialog.setWindowTitle("选择年份")
        dialog.setLabelText("请选择项目所属年份：")
        dialog.setFont(font)
        dialog.setComboBoxItems(years)
        dialog.setFixedSize(500, 350)
        selected_year, ok = dialog.getItem(self, "选择年份", "请选择项目所属年份：", years, 0, False)
        if not ok:
            return
        
        # 获取项目
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
            msg = self.create_styled_message_box("错误", f"{selected_year} 年没有非阶段性的收入类型项目！")
            msg.exec_()
            return
        
        project_names = [p[1] for p in projects]
        project_ids = {p[1]: p[0] for p in projects}
        project_months = {p[1]: p[2] for p in projects}
        
        # 选择项目（SearchableComboBoxDialog）
        dialog = SearchableComboBoxDialog(project_names, "选择项目", "请输入项目名称进行筛选：", self)
        dialog.setFont(font)
        if dialog.exec_():
            project_name = dialog.get_selected_item()
            if not project_name:
                return
            project_id = project_ids[project_name]
            project_month = project_months[project_name]
            if project_month is None:
                msg = self.create_styled_message_box(
                    "错误", f"项目 {project_name} 的创建月份未定义，请联系管理员检查数据库！"
                )
                msg.exec_()
                return
            
            # 选择阶段
            dialog = QInputDialog(self)
            dialog.setWindowTitle("选择阶段")
            dialog.setLabelText("请选择项目阶段：")
            dialog.setFont(font)
            dialog.setComboBoxItems(["第二阶段", "第三阶段", "第四阶段"])
            dialog.setFixedSize(500, 350)
            stage, ok = dialog.getItem(self, "选择阶段", "请选择项目阶段：", ["第二阶段", "第三阶段", "第四阶段"], 0, False)
            if not ok:
                return
            
            # 输入金额
            dialog = QInputDialog(self)
            dialog.setWindowTitle("输入金额")
            dialog.setLabelText("请输入金额（正数）：")
            dialog.setFont(font)
            dialog.setFixedSize(500, 350)
            amount, ok = dialog.getDouble(self, "输入金额", "请输入金额（正数）：", value=0.0, min=0.01, max=9999999.99, decimals=2)
            if not ok:
                return
            
            # 选择类型
            dialog = QInputDialog(self)
            dialog.setWindowTitle("选择类型")
            dialog.setLabelText("请选择收支类型：")
            dialog.setFont(font)
            dialog.setComboBoxItems(["收入", "支出"])
            dialog.setFixedSize(500, 350)
            trans_type, ok = dialog.getItem(self, "选择类型", "请选择收支类型：", ["收入", "支出"], 0, False)
            if not ok:
                return
            
            # 选择支付方式
            dialog = QInputDialog(self)
            dialog.setWindowTitle("选择支付方式")
            dialog.setLabelText("请选择支付方式：")
            dialog.setFont(font)
            dialog.setComboBoxItems(["微信", "支付宝", "对公账户", "对私账户", "现金"])
            dialog.setFixedSize(500, 350)
            payment_method, ok = dialog.getItem(self, "选择支付方式", "请选择支付方式：",
                                                ["微信", "支付宝", "对公账户", "对私账户", "现金"], 0, False)
            if not ok:
                return
            
            # 确认项目创建信息弹窗
            confirm_msg = f"项目名称: {project_name}\n阶段: {stage}\n金额: {amount}\n类型: {trans_type}\n支付方式: {payment_method}"
            confirm_dialog = self.create_styled_message_box(
                "确认创建", confirm_msg, buttons=QMessageBox.Ok | QMessageBox.Cancel
            )
            reply = confirm_dialog.exec_()
            
            if reply != QMessageBox.Ok:
                return
            
            # 保存交易记录
            success = self.db.add_transaction(project_id, amount, trans_type, payment_method, self.month, self.year, stage)
            if success:
                if trans_type == "收入":
                    shortcut_success, result = self.file_manager.create_shortcut(self.year, self.month, project_name, stage, selected_year, project_month)
                    if not shortcut_success:
                        msg = self.create_styled_message_box("提示", f"快捷方式创建失败: {result}")
                        msg.exec_()
                
                # 创建成功弹窗
                msg = self.create_styled_message_box("成功", "收支记录创建成功！")
                msg.exec_()
                
                QTimer.singleShot(0, self.load_transactions)
            else:
                msg = self.create_styled_message_box("失败", "保存收支记录失败！")
                msg.exec_()

    def closeEvent(self, event):
        self.deleteLater()
        super().closeEvent(event)

class SearchableComboBoxDialog(QDialog):
    def __init__(self, items, title="选择项目", label="请输入项目名称进行筛选：", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(400, 200)
        self.items = items
        self.selected_item = None
        self.filter_timer = QTimer(self)
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self.apply_filter)
        self.is_manual_input = True
        self.last_input_text = ""
        self.initUI(label)

    def initUI(self, label_text):
        layout = QVBoxLayout()
        layout.addWidget(QLabel(label_text))

        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.addItems(self.items)
        self.combo.setInsertPolicy(QComboBox.NoInsert)
        self.combo.setCompleter(None)
        self.combo.setEditText("")
        self.combo.currentIndexChanged.connect(self.on_selection_changed)
        self.combo.editTextChanged.connect(self.on_text_changed)
        self.combo.lineEdit().returnPressed.connect(self.on_return_pressed)
        layout.addWidget(self.combo)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确认")
        self.ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.combo.setFocus()

    def on_text_changed(self, text):
        self.is_manual_input = True
        self.last_input_text = text
        self.filter_timer.start(200)

    def apply_filter(self):
        text = self.combo.currentText().strip().lower()
        self.combo.blockSignals(True)
        current_text = self.combo.currentText()
        self.combo.clear()
        matching_items = [item for item in self.items if text in str(item).lower()]
        self.combo.addItems(matching_items if matching_items else self.items)
        self.combo.setEditText(current_text)
        if len(matching_items) == 1 and matching_items[0].lower() == text:
            self.selected_item = matching_items[0]
            self.is_manual_input = False
            self.combo.setEditText(self.selected_item)
            self.combo.hidePopup()
        elif self.is_manual_input and text and text != (self.selected_item or "").lower():
            self.combo.showPopup()
        self.combo.blockSignals(False)

    def on_selection_changed(self, index):
        if index >= 0:
            self.is_manual_input = False
            self.selected_item = self.combo.itemText(index)
            self.combo.setEditText(self.selected_item)
            self.combo.hidePopup()
            self.ok_button.setFocus()

    def on_return_pressed(self):
        current_text = self.combo.currentText().strip()
        if current_text in self.items:
            self.selected_item = current_text
            logging.info(f"Return pressed, selected: {self.selected_item}")
            self.accept()
        else:
            matching_items = [item for item in self.items if current_text.lower() in str(item).lower()]
            if len(matching_items) == 1:
                self.selected_item = matching_items[0]
                self.combo.setEditText(self.selected_item)
                self.combo.hidePopup()
                logging.info(f"Return pressed, auto-selected: {self.selected_item}")
                self.accept()
            else:
                logging.warning(f"Return pressed, but '{current_text}' not uniquely matched")
                QMessageBox.warning(self, "提示", "请选择一个有效的项目！")

    def accept(self):
        current_text = self.combo.currentText().strip()
        if current_text in self.items:
            self.selected_item = current_text
            logging.info(f"Accepted item: {self.selected_item}")
            super().accept()
        else:
            logging.warning(f"Invalid selection: '{current_text}' not in items")
            QMessageBox.warning(self, "提示", "请选择一个有效的项目！")

    def get_selected_item(self):
        return self.selected_item

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 设置全局样式表，美化按钮
    app.setStyleSheet("""
        QPushButton {
            font-family: 'Microsoft YaHei, SimSun, Arial';
            font-size: 18pt;
            padding: 5px 15px;
            background-color: #e0e0e0;
            border: 1px solid #a0a0a0;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
    """)
    window = MonthlyWindow("2025", 4)
    window.show()
    sys.exit(app.exec_())