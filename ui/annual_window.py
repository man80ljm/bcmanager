# ui/annual_window.py

import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

class AnnualWindow(QMainWindow):
    def __init__(self, year):
        super().__init__()
        self.year = year
        self.initUI()

    def initUI(self):
        self.setWindowTitle(f'{self.year} 年度详情 - 项目管理与财务记账系统')
        self.setFixedSize(600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel(f'{self.year} 年度详情')
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #d3d3d3; padding: 5px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 月份导航
        months_layout = QHBoxLayout()
        for month in range(1, 13):
            month_button = QPushButton(f"{month}月")
            month_button.setFixedSize(50, 30)
            month_button.setStyleSheet("background-color: #f0f0f0; border: 1px solid #d3d3d3;")
            # TODO: 点击月份后进入月度详情界面
            months_layout.addWidget(month_button)
        main_layout.addLayout(months_layout)

        # 季度统计
        quarters_layout = QHBoxLayout()
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            quarter_button = QPushButton(quarter)
            quarter_button.setFixedSize(50, 30)
            quarter_button.setStyleSheet("background-color: #f0f0f0; border: 1px solid #d3d3d3;")
            # TODO: 点击后显示季度统计
            quarters_layout.addWidget(quarter_button)
        main_layout.addLayout(quarters_layout)

        # 年度总收支按钮
        annual_button = QPushButton("年度总收支")
        annual_button.setStyleSheet("background-color: #d3d3d3; padding: 5px;")
        # TODO: 点击后显示年度统计
        main_layout.addWidget(annual_button, alignment=Qt.AlignCenter)

        main_layout.addStretch()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AnnualWindow("2025")
    window.show()
    sys.exit(app.exec_())