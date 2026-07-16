#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_import_mysql.py — 连接 MySQL 批量导入拆分后的 CSV
======================================================
依赖: pip install pymysql sqlalchemy pandas python-dotenv

用法:
  1. 修改下方 DB_CONFIG
  2. python src/02_import_mysql.py
"""

import pandas as pd
from pathlib import Path
import sys
import time

try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("请先安装依赖: pip install sqlalchemy pymysql pandas")
    sys.exit(1)

# ======================== 数据库配置 ========================
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "13551399593Zyj",
    "database": "o2o_coupon_db",
    "charset": "utf8mb4",
}

# ======================== 路径配置 ========================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "split_data"

# 导入顺序：先维度表，后事实表（因为事务表有外键依赖）
IMPORT_ORDER = [
    ("users.csv", "users"),
    ("merchants.csv", "merchants"),
    ("coupons.csv", "coupons"),
    ("transactions.csv", "transactions"),
]

# 每批导入行数（大表分批导入避免超时）
CHUNK_SIZE = 50000


def create_connection():
    """创建数据库连接"""
    conn_str = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        f"?charset={DB_CONFIG['charset']}"
    )
    engine = create_engine(conn_str, echo=False)
    return engine


def import_csv_to_table(engine, csv_path, table_name):
    """将 CSV 导入到 MySQL 表"""
    print(f"\n{'='*50}")
    print(f"导入: {csv_path.name} → {table_name}")

    if not csv_path.exists():
        print(f"  [MISS] File not found: {csv_path}")
        return False

    t0 = time.time()

    # 先清空表（TRUNCATE 比 DELETE 快，且重置 AUTO_INCREMENT）
    with engine.connect() as conn:
        # 临时禁用外键检查（导入事实表时避免约束报错）
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        conn.execute(text(f"TRUNCATE TABLE `{table_name}`;"))
        conn.commit()
        print(f"  → 已清空表 {table_name}")

    # 分批读取并导入
    total_rows = 0
    try:
        for chunk in pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False):
            # 将 NaN 替换为 None（MySQL NULL）
            chunk = chunk.where(pd.notnull(chunk), None)

            # 写入数据库
            chunk.to_sql(
                name=table_name,
                con=engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=5000,
            )
            total_rows += len(chunk)
            print(f"  → 已导入 {total_rows:>10,} 行...", end="\r")

    except Exception as e:
        print(f"\n  [FAIL] Import failed: {e}")
        return False
    finally:
        # 恢复外键检查
        with engine.connect() as conn:
            conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            conn.commit()

    elapsed = time.time() - t0
    print(f"\n  [OK] {table_name}: {total_rows:>10,} rows ({elapsed:.1f}s)")
    return True


def main():
    print("=" * 60)
    print("O2O 数据 MySQL 批量导入")
    print("=" * 60)

    # 连接测试
    try:
        engine = create_connection()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).scalar()
            print(f"[OK] MySQL connected (host={DB_CONFIG['host']})")
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        print("\n请检查 DB_CONFIG 中的连接参数")
        return

    # 逐表导入
    success = 0
    for filename, table_name in IMPORT_ORDER:
        csv_path = DATA_DIR / filename
        if import_csv_to_table(engine, csv_path, table_name):
            success += 1

    # 总结
    print(f"\n{'='*60}")
    print(f"导入完成: {success}/{len(IMPORT_ORDER)} 张表")
    print("=" * 60)


if __name__ == "__main__":
    main()
