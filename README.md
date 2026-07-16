# 🎟️ O2O 优惠券数据分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-9.7-orange)](https://mysql.com)
[![Power BI](https://img.shields.io/badge/Power%20BI-Desktop-yellow)](https://powerbi.microsoft.com/)

## 📋 项目背景

基于**天池 O2O 优惠券数据集**（约 1,330 万条用户行为记录），分析优惠券的发放与核销情况，构建 **RFM 用户价值分层模型**，为精准营销策略提供数据支撑。

> **核心问题**：什么样的优惠券最容易被核销？哪些商户的核销率最高？如何对用户进行价值分层？

## 📊 数据来源

- **数据集**：[天池 - O2O 优惠券使用预测](https://tianchi.aliyun.com/competition/entrance/231593/introduction)
- **原始文件**（不上传 Git，请自行下载）：
  - `ccf_offline_stage1_train.csv` — 线下消费训练集（~175 万条）
  - `online_train.csv` — 线上行为训练集（~1,143 万条）
  - `offline_test.csv` — 线下测试集（~11 万条）

### 数据字段说明

| 字段 | 说明 |
|------|------|
| User_id | 用户唯一标识 |
| Merchant_id | 商户唯一标识 |
| Coupon_id | 优惠券ID（NULL = 无券消费） |
| Discount_rate | 折扣率（`150:20` = 满150减20，`0.8` = 8折） |
| Distance | 用户-商户距离（仅offline数据） |
| Date_received | 领券日期 |
| Date | 核销日期（NULL = 未核销） |
| Action | 线上行为：0=浏览, 1=领取, 2=核销（仅online数据） |

### 数据拆分后（星型模型）

```
users (1,034,849人)  ──┐
merchants (16,415家)  ──┼── transactions (13,298,350条)
coupons (38,417种)     ─┘
```

## 🛠 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 数据库 | **MySQL 9.7** | 数据存储、SQL 分析 |
| 数据处理 | **Python 3.14** (Pandas / NumPy) | 拆分、清洗、统计、导出 |
| 可视化 | **Matplotlib** + **Power BI** | 静态图表 + 交互看板 |
| 版本管理 | Git | 代码版本管理 |

## 📁 项目结构

```
o2o-coupon-analysis/
├── data/
│   └── split_data/                       # 拆分后的 4 张表（原始数据不上传）
│       ├── users.csv                     # 1,034,849 人
│       ├── merchants.csv                 # 16,415 家
│       ├── coupons.csv                   # 38,417 种
│       └── transactions.csv              # 13,298,350 条
├── sql/
│   ├── 00_create_summary_tables.sql      # 预处理汇总表（加速分析）
│   ├── 01_create_tables.sql              # 建表 + 主外键 + 索引
│   ├── 02_import_data.sql                # LOAD DATA 批量导入
│   ├── 03_multi_join.sql                 # JOIN + 子查询 → 商户核销率
│   ├── 04_window_functions.sql           # 窗口函数 → 排名 + 月环比
│   ├── 05_cte_rfm.sql                    # CTE → RFM 用户分层 + 视图
│   └── 06_trend_analysis.sql             # 时空趋势 + 折扣 + 时差分析
├── src/
│   ├── 01_split_data.py                  # 拆分原始数据 → 4 张 CSV
│   ├── 02_import_mysql.py                # Python 批量导入 MySQL
│   ├── 03_sql_to_analysis.py             # 执行 SQL → Pandas 分析
│   ├── 04_visualization.py               # Matplotlib 生成 4 张图表
│   └── 05_export_powerbi.py              # 导出 Power BI 即用聚合 CSV
├── powerbi/
│   └── o2o_dashboard.pbix               # Power BI 交互看板（待完成）
├── output/
│   ├── powerbi/                          # Power BI 即用 CSV（8 张图已聚合）
│   │   ├── chart_monthly_trend.csv       # 月度趋势
│   │   ├── chart_coupon_type.csv         # 券类型对比
│   │   ├── chart_distance.csv            # 距离分析
│   │   ├── chart_rfm.csv                 # RFM 分层
│   │   ├── chart_day_type.csv            # 工作日/周末
│   │   ├── chart_gap.csv                 # 领券-核销时差
│   │   └── chart_threshold.csv           # 满减力度
│   ├── result_04_window.txt              # 窗口函数查询结果
│   ├── result_05_rfm.txt                 # RFM 分层明细（47MB）
│   ├── result_06_trend.txt               # 趋势分析结果
│   ├── usage_rate_by_merchant.png         # 商户核销率 TOP 20
│   ├── rfm_distribution.png              # RFM 用户分层分布
│   ├── monthly_trend.png                 # 月度核销趋势 + 环比
│   └── coupon_type_analysis.png           # 优惠券类型核销对比
├── README.md
├── 结论.md                               # 关键结论汇总
├── setup_mysql.bat                       # 一键 MySQL 建表+导入
└── run_analysis.bat                      # 一键 SQL 分析
```

## 🚀 快速开始

### 前置条件

```bash
pip install pandas numpy pymysql sqlalchemy matplotlib
```

### Step 1: 下载数据

从 [天池竞赛页面](https://tianchi.aliyun.com/competition/entrance/231593/introduction) 下载数据，放置到 `D:/下载/` 目录。

### Step 2: 拆分数据

```bash
py -3 src/01_split_data.py
# → data/split_data/ 下生成 4 张 CSV
```

### Step 3: 导入 MySQL

```bash
# 建表
mysql -u root -p < sql/01_create_tables.sql

# 导入（或直接用 DataGrip 右键 Import from File）
py -3 src/02_import_mysql.py
```

### Step 4: SQL 分析

在 DataGrip / MySQL CLI 中依次执行 `sql/` 目录下的 `03_*` ~ `06_*` 脚本。

### Step 5: Python 图表

```bash
py -3 src/04_visualization.py          # Matplotlib 4 张图
py -3 src/05_export_powerbi.py         # Power BI 聚合 CSV
```

### Step 6: Power BI 看板

Power BI Desktop → 获取数据 → 文本/CSV → 加载 `output/powerbi/` 目录下的 7 个 CSV，拖拽出图。

## 📈 分析模块详解

| # | SQL 脚本 | 分析内容 | SQL 技能点 |
|---|----------|----------|------------|
| 0 | `00_create_summary_tables.sql` | 预建 6 张汇总表 | CREATE TABLE AS SELECT |
| 1 | `01_create_tables.sql` | 4 表建表 + 主外键 + 索引 | CREATE TABLE / 建模 |
| 2 | `02_import_data.sql` | 批量导入 CSV | LOAD DATA / INSERT |
| 3 | `03_multi_join.sql` | 商户核销率（JOIN + 子查询） | JOIN + GROUP BY + HAVING |
| 4 | `04_window_functions.sql` | 排名 + 月环比 + 移动平均 | ROW_NUMBER / RANK / LAG |
| 5 | `05_cte_rfm.sql` | RFM 用户价值分层 | WITH (CTE) + 嵌套子查询 |
| 6 | `06_trend_analysis.sql` | 时空趋势 + 折扣 + 距离 + 时差 | 日期聚合 / 同比环比 |

## 📊 可视化

### Python 图表（Matplotlib）

| 图表 | 内容 | 图表类型 |
|------|------|----------|
| `usage_rate_by_merchant.png` | TOP 20 商户核销率排名 | 横向条形图 |
| `rfm_distribution.png` | 6 类用户占比 | 饼图 + 柱状图 |
| `monthly_trend.png` | 月度核销量 + 环比增长率 | 柱状+折线双轴图 |
| `coupon_type_analysis.png` | 满减券 vs 折扣券核销对比 | 分组柱状图 |

### Power BI 交互看板（8 张图）

| # | 图表 | CSV | 图表类型 |
|---|------|-----|----------|
| 1 | 月度核销趋势 | `chart_monthly_trend.csv` | 折线图 |
| 2 | 优惠券类型核销率 | `chart_coupon_type.csv` | 柱状图 |
| 3 | 距离 vs 核销率 | `chart_distance.csv` | 柱状图 |
| 4 | RFM 用户分层 | `chart_rfm.csv` | 环形图 |
| 5 | 工作日 vs 周末 | `chart_day_type.csv` | 柱状图 |
| 6 | 领券-核销时差 | `chart_gap.csv` | 柱状图 |
| 7 | 满减力度核销率 | `chart_threshold.csv` | 柱状图 |
| 8 | KPI 概览 | 各 CSV 汇总 | 多行卡片 |

> 以上 CSV 均为聚合后数据（几十行），Power BI 加载秒开，无需写 DAX。

## 💡 关键结论

*基于 13,298,350 条记录分析，覆盖 1,034,849 名用户、16,415 家商户。*

- **整体核销率**：满减券 8.88%、折扣券 11.58%（无券消费核销率 82.15%）
- **当天核销**：10.32% 的用户领券当天即核销；84.84% 的券领后未使用
- **RFM 分层**：核心用户 23.5% | 活跃用户 20.3% | 新用户 7.9% | 沉睡用户 9.1% | 流失用户 23.8%
- **优惠券类型**：满减券占比最高（176 万条），折扣券核销率略高（11.58% vs 8.88%）
- **距离效应**：0m 同位置核销率 13.46%，10m+ 仅 1.72%，距离越近核销率越高（约 7.8 倍差距）
- **时间规律**：月度核销量 1 月 194 万 → 6 月 232 万（+19.6%），2 月因春节回落至 112 万
- **工作日效应**：工作日日均核销 66,795 次，周末 55,146 次
- **满减力度**：≤20元满减券核销率最高（14.42%），随门槛升高核销率下降

> 详细结论与分析建议见 [结论.md](结论.md)

## ⚠️ 注意事项

- 数据集拆分后约 900MB（transactions.csv），处理时建议 8GB+ 内存
- MySQL 9.7 不支持 `mysql_native_password`，DataGrip 导入最方便
- MySQL 9.7 新增保留字（如 `year_month`、`dense_rank`），SQL 文件已适配
- 中文字体：Windows 推荐 SimHei，Mac 推荐 PingFang SC
- 原始数据不上传 Git（已在 `.gitignore` 中排除）

## 📝 License

本分析使用公开数据集，仅供学习交流。数据版权归天池平台及原作者所有。

---
*📅 分析日期：2026年7月*
