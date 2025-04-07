from PyQt5.QtWidgets import (QMainWindow, QTableWidget, QTableWidgetItem, QPushButton, QLabel, QVBoxLayout, QWidget,
                             QMenu, QInputDialog, QComboBox, QMessageBox,QHBoxLayout)
from PyQt5.QtGui import QIcon
from database.db_manager import DatabaseManager
from utils.file_manager import FileManager
import os

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
        self.setFixedSize(1300, 850)
        self.setWindowIcon(QIcon(r'D:\bcmanager\logo01.png'))  # 设置窗口图标

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["项目名称", "金额", "类型", "支付方式", "备注", "修改"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁用编辑
        layout.addWidget(self.table)

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

        self.load_transactions()

    def load_transactions(self):
        transactions = self.db.get_monthly_transactions(self.year, self.month)
        self.table.setRowCount(len(transactions))
        for row, (id, name, amount, trans_type, payment_method, stage) in enumerate(transactions):
            display_name = f"{name}（{stage}）" if stage else name
            self.table.setItem(row, 0, QTableWidgetItem(display_name))
            self.table.setItem(row, 1, QTableWidgetItem(str(amount)))
            self.table.setItem(row, 2, QTableWidgetItem(trans_type))
            self.table.setItem(row, 3, QTableWidgetItem(payment_method))
            remark_button = QPushButton("备注")
            self.table.setCellWidget(row, 4, remark_button)
            edit_button = QPushButton("修改")
            edit_button.clicked.connect(lambda checked, r=row: self.edit_transaction(r))  # 添加修改逻辑
            self.table.setCellWidget(row, 5, edit_button)

        total_income, total_expense, balance = self.db.get_monthly_summary(self.year, self.month)
        self.summary_label.setText(f"总收入: {total_income} | 总支出: {total_expense} | 结余: {balance}")

    def edit_transaction(self, row):
        # 占位方法，显示修改对话框
        QMessageBox.information(self, "提示", f"修改第 {row + 1} 行记录功能待实现！")

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
        success, project_id = self.db.add_project(project_name, self.year)
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
        years = self.db.get_years()
        if not years:
            QMessageBox.warning(self, "错误", "数据库中没有年份记录，请先创建年份！")
            return
        selected_year, ok = QInputDialog.getItem(self, "选择年份", "请选择项目所属年份：", years, 0, False)
        if not ok:
            print("取消选择年份")
            return

        # 步骤 2: 选择项目
        projects = self.db.get_projects_by_year(selected_year)
        if not projects:
            QMessageBox.warning(self, "错误", f"{selected_year} 年没有已有项目！")
            return
        project_names = [p[1] for p in projects]
        project_ids = {p[1]: p[0] for p in projects}
        project_name, ok = QInputDialog.getItem(self, "选择项目", "请选择已有项目：", project_names, 0, False)
        if not ok:
            print("取消选择项目")
            return
        project_id = project_ids[project_name]

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
            shortcut_success, result = self.file_manager.create_shortcut(self.year, self.month, project_name, stage, selected_year)
            if not shortcut_success:
                QMessageBox.warning(self, "提示", f"快捷方式创建失败: {result}")
            QMessageBox.information(self, "成功", "收支记录创建成功！")
            self.load_transactions()
        else:
            QMessageBox.warning(self, "失败", "保存收支记录失败！")

    def edit_transaction(self, row):
        QMessageBox.information(self, "提示", f"修改第 {row + 1} 行记录功能待实现！")

if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication
    import sys
    app = QApplication(sys.argv)
    window = MonthlyWindow("2025", 4)
    window.show()
    sys.exit(app.exec_())