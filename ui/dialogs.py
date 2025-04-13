from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QComboBox,
                             QDialogButtonBox, QMessageBox)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import resources

class EditTransactionDialog(QDialog):
    def __init__(self, transaction, db_manager, parent=None):
        super().__init__(parent)
        self.transaction = transaction  # 当前收支记录 (id, name, amount, trans_type, payment_method, stage)
        self.db = db_manager
        self.setWindowTitle("修改收支记录")
        self.setWindowIcon(QIcon(':/logo01.png'))  # 设置窗口图标
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(800, 600)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 项目名称（根据是否为已有项目的后续阶段决定是否可编辑）
        self.name_label = QLabel("项目名称:")
        self.name_input = QLineEdit(self.transaction[2])
        self.name_input.setPlaceholderText("请输入项目名称")
        
        # 检查该项目是否已有多个阶段记录
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

        # 金额
        self.amount_label = QLabel("金额:")
        self.amount_input = QLineEdit(str(self.transaction[3]))
        self.amount_input.setPlaceholderText("请输入金额（正数）")
        layout.addWidget(self.amount_label)
        layout.addWidget(self.amount_input)

        # 类型
        self.type_label = QLabel("类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["收入", "支出"])
        self.type_combo.setCurrentText(self.transaction[4])
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_combo)

        # 支付方式
        self.payment_method_label = QLabel("支付方式:")
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["微信", "支付宝", "对公账户", "对私账户", "现金"])
        self.payment_method_combo.setCurrentText(self.transaction[5])
        layout.addWidget(self.payment_method_label)
        layout.addWidget(self.payment_method_combo)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

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
        """返回更新后的数据"""
        amount = float(self.amount_input.text())
        trans_type = self.type_combo.currentText()
        payment_method = self.payment_method_combo.currentText()
        name = self.name_input.text().strip()
        return {
            "id": self.transaction[0],  # 收支记录 ID
            "name": name,  # 项目名称
            "amount": amount,
            "type": trans_type,
            "payment_method": payment_method
        }

    #新功能待实现