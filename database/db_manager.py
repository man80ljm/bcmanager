# database/db_manager.py

import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="project_accounting.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库，创建表结构"""
        # 检查数据库文件是否存在，不存在则创建
        if not os.path.exists(self.db_path):
            print(f"创建数据库文件：{self.db_path}")
        
        # 连接数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 读取 schema.sql 文件并执行
        with open("database/schema.sql", "r", encoding="utf-8") as f:
            schema = f.read()
        cursor.executescript(schema)

        # 提交更改并关闭连接
        conn.commit()
        conn.close()

    def connect(self):
        """创建并返回数据库连接"""
        return sqlite3.connect(self.db_path)

    def validate_user(self, username, password):
        """验证用户名和密码是否匹配"""
        conn = self.connect()
        cursor = conn.cursor()

        # 查询用户
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            return True, user  # 验证成功，返回 True 和用户信息
        return False, None  # 验证失败
    def add_year(self, year):
        """添加年份到数据库"""
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("INSERT INTO years (year, created_at) VALUES (?, ?)", (year, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:  # 如果年份已存在（违反唯一约束）
            return False
        finally:
            conn.close()

    def get_years(self):
        """获取所有年份"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT year FROM years ORDER BY year")
        years = [row[0] for row in cursor.fetchall()]
        conn.close()
        return years
    
    def is_year_exists(self, year):
        """检查年份是否已存在"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM years WHERE year = ?", (year,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def add_project(self, name, year):
        """添加新项目"""
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_id = cursor.fetchone()[0]
            cursor.execute("INSERT INTO projects (name, year_id, created_at) VALUES (?, ?, ?)", 
                         (name, year_id, created_at))
            project_id = cursor.lastrowid
            conn.commit()
            return True, project_id
        except sqlite3.IntegrityError:
            return False, None
        finally:
            conn.close()

    def add_transaction(self, project_id, amount, trans_type, payment_method, month, year):
        """添加收支记录"""
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_id = cursor.fetchone()[0]
            cursor.execute("""
                INSERT INTO transactions (project_id, amount, type, payment_method, month, year_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (project_id, amount, trans_type, payment_method, month, year_id, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_monthly_transactions(self, year, month):
        """获取某月的所有收支记录"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, p.name, t.amount, t.type, t.payment_method, t.stage
            FROM transactions t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.year_id = (SELECT id FROM years WHERE year = ?) AND t.month = ?
        """, (year, month))
        transactions = cursor.fetchall()
        conn.close()
        return transactions

    def get_monthly_summary(self, year, month):
        """获取某月汇总信息"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN type = '收入' THEN amount ELSE 0 END) as total_income,
                SUM(CASE WHEN type = '支出' THEN amount ELSE 0 END) as total_expense
            FROM transactions
            WHERE year_id = (SELECT id FROM years WHERE year = ?) AND month = ?
        """, (year, month))
        result = cursor.fetchone()
        conn.close()
        total_income = result[0] or 0
        total_expense = result[1] or 0
        return total_income, total_expense, total_income - total_expense

# 测试代码
if __name__ == '__main__':
    db = DatabaseManager()
    # 测试用户验证
    success, user = db.validate_user("admin", "123456")
    print("验证结果:", success, user)
    success, user = db.validate_user("admin", "wrongpassword")
    print("验证结果:", success, user)