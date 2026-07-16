-- ============================================================
-- 01_create_tables.sql
-- 建表语句 — 4 张表 + 主外键约束
-- 天池 O2O 优惠券数据集建模
-- ============================================================

-- 创建数据库（如不存在）
CREATE DATABASE IF NOT EXISTS o2o_coupon_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE o2o_coupon_db;

-- ----------------------------
-- 1. 用户维度表 (users)
-- ----------------------------
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id       BIGINT        NOT NULL COMMENT '用户ID（唯一标识）',
    PRIMARY KEY (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户维度表';

-- ----------------------------
-- 2. 商户维度表 (merchants)
-- ----------------------------
DROP TABLE IF EXISTS merchants;
CREATE TABLE merchants (
    merchant_id   BIGINT        NOT NULL COMMENT '商户ID（唯一标识）',
    -- 可扩展字段：商户名称、分类、城市等（原始数据未提供）
    PRIMARY KEY (merchant_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商户维度表';

-- ----------------------------
-- 3. 优惠券维度表 (coupons)
-- ----------------------------
DROP TABLE IF EXISTS coupons;
CREATE TABLE coupons (
    coupon_id     VARCHAR(32)   NOT NULL COMMENT '优惠券ID',
    discount_rate VARCHAR(32)   DEFAULT NULL COMMENT '原始折扣率（如 150:20 满150减20, 0.8 即8折）',
    discount_type ENUM('fixed','discount','none','unknown') DEFAULT NULL COMMENT '折扣类型：fixed=满减, discount=折扣',
    discount_man  DECIMAL(10,2) DEFAULT NULL COMMENT '满减门槛金额',
    discount_jian DECIMAL(10,2) DEFAULT NULL COMMENT '满减优惠金额',
    eq_discount   DECIMAL(6,4)  DEFAULT NULL COMMENT '等效折扣率（0~1），越小越优惠',
    PRIMARY KEY (coupon_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='优惠券维度表';

-- ----------------------------
-- 4. 交易事实表 (transactions)
-- ----------------------------
DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
    transaction_id  BIGINT        NOT NULL AUTO_INCREMENT COMMENT '交易流水号',
    user_id         BIGINT        NOT NULL COMMENT '用户ID',
    merchant_id     BIGINT        NOT NULL COMMENT '商户ID',
    coupon_id       VARCHAR(32)   DEFAULT NULL COMMENT '优惠券ID（无券消费则为NULL）',
    discount_rate   VARCHAR(32)   DEFAULT NULL COMMENT '原始折扣率',
    discount_type   VARCHAR(16)   DEFAULT NULL COMMENT '折扣类型：fixed/discount/none',
    discount_man    DECIMAL(10,2) DEFAULT NULL COMMENT '满减门槛',
    discount_jian   DECIMAL(10,2) DEFAULT NULL COMMENT '满减金额',
    discount_eq_rate DECIMAL(6,4) DEFAULT NULL COMMENT '等效折扣率',
    distance        INT           DEFAULT NULL COMMENT '用户-商户距离（米）',
    date_received   DATE          DEFAULT NULL COMMENT '领券日期',
    date_used       DATE          DEFAULT NULL COMMENT '核销日期（NULL=未核销）',
    action          TINYINT       DEFAULT NULL COMMENT '线上行为: 0=浏览, 1=领取, 2=核销',
    action_name     VARCHAR(16)   DEFAULT NULL COMMENT '行为名称：browse/receive/use',
    source          VARCHAR(16)   NOT NULL COMMENT '数据来源：online/offline/offline_test',

    PRIMARY KEY (transaction_id),

    -- 索引（加速 JOIN & 聚合查询）
    INDEX idx_user      (user_id),
    INDEX idx_merchant  (merchant_id),
    INDEX idx_coupon    (coupon_id),
    INDEX idx_date_recv (date_received),
    INDEX idx_date_used (date_used),
    INDEX idx_source    (source),

    -- 外键约束
    CONSTRAINT fk_txn_user     FOREIGN KEY (user_id)     REFERENCES users(user_id)     ON DELETE CASCADE,
    CONSTRAINT fk_txn_merchant FOREIGN KEY (merchant_id) REFERENCES merchants(merchant_id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_coupon   FOREIGN KEY (coupon_id)   REFERENCES coupons(coupon_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='交易事实表（合并线上线下）';

-- 查看建表结果
SHOW TABLES;
DESCRIBE users;
DESCRIBE merchants;
DESCRIBE coupons;
DESCRIBE transactions;
