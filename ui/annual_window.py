# ui/annual_window.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from ui.monthly_window import MonthlyWindow

class AnnualWindow(QMainWindow):
    def __init__(self, year):
        super().__init__()
        self.year = year
        self.active_monthly_windows = {}  # 可选：跟踪已打开的月份窗口，避免重复打开
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'{self.year} 年度详情 - 项目管理与财务记账系统')
        self.setFixedSize(600, 350)
        self.setWindowIcon(QIcon(r'D:\bcmanager\logo01.png'))  # 设置窗口图标

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
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        back_button.clicked.connect(self.close)  # 点击返回关闭当前窗口
        title_layout.addWidget(back_button)

        # 标题
        title_label = QLabel(f'{self.year} 年度详情')
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #d3d3d3; padding: 5px;")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFixedWidth(400)  # 设置固定宽度，缩小标题宽度
        title_layout.addWidget(title_label)  # 标题占大部分空间

        # 年度总收支按钮
        annual_button = QPushButton("总收支")
        annual_button.setFixedSize(70, 30)
        annual_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3;
                border: none;
                padding: 1px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        # TODO: 点击后显示年度统计
        title_layout.addWidget(annual_button)

        main_layout.addLayout(title_layout)

        # 月份导航（3行4列网格布局）
        months_label = QLabel("月份")
        months_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
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
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            month_button.clicked.connect(lambda checked, m=month: self.open_monthly_window(m))
            row = (month - 1) // 4  # 计算行号
            col = (month - 1) % 4   # 计算列号
            months_layout.addWidget(month_button, row, col)
        main_layout.addLayout(months_layout)

        # 季度统计（1行4列布局）
        quarters_label = QLabel("季度")
        quarters_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        main_layout.addWidget(quarters_label)

        quarters_layout = QHBoxLayout()
        quarters_layout.setSpacing(20)  # 设置按钮之间的间距

        # 先添加所有按钮
        for i, quarter in ["Q1", "Q2", "Q3", "Q4"]:
            quarter_button = QPushButton(quarter)
            quarter_button.setFixedSize(50, 30)
            quarter_button.setStyleSheet("""
                QPushButton {
                    background-color: #f0f0f0;
                    border: 1px solid #d3d3d3;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            # TODO: 点击后显示季度统计
            quarters_layout.addWidget(quarter_button)
            
        # 再设置伸缩因子，确保平均分布
        for i in range(4):
            quarters_layout.setStretch(i, 1)
        main_layout.addLayout(quarters_layout) 

        main_layout.addStretch()

    def open_monthly_window(self, month):
        # 可选：检查是否已打开该月份窗口，避免重复
        if month not in self.active_monthly_windows or self.active_monthly_windows[month].isHidden():
            monthly_window = MonthlyWindow(self.year, month)
            monthly_window.show()
            # 当窗口关闭时，从字典中移除
            monthly_window.destroyed.connect(lambda: self.active_monthly_windows.pop(month, None))
            self.active_monthly_windows[month] = monthly_window
        else:
            # 如果窗口已存在，将其置于前台
            self.active_monthly_windows[month].raise_()
            self.active_monthly_windows[month].activateWindow()

    def closeEvent(self, event):
        # 关闭年度窗口时，关闭所有打开的月度窗口
        for window in self.active_monthly_windows.values():
            window.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnnualWindow("2025")
    window.show()
    sys.exit(app.exec_())