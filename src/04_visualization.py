#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_visualization.py — Matplotlib 可视化（4 张关键图表）
========================================================
输入:  output/data_*.csv（由 03_sql_to_analysis.py 生成）
     或直接从 CSV 计算（无需 MySQL）

输出:  output/*.png
  1. usage_rate_by_merchant.png   — 商户核销率 TOP 20 横向条形图
  2. rfm_distribution.png         — RFM 用户分层饼图 + 人数
  3. monthly_trend.png            — 月度核销趋势折线图 + 环比
  4. coupon_type_analysis.png     — 优惠券类型核销率对比柱状图

用法: python src/04_visualization.py
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 无 GUI 后端
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager
from pathlib import Path
import sys
import warnings

warnings.filterwarnings("ignore")

# ======================== 中文字体配置 ========================
# Windows 常用中文字体：SimHei / Microsoft YaHei / KaiTi
# Mac: PingFang SC / Heiti SC / STHeiti
# Linux: WenQuanYi Micro Hei / Noto Sans CJK

_FONT_CANDIDATES = [
    "SimHei", "Microsoft YaHei", "PingFang SC", "Heiti SC",
    "STHeiti", "WenQuanYi Micro Hei", "Noto Sans CJK SC",
    "DejaVu Sans", "Arial Unicode MS", "sans-serif",
]

def setup_chinese_font():
    """自动检测并设置中文字体"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in _FONT_CANDIDATES:
        if font_name in available:
            plt.rcParams["font.family"] = font_name
            print(f"[OK] Using font: {font_name}")
            return font_name

    # 兜底：尝试从系统找
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = _FONT_CANDIDATES
    print("[WARN] No Chinese font detected, text may render as squares")
    return "sans-serif"


# ======================== 配置 ========================
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data" / "split_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 全局配色
COLORS = {
    "primary": "#2196F3",
    "secondary": "#FF9800",
    "success": "#4CAF50",
    "danger": "#F44336",
    "purple": "#9C27B0",
    "teal": "#009688",
    "grey": "#9E9E9E",
    "dark": "#333333",
}
PALETTE = ["#2196F3", "#4CAF50", "#FF9800", "#F44336", "#9C27B0", "#009688"]


def load_data():
    """加载中间数据文件，如不存在则从原始 CSV 计算"""
    merchant_csv = OUTPUT_DIR / "data_merchant_usage.csv"
    monthly_csv = OUTPUT_DIR / "data_monthly_trend.csv"
    coupon_csv = OUTPUT_DIR / "data_coupon_type.csv"
    rfm_csv = OUTPUT_DIR / "data_rfm.csv"

    data = {}

    # 尝试从中间文件加载
    for name, path in [
        ("merchant", merchant_csv),
        ("monthly", monthly_csv),
        ("coupon", coupon_csv),
        ("rfm", rfm_csv),
    ]:
        if path.exists():
            data[name] = pd.read_csv(path)
            print(f"[OK] Loaded: {path.name} ({len(data[name])} rows)")
        else:
            data[name] = None
            print(f"[MISS] Not found: {path.name}")

    return data


def compute_from_csv():
    """如果没有 MySQL 中间结果，直接从 transactions.csv 计算（备选方案）"""
    txn_path = DATA_DIR / "transactions.csv"

    if not txn_path.exists():
        print(f"[MISS] Source data not found: {txn_path}")
        print("  请先运行 01_split_data.py 拆分数据")
        return None

    print(f"从 transactions.csv 直接计算... ({txn_path.stat().st_size / 1e6:.1f} MB)")
    dtype = {
        "user_id": "int64",
        "merchant_id": "int64",
        "coupon_id": "str",
        "discount_type": "str",
        "discount_man": "float64",
        "discount_eq_rate": "float64",
        "date_received": "str",
        "date_used": "str",
        "source": "str",
    }
    df = pd.read_csv(txn_path, dtype=dtype, low_memory=False, usecols=list(dtype.keys()))
    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")
    df["date_used"] = pd.to_datetime(df["date_used"], errors="coerce")

    # 过滤仅训练数据
    mask = df["source"].isin(["offline", "online"])
    df_train = df[mask].copy()

    return df_train


# ================================================================
# 图表 1: 商户核销率 TOP 20
# ================================================================
def plot_merchant_usage_rate(df_merchant):
    """TOP 20 商户核销率横向条形图"""
    print("\n[1/4] 商户核销率排名 TOP 20...")

    if df_merchant is None or df_merchant.empty:
        # 从 CSV 备选计算
        df = compute_from_csv()
        if df is None:
            return
        merchant_stats = (
            df.groupby("merchant_id")
            .agg(
                received_cnt=("date_received", "count"),
                used_cnt=("date_used", lambda x: x.notna().sum()),
            )
            .query("received_cnt >= 50")
            .assign(usage_rate_pct=lambda d: round(d["used_cnt"] / d["received_cnt"] * 100, 2))
            .sort_values("usage_rate_pct", ascending=False)
            .head(20)
            .reset_index()
        )
    else:
        merchant_stats = df_merchant.sort_values("usage_rate_pct", ascending=False).head(20)

    fig, ax = plt.subplots(figsize=(12, 8))

    merchant_labels = [f"商户 #{int(mid)}" for mid in merchant_stats["merchant_id"]]
    rates = merchant_stats["usage_rate_pct"].values

    colors = [COLORS["primary"] if r >= rates.mean() else COLORS["grey"] for r in rates]
    bars = ax.barh(range(len(merchant_stats)), rates, color=colors, height=0.7, edgecolor="white", linewidth=0.5)

    # 数值标签
    for i, (bar, rate) in enumerate(zip(bars, rates)):
        ax.text(
            bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f"{rate:.1f}%", va="center", fontsize=9, fontweight="bold",
            color=COLORS["dark"],
        )

    ax.set_yticks(range(len(merchant_stats)))
    ax.set_yticklabels(merchant_labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("核销率 (%)", fontsize=12)
    ax.set_title("TOP 20 商户优惠券核销率排名", fontsize=15, fontweight="bold", pad=15)
    ax.set_xlim(0, rates.max() * 1.12)
    ax.axvline(x=rates.mean(), color=COLORS["secondary"], linestyle="--", linewidth=1, alpha=0.7)
    ax.text(
        rates.mean() + 0.2, 0.5, f"均值 {rates.mean():.1f}%",
        color=COLORS["secondary"], fontsize=9, va="center",
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()

    path = OUTPUT_DIR / "usage_rate_by_merchant.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ================================================================
# 图表 2: RFM 用户分层分布
# ================================================================
def plot_rfm_distribution(df_rfm):
    """RFM 4 类用户占比饼图 + 柱状图"""
    print("\n[2/4] RFM 用户分层分布...")

    if df_rfm is None or df_rfm.empty:
        df = compute_from_csv()
        if df is None:
            return
        # 简化版 RFM 计算
        user_stats = (
            df.groupby("user_id")
            .agg(
                last_used=("date_used", "max"),
                frequency=("date_used", lambda x: x.notna().sum()),
            )
            .query("frequency > 0")
        )
        ref_date = pd.Timestamp("2016-07-31")
        user_stats["recency"] = (ref_date - user_stats["last_used"].fillna(ref_date)).dt.days

        try:
            user_stats["r_score"] = 6 - pd.qcut(user_stats["recency"], q=5, labels=[5,4,3,2,1], duplicates="drop").astype(int)
            user_stats["f_score"] = pd.qcut(user_stats["frequency"], q=5, labels=[1,2,3,4,5], duplicates="drop").astype(int)
        except Exception:
            user_stats["r_score"] = user_stats["f_score"] = 3

        def seg(r):
            r_score, f_score = r["r_score"], r["f_score"]
            if r_score >= 4 and f_score >= 4: return "核心用户"
            elif r_score >= 4 and f_score <= 2: return "新用户"
            elif r_score <= 2 and f_score >= 4: return "沉睡用户"
            elif r_score <= 2 and f_score <= 2: return "流失用户"
            elif r_score >= 3 and f_score >= 3: return "活跃用户"
            else: return "一般用户"

        user_stats["segment"] = user_stats.apply(seg, axis=1)
        seg_counts = user_stats["segment"].value_counts()
    else:
        seg_counts = df_rfm["user_segment"].value_counts()

    # 创建双图：饼图 + 柱状图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

    # 饼图
    seg_colors = {
        "核心用户": COLORS["primary"],
        "活跃用户": COLORS["success"],
        "新用户": COLORS["teal"],
        "沉睡用户": COLORS["secondary"],
        "流失用户": COLORS["danger"],
        "一般用户": COLORS["grey"],
    }
    colors_pie = [seg_colors.get(s, COLORS["grey"]) for s in seg_counts.index]
    wedges, texts, autotexts = ax1.pie(
        seg_counts.values, labels=seg_counts.index, autopct="%1.1f%%",
        colors=colors_pie, startangle=90, pctdistance=0.6,
        explode=[0.05] * len(seg_counts),
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    ax1.set_title("RFM 用户分层占比", fontsize=14, fontweight="bold", pad=15)

    # 柱状图
    bars = ax2.bar(
        range(len(seg_counts)), seg_counts.values,
        color=colors_pie, edgecolor="white", linewidth=1.2,
    )
    for bar, val in zip(bars, seg_counts.values):
        ax2.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + val * 0.01,
            f"{val:,}\n({val/seg_counts.sum()*100:.1f}%)",
            ha="center", va="bottom", fontsize=10, fontweight="bold",
        )

    ax2.set_xticks(range(len(seg_counts)))
    ax2.set_xticklabels(seg_counts.index, fontsize=10)
    ax2.set_ylabel("用户数", fontsize=12)
    ax2.set_title("RFM 用户分层人数", fontsize=14, fontweight="bold", pad=15)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    path = OUTPUT_DIR / "rfm_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ================================================================
# 图表 3: 月度核销趋势 + 环比
# ================================================================
def plot_monthly_trend(df_monthly):
    """月度核销量折线图 + 环比增长标注"""
    print("\n[3/4] 月度核销趋势...")

    if df_monthly is None or df_monthly.empty:
        df = compute_from_csv()
        if df is None:
            return
        df_used = df[df["date_used"].notna()].copy()
        df_used["ym"] = df_used["date_used"].dt.strftime("%Y-%m")
        monthly = (
            df_used.groupby("ym")
            .agg(used_count=("user_id", "count"), unique_users=("user_id", "nunique"))
            .sort_index()
            .reset_index()
        )
        # 只保留 2016 年数据
        monthly = monthly[monthly["ym"].between("2016-01", "2016-07")]
    else:
        monthly = df_monthly.copy()
        if "year_month" in monthly.columns:
            monthly["ym"] = monthly["year_month"]

    # 计算环比
    monthly["prev"] = monthly["used_count"].shift(1)
    monthly["mom_pct"] = round((monthly["used_count"] - monthly["prev"]) / monthly["prev"] * 100, 1)

    fig, ax1 = plt.subplots(figsize=(14, 7))

    # 柱状图：核销量
    bars = ax1.bar(
        monthly["ym"], monthly["used_count"],
        color=COLORS["primary"], alpha=0.7, label="核销量", width=0.6,
    )
    ax1.set_xlabel("月份", fontsize=12)
    ax1.set_ylabel("核销量", fontsize=12, color=COLORS["primary"])
    ax1.tick_params(axis="y", labelcolor=COLORS["primary"])
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # 在柱子上标注数值
    for bar, val in zip(bars, monthly["used_count"]):
        ax1.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + val * 0.01,
            f"{val:,}", ha="center", fontsize=10, fontweight="bold",
        )

    # 折线图：环比增长率
    ax2 = ax1.twinx()
    valid_mom = monthly.dropna(subset=["mom_pct"])
    ax2.plot(
        valid_mom["ym"], valid_mom["mom_pct"],
        color=COLORS["secondary"], marker="o", markersize=8, linewidth=2,
        label="环比增长率", zorder=5,
    )

    # 环比标注
    for _, row in valid_mom.iterrows():
        color = COLORS["success"] if row["mom_pct"] > 0 else COLORS["danger"]
        ax2.annotate(
            f"{row['mom_pct']:+.1f}%",
            xy=(row["ym"], row["mom_pct"]),
            xytext=(0, 15 if row["mom_pct"] > 0 else -18),
            textcoords="offset points",
            ha="center", fontsize=10, fontweight="bold", color=color,
        )

    ax2.set_ylabel("环比增长率 (%)", fontsize=12, color=COLORS["secondary"])
    ax2.tick_params(axis="y", labelcolor=COLORS["secondary"])
    ax2.axhline(y=0, color=COLORS["grey"], linestyle=":", alpha=0.5)

    ax1.set_title("月度核销趋势 (2016年1月-7月) + 环比增长率", fontsize=15, fontweight="bold", pad=15)

    # 图例
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=10)

    ax1.spines["top"].set_visible(False)
    plt.tight_layout()

    path = OUTPUT_DIR / "monthly_trend.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ================================================================
# 图表 4: 优惠券类型核销率对比
# ================================================================
def plot_coupon_type_analysis(df_coupon):
    """满减 vs 折扣券核销率柱状图"""
    print("\n[4/4] 优惠券类型核销率对比...")

    if df_coupon is None or df_coupon.empty:
        df = compute_from_csv()
        if df is None:
            return
        coupon_mask = df["coupon_id"].notna() & df["date_received"].notna()
        coupon_data = df[coupon_mask].copy()
        coupon_type = (
            coupon_data.groupby("discount_type")
            .agg(
                total_count=("user_id", "count"),
                used_count=("date_used", lambda x: x.notna().sum()),
            )
            .assign(usage_rate_pct=lambda d: round(d["used_count"] / d["total_count"] * 100, 2))
            .sort_values("usage_rate_pct", ascending=False)
            .reset_index()
        )
    else:
        coupon_type = df_coupon.sort_values("usage_rate_pct", ascending=False)

    # 类型名称映射
    type_names = {
        "fixed": "满减券",
        "discount": "折扣券",
        "none": "无优惠券",
        "unknown": "未知类型",
    }
    coupon_type["label"] = coupon_type["discount_type"].map(type_names).fillna(coupon_type["discount_type"])

    fig, ax = plt.subplots(figsize=(12, 7))

    x = range(len(coupon_type))
    width = 0.35

    # 双柱：总量 vs 核销量
    bars1 = ax.bar(
        [i - width / 2 for i in x], coupon_type["total_count"],
        width, color=COLORS["primary"], alpha=0.8, label="领券总量", edgecolor="white",
    )
    bars2 = ax.bar(
        [i + width / 2 for i in x], coupon_type["used_count"],
        width, color=COLORS["success"], alpha=0.8, label="核销量", edgecolor="white",
    )

    # 核销率标注
    for i, (_, row) in enumerate(coupon_type.iterrows()):
        ax.text(
            i, max(row["total_count"], row["used_count"]) * 1.02,
            f"核销率\n{row['usage_rate_pct']:.1f}%",
            ha="center", fontsize=11, fontweight="bold", color=COLORS["danger"],
        )

    ax.set_xticks(x)
    ax.set_xticklabels(coupon_type["label"], fontsize=12)
    ax.set_ylabel("数量", fontsize=12)
    ax.set_title("优惠券类型核销率对比", fontsize=15, fontweight="bold", pad=15)
    ax.legend(fontsize=11, loc="upper right")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    path = OUTPUT_DIR / "coupon_type_analysis.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] {path}")


# ================================================================
# 主流程
# ================================================================
def main():
    print("=" * 60)
    print("O2O Data Visualization - 4 Key Charts")
    print("=" * 60)

    # 中文字体
    font_name = setup_chinese_font()

    # 加载数据
    data = load_data()

    # 生成图表
    plot_merchant_usage_rate(data.get("merchant"))
    plot_rfm_distribution(data.get("rfm"))
    plot_monthly_trend(data.get("monthly"))
    plot_coupon_type_analysis(data.get("coupon"))

    print(f"\n{'='*60}")
    print("[DONE] 4 charts saved to output/ directory")
    print(f"   1. {OUTPUT_DIR / 'usage_rate_by_merchant.png'}")
    print(f"   2. {OUTPUT_DIR / 'rfm_distribution.png'}")
    print(f"   3. {OUTPUT_DIR / 'monthly_trend.png'}")
    print(f"   4. {OUTPUT_DIR / 'coupon_type_analysis.png'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
