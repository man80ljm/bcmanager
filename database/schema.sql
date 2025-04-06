-- database/schema.sql

-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 用户ID，自增主键
    username TEXT NOT NULL UNIQUE,        -- 用户名，唯一且不为空
    password TEXT NOT NULL,               -- 密码，不为空
    role TEXT DEFAULT 'user'              -- 权限级别，默认值为'user'
);

-- 插入一个默认管理员用户（测试用）
INSERT OR IGNORE INTO users (username, password, role) VALUES ('bc', '123456', 'admin');

-- 创建年份表
CREATE TABLE IF NOT EXISTS years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL UNIQUE,  -- 年份值（例如 '2025'），唯一
    created_at TEXT NOT NULL    -- 创建日期（例如 '2025-04-06'）
);