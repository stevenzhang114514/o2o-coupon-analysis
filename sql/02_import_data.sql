-- ============================================================
-- 02_import_data.sql
-- 数据导入 — LOAD DATA INFILE 批量导入 4 张表
-- 使用前请先执行 01_create_tables.sql
-- ============================================================

USE o2o_coupon_db;

-- 注意：以下路径需根据实际 MySQL 环境修改
-- Windows 路径示例，Linux/Mac 需改为 /home/... 或 /Users/...
-- 建议先将 CSV 复制到 MySQL 的 secure_file_priv 目录

-- ----------------------------
-- 方法一：LOAD DATA INFILE（推荐，速度快）
-- ----------------------------

-- 1. 导入用户表
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/users.csv'
INTO TABLE users
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(user_id);

SELECT COUNT(*) AS user_count FROM users;  -- 验证

-- 2. 导入商户表
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/merchants.csv'
INTO TABLE merchants
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(merchant_id);

SELECT COUNT(*) AS merchant_count FROM merchants;  -- 验证

-- 3. 导入优惠券表
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/coupons.csv'
INTO TABLE coupons
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(coupon_id, discount_rate);

SELECT COUNT(*) AS coupon_count FROM coupons;  -- 验证

-- 4. 导入交易表（大表，可能耗时较长）
LOAD DATA INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/transactions.csv'
INTO TABLE transactions
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(transaction_id, user_id, merchant_id, coupon_id, discount_rate,
 @discount_type, @discount_man, @discount_jian, @discount_eq_rate,
 @distance, @date_received, @date_used, @action, @action_name, @source)
SET
 discount_type     = NULLIF(@discount_type, ''),
 discount_man      = NULLIF(@discount_man, ''),
 discount_jian     = NULLIF(@discount_jian, ''),
 discount_eq_rate  = NULLIF(@discount_eq_rate, ''),
 distance          = NULLIF(@distance, ''),
 date_received     = NULLIF(@date_received, ''),
 date_used         = NULLIF(@date_used, ''),
 action            = NULLIF(@action, ''),
 action_name       = NULLIF(@action_name, ''),
 source            = @source;

SELECT COUNT(*) AS transaction_count FROM transactions;  -- 验证


-- ----------------------------
-- 方法二：INSERT（适用于少量数据或远程导入）
-- 由 Python 脚本 02_import_mysql.py 逐批执行
-- ----------------------------
-- 参见 src/02_import_mysql.py
-- 使用 pandas + SQLAlchemy 批量 INSERT，自动处理 NULL 值


-- ----------------------------
-- 导入后基础统计
-- ----------------------------
SELECT 'users'        AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'merchants'    AS table_name, COUNT(*) AS row_count FROM merchants
UNION ALL
SELECT 'coupons'      AS table_name, COUNT(*) AS row_count FROM coupons
UNION ALL
SELECT 'transactions' AS table_name, COUNT(*) AS row_count FROM transactions;

-- 查看交易表抽样
SELECT * FROM transactions LIMIT 10;
