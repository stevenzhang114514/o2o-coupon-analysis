#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_split_data.py — 拆分天池 O2O 原始 CSV 为 4 张表
======================================================
输入:  online_train.csv / offline_train.csv / offline_test.csv
输出:  data/split_data/ 下的 4 张表
      - users.csv        用户维度表
      - merchants.csv     商户维度表
      - coupons.csv       优惠券维度表
      - transactions.csv  交易事实表（合并 online + offline）

用法: python src/01_split_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# ======================== 配置路径 ========================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = Path("D:/下载")  # 原始天池数据目录
OUTPUT_DIR = BASE_DIR / "data" / "split_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

ONLINE_TRAIN = DATA_RAW_DIR / "online_train.csv"
OFFLINE_TRAIN = DATA_RAW_DIR / "offline_train.csv"
OFFLINE_TEST = DATA_RAW_DIR / "offline_test.csv"

# ======================== 读取原始数据 ========================
print("[1/6] 读取原始数据...")

# online_train: 用户线上行为
# 列: User_id, Merchant_id, Action, Coupon_id, Discount_rate, Date_received, Date
# Action: 0=浏览, 1=领取, 2=核销
dtype_online = {
    "User_id": "int64",
    "Merchant_id": "int64",
    "Action": "int8",
    "Coupon_id": "str",
    "Discount_rate": "str",
    "Date_received": "str",
    "Date": "str",
}
df_online = pd.read_csv(ONLINE_TRAIN, dtype=dtype_online, low_memory=False)
print(f"    online_train:  {len(df_online):>12,} 行")

# offline_train: 用户线下行为
# 列: User_id, Merchant_id, Coupon_id, Discount_rate, Distance, Date_received, Date
dtype_offline = {
    "User_id": "int64",
    "Merchant_id": "int64",
    "Coupon_id": "str",
    "Discount_rate": "str",
    "Distance": "str",
    "Date_received": "str",
    "Date": "str",
}
df_offline = pd.read_csv(OFFLINE_TRAIN, dtype=dtype_offline, low_memory=False)
print(f"    offline_train: {len(df_offline):>12,} 行")

# offline_test: 测试集（无 Date 列）
df_test = pd.read_csv(OFFLINE_TEST, dtype=dtype_offline, low_memory=False)
print(f"    offline_test:  {len(df_test):>12,} 行")

# ======================== 标准化处理 ========================
print("[2/6] 数据标准化...")

# --- 处理 online 数据 ---
# 统一列名：添加 source 标记
df_online["source"] = "online"
# 在线数据没有 Distance，设空
df_online["Distance"] = np.nan
# Action 映射
action_map = {0: "browse", 1: "receive", 2: "use"}
df_online["action_name"] = df_online["Action"].map(action_map)

# 转换日期格式
df_online["Date_received"] = pd.to_datetime(
    df_online["Date_received"].replace("null", np.nan), format="%Y%m%d", errors="coerce"
)
df_online["Date"] = pd.to_datetime(
    df_online["Date"].replace("null", np.nan), format="%Y%m%d", errors="coerce"
)

# --- 处理 offline 数据 ---
df_offline["source"] = "offline"
df_offline["Action"] = np.nan
df_offline["action_name"] = np.nan  # offline 只有领券/用券结果

df_offline["Date_received"] = pd.to_datetime(
    df_offline["Date_received"].replace("null", np.nan), format="%Y%m%d", errors="coerce"
)
df_offline["Date"] = pd.to_datetime(
    df_offline["Date"].replace("null", np.nan), format="%Y%m%d", errors="coerce"
)

df_offline["Distance"] = pd.to_numeric(
    df_offline["Distance"].replace("null", np.nan), errors="coerce"
)

# --- 处理 test 数据 ---
df_test["source"] = "offline_test"
df_test["Action"] = np.nan
df_test["action_name"] = np.nan
df_test["Date"] = pd.NaT  # 测试集无核销日期

df_test["Date_received"] = pd.to_datetime(
    df_test["Date_received"].replace("null", np.nan), format="%Y%m%d", errors="coerce"
)
df_test["Distance"] = pd.to_numeric(
    df_test["Distance"].replace("null", np.nan), errors="coerce"
)

# ======================== 合并事实表 ========================
print("[3/6] 合并事实表...")

# 统一列顺序（事实表字段）
fact_cols = [
    "User_id", "Merchant_id", "Coupon_id", "Discount_rate",
    "Distance", "Date_received", "Date", "Action", "action_name", "source"
]

# 确保所有 df 都有这些列
for col in fact_cols:
    if col not in df_online.columns:
        df_online[col] = np.nan

df_transactions = pd.concat(
    [df_online[fact_cols], df_offline[fact_cols], df_test[fact_cols]],
    ignore_index=True,
)
print(f"    合并后总行数: {len(df_transactions):>12,}")

# 添加唯一交易 ID
df_transactions.insert(0, "transaction_id", range(1, len(df_transactions) + 1))

# ======================== 提取维度表 ========================
print("[4/6] 提取维度表...")

# --- users ---
df_users = pd.DataFrame(
    {"user_id": sorted(df_transactions["User_id"].dropna().unique())}
)
df_users["user_id"] = df_users["user_id"].astype("int64")
print(f"    users:        {len(df_users):>12,} 人")

# --- merchants ---
df_merchants = pd.DataFrame(
    {"merchant_id": sorted(df_transactions["Merchant_id"].dropna().unique())}
)
df_merchants["merchant_id"] = df_merchants["merchant_id"].astype("int64")
print(f"    merchants:    {len(df_merchants):>12,} 家")

# --- coupons ---
coupon_mask = df_transactions["Coupon_id"].notna() & (df_transactions["Coupon_id"] != "null")
df_coupons = (
    df_transactions.loc[coupon_mask, ["Coupon_id", "Discount_rate"]]
    .drop_duplicates(subset="Coupon_id")
    .sort_values("Coupon_id")
    .reset_index(drop=True)
)
# 标准化 Discount_rate 列名
df_coupons.rename(columns={"Coupon_id": "coupon_id", "Discount_rate": "discount_rate"}, inplace=True)
print(f"    coupons:      {len(df_coupons):>12,} 种")

# ======================== 清洗 transactions 折扣率 ========================
print("[5/6] 清洗折扣率字段...")

def parse_discount(rate_str):
    """
    解析折扣率:
    - '150:20' -> 满150减20
    - '0.8'    -> 8折
    - null      -> 无优惠
    返回 (discount_type, discount_man, discount_jian, discount_rate)
    """
    if pd.isna(rate_str) or rate_str in ("null", "", "None"):
        return ("none", np.nan, np.nan, np.nan)

    rate_str = str(rate_str).strip()

    if ":" in rate_str:
        parts = rate_str.split(":")
        try:
            man = float(parts[0])
            jian = float(parts[1])
            # 计算等效折扣率: (man - jian) / man
            eq_rate = round((man - jian) / man, 4) if man > 0 else np.nan
            return ("fixed", man, jian, eq_rate)
        except ValueError:
            return ("unknown", np.nan, np.nan, np.nan)
    else:
        try:
            rate = float(rate_str)
            if 0 < rate <= 1:
                return ("discount", np.nan, np.nan, rate)
            elif rate > 1:
                return ("discount", np.nan, np.nan, rate / 100.0)
            else:
                return ("unknown", np.nan, np.nan, np.nan)
        except ValueError:
            return ("unknown", np.nan, np.nan, np.nan)


# 应用到 transactions
parsed = df_transactions["Discount_rate"].apply(parse_discount)
df_transactions["discount_type"] = [p[0] for p in parsed]
df_transactions["discount_man"] = [p[1] for p in parsed]
df_transactions["discount_jian"] = [p[2] for p in parsed]
df_transactions["discount_eq_rate"] = [p[3] for p in parsed]

# 保留原始字段并重命名
df_transactions.rename(
    columns={
        "User_id": "user_id",
        "Merchant_id": "merchant_id",
        "Coupon_id": "coupon_id",
        "Date_received": "date_received",
        "Date": "date_used",
    },
    inplace=True,
)

# ======================== 保存 ========================
print("[6/6] Saving CSV files...")


def save_csv(df, filename):
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"    [OK] {filename:<25s} {len(df):>12,} rows -> {path}")


save_csv(df_users, "users.csv")
save_csv(df_merchants, "merchants.csv")
save_csv(df_coupons, "coupons.csv")
save_csv(df_transactions, "transactions.csv")

# ======================== 输出统计 ========================
print("\n" + "=" * 60)
print("拆分完成！汇总：")
print(f"  用户维度:     {len(df_users):>10,} 行")
print(f"  商户维度:     {len(df_merchants):>10,} 行")
print(f"  优惠券维度:   {len(df_coupons):>10,} 行")
print(f"  交易事实表:   {len(df_transactions):>10,} 行")
print(f"\n  输出目录:     {OUTPUT_DIR}")
print("=" * 60)
