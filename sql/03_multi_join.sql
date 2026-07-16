-- ============================================================
-- 03_multi_join.sql
-- 多表关联查询 — 商户核销率分析
-- 技能点: JOIN + GROUP BY + HAVING + 子查询
-- ============================================================

USE o2o_coupon_db;

-- ----------------------------
-- 1. 各商户优惠券核销率
--    核销率 = 已使用券数 / 领取券数
-- ----------------------------
SELECT
    m.merchant_id,
    COUNT(DISTINCT t.transaction_id)                                          AS total_txn,        -- 总交易数
    SUM(CASE WHEN t.date_used IS NOT NULL THEN 1 ELSE 0 END)                 AS used_count,       -- 已核销
    SUM(CASE WHEN t.date_used IS NULL AND t.date_received IS NOT NULL
             THEN 1 ELSE 0 END)                                               AS unused_count,     -- 已领取未核销
    ROUND(
        SUM(CASE WHEN t.date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN t.date_received IS NOT NULL THEN 1 ELSE 0 END), 0),
        2
    )                                                                         AS usage_rate_pct    -- 核销率(%)
FROM merchants m
LEFT JOIN transactions t ON m.merchant_id = t.merchant_id
WHERE t.source IN ('offline', 'online')  -- 仅训练数据
GROUP BY m.merchant_id
HAVING SUM(CASE WHEN t.date_received IS NOT NULL THEN 1 ELSE 0 END) >= 100   -- 至少 100 条领券记录
ORDER BY usage_rate_pct DESC;

-- ----------------------------
-- 2. 商户核销率排名（含子查询）
--    使用子查询先计算每个商户的核销指标，再排名
-- ----------------------------
SELECT
    merchant_id,
    total_received,
    total_used,
    usage_rate_pct,
    -- 排名
    RANK()       OVER (ORDER BY usage_rate_pct DESC) AS rank_by_rate,
    DENSE_RANK() OVER (ORDER BY usage_rate_pct DESC) AS dense_rank_by_rate,
    ROW_NUMBER() OVER (ORDER BY usage_rate_pct DESC) AS row_num
FROM (
    -- 子查询：计算每个商户的核销指标
    SELECT
        m.merchant_id,
        COUNT(CASE WHEN t.date_received IS NOT NULL THEN 1 END) AS total_received,
        COUNT(CASE WHEN t.date_used IS NOT NULL THEN 1 END)     AS total_used,
        ROUND(
            COUNT(CASE WHEN t.date_used IS NOT NULL THEN 1 END) * 100.0
            / NULLIF(COUNT(CASE WHEN t.date_received IS NOT NULL THEN 1 END), 0), 2
        ) AS usage_rate_pct
    FROM merchants m
    INNER JOIN transactions t ON m.merchant_id = t.merchant_id
    WHERE t.source IN ('offline', 'online')
    GROUP BY m.merchant_id
    HAVING total_received >= 50  -- 过滤样本量太少的商户
) AS merchant_stats
ORDER BY usage_rate_pct DESC
LIMIT 30;

-- ----------------------------
-- 3. 高价值商户 + 优惠券组合分析
--    核销率 > 50% 的商户，看他们的优惠券类型分布
-- ----------------------------
SELECT
    m.merchant_id,
    t.discount_type,
    COUNT(*)                                    AS txn_count,
    ROUND(AVG(t.discount_eq_rate), 4)           AS avg_eq_discount,
    SUM(CASE WHEN t.date_used IS NOT NULL THEN 1 ELSE 0 END) AS used_cnt
FROM merchants m
INNER JOIN transactions t ON m.merchant_id = t.merchant_id
WHERE m.merchant_id IN (
    -- 子查询：核销率前 10 的商户
    SELECT merchant_id
    FROM (
        SELECT
            merchant_id,
            COUNT(CASE WHEN date_received IS NOT NULL THEN 1 END) AS received,
            COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END)     AS used
        FROM transactions
        WHERE source IN ('offline', 'online')
        GROUP BY merchant_id
        HAVING received >= 100
    ) sub
    WHERE used * 1.0 / received > 0.3
)
  AND t.coupon_id IS NOT NULL
GROUP BY m.merchant_id, t.discount_type
ORDER BY m.merchant_id, txn_count DESC;

-- ----------------------------
-- 4. 全局统计汇总
-- ----------------------------
SELECT
    '整体'                                                       AS scope,
    COUNT(DISTINCT user_id)                                     AS total_users,
    COUNT(DISTINCT merchant_id)                                 AS total_merchants,
    COUNT(DISTINCT coupon_id)                                   AS total_coupons,
    COUNT(*)                                                    AS total_records,
    SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END)  AS received_cnt,
    SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END)      AS used_cnt,
    ROUND(
        SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END), 0),
        2
    ) AS overall_usage_rate_pct
FROM transactions
WHERE source IN ('offline', 'online');
