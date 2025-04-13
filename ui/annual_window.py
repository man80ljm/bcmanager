import logging
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QGridLayout, QDialog, QMessageBox)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QIcon
from ui.monthly_window import MonthlyWindow
from database.db_manager import DatabaseManager
from datetime import datetime
import resources

# 在文件顶部配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QuarterlySummaryDialog(QDialog):
    def __init__(self, year, quarter, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{year}年 Q{quarter} 季度统计")
        self.setFixedSize(600, 300)
        self.setWindowIcon(QIcon(':/logo01.png'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去掉疑问号
        self.year = year
        self.quarter = quarter
        self.db = DatabaseManager()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 确定季度的月份范围
        if self.quarter == 1:
            months = [1, 2, 3]
            quarter_name = "Q1 (1-3月)"
        elif self.quarter == 2:
            months = [4, 5, 6]
            quarter_name = "Q2 (4-6月)"
        elif self.quarter == 3:
            months = [7, 8, 9]
            quarter_name = "Q3 (7-9月)"
        elif self.quarter == 4:
            months = [10, 11, 12]
            quarter_name = "Q4 (10-12月)"

        # 统计指定季度的收支，并记录每个月的明细
        total_income = 0
        total_expense = 0
        monthly_details = []  # 存储每个月的明细
        for month in months:
            income, expense, balance = self.db.get_monthly_summary(self.year, month)
            total_income += income
            total_expense += expense
            # 添加每月的明细
            monthly_details.append(f"{month}月：收入 {income}，支出 {expense}，结余 {balance}")

        total_balance = total_income - total_expense

        # 构建显示内容：先显示每月的明细，再显示总计
        summary_text = f"{self.year}年 {quarter_name} 统计：\n\n"
        summary_text += "\n".join(monthly_details)  # 每月的明细
        summary_text += f"\n\n总计：收入 {total_income}，支出 {total_expense}，结余 {total_balance}"

        # 显示统计结果
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("font-size: 22px; padding: 10px;")
        layout.addWidget(summary_label)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

class AnnualSummaryDialog(QDialog):
    def __init__(self, year, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{year}年 总收支统计")
        self.setFixedSize(500, 300)
        self.setWindowIcon(QIcon(':/logo01.png'))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去掉疑问号
        self.year = year
        self.db = DatabaseManager()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 统计年度总收支
        total_income = 0
        total_expense = 0
        for month in range(1, 13):
            income, expense, _ = self.db.get_monthly_summary(self.year, month)
            total_income += income
            total_expense += expense

        profit = total_income - total_expense

        # 显示统计结果
        summary_label = QLabel(
            f"{self.year}年 总收支统计：\n\n"
            f"总收入: {total_income}\n"
            f"总支出: {total_expense}\n"
            f"盈利: {profit}"
        )
        summary_label.setStyleSheet("font-size: 22px; padding: 10px;")
        layout.addWidget(summary_label)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        self.setLayout(layout)

class AnnualWindow(QMainWindow):
    def __init__(self, year):
        super().__init__()
        self.year = year
        self.active_monthly_windows = {}  # 跟踪已打开的月份窗口
        self.active_quarterly_dialogs = {}  # 跟踪已打开的季度统计弹窗
        self.annual_summary_dialog = None  # 跟踪年度总收支弹窗
        self.last_click_time = 0  # 记录上次点击时间
        self.debounce_interval = 300  # 防抖间隔（毫秒）
        self.db = DatabaseManager()
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'{self.year} 年度详情')
        self.setFixedSize(600, 350)
        self.setWindowIcon(QIcon(':/logo01.png'))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题栏布局（包含返回按钮、标题、总收支按钮）
        title_layout = QHBoxLayout()

        # 返回按钮
        back_button = QPushButton("返回")
        back_button.setFixedSize(70, 30)
        back_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3;
                border: none;
                padding: 1px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        back_button.clicked.connect(self.close)
        title_layout.addWidget(back_button)

        # 标题
        title_label = QLabel(f'{self.year} 年度详情')
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; background-color: #d3d3d3; padding: 5px;")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFixedWidth(400)
        title_layout.addWidget(title_label)

        # 年度总收支按钮
        annual_button = QPushButton("总收支")
        annual_button.setFixedSize(70, 30)
        annual_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3;
                border: none;
                padding: 1px;
                border-radius: 3px;
                font-size: 20px;                    
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        annual_button.clicked.connect(self.show_annual_summary)
        title_layout.addWidget(annual_button)

        main_layout.addLayout(title_layout)

        # 月份导航（3行4列网格布局）
        months_label = QLabel("月份")
        months_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(months_label)

        months_layout = QGridLayout()
        for month in range(1, 13):
            month_button = QPushButton(f"{month}月")
            month_button.setFixedSize(50, 30)
            month_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d3d3d3;
                    border-radius: 5px;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            month_button.clicked.connect(lambda checked, m=month: self.open_monthly_window(m))
            row = (month - 1) // 4
            col = (month - 1) % 4
            months_layout.addWidget(month_button, row, col)
        main_layout.addLayout(months_layout)

        # 季度统计（1行4列布局）
        quarters_label = QLabel("季度")
        quarters_label.setStyleSheet("font-size: 20px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(quarters_label)

        quarters_layout = QHBoxLayout()
        quarters_layout.setSpacing(20)

        # 添加季度按钮
        for quarter in range(1, 5):
            quarter_button = QPushButton(f"Q{quarter}")
            quarter_button.setFixedSize(50, 30)
            quarter_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d3d3d3;
                    border-radius: 5px;
                    font-size: 20px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            quarter_button.clicked.connect(lambda checked, q=quarter: self.show_quarterly_summary(q))
            quarters_layout.addWidget(quarter_button)

        for i in range(4):
            quarters_layout.setStretch(i, 1)
        main_layout.addLayout(quarters_layout)

        main_layout.addStretch()

    def show_quarterly_summary(self, quarter):
        """显示指定季度的收支统计"""
        # 确定季度的月份范围
        if quarter == 1:
            months = [1, 2, 3]
            quarter_name = "Q1 (1-3月)"
        elif quarter == 2:
            months = [4, 5, 6]
            quarter_name = "Q2 (4-6月)"
        elif quarter == 3:
            months = [7, 8, 9]
            quarter_name = "Q3 (7-9月)"
        elif quarter == 4:
            months = [10, 11, 12]
            quarter_name = "Q4 (10-12月)"
        else:
            return

        # 检查是否已存在该季度的弹窗
        if quarter in self.active_quarterly_dialogs:
            dialog = self.active_quarterly_dialogs[quarter]
            try:
                if dialog.isVisible() and not dialog.isHidden():
                    logging.info(f"Quarter {quarter} summary dialog already open, raising to front")
                    dialog.raise_()
                    dialog.activateWindow()
                    return
                else:
                    logging.warning(f"Quarter {quarter} dialog found but not visible, removing")
                    dialog.close()
                    dialog.deleteLater()
                    self.active_quarterly_dialogs.pop(quarter, None)
            except RuntimeError:
                logging.warning(f"Quarter {quarter} dialog is invalid, removing")
                self.active_quarterly_dialogs.pop(quarter, None)

        # 创建新弹窗
        dialog = QuarterlySummaryDialog(self.year, quarter, parent=self)
        dialog.show()
        
        # 连接销毁信号并清理字典
        dialog.destroyed.connect(lambda: self.active_quarterly_dialogs.pop(quarter, None))
        self.active_quarterly_dialogs[quarter] = dialog

    def show_annual_summary(self):
        """显示年度总收支统计"""
        # 检查是否已存在年度总收支弹窗
        if self.annual_summary_dialog:
            try:
                if self.annual_summary_dialog.isVisible() and not self.annual_summary_dialog.isHidden():
                    logging.info("Annual summary dialog already open, raising to front")
                    self.annual_summary_dialog.raise_()
                    self.annual_summary_dialog.activateWindow()
                    return
                else:
                    logging.warning("Annual summary dialog found but not visible, removing")
                    self.annual_summary_dialog.close()
                    self.annual_summary_dialog.deleteLater()
                    self.annual_summary_dialog = None
            except RuntimeError:
                logging.warning("Annual summary dialog is invalid, removing")
                self.annual_summary_dialog = None

        # 创建新弹窗
        dialog = AnnualSummaryDialog(self.year, self)
        dialog.show()
        
        # 连接销毁信号并清理
        dialog.destroyed.connect(lambda: setattr(self, 'annual_summary_dialog', None))
        self.annual_summary_dialog = dialog

    def open_monthly_window(self, month):
        current_time = QTime.currentTime().msecsSinceStartOfDay()
        if current_time - self.last_click_time < self.debounce_interval:
            logging.info(f"Debounced click for month {month}")
            return
        self.last_click_time = current_time

        logging.info(f"Opening monthly window for {self.year}-{month}")
        if month in self.active_monthly_windows:
            window = self.active_monthly_windows[month]
            try:
                if window.isVisible() and not window.isHidden():
                    logging.info(f"Month {month} window already open, raising to front")
                    window.raise_()
                    window.activateWindow()
                    return
                else:
                    logging.warning(f"Month {month} window found but not visible, removing")
                    window.close()
                    window.deleteLater()
                    self.active_monthly_windows.pop(month, None)
            except RuntimeError:
                logging.warning(f"Month {month} window is invalid, removing")
                self.active_monthly_windows.pop(month, None)

        monthly_window = MonthlyWindow(self.year, month, parent=self)
        monthly_window.show()
        monthly_window.destroyed.connect(lambda: self.active_monthly_windows.pop(month, None))
        self.active_monthly_windows[month] = monthly_window

    def closeEvent(self, event):
        # 关闭并清理所有月度窗口
        for month, window in list(self.active_monthly_windows.items()):
            try:
                window.close()
                window.deleteLater()
                self.active_monthly_windows.pop(month, None)
            except Exception as e:
                print(f"Error closing window for month {month}: {e}")

        # 关闭并清理所有季度统计弹窗
        for quarter, dialog in list(self.active_quarterly_dialogs.items()):
            try:
                dialog.close()
                dialog.deleteLater()
                self.active_quarterly_dialogs.pop(quarter, None)
            except Exception as e:
                print(f"Error closing quarterly dialog for quarter {quarter}: {e}")

        # 关闭并清理年度总收支弹窗
        if self.annual_summary_dialog:
            try:
                self.annual_summary_dialog.close()
                self.annual_summary_dialog.deleteLater()
                self.annual_summary_dialog = None
            except Exception as e:
                print(f"Error closing annual summary dialog: {e}")

        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnnualWindow("2025")
    window.show()
    sys.exit(app.exec_())