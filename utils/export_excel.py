# export_excel.py

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime
import os
from database.db_manager import DatabaseManager

class ExcelExporter:
    def __init__(self, db_manager):
        self.db = db_manager

    def export_by_year(self, year, output_dir="exports"):
        """
        按年份导出 Excel 文件
        :param year: 年份（例如 "2025"）
        :param output_dir: 导出目录
        """
        # 创建导出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 获取该年份的所有月份数据
        writer = pd.ExcelWriter(
            os.path.join(output_dir, f"{year}_transactions.xlsx"),
            engine="openpyxl"
        )
        has_data = False  # 标记是否有数据

        # 遍历 12 个月
        for month in range(1, 13):
            transactions = self.db.get_monthly_transactions(year, month)
            if not transactions:
                continue  # 如果该月没有数据，跳过

            # 准备表格数据
            data = []
            for idx, trans in enumerate(transactions, 1):
                trans_id = trans[0]  # transactions.id
                created_at = trans[1]  # transactions.created_at
                project_name = trans[2] if trans[2] else "未知项目"  # projects.name
                amount = trans[3]  # transactions.amount
                trans_type = trans[4]  # transactions.type
                payment_method = trans[5]  # transactions.payment_method
                stage = trans[6] if trans[6] else ""  # transactions.stage
                status = trans[7]  # transactions.status
                # initial_amount = trans[8]  # 如果需要可以添加

                # 获取备注（收入）
                remark = ""
                if trans_type == "收入":
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute("SELECT content FROM remarks WHERE transaction_id = ?", (trans_id,))
                    result = cursor.fetchone()
                    remark = result[0] if result else ""
                    conn.close()

                # 获取支出详情（支出）
                expense_details = ""
                if trans_type == "支出":
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT name, amount FROM expense_details WHERE transaction_id = ?",
                        (trans_id,)
                    )
                    details = cursor.fetchall()
                    expense_details = ", ".join([f"{name}:{amount}" for name, amount in details])
                    conn.close()

                # 添加一行数据
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

            # 如果该月有数据，生成 sheet
            if data:
                has_data = True
                df = pd.DataFrame(data, columns=[
                    "序号", "创建时间", "项目名称", "金额", "类型",
                    "支付方式", "阶段", "状态", "备注（收入）", "支出详情（支出）"
                ])
                df.to_excel(writer, sheet_name=f"{month}月", index=False)

                # 设置样式
                worksheet = writer.sheets[f"{month}月"]
                # 设置表头样式
                header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
                header_font = Font(bold=True)
                for cell in worksheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")

                # 自动调整列宽
                for col_idx, column in enumerate(worksheet.columns, 1):
                    max_length = 0
                    column_letter = get_column_letter(col_idx)
                    for cell in column:
                        try:
                            # 计算内容的实际宽度（考虑中文字符）
                            cell_value = str(cell.value)
                            # 中文字符按 2 个单位宽度计算，英文字符按 1 个单位
                            length = sum(2 if ord(char) > 127 else 1 for char in cell_value)
                            max_length = max(max_length, length)
                        except:
                            pass
                    # 设置列宽，添加一些额外空间
                    adjusted_width = max_length * 1.2  # 乘以 1.2 增加一些余量
                    worksheet.column_dimensions[column_letter].width = max(adjusted_width, 10)  # 最小宽度为 10

                # 添加汇总信息（总收入、总支出、净收入）
                total_income, total_expense, net_income = self.db.get_monthly_summary(year, month)
                summary_row = [
                    "", "", "", "", "", "", "", "总收入", f"{total_income:.2f}", ""
                ]
                worksheet.append(summary_row)
                worksheet.append(["", "", "", "", "", "", "", "总支出", f"{total_expense:.2f}", ""])
                worksheet.append(["", "", "", "", "", "", "", "净收入", f"{net_income:.2f}", ""])

        # 保存 Excel 文件
        if has_data:
            writer.close()
            print(f"成功导出 {year} 年的数据到 {output_dir}/{year}_transactions.xlsx")
            return True
        else:
            print(f"{year} 年没有数据，跳过导出")
            writer.close()
            os.remove(os.path.join(output_dir, f"{year}_transactions.xlsx"))
            return False

    def export_all_years(self, output_dir="exports"):
        """
        导出所有年份的数据
        """
        years = self.db.get_years()
        for year in years:
            self.export_by_year(year, output_dir)

# 测试代码
if __name__ == "__main__":
    db = DatabaseManager()
    exporter = ExcelExporter(db)
    exporter.export_by_year("2025")