# database/db_manager.py

import sqlite3
import os
from datetime import datetime
import logging
import sys
import traceback

# 默认 schema（备用，防止 schema.sql 缺失）
DEFAULT_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user'
);
INSERT OR IGNORE INTO users (username, password, role) VALUES ('bc', '123456', 'admin');
CREATE TABLE IF NOT EXISTS years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    year_id INTEGER,
    month INTEGER CHECK (month BETWEEN 1 AND 12),
    created_at TEXT NOT NULL,
    FOREIGN KEY (year_id) REFERENCES years(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    amount REAL NOT NULL,
    initial_amount REAL NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('收入', '支出')),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('微信', '支付宝', '对公账户', '对私账户', '现金')),
    stage TEXT,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year_id INTEGER,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT '未结项' CHECK (status IN ('未结项', '已结项')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (year_id) REFERENCES years(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS remarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER UNIQUE,
    content TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS expense_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('收入', '支出')),
    amount REAL NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
);
"""

class DatabaseManager:
    def __init__(self, db_path="project_accounting.db", strict_schema=False):
        # 设置统一日志
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # 获取资源基础路径
        self.base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logging.debug(f"base_path: {self.base_path}")  # 修复：print 改为 logging

        # 调试打包环境
        if hasattr(sys, '_MEIPASS'):
            logging.debug(f"临时目录内容: {os.listdir(self.base_path)}")
            database_dir = os.path.join(self.base_path, "database")
            if os.path.exists(database_dir):
                logging.debug(f"database 目录内容: {os.listdir(database_dir)}")
            else:
                logging.warning("database 目录不存在！")
                if "schema.sql" in os.listdir(self.base_path):
                    try:
                        os.makedirs(database_dir, exist_ok=True)
                        import shutil
                        shutil.move(
                            os.path.join(self.base_path, "schema.sql"),
                            os.path.join(database_dir, "schema.sql")
                        )
                        logging.info("已将 schema.sql 移动到 database/ 目录")
                    except Exception as e:
                        logging.error(f"移动 schema.sql 失败: {str(e)}")

        # 设置数据库路径
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.db_path = os.path.join(exe_dir, db_path)
        logging.debug(f"db_path: {self.db_path}")
        if not os.path.exists(self.db_path):
            temp_db_path = os.path.join(self.base_path, db_path)
            if os.path.exists(temp_db_path):
                try:
                    import shutil
                    shutil.copy(temp_db_path, self.db_path)
                    logging.info(f"从 {temp_db_path} 复制数据库到 {self.db_path}")
                except Exception as e:
                    logging.error(f"复制数据库失败: {str(e)}")
            else:
                logging.info(f"未找到初始数据库文件 {db_path}，将创建新数据库")

        # 设置 schema.sql 路径
        self.schema_path = os.path.join(self.base_path, "database", "schema.sql")
        logging.debug(f"schema_path: {self.schema_path}")

        # 保存 strict_schema
        self.strict_schema = strict_schema  # 修复：正确保存参数
        self._year_cache = None  # 初始化缓存

        try:
            self.init_database()
            self.verify_tables()
        except Exception as e:
            logging.error(f"数据库初始化失败: {str(e)}\n{traceback.format_exc()}")
            raise RuntimeError(f"无法初始化数据库，请检查日志并修复问题：{str(e)}")  # 改进：更友好错误

    def connect(self):
        """创建并返回数据库连接，启用外键约束"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")  # 修复：启用外键
        return conn
    
    def verify_tables(self):
        required_tables = ["users", "years", "projects", "transactions", "remarks", "expense_details"]
        conn = self.connect()
        cursor = conn.cursor()
        for table in required_tables:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if not cursor.fetchone():
                conn.close()
                raise RuntimeError(f"数据库缺少必要的表：{table}。请删除 project_accounting.db 文件并重新运行程序。")
        conn.close()

    def init_database(self):
        if not os.path.exists(self.db_path):
            logging.info(f"创建数据库文件：{self.db_path}")

        with self.connect() as conn:
            cursor = conn.cursor()
            conn.execute("BEGIN TRANSACTION")
            try:
                # 检查并升级 projects 表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
                projects_table_exists = cursor.fetchone() is not None
                if projects_table_exists:
                    cursor.execute("PRAGMA table_info(projects)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'month' not in columns:
                        logging.info("projects 表缺少 month 列，正在升级表结构...")
                        cursor.execute("""
                            CREATE TABLE projects_temp (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                year_id INTEGER,
                                month INTEGER CHECK (month BETWEEN 1 AND 12),
                                created_at TEXT NOT NULL,
                                FOREIGN KEY (year_id) REFERENCES years(id) ON DELETE CASCADE
                            )
                        """)
                        cursor.execute("""
                            INSERT INTO projects_temp (id, name, year_id, created_at)
                            SELECT id, name, year_id, created_at FROM projects
                        """)
                        cursor.execute("DROP TABLE projects")
                        cursor.execute("ALTER TABLE projects_temp RENAME TO projects")
                        logging.info("projects 表结构升级完成！")

                # 检查并升级 transactions 表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
                transactions_table_exists = cursor.fetchone() is not None
                if transactions_table_exists:
                    cursor.execute("PRAGMA table_info(transactions)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'status' not in columns:
                        logging.info("transactions 表缺少 status 列，正在升级表结构...")
                        cursor.execute("ALTER TABLE transactions ADD COLUMN status TEXT DEFAULT '未结项' CHECK (status IN ('未结项', '已结项'))")
                        logging.info("transactions 表结构升级完成！")
                    if 'initial_amount' not in columns:
                        logging.info("transactions 表缺少 initial_amount 列，正在升级表结构...")
                        cursor.execute("ALTER TABLE transactions ADD COLUMN initial_amount REAL NOT NULL DEFAULT 0")
                        cursor.execute("UPDATE transactions SET initial_amount = amount")
                        logging.info("transactions 表结构升级完成！")
                    if 'stage' not in columns:
                        logging.info("transactions 表缺少 stage 列，正在升级表结构...")
                        cursor.execute("ALTER TABLE transactions ADD COLUMN stage TEXT")
                        logging.info("transactions 表结构升级完成！")

                # 检查并升级 remarks 表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='remarks'")
                remarks_table_exists = cursor.fetchone() is not None
                if remarks_table_exists:
                    cursor.execute("PRAGMA table_info(remarks)")
                    columns = cursor.fetchall()
                    transaction_id_unique = False
                    for col in columns:
                        if col[1] == "transaction_id":
                            # 检查 UNIQUE 约束
                            cursor.execute("PRAGMA index_list(remarks)")
                            indexes = cursor.fetchall()
                            for index in indexes:
                                cursor.execute(f"PRAGMA index_info({index[1]})")
                                if any(col[1] == "transaction_id" for col in cursor.fetchall()):
                                    transaction_id_unique = True
                                    break
                            break
                    if not transaction_id_unique:
                        logging.info("remarks 表缺少 transaction_id 的 UNIQUE 约束，正在升级表结构...")
                        cursor.execute("""
                            CREATE TABLE remarks_temp (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                transaction_id INTEGER UNIQUE,
                                content TEXT,
                                updated_at TEXT NOT NULL,
                                FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
                            )
                        """)
                        cursor.execute("""
                            INSERT INTO remarks_temp (id, transaction_id, content, updated_at)
                            SELECT id, transaction_id, content, updated_at
                            FROM remarks
                            WHERE transaction_id IS NOT NULL
                            GROUP BY transaction_id
                            HAVING MAX(id)
                        """)
                        cursor.execute("DROP TABLE remarks")
                        cursor.execute("ALTER TABLE remarks_temp RENAME TO remarks")
                        logging.info("remarks 表结构升级完成！")

                # 检查 expense_details 表
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_details'")
                expense_details_table_exists = cursor.fetchone() is not None

                # 加载 schema
                schema = ""
                if self.strict_schema and not os.path.exists(self.schema_path):
                    raise FileNotFoundError(f"未找到 schema.sql 文件，路径：{self.schema_path}")
                if os.path.exists(self.schema_path):
                    try:
                        with open(self.schema_path, "r", encoding="utf-8") as f:
                            schema = f.read()
                    except Exception as e:
                        logging.error(f"读取 schema.sql 失败: {str(e)}")
                        schema = DEFAULT_SCHEMA
                else:
                    logging.warning("schema.sql 不存在，使用默认 schema")
                    schema = DEFAULT_SCHEMA

                # 过滤已存在表
                schema_lines = schema.splitlines()
                filtered_lines = []
                skip = False
                for line in schema_lines:
                    if line.strip().startswith("CREATE TABLE IF NOT EXISTS projects") and projects_table_exists:
                        skip = True
                        continue
                    elif line.strip().startswith("CREATE TABLE IF NOT EXISTS transactions") and transactions_table_exists:
                        skip = True
                        continue
                    elif line.strip().startswith("CREATE TABLE IF NOT EXISTS remarks") and remarks_table_exists:
                        skip = True
                        continue
                    elif line.strip().startswith("CREATE TABLE IF NOT EXISTS expense_details") and expense_details_table_exists:
                        skip = True
                        continue
                    if skip and line.strip().endswith(";"):
                        skip = False
                        continue
                    if not skip:
                        filtered_lines.append(line)
                schema = "\n".join(filtered_lines)
                cursor.executescript(schema)

                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_year_month ON transactions(year_id, month)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_remarks_transaction_id ON remarks(transaction_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_expense_details_transaction_id ON expense_details(transaction_id)")

                conn.commit()
                logging.info("数据库初始化成功")
            except Exception as e:
                conn.rollback()
                logging.error(f"数据库初始化失败: {str(e)}\n{traceback.format_exc()}")
                raise

    def add_transaction(self, project_id, amount, trans_type, payment_method, month, year, stage=None):
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_row = cursor.fetchone()
            if not year_row:
                raise ValueError(f"年份 {year} 不存在")
            year_id = year_row[0]
            # 检查是否已经存在相同 project_id、year、month 和 stage 的记录
            cursor.execute("""
                SELECT id FROM transactions 
                WHERE project_id = ? AND year_id = ? AND month = ? AND stage = ?
            """, (project_id, year_id, month, stage))
            existing_transaction = cursor.fetchone()
            if existing_transaction:
                raise ValueError(f"该项目在 {year} 年 {month} 月已存在 {stage} 的记录，请选择其他阶段！")
            
            print(f"插入收支记录: project_id={project_id}, amount={amount}, type={trans_type}, payment_method={payment_method}, stage={stage}, month={month}, year_id={year_id}")
            cursor.execute("""
                INSERT INTO transactions (project_id, amount, initial_amount, type, payment_method, stage, month, year_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (project_id, amount, amount, trans_type, payment_method, stage, month, year_id, created_at))
            transaction_id = cursor.lastrowid
            conn.commit()
            print("收支记录插入成功")
            return True
        except Exception as e:
            print(f"添加收支记录失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_transaction_initial_amount(self, transaction_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT initial_amount FROM transactions WHERE id = ?", (transaction_id,))
        amount = cursor.fetchone()[0]
        conn.close()
        return amount

    def get_expense_details_total(self, transaction_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(CASE 
                    WHEN type = '收入' THEN amount 
                    WHEN type = '支出' THEN -amount 
                    ELSE 0 
                    END)
            FROM expense_details 
            WHERE transaction_id = ?
        """, (transaction_id,))
        total = cursor.fetchone()[0] or 0
        conn.close()
        logging.info(f"Calculated details_total for transaction_id={transaction_id}: {total}")
        return total

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

    def get_monthly_transactions(self, year, month):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id, t.created_at, p.name, t.amount, t.type, t.payment_method, t.stage, t.status, t.initial_amount
            FROM transactions t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.year_id = (SELECT id FROM years WHERE year = ?) AND t.month = ?
        """, (year, month))
        transactions = cursor.fetchall()
        conn.close()
        return transactions

    def get_monthly_summary(self, year, month):
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

    def update_transaction(self, transaction_id, amount, trans_type, payment_method, stage=None):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # 获取当前类型和阶段
            cursor.execute("SELECT type, stage FROM transactions WHERE id = ?", (transaction_id,))
            result = cursor.fetchone()
            if result is None:
                raise ValueError(f"Transaction with id {transaction_id} not found")
            old_type, old_stage = result
            
            # 打印参数以调试
            logging.info(f"Updating transaction with: transaction_id={transaction_id}, amount={amount}, trans_type={trans_type}, payment_method={payment_method}, stage={stage}")
            
            # 更新初始金额、类型、支付方式和阶段
            cursor.execute("""
                UPDATE transactions
                SET initial_amount = ?, type = ?, payment_method = ?, stage = ?
                WHERE id = ?
            """, (amount, trans_type, payment_method, stage, transaction_id))
            
            # 类型变化时清理旧数据
            if old_type != trans_type:
                if old_type == "收入":  # 收入 -> 支出
                    cursor.execute("DELETE FROM remarks WHERE transaction_id = ?", (transaction_id,))
                else:  # 支出 -> 收入
                    cursor.execute("DELETE FROM expense_details WHERE transaction_id = ?", (transaction_id,))
            
            # 更新 amount：如果是支出类型，累加 expense_details 的总和
            if trans_type == "支出":
                details_total = self.get_expense_details_total(transaction_id)
                new_amount = amount + details_total
            else:
                new_amount = amount
            cursor.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amount, transaction_id))
            
            conn.commit()
            logging.info(f"Transaction {transaction_id} updated successfully")
            return True, old_type, trans_type, old_stage
        except Exception as e:
            logging.error(f"更新收支记录失败: {str(e)}")
            return False, None, None, None
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

    def add_project(self, name, year, month):
        """添加新项目到数据库"""
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            # 获取 year_id
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_row = cursor.fetchone()
            if not year_row:
                # 如果年份不存在，自动创建
                cursor.execute("INSERT INTO years (year, created_at) VALUES (?, ?)", (year, created_at))
                year_id = cursor.lastrowid
            else:
                year_id = year_row[0]
            
            # 插入项目
            cursor.execute("""
                INSERT INTO projects (name, year_id, month, created_at)
                VALUES (?, ?, ?, ?)
            """, (name, year_id, month, created_at))
            project_id = cursor.lastrowid
            conn.commit()
            print(f"项目添加成功: name={name}, year_id={year_id}, month={month}, project_id={project_id}")
            return True, project_id
        except Exception as e:
            print(f"添加项目失败: {str(e)}")
            return False, None
        finally:
            conn.close()

    def update_transaction_status(self, transaction_id, status):
        """更新交易记录的状态"""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # 验证状态值是否合法
            if status not in ("未结项", "已结项"):
                raise ValueError(f"无效的状态值: {status}，必须是 '未结项' 或 '已结项'")
            
            # 更新状态
            cursor.execute("""
                UPDATE transactions
                SET status = ?
                WHERE id = ?
            """, (status, transaction_id))
            
            # 检查是否成功更新
            if cursor.rowcount == 0:
                raise ValueError(f"Transaction with id {transaction_id} not found")
            
            conn.commit()
            logging.info(f"Transaction {transaction_id} status updated to {status}")
            return True
        except Exception as e:
            logging.error(f"更新交易状态失败: transaction_id={transaction_id}, status={status}, error={str(e)}")
            return False
        finally:
            conn.close()

    def search_income_projects(self, keyword):
        """
        模糊搜索收入项目，返回项目名、年份、月份
        返回格式：[(project_id, project_name, year, month), ...]
        """
        conn = self.connect()
        cursor = conn.cursor()
        query = """
            SELECT p.id, p.name, y.year, t.month
            FROM transactions t
            JOIN projects p ON t.project_id = p.id
            JOIN years y ON t.year_id = y.id
            WHERE t.type = '收入' AND p.name LIKE ?
            ORDER BY y.year DESC, t.month DESC
        """
        cursor.execute(query, ('%' + keyword + '%',))
        results = cursor.fetchall()
        conn.close()
        return results
    
    # 在 db_manager.py 中添加新方法
    def has_transactions_in_year(self, year):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1
            FROM transactions
            WHERE year_id = (SELECT id FROM years WHERE year = ?)
            LIMIT 1
        """, (year,))
        has_data = cursor.fetchone() is not None
        conn.close()
        return has_data

# 测试代码
if __name__ == '__main__':
    db = DatabaseManager()
    # 测试用户验证
    success, user = db.validate_user("admin", "123456")
    print("验证结果:", success, user)
    success, user = db.validate_user("admin", "wrongpassword")
    print("验证结果:", success, user)