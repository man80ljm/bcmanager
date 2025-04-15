# database/db_manager.py

import sqlite3
import os
from datetime import datetime
import logging
import sys
import traceback
from hashlib import sha256 as hashlib_sha256

# 定义默认的数据库 schema，包含所有表的结构
DEFAULT_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    security_question TEXT,
    security_answer TEXT
);

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
    """数据库管理类，负责数据库的初始化、连接和操作"""
    def __init__(self, db_path="project_accounting.db", strict_schema=False):
        """初始化数据库管理器，设置路径并初始化数据库

        Args:
            db_path (str): 数据库文件路径，默认为 "project_accounting.db"
            strict_schema (bool): 是否严格要求 schema 文件存在，默认为 False
        """
        # 设置统一日志格式，记录时间、日志级别和消息
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # 获取资源基础路径（适配打包环境）
        self.base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        logging.debug(f"base_path: {self.base_path}")

        # 调试打包环境（如果使用 PyInstaller 打包）
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

        # 设置数据库文件路径（基于可执行文件目录）
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

        # 设置 schema.sql 文件路径
        self.schema_path = os.path.join(self.base_path, "database", "schema.sql")
        logging.debug(f"schema_path: {self.schema_path}")

        # 保存 strict_schema 参数和初始化缓存
        self.strict_schema = strict_schema
        self._year_cache = None

        # 初始化数据库并验证表结构
        try:
            self.init_database()
            self.verify_tables()
        except Exception as e:
            logging.error(f"数据库初始化失败: {str(e)}\n{traceback.format_exc()}")
            raise RuntimeError(f"无法初始化数据库，请检查日志并修复问题：{str(e)}")

    def connect(self):
        """创建并返回数据库连接，启用外键约束

        Returns:
            sqlite3.Connection: 数据库连接对象
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def verify_tables(self):
        """验证数据库中是否存在所有必要的表"""
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
        """初始化数据库，创建表结构并升级现有表"""
        if not os.path.exists(self.db_path):
            logging.info(f"创建数据库文件：{self.db_path}")

        with self.connect() as conn:
            cursor = conn.cursor()
            conn.execute("BEGIN TRANSACTION")
            try:
                # 检查并升级 users 表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                users_table_exists = cursor.fetchone() is not None
                if users_table_exists:
                    cursor.execute("PRAGMA table_info(users)")
                    columns = [col[1] for col in cursor.fetchall()]
                    if 'security_question' not in columns:
                        logging.info("users 表缺少 security_question 列，正在升级表结构...")
                        cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
                        logging.info("users 表结构升级完成！")
                    if 'security_answer' not in columns:
                        logging.info("users 表缺少 security_answer 列，正在升级表结构...")
                        cursor.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
                        logging.info("users 表结构升级完成！")

                    # 清理 users 表，确保只有一条记录（id = 1）
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    if user_count > 1:
                        logging.warning(f"users 表中有 {user_count} 条记录，正在清理多余记录...")
                        cursor.execute("DELETE FROM users WHERE id != 1")
                        logging.info("已清理 users 表多余记录")
                    elif user_count == 0:
                        # 如果表为空，插入默认用户
                        logging.info("users 表为空，正在插入默认用户...")
                        default_username = "bc"
                        default_password_hash = "5dd2b2cbf23d7c2815e7100bcbef2325c1af832ae703b834e8508cbfc595a790"
                        cursor.execute("INSERT INTO users (id, username, password, role) VALUES (1, ?, ?, 'admin')",
                                       (default_username, default_password_hash))
                        logging.info("默认用户插入成功")

                    # 验证清理结果
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    if user_count != 1:
                        raise RuntimeError(f"users 表记录数异常，期望 1 条，实际 {user_count} 条")

                # 检查并升级 projects 表结构
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

                # 检查并升级 transactions 表结构
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

                # 检查并升级 remarks 表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='remarks'")
                remarks_table_exists = cursor.fetchone() is not None
                if remarks_table_exists:
                    cursor.execute("PRAGMA table_info(remarks)")
                    columns = cursor.fetchall()
                    transaction_id_unique = False
                    for col in columns:
                        if col[1] == "transaction_id":
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

                # 检查 expense_details 表是否存在
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_details'")
                expense_details_table_exists = cursor.fetchone() is not None

                # 加载 schema 文件或使用默认 schema
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

                # 过滤 schema 中已存在的表，防止重复创建
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

                # 检查默认账户是否存在
                cursor.execute("SELECT * FROM users WHERE username = 'bc'")
                default_user = cursor.fetchone()
                logging.info(f"默认账户检查 - 用户名: bc, 数据: {default_user}")

                # 创建索引以优化查询性能
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
        """添加新的收支记录到数据库

        Args:
            project_id (int): 项目 ID
            amount (float): 金额
            trans_type (str): 交易类型（'收入' 或 '支出'）
            payment_method (str): 支付方式
            month (int): 月份（1-12）
            year (str): 年份
            stage (str, optional): 阶段

        Returns:
            bool: 是否添加成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_row = cursor.fetchone()
            if not year_row:
                raise ValueError(f"年份 {year} 不存在")
            year_id = year_row[0]
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
        """获取指定收支记录的初始金额

        Args:
            transaction_id (int): 收支记录 ID

        Returns:
            float: 初始金额
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT initial_amount FROM transactions WHERE id = ?", (transaction_id,))
        amount = cursor.fetchone()[0]
        conn.close()
        return amount

    def get_expense_details_total(self, transaction_id):
        """计算指定收支记录的支出详情总和

        Args:
            transaction_id (int): 收支记录 ID

        Returns:
            float: 支出详情总和（收入为正，支出为负）
        """
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

    def validate_user(self, username, hashed_password):
        """验证用户名和密码是否匹配，仅验证 id = 1 的记录

        Args:
            username (str): 用户名
            hashed_password (str): 密码的哈希值

        Returns:
            tuple: (bool, tuple) - 是否验证成功及用户信息
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = 1 AND username = ? AND password = ?", (username, hashed_password))
        user = cursor.fetchone()
        conn.close()
        if user:
            return True, user
        return False, None

    def get_user_security_info(self, username):
        """获取用户的安全问题和答案信息

        Args:
            username (str): 用户名

        Returns:
            tuple: (security_question, security_answer, username, password) 或 None
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT security_question, security_answer, username, password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result
        return None

    def verify_security_answer(self, username, answer):
        """验证用户输入的安全答案是否正确

        Args:
            username (str): 用户名
            answer (str): 用户输入的安全答案

        Returns:
            tuple: (bool, str, str) - 是否验证成功，用户名，密码
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT security_answer, username, password FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        if result:
            stored_answer_hash, stored_username, stored_password = result
            if not stored_answer_hash:
                return False, None, None
            input_answer_hash = hashlib_sha256(answer.encode()).hexdigest()
            if input_answer_hash == stored_answer_hash:
                return True, stored_username, stored_password
        return False, None, None

    def add_year(self, year):
        """添加年份到数据库

        Args:
            year (str): 年份值（例如 '2025'）

        Returns:
            bool: 是否添加成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("INSERT INTO years (year, created_at) VALUES (?, ?)", (year, created_at))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_years(self):
        """获取所有年份，按年份排序

        Returns:
            list: 年份列表
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT year FROM years ORDER BY year")
        years = [row[0] for row in cursor.fetchall()]
        conn.close()
        return years
    
    def is_year_exists(self, year):
        """检查指定年份是否已存在

        Args:
            year (str): 年份值

        Returns:
            bool: 是否存在
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM years WHERE year = ?", (year,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
       
    def get_projects_by_year(self, year):
        """获取指定年份的所有项目

        Args:
            year (str): 年份值

        Returns:
            list: 项目列表，格式为 [(id, name, month), ...]
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, month
            FROM projects 
            WHERE year_id = (SELECT id FROM years WHERE year = ?)
        """, (year,))
        projects = cursor.fetchall()
        print(f"Raw projects data for year {year}: {projects}")
        conn.close()
        return projects

    def get_monthly_transactions(self, year, month):
        """获取指定年份和月份的收支记录

        Args:
            year (str): 年份值
            month (int): 月份（1-12）

        Returns:
            list: 收支记录列表
        """
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
        """获取指定年份和月份的收支汇总

        Args:
            year (str): 年份值
            month (int): 月份（1-12）

        Returns:
            tuple: (total_income, total_expense, balance)
        """
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
        """更新指定收支记录

        Args:
            transaction_id (int): 收支记录 ID
            amount (float): 金额
            trans_type (str): 交易类型（'收入' 或 '支出'）
            payment_method (str): 支付方式
            stage (str, optional): 阶段

        Returns:
            tuple: (bool, str, str, str) - 是否更新成功，旧类型，新类型，旧阶段
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT type, stage FROM transactions WHERE id = ?", (transaction_id,))
            result = cursor.fetchone()
            if result is None:
                raise ValueError(f"Transaction with id {transaction_id} not found")
            old_type, old_stage = result
            logging.info(f"更新收支记录: transaction_id={transaction_id}, amount={amount}, trans_type={trans_type}, payment_method={payment_method}, stage={stage}")
            cursor.execute("""
                UPDATE transactions
                SET initial_amount = ?, type = ?, payment_method = ?, stage = ?
                WHERE id = ?
            """, (amount, trans_type, payment_method, stage, transaction_id))
            if old_type != trans_type:
                if old_type == "收入":
                    cursor.execute("DELETE FROM remarks WHERE transaction_id = ?", (transaction_id,))
                else:
                    cursor.execute("DELETE FROM expense_details WHERE transaction_id = ?", (transaction_id,))
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
        """更新项目的名称

        Args:
            project_id (int): 项目 ID
            name (str): 新项目名称

        Returns:
            bool: 是否更新成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            print(f"更新项目名称: project_id={project_id}, name={name}")
            cursor.execute("UPDATE projects SET name = ? WHERE id = ?", (name, project_id))
            conn.commit()
            print(f"项目 {project_id} 名称更新成功")
            return True
        except Exception as e:
            print(f"更新项目名称失败: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_transaction(self, transaction_id):
        """删除指定收支记录及其关联数据

        Args:
            transaction_id (int): 收支记录 ID

        Returns:
            bool: 是否删除成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM remarks WHERE transaction_id = ?", (transaction_id,))
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
        """添加新项目到数据库

        Args:
            name (str): 项目名称
            year (str): 年份
            month (int): 月份（1-12）

        Returns:
            tuple: (bool, int) - 是否添加成功及项目 ID
        """
        conn = self.connect()
        cursor = conn.cursor()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cursor.execute("SELECT id FROM years WHERE year = ?", (year,))
            year_row = cursor.fetchone()
            if not year_row:
                cursor.execute("INSERT INTO years (year, created_at) VALUES (?, ?)", (year, created_at))
                year_id = cursor.lastrowid
            else:
                year_id = year_row[0]
            cursor.execute("INSERT INTO projects (name, year_id, month, created_at) VALUES (?, ?, ?, ?)", (name, year_id, month, created_at))
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
        """更新指定收支记录的状态

        Args:
            transaction_id (int): 收支记录 ID
            status (str): 新状态（'未结项' 或 '已结项'）

        Returns:
            bool: 是否更新成功
        """
        conn = self.connect()
        cursor = conn.cursor()
        try:
            if status not in ("未结项", "已结项"):
                raise ValueError(f"无效的状态值: {status}，必须是 '未结项' 或 '已结项'")
            cursor.execute("UPDATE transactions SET status = ? WHERE id = ?", (status, transaction_id))
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
        """模糊搜索收入项目，返回项目名、年份和月份

        Args:
            keyword (str): 搜索关键字

        Returns:
            list: 项目列表，格式为 [(project_id, project_name, year, month), ...]
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

    def has_transactions_in_year(self, year):
        """检查指定年份是否有收支记录

        Args:
            year (str): 年份值

        Returns:
            bool: 是否有收支记录
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM transactions WHERE year_id = (SELECT id FROM years WHERE year = ?) LIMIT 1", (year,))
        has_data = cursor.fetchone() is not None
        conn.close()
        return has_data

# 测试代码
if __name__ == '__main__':
    """测试 DatabaseManager 类的功能"""
    db = DatabaseManager()
    success, user = db.validate_user("admin", "5900145")
    print("验证结果:", success, user)
    success, user = db.validate_user("admin", "wrongpassword")
    print("验证结果:", success, user)