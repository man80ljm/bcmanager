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

# 测试代码
if __name__ == '__main__':
    db = DatabaseManager()
    # 测试用户验证
    success, user = db.validate_user("admin", "123456")
    print("验证结果:", success, user)
    success, user = db.validate_user("admin", "wrongpassword")
    print("验证结果:", success, user)