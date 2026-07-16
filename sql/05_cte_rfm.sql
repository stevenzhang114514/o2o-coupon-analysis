-- ============================================================
-- 05_cte_rfm.sql
-- CTE + RFM 用户价值分层
-- 技能点: WITH (CTE) + 嵌套子查询 + CASE WHEN 分层
--
-- RFM 模型：
--   R (Recency)  : 最近一次核销距今天数 → 越小越好
--   F (Frequency): 核销次数               → 越大越好
--   M (Monetary) : 等效优惠力度（折扣越大=用户越活跃）→ 越大越好
-- ============================================================

USE o2o_coupon_db;

-- 设定参考日期（数据集中最后一天）
SET @ref_date = '2016-07-31';

-- ----------------------------
-- RFM 计算（CTE 链式构建）
-- ----------------------------
WITH
-- Step 1: 计算每个用户的基础指标
user_base AS (
    SELECT
        user_id,
        MAX(date_used)                                              AS last_used_date,   -- 最近核销日
        COUNT(DISTINCT CASE WHEN date_used IS NOT NULL
                      THEN DATE(date_used) END)                     AS active_days,      -- 活跃天数
        COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END)           AS frequency,         -- 核销次数 (F)
        COUNT(CASE WHEN date_received IS NOT NULL THEN 1 END)       AS total_received,    -- 总领券数
        ROUND(AVG(CASE WHEN date_used IS NOT NULL
                       THEN discount_eq_rate END), 4)               AS avg_discount,      -- 平均折扣率
        ROUND(AVG(CASE WHEN date_used IS NOT NULL
                       THEN discount_man END), 2)                   AS avg_threshold       -- 平均满减门槛
    FROM transactions
    WHERE source IN ('offline', 'online')
    GROUP BY user_id
),

-- Step 2: 计算 RFM 三个维度得分
rfm_raw AS (
    SELECT
        user_id,
        -- R: 距参考日天数
        DATEDIFF(@ref_date, COALESCE(last_used_date, '2016-01-01')) AS recency_days,
        -- F: 核销次数
        frequency,
        -- M: 用平均满减门槛作为消费力代理指标
        COALESCE(avg_threshold, 0)                                   AS monetary,
        total_received,
        active_days,
        avg_discount
    FROM user_base
),

-- Step 3: 五分位打分（1~5，5 为最优）
rfm_scored AS (
    SELECT
        *,
        -- R 打分：天数越少分越高（NTILE 反转）
        6 - NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
        -- F 打分：次数越多分越高
        NTILE(5) OVER (ORDER BY frequency ASC)         AS f_score,
        -- M 打分：门槛越高（消费力越强）分越高
        NTILE(5) OVER (ORDER BY monetary ASC)          AS m_score
    FROM rfm_raw
    WHERE frequency > 0  -- 只分析有核销行为的用户
),

-- Step 4: 计算综合 RFM 得分
rfm_combined AS (
    SELECT
        *,
        r_score + f_score + m_score                       AS rfm_total,
        CONCAT(r_score, f_score, m_score)                 AS rfm_cell,  -- 如 "555"
        -- R 和 F 是最重要的，加权
        ROUND(r_score * 0.4 + f_score * 0.4 + m_score * 0.2, 2) AS rfm_weighted
    FROM rfm_scored
)

-- Step 5: 用户分层
SELECT
    user_id,
    recency_days,
    frequency,
    monetary,
    total_received,
    r_score,
    f_score,
    m_score,
    rfm_total,
    rfm_weighted,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN '核心用户'       -- 高 R + 高 F
        WHEN r_score >= 4 AND f_score <= 2 THEN '新用户'        -- 高 R + 低 F（最近活跃但次数少）
        WHEN r_score <= 2 AND f_score >= 4 THEN '沉睡用户'      -- 低 R + 高 F（曾经活跃）
        WHEN r_score <= 2 AND f_score <= 2 THEN '流失用户'      -- 低 R + 低 F
        WHEN r_score >= 3 AND f_score >= 3 THEN '活跃用户'      -- 中等
        ELSE '一般用户'
    END AS user_segment,
    -- 细分标签
    CASE
        WHEN r_score = 5 AND f_score = 5 THEN '超级核心'
        WHEN r_score >= 4 AND f_score >= 4 THEN '核心'
        WHEN r_score >= 4 AND f_score = 3 THEN '潜力'
        WHEN r_score >= 4 AND f_score <= 2 THEN '新客'
        WHEN r_score = 3 AND f_score >= 3 THEN '稳定'
        WHEN r_score <= 2 AND f_score >= 4 THEN '沉睡-高价值'
        WHEN r_score <= 2 AND f_score >= 2 THEN '流失边缘'
        ELSE '待激活'
    END AS user_sub_segment
FROM rfm_combined
ORDER BY rfm_weighted DESC;


-- ----------------------------
-- 分层统计汇总
-- ----------------------------
WITH rfm_result AS (
    -- 复用上面的完整 CTE（实际使用时可直接引用上面的查询结果）
    -- 此处简化为独立的汇总层
    SELECT
        user_id,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN '核心用户'
            WHEN r_score >= 4 AND f_score <= 2 THEN '新用户'
            WHEN r_score <= 2 AND f_score >= 4 THEN '沉睡用户'
            WHEN r_score <= 2 AND f_score <= 2 THEN '流失用户'
            WHEN r_score >= 3 AND f_score >= 3 THEN '活跃用户'
            ELSE '一般用户'
        END AS segment
    FROM (
        SELECT
            user_id,
            6 - NTILE(5) OVER (ORDER BY DATEDIFF(@ref_date, COALESCE(last_date, '2016-01-01')) ASC) AS r_score,
            NTILE(5) OVER (ORDER BY freq ASC) AS f_score
        FROM (
            SELECT
                user_id,
                MAX(date_used) AS last_date,
                COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END) AS freq
            FROM transactions
            WHERE source IN ('offline', 'online')
            GROUP BY user_id
        ) t
        WHERE freq > 0
    ) scored
)
SELECT
    segment,
    COUNT(*)                                          AS user_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS pct
FROM rfm_result
GROUP BY segment
ORDER BY user_count DESC;


-- ----------------------------
-- RFM 变量视图（方便 Power BI / Python 直接查询）
-- ----------------------------
CREATE OR REPLACE VIEW v_user_rfm AS
WITH user_base AS (
    SELECT
        user_id,
        MAX(date_used)                                          AS last_used_date,
        COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END)       AS frequency,
        ROUND(COALESCE(AVG(CASE WHEN date_used IS NOT NULL
                           THEN discount_man END), 0), 2)       AS avg_monetary,
        COUNT(CASE WHEN date_received IS NOT NULL THEN 1 END)   AS total_received
    FROM transactions
    WHERE source IN ('offline', 'online')
    GROUP BY user_id
),
rfm_scored AS (
    SELECT
        user_id,
        last_used_date,
        frequency,
        avg_monetary,
        total_received,
        DATEDIFF('2016-07-31', COALESCE(last_used_date, '2016-01-01')) AS recency_days,
        6 - NTILE(5) OVER (ORDER BY DATEDIFF('2016-07-31', COALESCE(last_used_date, '2016-01-01')) ASC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)                                                             AS f_score,
        NTILE(5) OVER (ORDER BY COALESCE(avg_monetary, 0) ASC)                                             AS m_score
    FROM user_base
    WHERE frequency > 0
)
SELECT
    user_id,
    last_used_date,
    frequency,
    avg_monetary,
    total_received,
    recency_days,
    r_score, f_score, m_score,
    r_score + f_score + m_score AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN '核心用户'
        WHEN r_score >= 4 AND f_score <= 2 THEN '新用户'
        WHEN r_score <= 2 AND f_score >= 4 THEN '沉睡用户'
        WHEN r_score <= 2 AND f_score <= 2 THEN '流失用户'
        WHEN r_score >= 3 AND f_score >= 3 THEN '活跃用户'
        ELSE '一般用户'
    END AS user_segment
FROM rfm_scored;
