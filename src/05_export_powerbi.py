#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_export_powerbi.py — 导出 Power BI 即用 CSV（含所有计算列 + 聚合表）
========================================================
用法: py -3 src/05_export_powerbi.py
输出: output/powerbi/ 目录下的 CSV，拖入 Power BI 直接可视化
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "split_data"
OUT_DIR = BASE_DIR / "output" / "powerbi"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TXN_PATH = DATA_DIR / "transactions.csv"
CHUNK_SIZE = 100000


def process_chunk(chunk):
    """给一个 chunk 加上所有计算列"""
    # 日期转换
    chunk["date_received"] = pd.to_datetime(chunk["date_received"], errors="coerce")
    chunk["date_used"] = pd.to_datetime(chunk["date_used"], errors="coerce")

    # 01: 是否核销 / 是否领券
    chunk["is_used"] = chunk["date_used"].notna().astype(int)
    chunk["is_received"] = chunk["date_received"].notna().astype(int)

    # 02: 距离分组
    def distance_bucket(d):
        if pd.isna(d) or d == "":
            return "未知"
        d = float(d)
        if d == 0:
            return "0m(同位置)"
        elif d == 1:
            return "1m"
        elif d <= 3:
            return "2-3m"
        elif d <= 5:
            return "4-5m"
        elif d <= 10:
            return "6-10m"
        else:
            return "10m+"

    chunk["distance_bucket"] = chunk["Distance"].apply(distance_bucket)

    # 03: 工作日 vs 周末
    chunk["day_type"] = chunk["date_used"].apply(
        lambda d: "周末" if pd.notna(d) and d.weekday() >= 5 else ("工作日" if pd.notna(d) else "未知")
    )

    # 04: 领券-核销时差
    chunk["gap_days"] = (chunk["date_used"] - chunk["date_received"]).dt.days

    def gap_bucket(d):
        if pd.isna(d):
            return "未核销"
        d = int(d)
        if d == 0:
            return "当天核销"
        elif d == 1:
            return "次日核销"
        elif d <= 3:
            return "2-3天"
        elif d <= 7:
            return "4-7天"
        elif d <= 15:
            return "8-15天"
        elif d <= 30:
            return "16-30天"
        else:
            return ">30天"

    chunk["gap_bucket"] = chunk["gap_days"].apply(gap_bucket)

    # 05: 满减门槛分桶
    def threshold_bucket(row):
        t = row["discount_type"]
        m = row["discount_man"]
        if t != "fixed" or pd.isna(m):
            return "非满减"
        m = float(m)
        if m <= 20:
            return "<=20元"
        elif m <= 50:
            return "21-50元"
        elif m <= 100:
            return "51-100元"
        elif m <= 200:
            return "101-200元"
        elif m <= 500:
            return "201-500元"
        else:
            return ">500元"

    chunk["threshold_bucket"] = chunk.apply(threshold_bucket, axis=1)

    # 06: 折扣类型中文名
    type_map = {"fixed": "满减券", "discount": "折扣券", "none": "无优惠券", "unknown": "未知"}
    chunk["discount_type_cn"] = chunk["discount_type"].map(type_map).fillna("未知")

    # 07: 年-月（用于折线图）
    chunk["year_month"] = chunk["date_used"].dt.strftime("%Y-%m")

    return chunk


def main():
    print("=" * 60)
    print("Exporting Power BI ready CSV files...")
    print("=" * 60)

    if not TXN_PATH.exists():
        print(f"[MISS] {TXN_PATH}")
        return

    # ====================
    # 1. 全量 transactions（加计算列，分批写入）
    # ====================
    print("\n[1/7] Processing transactions with computed columns...")
    txn_out = OUT_DIR / "transactions_enriched.csv"
    first_chunk = True
    total = 0

    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        # 只保留需要的列（减小体积）
        cols = [
            "user_id", "merchant_id", "coupon_id", "discount_type", "discount_type_cn",
            "discount_man", "discount_jian", "discount_eq_rate",
            "Distance", "distance_bucket", "date_received", "date_used",
            "is_used", "is_received", "day_type", "gap_days", "gap_bucket",
            "threshold_bucket", "year_month", "source", "action_name",
        ]
        chunk = chunk[[c for c in cols if c in chunk.columns]]
        chunk.to_csv(txn_out, index=False, mode="w" if first_chunk else "a",
                     header=first_chunk, encoding="utf-8-sig")
        total += len(chunk)
        first_chunk = False
        print(f"  processed {total:>12,} rows...", end="\r")

    print(f"\n  [OK] {total:,} rows -> {txn_out}")

    # ====================
    # 2-7: 各图表聚合 CSV（直接拖入 Power BI 出图）
    # ====================

    print("\n[2/7] Monthly trend aggregation...")
    # 读回来做聚合（用 enriched 文件可能太大，直接用原始 transactions 聚合更快）
    del chunk  # 释放内存
    monthly = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        g = chunk[chunk["date_used"].notna() & chunk["year_month"].notna()].groupby("year_month").agg(
            used_count=("is_used", "sum"),
            unique_users=("user_id", "nunique"),
            unique_merchants=("merchant_id", "nunique"),
        ).reset_index()
        monthly.append(g)
    df_monthly = pd.concat(monthly).groupby("year_month").agg(
        used_count=("used_count", "sum"),
        unique_users=("unique_users", "sum"),  # approximate
        unique_merchants=("unique_merchants", "sum"),
    ).reset_index().sort_values("year_month")
    df_monthly["avg_uses_per_user"] = round(df_monthly["used_count"] / df_monthly["unique_users"], 2)
    df_monthly.to_csv(OUT_DIR / "chart_monthly_trend.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_monthly)} rows")

    print("\n[3/7] Coupon type aggregation...")
    coupon_type = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        mask = chunk["coupon_id"].notna() & chunk["date_received"].notna()
        g = chunk[mask].groupby("discount_type_cn").agg(
            total_count=("is_received", "sum"),
            used_count=("is_used", "sum"),
        ).reset_index()
        coupon_type.append(g)
    df_ct = pd.concat(coupon_type).groupby("discount_type_cn").sum().reset_index()
    df_ct["usage_rate_pct"] = round(df_ct["used_count"] / df_ct["total_count"] * 100, 2)
    df_ct.to_csv(OUT_DIR / "chart_coupon_type.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_ct)} rows")

    print("\n[4/7] Distance aggregation...")
    distance = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        mask = (chunk["source"] == "offline") & chunk["date_received"].notna()
        g = chunk[mask].groupby("distance_bucket").agg(
            total_count=("is_received", "sum"),
            used_count=("is_used", "sum"),
        ).reset_index()
        distance.append(g)
    df_dist = pd.concat(distance).groupby("distance_bucket").sum().reset_index()
    df_dist["usage_rate_pct"] = round(df_dist["used_count"] / df_dist["total_count"] * 100, 2)
    order = ["0m(同位置)", "1m", "2-3m", "4-5m", "6-10m", "10m+", "未知"]
    df_dist["_order"] = df_dist["distance_bucket"].apply(lambda x: order.index(x) if x in order else 99)
    df_dist = df_dist.sort_values("_order").drop(columns=["_order"])
    df_dist.to_csv(OUT_DIR / "chart_distance.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_dist)} rows")

    print("\n[5/7] Weekday/weekend aggregation...")
    daytype = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        mask = chunk["date_used"].notna()
        g = chunk[mask].groupby("day_type").agg(
            used_count=("is_used", "sum"),
            unique_users=("user_id", "nunique"),
        ).reset_index()
        daytype.append(g)
    df_day = pd.concat(daytype).groupby("day_type").agg(
        used_count=("used_count", "sum"),
        unique_users=("unique_users", "sum"),
    ).reset_index()
    df_day.to_csv(OUT_DIR / "chart_day_type.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_day)} rows")

    print("\n[6/7] Gap (receive-to-use) aggregation...")
    gap = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        mask = chunk["date_received"].notna()
        g = chunk[mask].groupby("gap_bucket").size().reset_index(name="cnt")
        gap.append(g)
    df_gap = pd.concat(gap).groupby("gap_bucket").sum().reset_index()
    df_gap["pct"] = round(df_gap["cnt"] / df_gap["cnt"].sum() * 100, 2)
    gap_order = ["当天核销", "次日核销", "2-3天", "4-7天", "8-15天", "16-30天", ">30天", "未核销"]
    df_gap["_order"] = df_gap["gap_bucket"].apply(lambda x: gap_order.index(x) if x in gap_order else 99)
    df_gap = df_gap.sort_values("_order").drop(columns=["_order"])
    df_gap.to_csv(OUT_DIR / "chart_gap.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_gap)} rows")

    print("\n[7/7] Threshold bucket aggregation...")
    thresh = []
    for chunk in pd.read_csv(TXN_PATH, chunksize=CHUNK_SIZE, low_memory=False):
        chunk = process_chunk(chunk)
        mask = chunk["coupon_id"].notna() & chunk["date_received"].notna()
        g = chunk[mask].groupby("threshold_bucket").agg(
            total_count=("is_received", "sum"),
            used_count=("is_used", "sum"),
        ).reset_index()
        thresh.append(g)
    df_th = pd.concat(thresh).groupby("threshold_bucket").sum().reset_index()
    df_th["usage_rate_pct"] = round(df_th["used_count"] / df_th["total_count"] * 100, 2)
    th_order = ["<=20元", "21-50元", "51-100元", "101-200元", "201-500元", ">500元", "非满减"]
    df_th["_order"] = df_th["threshold_bucket"].apply(lambda x: th_order.index(x) if x in th_order else 99)
    df_th = df_th.sort_values("_order").drop(columns=["_order"])
    df_th.to_csv(OUT_DIR / "chart_threshold.csv", index=False, encoding="utf-8-sig")
    print(f"  [OK] {len(df_th)} rows")

    # ====================
    # 同时复制 RFM 结果
    # ====================
    rfm_src = BASE_DIR / "output" / "result_05_rfm.txt"
    if rfm_src.exists():
        df_rfm = pd.read_csv(rfm_src, sep="\t")
        # 聚合 RFM 分层
        rfm_agg = df_rfm.groupby("user_segment").size().reset_index(name="user_count")
        rfm_agg["pct"] = round(rfm_agg["user_count"] / rfm_agg["user_count"].sum() * 100, 2)
        rfm_agg.to_csv(OUT_DIR / "chart_rfm.csv", index=False, encoding="utf-8-sig")
        print(f"\n  [OK] RFM segmentation: {len(rfm_agg)} segments -> chart_rfm.csv")

    print(f"\n{'='*60}")
    print(f"[DONE] All Power BI CSVs saved to: {OUT_DIR}")
    print("Files:")
    for f in sorted(OUT_DIR.glob("*.csv")):
        print(f"  {f.name} ({f.stat().st_size/1024:.0f} KB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
