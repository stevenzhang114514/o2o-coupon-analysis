-- ============================================================
-- 00_create_summary_tables.sql
-- 预处理：创建汇总表，避免每次分析都扫 1300 万行
-- 在 DataGrip 中先跑这个，后面的分析 SQL 秒出结果
-- ============================================================

USE o2o_coupon_db;

-- ----------------------------
-- 汇总表 1: 商户核销率（03 号 SQL 用）
-- ----------------------------
DROP TABLE IF EXISTS summary_merchant_usage;
CREATE TABLE summary_merchant_usage AS
SELECT
    merchant_id,
    COUNT(*)                                              AS total_received,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) AS used_count,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    ) AS usage_rate_pct
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_received IS NOT NULL
GROUP BY merchant_id
HAVING total_received >= 50
ORDER BY usage_rate_pct DESC;

CREATE INDEX idx_smu_rate ON summary_merchant_usage(usage_rate_pct DESC);
SELECT CONCAT('summary_merchant_usage: ', COUNT(*), ' rows') AS result FROM summary_merchant_usage;

-- ----------------------------
-- 汇总表 2: 月度核销趋势（04/06 号 SQL 用）
-- ----------------------------
DROP TABLE IF EXISTS summary_monthly_trend;
CREATE TABLE summary_monthly_trend AS
SELECT
    DATE_FORMAT(date_used, '%Y-%m') AS ym,
    COUNT(*)                        AS used_count,
    COUNT(DISTINCT user_id)         AS unique_users,
    COUNT(DISTINCT merchant_id)     AS unique_merchants
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_used IS NOT NULL
  AND date_used >= '2016-01-01'
  AND date_used < '2016-08-01'
GROUP BY DATE_FORMAT(date_used, '%Y-%m')
ORDER BY ym;

SELECT CONCAT('summary_monthly_trend: ', COUNT(*), ' rows') AS result FROM summary_monthly_trend;

-- ----------------------------
-- 汇总表 3: 优惠券类型统计（06 号 SQL 用）
-- ----------------------------
DROP TABLE IF EXISTS summary_coupon_type;
CREATE TABLE summary_coupon_type AS
SELECT
    discount_type,
    COUNT(*)                                                      AS total_count,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)        AS used_count,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                              AS usage_rate_pct,
    ROUND(AVG(discount_eq_rate), 4)                                AS avg_eq_rate,
    ROUND(AVG(discount_man), 2)                                    AS avg_threshold,
    ROUND(AVG(discount_jian), 2)                                   AS avg_reduction
FROM transactions
WHERE source IN ('offline', 'online')
  AND coupon_id IS NOT NULL
  AND date_received IS NOT NULL
GROUP BY discount_type
ORDER BY usage_rate_pct DESC;

SELECT CONCAT('summary_coupon_type: ', COUNT(*), ' rows') AS result FROM summary_coupon_type;

-- ----------------------------
-- 汇总表 4: RFM 用户分层（05 号 SQL 用）
-- ----------------------------
DROP TABLE IF EXISTS summary_rfm_scores;
CREATE TABLE summary_rfm_scores AS
SELECT
    user_id,
    MAX(date_used)                                                AS last_used_date,
    COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END)             AS frequency,
    ROUND(COALESCE(AVG(CASE WHEN date_used IS NOT NULL
                       THEN discount_man END), 0), 2)             AS avg_monetary,
    COUNT(CASE WHEN date_received IS NOT NULL THEN 1 END)         AS total_received,
    DATEDIFF('2016-07-31', COALESCE(MAX(date_used), '2016-01-01')) AS recency_days
FROM transactions
WHERE source IN ('offline', 'online')
GROUP BY user_id
HAVING frequency > 0;

SELECT CONCAT('summary_rfm_scores: ', COUNT(*), ' rows') AS result FROM summary_rfm_scores;

-- ----------------------------
-- 汇总表 5: 折扣分桶统计
-- ----------------------------
DROP TABLE IF EXISTS summary_threshold_bucket;
CREATE TABLE summary_threshold_bucket AS
SELECT
    CASE
        WHEN discount_man IS NULL THEN '非满减'
        WHEN discount_man <= 20   THEN '<=20元'
        WHEN discount_man <= 50   THEN '21-50元'
        WHEN discount_man <= 100  THEN '51-100元'
        WHEN discount_man <= 200  THEN '101-200元'
        WHEN discount_man <= 500  THEN '201-500元'
        ELSE '>500元'
    END                                                              AS threshold_bucket,
    COUNT(*)                                                         AS total_cnt,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)           AS used_cnt,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
        2
    )                                                                AS usage_rate_pct,
    ROUND(AVG(discount_eq_rate), 4)                                  AS avg_eq_discount
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_received IS NOT NULL
  AND coupon_id IS NOT NULL
GROUP BY
    CASE
        WHEN discount_man IS NULL THEN '非满减'
        WHEN discount_man <= 20   THEN '<=20元'
        WHEN discount_man <= 50   THEN '21-50元'
        WHEN discount_man <= 100  THEN '51-100元'
        WHEN discount_man <= 200  THEN '101-200元'
        WHEN discount_man <= 500  THEN '201-500元'
        ELSE '>500元'
    END;

SELECT CONCAT('summary_threshold_bucket: ', COUNT(*), ' rows') AS result FROM summary_threshold_bucket;

-- ----------------------------
-- 汇总表 6: 领券-核销时差
-- ----------------------------
DROP TABLE IF EXISTS summary_gap_analysis;
CREATE TABLE summary_gap_analysis AS
SELECT
    CASE
        WHEN DATEDIFF(date_used, date_received) IS NULL THEN '未核销'
        WHEN DATEDIFF(date_used, date_received) = 0  THEN '当天核销'
        WHEN DATEDIFF(date_used, date_received) = 1  THEN '次日核销'
        WHEN DATEDIFF(date_used, date_received) <= 3 THEN '2-3天'
        WHEN DATEDIFF(date_used, date_received) <= 7 THEN '4-7天'
        WHEN DATEDIFF(date_used, date_received) <= 15 THEN '8-15天'
        WHEN DATEDIFF(date_used, date_received) <= 30 THEN '16-30天'
        ELSE '>30天'
    END          AS gap_bucket,
    COUNT(*)     AS cnt
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_received IS NOT NULL
GROUP BY gap_bucket;

SELECT CONCAT('summary_gap_analysis: ', COUNT(*), ' rows') AS result FROM summary_gap_analysis;

-- ======================== 完成 ========================
SELECT 'All summary tables created!' AS status;
SHOW TABLES LIKE 'summary_%';
