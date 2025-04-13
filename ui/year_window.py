import sys
import os
import resources
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout,QGridLayout, QPushButton, QLabel,
                             QDialog, QLineEdit, QMessageBox,QScrollArea,
                             QComboBox, QDialogButtonBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from database.db_manager import DatabaseManager  # 使用相对路径导入
from utils.file_manager import FileManager  # 导入 FileManager
from utils.export_excel import ExcelExporter  # 直接从 utils 导入

class YearWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        self.db = DatabaseManager()  # 初始化数据库管理器
        self.file_manager = FileManager()  # 初始化 FileManager
        self.exporter = ExcelExporter(self.db, parent=self)  # 初始化 ExcelExporter
        self.initUI()
    
    def initUI(self):
        # 设置窗口标题和大小
        self.setWindowTitle('年份管理')
        self.setFixedSize(800, 500)
        # 设置窗口图标
        self.setWindowIcon(QIcon(':/logo01.png'))  # 使用和界面相同的logo路径

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 在这里添加，去掉 central_widget 的边距
        central_widget.setContentsMargins(0, 0, 0, 0)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)  # 统一设置主布局的边距
        main_layout.setSpacing(10)  # 主布局的间距

        # 按钮宽度
        button_width = 120
        # 顶部按钮布局
        top_button_layout = QHBoxLayout()
        top_button_layout.setContentsMargins(0, 0, 0, 0)  # 去掉顶部布局的边距
        top_button_layout.setSpacing(5)  # 控件间距

        # 创建年份按钮
        self.create_button = QPushButton("创建年份")
        self.create_button.setFixedWidth(button_width)
        self.create_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3; 
                padding: 5px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        self.create_button.clicked.connect(self.create_year)
        top_button_layout.addWidget(self.create_button)

        # 创建子布局来放置搜索框和搜索按钮
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)  # 去掉子布局的边距
        search_layout.setSpacing(5)  # 搜索框和搜索按钮之间的间距

        # 添加搜索框和搜索按钮
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索收入项目...")
        self.search_input.setFixedWidth(200)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 5px;
                border: 1px solid #d3d3d3;
                border-radius: 3px;
                font-size: 20px;
            }
        """)
        # 回车键触发搜索
        self.search_input.returnPressed.connect(self.perform_search)

        self.search_button = QPushButton("搜索")
        self.search_button.setFixedWidth(button_width)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3; 
                padding: 5px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        self.search_button.clicked.connect(self.perform_search)

        # 将搜索框和搜索按钮添加到子布局
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)

        # 计算子布局的宽度，确保和底部的“恢复”按钮对齐
        search_widget.setFixedWidth(200 + button_width + 5)  # 搜索框宽度 + 按钮宽度 + 间距
        
        # 将子布局添加到 top_button_layout，并靠右
        top_button_layout.addStretch()
        top_button_layout.addWidget(search_widget, alignment=Qt.AlignRight)  # 显式设置右对齐

        main_layout.addLayout(top_button_layout)
        
        # # 添加弹簧使按钮靠左
        # top_button_layout.addStretch()
        # main_layout.addLayout(top_button_layout)

        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        # 年份列表容器
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: white;")
        self.years_layout = QGridLayout(self.scroll_content)
        self.years_layout.setSpacing(10)
        
        # 设置滚动区域的内容
        scroll.setWidget(self.scroll_content)
        main_layout.addWidget(scroll)

        # 底部按钮布局
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.setContentsMargins(0, 0, 0, 0)
        bottom_button_layout.setSpacing(5)
        
        # 备份按钮
        self.backup_button = QPushButton("备份")
        self.backup_button.setFixedWidth(button_width)
        self.backup_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3; 
                padding: 5px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        self.backup_button.clicked.connect(self.backup_database)  # 绑定备份事件

        # 添加导出按钮
        self.export_button = QPushButton("导出")
        self.export_button.setFixedWidth(button_width)
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3; 
                padding: 5px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        self.export_button.clicked.connect(self.export_data)

        # 恢复按钮
        self.restore_button = QPushButton("恢复")
        self.restore_button.setFixedWidth(button_width)
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #d3d3d3; 
                padding: 5px;
                border-radius: 3px;
                font-size: 20px;
            }
            QPushButton:hover {
                background-color: #c0c0c0;
            }
        """)
        self.restore_button.clicked.connect(self.restore_database)  # 绑定恢复事件
        # 添加弹簧使按钮分开
        bottom_button_layout.addWidget(self.backup_button)
        bottom_button_layout.addStretch()  # 弹簧，让“导出”居中
        bottom_button_layout.addWidget(self.export_button)  # 添加导出按钮
        bottom_button_layout.addStretch()  # 弹簧，让“恢复”靠右
        bottom_button_layout.addWidget(self.restore_button)
        
        main_layout.addLayout(bottom_button_layout)

        self.load_years()

    def export_data(self):
        """弹出对话框选择年份并导出数据"""
        self.export_button.setEnabled(False)

        # 获取所有年份
        years = self.db.get_years()
        if not years:
            QMessageBox.warning(self, "无数据", "数据库中没有年份数据可导出！")
            self.export_button.setEnabled(True)
            return

        # 弹出选择年份的对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择导出年份")
        dialog.setFixedSize(600, 300)
        dialog.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        label = QLabel("请选择要导出的年份：")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(years)
        layout.addWidget(combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec_():
            selected_year = combo.currentText()
            try:
                has_data = self.db.has_transactions_in_year(selected_year)
                print(f"检查年份 {selected_year} 是否有数据: {has_data}")
                if not has_data:
                    QMessageBox.warning(self, "无数据", f"{selected_year} 年没有数据可导出！")
                    self.export_button.setEnabled(True)
                    return
            except Exception as e:
                QMessageBox.warning(self, "错误", f"检查年份数据失败：{str(e)}")
                self.export_button.setEnabled(True)
                return
            # 调用导出方法
            success, reason = self.exporter.export_by_year(selected_year)
            if success:
                QMessageBox.information(self, "导出成功", f"{selected_year} 年的数据已导出到 exports/{selected_year}_transactions.xlsx")
            elif reason == "no_data":
                QMessageBox.warning(self, "无数据", f"{selected_year} 年没有数据可导出！")
            elif reason == "file_locked":
                # 文件被占用，提示已在 export_by_year 中显示，不需要额外提示
                pass
            else:
                # 其他未知失败原因
                QMessageBox.warning(self, "错误", f"导出 {selected_year} 年数据失败，原因未知")

        self.export_button.setEnabled(True)

    def perform_search(self):
        """执行模糊搜索并显示结果"""
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "输入错误", "请输入搜索关键词！")
            return

        # 调用数据库方法搜索收入项目
        results = self.db.search_income_projects(keyword)
        if not results:
            QMessageBox.information(self, "无结果", f"未找到与 '{keyword}' 相关的收入项目。")
            return

        # 如果只有一个结果，直接跳转
        if len(results) == 1:
            project_id, project_name, year, month = results[0]
            self.open_monthly_window(year, month)
            return

        # 如果有多个结果，弹出对话框让用户选择
        dialog = QDialog(self)
        dialog.setWindowTitle("选择项目")
        dialog.setFixedSize(600, 400)
        dialog.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        layout = QVBoxLayout()
        label = QLabel(f"找到以下与 '{keyword}' 相关的收入项目，请选择：")
        layout.addWidget(label)

        combo = QComboBox()
        options = [f"{name} ({year}年{month}月)" for _, name, year, month in results]
        combo.addItems(options)
        layout.addWidget(combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec_():
            selected_index = combo.currentIndex()
            project_id, project_name, year, month = results[selected_index]
            self.open_monthly_window(year, month)

    def open_monthly_window(self, year, month):
        """打开月度详情窗口"""
        from .monthly_window import MonthlyWindow
        self.monthly_window = MonthlyWindow(year, month)
        self.monthly_window.show()

    def clear_years_layout(self):
        """清空当前的年份卡片布局"""
        # 移除所有部件并销毁
        for i in reversed(range(self.years_layout.count())):
            item = self.years_layout.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    self.years_layout.removeWidget(widget)
                    widget.deleteLater()
        # 确保布局被重置
        self.years_layout.update()

    def load_years(self):
        """从数据库加载年份并按顺序显示"""
        years = self.db.get_years()
        print("Years in database:", years)
        # 清空现有布局
        self.clear_years_layout()
        # 添加年份卡片
        for year in years:
            self.add_year_card(f"{year}年")

    def add_year_card(self, year):
        """添加年份卡片"""
        year_button = QPushButton(year)
        year_button.setFixedSize(100, 50)
        year_button.setStyleSheet("""
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
        year_button.clicked.connect(lambda: self.open_annual_window(year))
        # 计算当前要添加的按钮位置
        total_items = self.years_layout.count()
        row = total_items // 5
        col = total_items % 5
        # TODO: 点击年份后进入年度详情界面
        self.years_layout.addWidget(year_button, row, col)
    
    def open_annual_window(self, year):
        print("Attempting to import AnnualWindow...")
        from .annual_window import AnnualWindow
        print("Import successful!")
        self.annual_window = AnnualWindow(year[:-1])  # 去掉“年”字，例如 "2025年" -> "2025"
        self.annual_window.show()
    
    def create_year(self):
        """创建新年份"""
        # 禁用按钮，防止重复点击
        self.create_button.setEnabled(False)
        try:
            dialog = CreateYearDialog(self)
            if dialog.exec_():
                year = dialog.get_year()
                if not year.isdigit() or len(year) != 4:
                    QMessageBox.warning(self, "输入错误", "请输入有效的4位年份（例如：2025）")
                    return
                # 检查年份是否已存在
                if self.db.is_year_exists(year):
                    QMessageBox.warning(self, "年份重复", "请不要输入重复年份！")
                    return
                # 添加年份卡片
                self.add_year_card(f"{year}年")
                # 保存到数据库
                self.db.add_year(year) # 保存到数据库
                self.load_years()  # 重新加载并排序年份
                # QMessageBox.information(self, "成功", f"年份 {year} 已创建并排序！")
        finally:
        # 无论成功与否，操作完成后重新启用按钮
            self.create_button.setEnabled(True)

    def backup_database(self):
        """备份数据库"""
        self.backup_button.setEnabled(False)
        success, result = self.file_manager.backup_database()
        if success:
            QMessageBox.information(self, "备份成功", f"数据库已备份到：\n{result}")
        else:
            QMessageBox.warning(self, "备份失败", f"备份失败：\n{result}")
        self.backup_button.setEnabled(True)

    def restore_database(self):
        """恢复数据库"""
        self.restore_button.setEnabled(False)

        # 获取备份文件列表
        backup_files = self.file_manager.get_backup_files()
        if not backup_files:
            QMessageBox.warning(self, "无备份文件", "db_backup 文件夹中没有可用的备份文件！")
            self.restore_button.setEnabled(True)
            return

        # 弹出选择备份文件的对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("选择备份文件")
        dialog.setFixedSize(600, 300)
        dialog.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去除问号按钮

        layout = QVBoxLayout()
        label = QLabel("请选择要恢复的备份文件：")
        layout.addWidget(label)

        combo = QComboBox()
        combo.addItems(backup_files)
        layout.addWidget(combo)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec_():
            selected_file = combo.currentText()
            # 二次确认
            reply = QMessageBox.question(
                self, "确认恢复",
                f"确定要从 {selected_file} 恢复数据库吗？\n这将覆盖当前数据库！",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                success, message = self.file_manager.restore_database(selected_file)
                if success:
                    QMessageBox.information(self, "恢复成功", message)
                    # 重新加载年份，因为数据库已更改
                    self.load_years()
                else:
                    QMessageBox.warning(self, "恢复失败", f"恢复失败：\n{message}")

        self.restore_button.setEnabled(True)
        

class CreateYearDialog(QDialog):
    """创建年份的对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("创建新年份")
        self.setFixedSize(600, 300)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)  # 去除问号按钮
        layout = QVBoxLayout()

        # 年份输入框
        self.year_input = QLineEdit()
        self.year_input.setPlaceholderText("请输入年份（例如：2025）")
        layout.addWidget(self.year_input)

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        confirm_button = QPushButton("确定")
        confirm_button.clicked.connect(self.accept)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_year(self):
        """获取用户输入的年份"""
        return self.year_input.text().strip()



# 测试代码
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = YearWindow()
    window.show()
    sys.exit(app.exec_())