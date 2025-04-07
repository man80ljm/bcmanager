from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QDialogButtonBox, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

class EditTransactionDialog(QDialog):
    def __init__(self, transaction, parent=None):
        super().__init__(parent)
        self.transaction = transaction  # 当前收支记录 (id, name, amount, trans_type, payment_method, stage)
        self.setWindowTitle("修改收支记录")
        self.setWindowIcon(QIcon(r'D:\bcmanager\logo01.png'))  # 设置窗口图标
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(800, 600)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # 项目名称（只读）
        self.name_label = QLabel(f"项目名称: {self.transaction[1]}")
        layout.addWidget(self.name_label)

        # 金额
        self.amount_label = QLabel("金额:")
        self.amount_input = QLineEdit(str(self.transaction[2]))
        self.amount_input.setPlaceholderText("请输入金额（正数）")
        layout.addWidget(self.amount_label)
        layout.addWidget(self.amount_input)

        # 类型
        self.type_label = QLabel("类型:")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["收入", "支出"])
        self.type_combo.setCurrentText(self.transaction[3])
        layout.addWidget(self.type_label)
        layout.addWidget(self.type_combo)

        # 支付方式
        self.payment_method_label = QLabel("支付方式:")
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["微信", "支付宝", "对公账户", "对私账户", "现金"])
        self.payment_method_combo.setCurrentText(self.transaction[4])
        layout.addWidget(self.payment_method_label)
        layout.addWidget(self.payment_method_combo)

        # 阶段
        self.stage_label = QLabel("阶段（可选）:")
        self.stage_combo = QComboBox()
        self.stage_combo.addItems(["无", "第二阶段", "第三阶段", "第四阶段"])
        self.stage_combo.setCurrentText(self.transaction[5] if self.transaction[5] else "无")
        layout.addWidget(self.stage_label)
        layout.addWidget(self.stage_combo)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def validate_and_accept(self):
        """验证输入并接受修改"""
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
        stage = self.stage_combo.currentText()
        if stage == "无":
            stage = None
        return {
            "id": self.transaction[0],
            "amount": amount,
            "type": trans_type,
            "payment_method": payment_method,
            "stage": stage
        }