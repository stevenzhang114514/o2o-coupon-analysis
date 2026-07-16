-- ============================================================
-- 06_trend_analysis.sql
-- 时空趋势聚合 — 日期聚合 + 同比环比 + 距离分析
-- 技能点: 日期函数 + GROUP BY + 同比/环比计算
-- ============================================================

USE o2o_coupon_db;

-- ----------------------------
-- 1. 月度核销趋势（多维聚合）
-- ----------------------------
SELECT
    DATE_FORMAT(date_used, '%Y-%m')                      AS ym,
    YEAR(date_used)                                      AS year_num,
    MONTH(date_used)                                     AS month_num,
    -- 核销量指标
    COUNT(*)                                             AS used_count,
    COUNT(DISTINCT user_id)                              AS unique_users,
    COUNT(DISTINCT merchant_id)                          AS unique_merchants,
    ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS avg_uses_per_user,
    -- 折扣指标
    ROUND(AVG(CASE WHEN discount_eq_rate IS NOT NULL
              THEN discount_eq_rate END), 4)             AS avg_discount_rate,
    ROUND(AVG(CASE WHEN discount_type = 'fixed' AND discount_man IS NOT NULL
              THEN discount_man END), 2)                 AS avg_fixed_threshold
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_used IS NOT NULL
  AND date_used >= '2016-01-01'
  AND date_used <  '2016-08-01'
GROUP BY DATE_FORMAT(date_used, '%Y-%m'), YEAR(date_used), MONTH(date_used)
ORDER BY ym;

-- ----------------------------
-- 2. 按折扣类型分析核销率
-- ----------------------------
SELECT
    discount_type,
    COUNT(*)                                                        AS total_count,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)          AS used_count,
    SUM(CASE WHEN date_used IS NULL AND date_received IS NOT NULL
             THEN 1 ELSE 0 END)                                      AS unused_count,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 2
    )                                                                AS usage_rate_pct,
    ROUND(AVG(discount_eq_rate), 4)                                  AS avg_eq_rate,
    ROUND(AVG(discount_man), 2)                                      AS avg_threshold,
    ROUND(AVG(discount_jian), 2)                                     AS avg_reduction
FROM transactions
WHERE source IN ('offline', 'online')
  AND coupon_id IS NOT NULL
  AND date_received IS NOT NULL
GROUP BY discount_type
ORDER BY usage_rate_pct DESC;

-- ----------------------------
-- 3. 满减力度分桶分析（核销率 vs 折扣力度）
--    按满减门槛分桶，看哪个区间的券核销率最高
-- ----------------------------
SELECT
    CASE
        WHEN discount_man IS NULL THEN '非满减'
        WHEN discount_man <= 20   THEN '≤20元'
        WHEN discount_man <= 50   THEN '21-50元'
        WHEN discount_man <= 100  THEN '51-100元'
        WHEN discount_man <= 200  THEN '101-200元'
        WHEN discount_man <= 500  THEN '201-500元'
        ELSE '>500元'
    END                                                               AS threshold_bucket,
    COUNT(*)                                                          AS total_cnt,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)            AS used_cnt,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 2
    )                                                                 AS usage_rate_pct,
    -- 等效折扣力度（越低越优惠）
    ROUND(AVG(discount_eq_rate), 4)                                   AS avg_eq_discount
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_received IS NOT NULL
  AND coupon_id IS NOT NULL
GROUP BY
    CASE
        WHEN discount_man IS NULL THEN '非满减'
        WHEN discount_man <= 20   THEN '≤20元'
        WHEN discount_man <= 50   THEN '21-50元'
        WHEN discount_man <= 100  THEN '51-100元'
        WHEN discount_man <= 200  THEN '101-200元'
        WHEN discount_man <= 500  THEN '201-500元'
        ELSE '>500元'
    END
ORDER BY
    CASE threshold_bucket
        WHEN '非满减' THEN 0 WHEN '≤20元' THEN 1 WHEN '21-50元' THEN 2
        WHEN '51-100元' THEN 3 WHEN '101-200元' THEN 4
        WHEN '201-500元' THEN 5 ELSE 6
    END;

-- ----------------------------
-- 4. 距离 vs 核销率分析
-- ----------------------------
SELECT
    CASE
        WHEN distance IS NULL THEN '未知'
        WHEN distance = 0    THEN '0m（同位置）'
        WHEN distance = 1    THEN '1m'
        WHEN distance <= 3   THEN '2-3m'
        WHEN distance <= 5   THEN '4-5m'
        WHEN distance <= 10  THEN '6-10m'
        ELSE '>10m'
    END                                                               AS distance_bucket,
    COUNT(*)                                                          AS total_cnt,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)            AS used_cnt,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
        / NULLIF(COUNT(*), 0), 2
    )                                                                 AS usage_rate_pct
FROM transactions
WHERE source = 'offline'  -- 仅 offline 有距离字段
  AND date_received IS NOT NULL
GROUP BY
    CASE
        WHEN distance IS NULL THEN '未知'
        WHEN distance = 0    THEN '0m（同位置）'
        WHEN distance = 1    THEN '1m'
        WHEN distance <= 3   THEN '2-3m'
        WHEN distance <= 5   THEN '4-5m'
        WHEN distance <= 10  THEN '6-10m'
        ELSE '>10m'
    END
ORDER BY usage_rate_pct DESC;

-- ----------------------------
-- 5. 工作日 vs 周末核销对比
-- ----------------------------
SELECT
    CASE WHEN DAYOFWEEK(date_used) IN (1, 7) THEN '周末' ELSE '工作日' END AS day_type,
    COUNT(*)                                                               AS used_count,
    COUNT(DISTINCT user_id)                                                AS unique_users,
    ROUND(AVG(CASE WHEN discount_eq_rate IS NOT NULL
              THEN discount_eq_rate END), 4)                               AS avg_discount,
    ROUND(COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT DATE(date_used)), 0), 0)  AS avg_daily_uses
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_used IS NOT NULL
GROUP BY CASE WHEN DAYOFWEEK(date_used) IN (1, 7) THEN '周末' ELSE '工作日' END;

-- ----------------------------
-- 6. 每周核销趋势（周度聚合）
-- ----------------------------
SELECT
    YEARWEEK(date_used, 1)                                     AS yw,
    MIN(date_used)                                             AS week_start,
    MAX(date_used)                                             AS week_end,
    COUNT(*)                                                   AS used_count,
    COUNT(DISTINCT user_id)                                    AS unique_users,
    -- 上周核销量
    LAG(COUNT(*)) OVER (ORDER BY YEARWEEK(date_used, 1))      AS prev_week_used,
    -- 周环比
    ROUND(
        (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY YEARWEEK(date_used, 1)))
        * 100.0 / NULLIF(LAG(COUNT(*)) OVER (ORDER BY YEARWEEK(date_used, 1)), 0),
        2
    )                                                          AS wow_growth_pct
FROM transactions
WHERE source IN ('offline', 'online')
  AND date_used IS NOT NULL
  AND date_used >= '2016-01-01'
  AND date_used <  '2016-08-01'
GROUP BY YEARWEEK(date_used, 1)
ORDER BY yw;

-- ----------------------------
-- 7. 领券-核销时差分布
-- ----------------------------
SELECT
    CASE
        WHEN days_diff IS NULL THEN '未核销'
        WHEN days_diff = 0    THEN '当天核销'
        WHEN days_diff = 1    THEN '次日核销'
        WHEN days_diff <= 3   THEN '2-3天'
        WHEN days_diff <= 7   THEN '4-7天'
        WHEN days_diff <= 15  THEN '8-15天'
        WHEN days_diff <= 30  THEN '16-30天'
        ELSE '>30天'
    END               AS gap_bucket,
    COUNT(*)          AS cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM (
    SELECT
        DATEDIFF(date_used, date_received) AS days_diff
    FROM transactions
    WHERE source IN ('offline', 'online')
      AND date_received IS NOT NULL
) t
GROUP BY
    CASE
        WHEN days_diff IS NULL THEN '未核销'
        WHEN days_diff = 0    THEN '当天核销'
        WHEN days_diff = 1    THEN '次日核销'
        WHEN days_diff <= 3   THEN '2-3天'
        WHEN days_diff <= 7   THEN '4-7天'
        WHEN days_diff <= 15  THEN '8-15天'
        WHEN days_diff <= 30  THEN '16-30天'
        ELSE '>30天'
    END
ORDER BY
    CASE gap_bucket
        WHEN '当天核销' THEN 1 WHEN '次日核销' THEN 2
        WHEN '2-3天' THEN 3 WHEN '4-7天' THEN 4
        WHEN '8-15天' THEN 5 WHEN '16-30天' THEN 6
        WHEN '>30天' THEN 7 ELSE 8
    END;
