import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
from database.db_manager import DatabaseManager
from PyQt5.QtWidgets import QMessageBox


class ExcelExporter:
    def __init__(self, db_manager, parent=None):
        self.db = db_manager
        self.parent = parent

    def export_by_year(self, year, output_dir="exports"):
        # 创建导出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 定义目标文件路径
        output_file = os.path.join(output_dir, f"{year}_transactions.xlsx")

        # 尝试初始化 ExcelWriter
        try:
            writer = pd.ExcelWriter(
                output_file,
                engine="openpyxl"
            )
        except (PermissionError, IOError) as e:
            # 文件被锁定（例如已在 Excel 中打开）
            if self.parent:
                QMessageBox.warning(
                    self.parent,
                    "导出失败",
                    "无法导出！请关闭文件再导出！"
                )
            else:
                print("无法导出！请关闭文件再导出！")
            return False, "file_locked"

        has_data = False
        negative_expense_items = ["社保"]

        for month in range(1, 13):
            transactions = self.db.get_monthly_transactions(year, month)
            if not transactions:
                continue

            data = []
            for idx, trans in enumerate(transactions, 1):
                trans_id = trans[0]
                created_at = trans[1]
                project_name = trans[2] if trans[2] else "未知项目"
                amount = trans[3]
                trans_type = trans[4]
                payment_method = trans[5]
                stage = trans[6] if trans[6] else ""
                status = trans[7]

                remark = ""
                if trans_type == "收入":
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute("SELECT content FROM remarks WHERE transaction_id = ?", (trans_id,))
                    result = cursor.fetchone()
                    remark = result[0] if result else ""
                    conn.close()

                expense_details = ""
                if trans_type == "支出":
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name, amount FROM expense_details WHERE transaction_id = ?",
                        (trans_id,)
                    )
                    details = cursor.fetchall()
                    if details:
                        detail_strings = [
                            f"{name}:{-amount:.2f}" if name in negative_expense_items else f"{name}:{amount:.2f}"
                            for name, amount in details
                        ]
                        total = sum(
                            -amount if name in negative_expense_items else amount
                            for name, amount in details
                        )
                        expense_details = ", ".join(detail_strings) + f", 总额:{total:.2f}"
                    conn.close()

                data.append([
                    idx,
                    created_at,
                    project_name,
                    f"{amount:.2f}",
                    trans_type,
                    payment_method,
                    stage,
                    status,
                    remark,
                    expense_details
                ])

            if data:
                has_data = True
                df = pd.DataFrame(data, columns=[
                    "序号", "创建时间", "项目名称", "金额", "类型",
                    "支付方式", "阶段", "状态", "备注（收入）", "支出详情（支出）"
                ])
                df.to_excel(writer, sheet_name=f"{month}月", index=False)

                worksheet = writer.sheets[f"{month}月"]
                header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
                header_font = Font(bold=True)
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                for col_idx, column in enumerate(worksheet.columns, 1):
                    max_length = 0
                    column_letter = get_column_letter(col_idx)
                    for cell in column:
                        try:
                            cell_value = str(cell.value)
                            length = sum(2 if ord(char) > 127 else 1 for char in cell_value)
                            max_length = max(max_length, length)
                        except:
                            pass
                    adjusted_width = max_length * 1.2
                    worksheet.column_dimensions[column_letter].width = max(adjusted_width, 10)

                total_income, total_expense, net_income = self.db.get_monthly_summary(year, month)
                print(f"Year: {year}, Month: {month}, Total Income: {total_income}, Total Expense: {total_expense}, Net Income: {net_income}")
                summary_row = [
                    "", "", "", "", "", "", "", "总收入", f"{total_income:.2f}", ""
                ]
                worksheet.append(summary_row)
                worksheet.append(["", "", "", "", "", "", "", "总支出", f"{total_expense:.2f}", ""])
                worksheet.append(["", "", "", "", "", "", "", "净收入", f"{net_income:.2f}", ""])
                worksheet.append(["", "", "", "", "", "", "", "总额", f"{net_income:.2f}元", ""])

        try:
            if has_data:
                writer.close()
                print(f"成功导出 {year} 年的数据到 {output_file}")
                return True, None
            else:
                print(f"{year} 年没有数据，跳过导出")
                writer.close()
                os.remove(output_file)
                return False, "no_data"
        except (PermissionError, IOError) as e:
            if self.parent:
                QMessageBox.warning(
                    self.parent,
                    "导出失败",
                    "无法导出！请关闭文件再导出！"
                )
            else:
                print("无法导出！请关闭文件再导出！")
            return False, "file_locked"

    def export_all_years(self, output_dir="exports"):
        years = self.db.get_years()
        for year in years:
            self.export_by_year(year, output_dir)

if __name__ == "__main__":
    db = DatabaseManager()
    exporter = ExcelExporter(db)
    exporter.export_by_year("2025")