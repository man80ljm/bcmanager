# database/db_manager.py

import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path="project_accounting.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库，创建表结构，并处理表结构升级"""
        if not os.path.exists(self.db_path):
            print(f"创建数据库文件：{self.db_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 检查 projects 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        projects_table_exists = cursor.fetchone() is not None

        # 如果 projects 表存在，检查是否有 month 列
        if projects_table_exists:
            cursor.execute("PRAGMA table_info(projects)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'month' not in columns:
                print("projects 表缺少 month 列，正在升级表结构...")
                cursor.execute("""
                    CREATE TABLE projects_temp (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        year_id INTEGER,
                        month INTEGER CHECK (month BETWEEN 1 AND 12),
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (year_id) REFERENCES years(id)
                    )
                """)
                cursor.execute("""
                    INSERT INTO projects_temp (id, name, year_id, created_at)
                    SELECT id, name, year_id, created_at FROM projects
                """)
                cursor.execute("DROP TABLE projects")
                cursor.execute("ALTER TABLE projects_temp RENAME TO projects")
                print("projects 表结构升级完成！")

        # 检查 transactions 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        transactions_table_exists = cursor.fetchone() is not None

        # 如果 transactions 表存在，检查是否有 status 列
        if transactions_table_exists:
            cursor.execute("PRAGMA table_info(transactions)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'status' not in columns:
                print("transactions 表缺少 status 列，正在升级表结构...")
                cursor.execute("ALTER TABLE transactions ADD COLUMN status TEXT DEFAULT '未结项' CHECK (status IN ('未结项', '已结项'))")
                print("transactions 表结构升级完成！")

        # 读取 schema.sql 文件
        with open("database/schema.sql", "r", encoding="utf-8") as f:
            schema_lines = f.read().splitlines()

        # 如果 projects 表存在，过滤掉 projects 表定义
        # 如果 transactions 表存在，过滤掉 transactions 表定义
        filtered_lines = []
        skip = False
        skip_table = None
        for line in schema_lines:
            # 检查是否需要开始跳过
            if line.strip().startswith("CREATE TABLE IF NOT EXISTS projects") and projects_table_exists:
                skip = True
                skip_table = "projects"
                continue
            elif line.strip().startswith("CREATE TABLE IF NOT EXISTS transactions") and transactions_table_exists:
                skip = True
                skip_table = "transactions"
                continue

            # 检查是否结束跳过
            if skip and line.strip().endswith(";"):
                skip = False
                skip_table = None
                continue

            # 如果不在跳过模式，添加该行
            if not skip:
                filtered_lines.append(line)

        schema = "\n".join(filtered_lines)

        # 执行 schema
        cursor.executescript(schema)

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
    
    def add_project(self, name, year, month):
        """添加新项目"""
        if month is None or not (1 <= month <= 12):
            raise ValueError("月份必须在 1-12 之间")
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_id = cursor.fetchone()
            if not year_id:
                raise ValueError(f"年份 {year} 不存在")
            year_id = year_id[0]
            cursor.execute("INSERT INTO projects (name, year_id, month, created_at) VALUES (?, ?, ?, ?)", 
                        (name, year_id, month, created_at))
            project_id = cursor.lastrowid
            conn.commit()
            return True, project_id
        except sqlite3.IntegrityError:
            return False, None
        finally:
            conn.close()
    
    def get_projects_by_year(self, year):
        """获取指定年份的所有项目"""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, month
            FROM projects 
            WHERE year_id = (SELECT id FROM years WHERE year = ?)
        """, (year,))
        projects = cursor.fetchall()  # 返回 [(id, name, month), ...]
        print(f"Raw projects data for year {year}: {projects}")  # 添加日志
        conn.close()
        return projects

    def add_transaction(self, project_id, amount, trans_type, payment_method, month, year, stage=None):
        """添加收支记录，支持阶段"""
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_row = cursor.fetchone()
            if not year_row:
                raise ValueError(f"年份 {year} 不存在")
            year_id = year_row[0]
            print(f"插入收支记录: project_id={project_id}, amount={amount}, type={trans_type}, payment_method={payment_method}, stage={stage}, month={month}, year_id={year_id}")
            cursor.execute("""
                INSERT INTO transactions (project_id, amount, type, payment_method, stage, month, year_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, amount, trans_type, payment_method, stage, month, year_id, created_at))
            conn.commit()
            print("收支记录插入成功")
            return True
        except Exception as e:
            print(f"添加收支记录失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_monthly_transactions(self, year, month):
            """获取某月的所有收支记录，包括状态"""
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.created_at, p.name, t.amount, t.type, t.payment_method, t.stage, t.status
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

    def update_transaction(self, transaction_id, amount, trans_type, payment_method):
            """更新收支记录（不再更新 stage）"""
            conn = self.connect()
            cursor = conn.cursor()
            try:
                print(f"更新收支记录: id={transaction_id}, amount={amount}, type={trans_type}, payment_method={payment_method}")
                cursor.execute("""
                    UPDATE transactions
                    SET amount = ?, type = ?, payment_method = ?
                    WHERE id = ?
                """, (amount, trans_type, payment_method, transaction_id))
                conn.commit()
                print(f"收支记录 {transaction_id} 更新成功")
                return True
            except Exception as e:
                print(f"更新收支记录失败: {str(e)}")
                return False
            finally:
                conn.close()

    def update_transaction_status(self, transaction_id, status):
            """更新收支记录的状态"""
            conn = self.connect()
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE transactions
                    SET status = ?
                    WHERE id = ?
                """, (status, transaction_id))
                conn.commit()
                return True
            except Exception as e:
                print(f"更新状态失败: {str(e)}")
                return False
            finally:
                conn.close()

    def update_project_name(self, project_id, name):
        """更新项目的名称"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            print(f"更新项目名称: project_id={project_id}, name={name}")
            cursor.execute("""
                UPDATE projects
                SET name = ?
                WHERE id = ?
            """, (name, project_id))
            conn.commit()
            print(f"项目 {project_id} 名称更新成功")
            return True
        except Exception as e:
            print(f"更新项目名称失败: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_transaction(self, transaction_id):
        """删除收支记录"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # 先删除关联的备注（如果有）
            cursor.execute("DELETE FROM remarks WHERE transaction_id = ?", (transaction_id,))
            # 删除收支记录
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()
            print(f"收支记录 {transaction_id} 删除成功")
            return True
        except Exception as e:
            print(f"删除收支记录失败: {str(e)}")
            return False
        finally:
            conn.close()
            
# 测试代码
if __name__ == '__main__':
    db = DatabaseManager()
    # 测试用户验证
    success, user = db.validate_user("admin", "123456")
    print("验证结果:", success, user)
    success, user = db.validate_user("admin", "wrongpassword")
    print("验证结果:", success, user)