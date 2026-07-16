#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_sql_to_analysis.py — 执行 SQL 查询 → Pandas DataFrame → 统计分析
====================================================================
从 MySQL 读取 6 个分析 SQL 的结果，进行 Python 侧的统计和汇总。

用法:
  1. 确保数据已导入 MySQL（运行过 02_import_mysql.py）
  2. python src/03_sql_to_analysis.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("请先安装依赖: pip install sqlalchemy pymysql pandas")
    sys.exit(1)

# ======================== 配置 ========================
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password_here",
    "database": "o2o_coupon_db",
    "charset": "utf8mb4",
}


def get_engine():
    conn_str = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        f"?charset={DB_CONFIG['charset']}"
    )
    return create_engine(conn_str, echo=False)


def run_query(engine, label, sql, params=None):
    """执行 SQL 并返回 DataFrame"""
    print(f"\n[{label}]")
    try:
        df = pd.read_sql(sql, engine, params=params)
        print(f"  → {len(df)} 行, {len(df.columns)} 列")
        return df
    except Exception as e:
        print(f"  [FAIL] Query failed: {e}")
        return pd.DataFrame()


def analyze_merchant_usage(engine):
    """分析1：商户核销率（为可视化准备数据）"""
    sql = """
        SELECT
            m.merchant_id,
            COUNT(DISTINCT t.transaction_id) AS total_txn,
            SUM(CASE WHEN t.date_used IS NOT NULL THEN 1 ELSE 0 END) AS used_count,
            SUM(CASE WHEN t.date_used IS NULL AND t.date_received IS NOT NULL
                     THEN 1 ELSE 0 END) AS unused_count,
            ROUND(
                SUM(CASE WHEN t.date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
                / NULLIF(SUM(CASE WHEN t.date_received IS NOT NULL THEN 1 ELSE 0 END), 0), 2
            ) AS usage_rate_pct
        FROM merchants m
        LEFT JOIN transactions t ON m.merchant_id = t.merchant_id
        WHERE t.source IN ('offline', 'online')
        GROUP BY m.merchant_id
        HAVING SUM(CASE WHEN t.date_received IS NOT NULL THEN 1 ELSE 0 END) >= 50
        ORDER BY usage_rate_pct DESC
    """
    return run_query(engine, "商户核销率", sql)


def analyze_monthly_trend(engine):
    """分析2：月度核销趋势"""
    sql = """
        SELECT
            DATE_FORMAT(date_used, '%Y-%m') AS year_month,
            COUNT(*) AS used_count,
            COUNT(DISTINCT user_id) AS unique_users,
            COUNT(DISTINCT merchant_id) AS unique_merchants
        FROM transactions
        WHERE source IN ('offline', 'online')
          AND date_used IS NOT NULL
          AND date_used >= '2016-01-01'
          AND date_used < '2016-08-01'
        GROUP BY DATE_FORMAT(date_used, '%Y-%m')
        ORDER BY year_month
    """
    return run_query(engine, "月度趋势", sql)


def analyze_coupon_type(engine):
    """分析3：优惠券类型核销对比"""
    sql = """
        SELECT
            discount_type,
            COUNT(*) AS total_count,
            SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) AS used_count,
            ROUND(
                SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
                / NULLIF(COUNT(*), 0), 2
            ) AS usage_rate_pct,
            ROUND(AVG(discount_eq_rate), 4) AS avg_eq_rate
        FROM transactions
        WHERE source IN ('offline', 'online')
          AND coupon_id IS NOT NULL
          AND date_received IS NOT NULL
        GROUP BY discount_type
        ORDER BY usage_rate_pct DESC
    """
    return run_query(engine, "优惠券类型分析", sql)


def analyze_rfm(engine):
    """分析4：RFM 用户分层（在 Python 侧计算）"""
    sql = """
        SELECT
            user_id,
            MAX(date_used) AS last_used_date,
            COUNT(CASE WHEN date_used IS NOT NULL THEN 1 END) AS frequency,
            COALESCE(AVG(CASE WHEN date_used IS NOT NULL
                         THEN discount_man END), 0) AS avg_monetary,
            COUNT(CASE WHEN date_received IS NOT NULL THEN 1 END) AS total_received
        FROM transactions
        WHERE source IN ('offline', 'online')
        GROUP BY user_id
        HAVING frequency > 0
    """
    df = run_query(engine, "RFM用户数据", sql)

    if df.empty:
        return df

    # Python 侧计算 RFM 分数
    ref_date = pd.Timestamp("2016-07-31")
    df["last_used_date"] = pd.to_datetime(df["last_used_date"])
    df["recency_days"] = (ref_date - df["last_used_date"].fillna(ref_date)).dt.days

    # NTILE 打分 (1~5, 5 为最优)
    try:
        df["r_score"] = 6 - pd.qcut(df["recency_days"], q=5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
    except Exception:
        df["r_score"] = 3  # 兜底

    try:
        df["f_score"] = pd.qcut(df["frequency"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    except Exception:
        df["f_score"] = 3

    try:
        df["m_score"] = pd.qcut(df["avg_monetary"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    except Exception:
        df["m_score"] = 3

    df["rfm_total"] = df["r_score"] + df["f_score"] + df["m_score"]

    # 分层
    def segment(row):
        r, f = row["r_score"], row["f_score"]
        if r >= 4 and f >= 4:
            return "核心用户"
        elif r >= 4 and f <= 2:
            return "新用户"
        elif r <= 2 and f >= 4:
            return "沉睡用户"
        elif r <= 2 and f <= 2:
            return "流失用户"
        elif r >= 3 and f >= 3:
            return "活跃用户"
        else:
            return "一般用户"

    df["user_segment"] = df.apply(segment, axis=1)

    # 汇总
    summary = (
        df.groupby("user_segment")
        .agg(user_count=("user_id", "count"))
        .assign(pct=lambda x: round(x["user_count"] / x["user_count"].sum() * 100, 2))
        .sort_values("user_count", ascending=False)
    )
    print("\n[RFM分层汇总]")
    print(summary.to_string())

    return df


def analyze_overall_stats(engine):
    """分析5：全局统计"""
    sql = """
        SELECT
            COUNT(DISTINCT user_id) AS total_users,
            COUNT(DISTINCT merchant_id) AS total_merchants,
            COUNT(DISTINCT coupon_id) AS total_coupons,
            COUNT(*) AS total_records,
            SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END) AS received_cnt,
            SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) AS used_cnt,
            ROUND(
                SUM(CASE WHEN date_used IS NOT NULL THEN 1 ELSE 0 END) * 100.0
                / NULLIF(SUM(CASE WHEN date_received IS NOT NULL THEN 1 ELSE 0 END), 0), 2
            ) AS overall_usage_rate_pct
        FROM transactions
        WHERE source IN ('offline', 'online')
    """
    return run_query(engine, "全局统计", sql)


def main():
    print("=" * 60)
    print("O2O 数据分析 — SQL 查询 + Pandas 统计")
    print("=" * 60)

    engine = get_engine()

    # 全局统计
    stats = analyze_overall_stats(engine)
    if not stats.empty:
        print("\n" + "=" * 50)
        print("Global Statistics Summary")
        print("=" * 50)
        for col in stats.columns:
            print(f"  {col}: {stats[col].iloc[0]:,}")

    # 各维度分析
    df_merchant = analyze_merchant_usage(engine)
    df_monthly = analyze_monthly_trend(engine)
    df_coupon = analyze_coupon_type(engine)
    df_rfm = analyze_rfm(engine)

    # 保存中间结果（供可视化脚本使用）
    print("\n保存中间结果...")
    if not df_merchant.empty:
        df_merchant.to_csv(OUTPUT_DIR / "data_merchant_usage.csv", index=False)
        print(f"  [OK] data_merchant_usage.csv ({len(df_merchant)} 行)")

    if not df_monthly.empty:
        df_monthly.to_csv(OUTPUT_DIR / "data_monthly_trend.csv", index=False)
        print(f"  [OK] data_monthly_trend.csv ({len(df_monthly)} 行)")

    if not df_coupon.empty:
        df_coupon.to_csv(OUTPUT_DIR / "data_coupon_type.csv", index=False)
        print(f"  [OK] data_coupon_type.csv ({len(df_coupon)} 行)")

    if not df_rfm.empty:
        df_rfm.to_csv(OUTPUT_DIR / "data_rfm.csv", index=False)
        print(f"  [OK] data_rfm.csv ({len(df_rfm)} 行)")

    print(f"\n所有中间结果保存至: {OUTPUT_DIR}")
    print("下一步: python src/04_visualization.py")


if __name__ == "__main__":
    main()
