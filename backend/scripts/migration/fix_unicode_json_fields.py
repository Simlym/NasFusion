# -*- coding: utf-8 -*-
"""
修复 JSON 字段中的 Unicode 编码问题

问题描述：
    历史数据中，JSON 字段（如 genres, countries, languages 等）存储为 Unicode 转义序列，
    例如 ["\u5386\u53f2", "\u6218\u4e89"] 而不是 ["历史", "战争"]

    这导致前端使用中文筛选时无法匹配（如 genre=科幻）

解决方案：
    将所有 Unicode 转义序列重新序列化为明文 UTF-8 存储

使用方法：
    cd backend
    python scripts/migration/fix_unicode_json_fields.py

    可选参数：
    --dry-run    只检查不修改，预览受影响的数据
    --table      指定表名（默认处理所有表）
"""

import asyncio
import argparse
import json
import re
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from app.core.database import async_session_local
from app.core.config import settings


# 需要修复的表和 JSON 字段
TABLES_TO_FIX = {
    "unified_movies": [
        "genres", "tags", "languages", "countries",
        "aka", "directors", "actors", "writers", "production_companies"
    ],
    "unified_tv_series": [
        "genres", "tags", "languages", "countries",
        "aka", "creators", "actors", "networks", "production_companies"
    ],
    "pt_resources": [
        "tags", "labels"
    ],
    "media_files": [
        "audio_tracks", "subtitles"
    ],
}


def has_unicode_escape(value: str) -> bool:
    """检查字符串是否包含 Unicode 转义序列"""
    if not value:
        return False
    return bool(re.search(r'\\u[0-9a-fA-F]{4}', value))


def decode_unicode_escapes(value: str) -> str:
    """
    解码 Unicode 转义序列

    例如: '["\u5386\u53f2"]' -> '["历史"]'
    """
    if not value:
        return value

    try:
        # 先解析 JSON
        data = json.loads(value)
        # 重新序列化，保持 Unicode 明文
        return json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    except (json.JSONDecodeError, TypeError):
        return value


async def check_table(table_name: str, columns: list[str], dry_run: bool = True):
    """检查并修复单个表"""

    db_type = settings.database.DB_TYPE.lower()

    async with async_session_local() as db:
        for column in columns:
            # 检查列是否存在
            if db_type == "postgresql":
                check_sql = text(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = :table AND column_name = :column
                """)
            else:  # sqlite
                check_sql = text(f"PRAGMA table_info({table_name})")

            result = await db.execute(check_sql, {"table": table_name, "column": column} if db_type == "postgresql" else {})

            if db_type == "postgresql":
                if not result.fetchone():
                    print(f"  ⚠️  列 {table_name}.{column} 不存在，跳过")
                    continue
            else:
                columns_info = result.fetchall()
                column_names = [row[1] for row in columns_info]
                if column not in column_names:
                    print(f"  ⚠️  列 {table_name}.{column} 不存在，跳过")
                    continue

            # 查询包含 Unicode 转义的记录
            if db_type == "postgresql":
                # PostgreSQL: 将 JSONB 转为 text 再匹配
                query = text(f"""
                    SELECT id, {column}::text as col_value
                    FROM {table_name}
                    WHERE {column}::text LIKE '%\\u%'
                    LIMIT 1000
                """)
            else:
                # SQLite: 直接匹配文本
                query = text(f"""
                    SELECT id, {column} as col_value
                    FROM {table_name}
                    WHERE {column} LIKE '%\\u%'
                    LIMIT 1000
                """)

            result = await db.execute(query)
            rows = result.fetchall()

            if not rows:
                print(f"  ✓ {table_name}.{column}: 无需修复")
                continue

            print(f"  🔧 {table_name}.{column}: 发现 {len(rows)} 条需要修复的记录")

            if dry_run:
                # 预览模式：显示前 3 条示例
                for row in rows[:3]:
                    record_id, col_value = row
                    if col_value:
                        decoded = decode_unicode_escapes(col_value)
                        print(f"      ID={record_id}:")
                        print(f"        原始: {col_value[:100]}...")
                        print(f"        修复: {decoded[:100]}...")
            else:
                # 执行修复
                fixed_count = 0
                for row in rows:
                    record_id, col_value = row
                    if col_value and has_unicode_escape(col_value):
                        decoded = decode_unicode_escapes(col_value)
                        if decoded != col_value:
                            if db_type == "postgresql":
                                update_sql = text(f"""
                                    UPDATE {table_name}
                                    SET {column} = :new_value::jsonb
                                    WHERE id = :id
                                """)
                            else:
                                update_sql = text(f"""
                                    UPDATE {table_name}
                                    SET {column} = :new_value
                                    WHERE id = :id
                                """)
                            await db.execute(update_sql, {"new_value": decoded, "id": record_id})
                            fixed_count += 1

                await db.commit()
                print(f"      ✅ 已修复 {fixed_count} 条记录")


async def main():
    parser = argparse.ArgumentParser(description="修复 JSON 字段中的 Unicode 编码问题")
    parser.add_argument("--dry-run", action="store_true", help="只检查不修改，预览受影响的数据")
    parser.add_argument("--table", type=str, help="指定表名（默认处理所有表）")
    args = parser.parse_args()

    print("=" * 60)
    print("JSON 字段 Unicode 编码修复工具")
    print("=" * 60)
    print(f"数据库类型: {settings.database.DB_TYPE}")
    print(f"运行模式: {'预览模式 (--dry-run)' if args.dry_run else '修复模式'}")
    print()

    if not args.dry_run:
        confirm = input("⚠️  即将修改数据库，是否继续？(y/N): ")
        if confirm.lower() != 'y':
            print("已取消")
            return

    tables = TABLES_TO_FIX
    if args.table:
        if args.table not in TABLES_TO_FIX:
            print(f"❌ 未知的表名: {args.table}")
            print(f"   可用的表: {', '.join(TABLES_TO_FIX.keys())}")
            return
        tables = {args.table: TABLES_TO_FIX[args.table]}

    for table_name, columns in tables.items():
        print(f"\n📋 处理表: {table_name}")
        await check_table(table_name, columns, dry_run=args.dry_run)

    print("\n" + "=" * 60)
    if args.dry_run:
        print("预览完成。如需执行修复，请去掉 --dry-run 参数重新运行")
    else:
        print("修复完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
