-- ============================================================
-- 04_window_functions.sql
-- 窗口函数 — 商户排名 + 月环比分析
-- 技能点: ROW_NUMBER / RANK / DENSE_RANK / LAG / LEAD
-- ============================================================

USE o2o_coupon_db;

-- ----------------------------
-- 1. 商户核销率排名（三种排名函数对比）
--    ROW_NUMBER: 严格行号，无并列
--    RANK:       有并列则跳号（1,2,2,4）
--    DENSE_RANK: 有并列不跳号（1,2,2,3）
-- ----------------------------
WITH merchant_stats AS (
    SELECT
        merchant_id,
        COUNT(*)                                              AS total_records,
        SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END) AS received_cnt,
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)     AS used_cnt,
        ROUND(
            SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
            / NULLIF(SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END), 0), 2
        ) AS usage_rate
    FROM transactions
    WHERE source IN ('offline', 'online')
    GROUP BY merchant_id
    HAVING received_cnt >= 30
)
SELECT
    merchant_id,
    received_cnt,
    used_cnt,
    usage_rate,
    -- 三种排名函数
    ROW_NUMBER() OVER (ORDER BY usage_rate DESC) AS row_num,
    RANK()       OVER (ORDER BY usage_rate DESC) AS rank_num,
    DENSE_RANK() OVER (ORDER BY usage_rate DESC) AS dense_rnk,
    -- 百分比排名
    ROUND(PERCENT_RANK() OVER (ORDER BY usage_rate DESC) * 100, 2) AS pct_rank,
    -- 分位数
    NTILE(10)    OVER (ORDER BY usage_rate DESC) AS decile
FROM merchant_stats
ORDER BY usage_rate DESC
LIMIT 50;

-- ----------------------------
-- 2. 月度核销量趋势 + 环比增长率（LAG）
-- ----------------------------
WITH monthly_stats AS (
    SELECT
        DATE_FORMAT(date_used, '%Y-%m') AS ym,
        COUNT(*)                        AS used_count,
        COUNT(DISTINCT user_id)         AS unique_users,
        COUNT(DISTINCT merchant_id)     AS unique_merchants
    FROM transactions
    WHERE source IN ('offline', 'online')
      AND date_used IS NOT NULL
      AND date_used >= '2016-01-01'
      AND date_used <  '2016-08-01'
    GROUP BY DATE_FORMAT(date_used, '%Y-%m')
)
SELECT
    ym,
    used_count,
    unique_users,
    unique_merchants,
    -- LAG: 上月核销量
    LAG(used_count, 1) OVER (ORDER BY ym) AS prev_month_used,
    -- 环比增长量
    used_count - LAG(used_count, 1) OVER (ORDER BY ym) AS mom_change,
    -- 环比增长率 (%)
    ROUND(
        (used_count - LAG(used_count, 1) OVER (ORDER BY ym)) * 100.0
        / NULLIF(LAG(used_count, 1) OVER (ORDER BY ym), 0),
        2
    ) AS mom_growth_pct,
    -- LEAD: 下月核销量（用于预测对比）
    LEAD(used_count, 1) OVER (ORDER BY ym) AS next_month_used,
    -- 累计核销量
    SUM(used_count) OVER (ORDER BY ym ROWS UNBOUNDED PRECEDING) AS cumulative_used
FROM monthly_stats
ORDER BY ym;

-- ----------------------------
-- 3. 各商户月度核销趋势（每个商户的 LAG 环比）
-- ----------------------------
WITH merchant_monthly AS (
    SELECT
        merchant_id,
        DATE_FORMAT(date_used, '%Y-%m') AS ym,
        COUNT(*)                        AS used_count
    FROM transactions
    WHERE source IN ('offline', 'online')
      AND date_used IS NOT NULL
      AND date_used >= '2016-01-01'
      AND date_used <  '2016-08-01'
    GROUP BY merchant_id, DATE_FORMAT(date_used, '%Y-%m')
)
SELECT
    merchant_id,
    ym,
    used_count,
    -- 按商户分区取上月值
    LAG(used_count, 1) OVER (PARTITION BY merchant_id ORDER BY ym) AS prev_month,
    -- 商户内环比增长率
    ROUND(
        (used_count - LAG(used_count, 1) OVER (PARTITION BY merchant_id ORDER BY ym))
        * 100.0 / NULLIF(LAG(used_count, 1) OVER (PARTITION BY merchant_id ORDER BY ym), 0),
        2
    ) AS mom_growth_pct,
    -- 商户内排名（核销量最高的月份）
    RANK() OVER (PARTITION BY merchant_id ORDER BY used_count DESC) AS month_rank
FROM merchant_monthly
ORDER BY merchant_id, ym
LIMIT 100;

-- ----------------------------
-- 4. 优惠券核销的移动平均
-- ----------------------------
WITH daily_usage AS (
    SELECT
        date_used,
        COUNT(*) AS daily_used
    FROM transactions
    WHERE source IN ('offline', 'online')
      AND date_used IS NOT NULL
    GROUP BY date_used
)
SELECT
    date_used,
    daily_used,
    -- 7 天移动平均
    ROUND(AVG(daily_used) OVER (ORDER BY date_used
          ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS ma_7d,
    -- 30 天移动平均
    ROUND(AVG(daily_used) OVER (ORDER BY date_used
          ROWS BETWEEN 29 PRECEDING AND CURRENT ROW), 1) AS ma_30d
FROM daily_usage
ORDER BY date_used;

-- ----------------------------
-- 5. FIRST_VALUE / LAST_VALUE — 每月首末核销量
-- ----------------------------
WITH monthly_daily AS (
    SELECT
        DATE_FORMAT(date_used, '%Y-%m') AS ym,
        date_used,
        COUNT(*) AS daily_count
    FROM transactions
    WHERE date_used IS NOT NULL
    GROUP BY DATE_FORMAT(date_used, '%Y-%m'), date_used
)
SELECT DISTINCT
    ym,
    FIRST_VALUE(daily_count) OVER (PARTITION BY ym ORDER BY date_used
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS first_day_count,
    LAST_VALUE(daily_count)  OVER (PARTITION BY ym ORDER BY date_used
        ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS last_day_count,
    MAX(daily_count) OVER (PARTITION BY ym) AS peak_day_count,
    AVG(daily_count) OVER (PARTITION BY ym) AS avg_daily_count
FROM monthly_daily
ORDER BY ym;
