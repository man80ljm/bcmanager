-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'user',
    security_question TEXT,           -- 安全问题
    security_answer TEXT             -- 安全答案（哈希值）
);

-- 创建年份表
CREATE TABLE IF NOT EXISTS years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL UNIQUE,  -- 年份值（例如 '2025'），唯一
    created_at TEXT NOT NULL    -- 创建日期（例如 '2025-04-06'）
);

-- 项目表
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    year_id INTEGER,
    month INTEGER CHECK (month BETWEEN 1 AND 12),  -- 新增 month 字段
    created_at TEXT NOT NULL,
    FOREIGN KEY (year_id) REFERENCES years(id)
);

-- 创建收支记录表
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    amount REAL NOT NULL,              -- 总金额（initial_amount + expense_details 的总和）
    initial_amount REAL NOT NULL,      -- 用户创建或修改时输入的初始金额
    type TEXT NOT NULL CHECK (type IN ('收入', '支出')),
    payment_method TEXT NOT NULL CHECK (payment_method IN ('微信', '支付宝', '对公账户', '对私账户', '现金')),
    stage TEXT,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    year_id INTEGER,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT '未结项' CHECK (status IN ('未结项', '已结项')),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (year_id) REFERENCES years(id)
);

-- 收入详情表
CREATE TABLE IF NOT EXISTS remarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER UNIQUE,
    content TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);

-- 支出详情表
CREATE TABLE IF NOT EXISTS expense_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('收入', '支出')),
    amount REAL NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);