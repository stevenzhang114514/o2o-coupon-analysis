# 🎟️ O2O 优惠券数据分析

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)
[![MySQL](https://img.shields.io/badge/MySQL-8.0+-orange)](https://mysql.com)
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

### 数据拆分后（4 张表）

原始宽表拆分为星型模型：
```
users (用户维度) ──┐
merchants (商户维度)─┼── transactions (事实表)
coupons (优惠券维度)─┘
```

## 🛠 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 数据库 | **MySQL 8.0** | 数据存储、SQL 分析 |
| 数据处理 | **Python** (Pandas / NumPy) | 数据拆分、清洗、统计 |
| 可视化 | **Matplotlib** | 静态图表生成 |
| BI看板 | **Power BI** | 交互式数据看板 |
| 版本管理 | Git | 代码版本管理 |

## 📁 项目结构

```
o2o-coupon-analysis/
├── data/
│   ├── ccf_offline_stage1_train.csv     # 天池原始数据（不上传，见数据来源）
│   └── split_data/                       # 拆分后的 4 张表
│       ├── users.csv                     # 用户维度表
│       ├── merchants.csv                 # 商户维度表
│       ├── coupons.csv                   # 优惠券维度表
│       └── transactions.csv              # 交易事实表
├── sql/
│   ├── 01_create_tables.sql              # 建表语句（4表 + 主外键 + 索引）
│   ├── 02_import_data.sql                # LOAD DATA 批量导入
│   ├── 03_multi_join.sql                 # 多表 JOIN：商户核销率
│   ├── 04_window_functions.sql           # 窗口函数：排名 + 月环比
│   ├── 05_cte_rfm.sql                    # CTE + RFM 用户分层
│   └── 06_trend_analysis.sql             # 时空趋势聚合
├── src/
│   ├── 01_split_data.py                  # 拆分原始数据 → 4 张 CSV
│   ├── 02_import_mysql.py                # Python 批量导入 MySQL
│   ├── 03_sql_to_analysis.py             # 执行 SQL → Pandas 分析
│   └── 04_visualization.py               # Matplotlib 生成 4 张图表
├── powerbi/
│   └── o2o_dashboard.pbix               # Power BI 交互看板
├── output/
│   ├── usage_rate_by_merchant.png         # 商户核销率 TOP 20
│   ├── rfm_distribution.png              # RFM 用户分层分布
│   ├── monthly_trend.png                 # 月度核销趋势 + 环比
│   └── coupon_type_analysis.png           # 优惠券类型核销对比
├── README.md
└── .gitignore
```

## 🚀 快速开始

### 前置条件

```bash
# Python 依赖
pip install pandas numpy pymysql sqlalchemy matplotlib

# MySQL 8.0+
# Power BI Desktop (可选)
```

### Step 1: 下载数据

从 [天池竞赛页面](https://tianchi.aliyun.com/competition/entrance/231593/introduction) 下载数据，放置到 `data/` 目录。

### Step 2: 拆分数据

```bash
python src/01_split_data.py
```

输出：`data/split_data/` 下生成 4 张 CSV。

### Step 3: 导入 MySQL

```bash
# 1) 先在 MySQL 中执行建表
mysql -u root -p < sql/01_create_tables.sql

# 2) 或用 Python 导入
#    修改 src/02_import_mysql.py 中的 DB_CONFIG
python src/02_import_mysql.py
```

### Step 4: 执行分析

```bash
# MySQL 侧：逐个执行 sql/ 下的 .sql 文件
# Python 侧：
python src/03_sql_to_analysis.py
python src/04_visualization.py
```

## 📈 分析模块详解

| # | SQL 脚本 | 分析内容 | SQL 技能点 |
|---|----------|----------|------------|
| 1 | `01_create_tables.sql` | 4 表建表 + 主外键 + 索引 | CREATE TABLE / 建模 |
| 2 | `02_import_data.sql` | 批量导入 CSV | LOAD DATA / INSERT |
| 3 | `03_multi_join.sql` | 商户核销率（JOIN + 子查询） | JOIN + GROUP BY + HAVING |
| 4 | `04_window_functions.sql` | 排名 + 月环比 + 移动平均 | ROW_NUMBER / RANK / LAG |
| 5 | `05_cte_rfm.sql` | RFM 用户价值分层 | WITH (CTE) + 嵌套子查询 |
| 6 | `06_trend_analysis.sql` | 时空趋势 + 折扣分析 | 日期聚合 / 同比环比 |

### 4 张关键可视化

| 图表 | 内容 | 图表类型 |
|------|------|----------|
| `usage_rate_by_merchant.png` | TOP 20 商户核销率排名 | 横向条形图 |
| `rfm_distribution.png` | 核心/活跃/新用户/沉睡 占比 | 饼图 + 柱状图 |
| `monthly_trend.png` | 月度核销量 + 环比增长率 | 柱状+折线双轴图 |
| `coupon_type_analysis.png` | 满减券 vs 折扣券核销对比 | 分组柱状图 |

## 💡 关键结论

*基于 13,298,350 条记录分析，数据集覆盖 1,034,849 名用户、16,415 家商户。*

- **整体核销率**：满减券 8.88%、折扣券 11.58%（无券消费核销率 82.15%）
- **当天核销**：10.32% 的用户领券当天即核销；84.84% 的券领后未使用
- **RFM 分层**：核心用户 23.5% | 活跃用户 20.3% | 新用户 7.9% | 沉睡用户 9.1% | 流失用户 23.8%
- **优惠券类型**：满减券占比最高（176 万条），折扣券核销率略高（11.58% vs 8.88%）
- **距离效应**：0m 同位置核销率 13.46%，10m+ 仅 1.72%，距离越近核销率越高（约 7.8 倍差距）
- **时间规律**：月度核销量 1 月 194 万 → 6 月 232 万（+19.6%），2 月因春节回落至 112 万
- **工作日效应**：工作日日均核销 66,795 次，周末 55,146 次

## 📊 Power BI 看板

`powerbi/o2o_dashboard.pbix` 包含以下页面：

1. **核销概览** — KPI 卡片 + 月度趋势折线图
2. **商户排名** — TOP 商户核销率排行榜
3. **用户分析** — RFM 分层饼图 + 用户明细表
4. **优惠券分析** — 折扣类型对比 + 满减力度分桶

> 使用前请在 Power BI 中配置 MySQL 数据源连接。

## ⚠️ 注意事项

- 数据集约 1.5 GB（原始 CSV），拆分后约 2 GB，请确保磁盘空间充足
- MySQL 导入大表时建议调大 `max_allowed_packet` 和 `innodb_buffer_pool_size`
- 中文字体：Windows 推荐 SimHei，Mac 推荐 PingFang SC，Linux 安装 `fonts-noto-cjk`
- 原始数据不上传 Git（已在 `.gitignore` 中排除）

## 📝 License

本分析使用公开数据集，仅供学习交流。数据版权归天池平台及原作者所有。

---
*📅 分析日期：2026年7月*
