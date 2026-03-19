# -*- coding: utf-8 -*-
"""
投票数字段迁移脚本

用途：
1. 将 votes_count 字段拆分为 votes_tmdb、votes_douban、votes_imdb
2. 根据 metadata_source 迁移现有数据到对应字段
3. 删除旧的 votes_count 字段

影响表：
- unified_movies
- unified_tv_series

使用方法：
    python scripts/migration/migrate_votes_fields.py
    python scripts/migration/migrate_votes_fields.py --drop-old-fields  # 删除旧字段
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


# ============ 数据库连接配置 ============

def get_database_url():
    """获取数据库连接 URL"""
    db_type = os.getenv("DB_TYPE", "sqlite").lower()

    if db_type == "postgresql":
        # 优先使用 DB_POSTGRES_* 环境变量（与应用配置一致）
        # 如果不存在则尝试 POSTGRES_*（向后兼容）
        server = os.getenv("DB_POSTGRES_SERVER") or os.getenv("POSTGRES_SERVER", "localhost")
        user = os.getenv("DB_POSTGRES_USER") or os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("DB_POSTGRES_PASSWORD") or os.getenv("POSTGRES_PASSWORD", "")
        db_name = os.getenv("DB_POSTGRES_DB") or os.getenv("POSTGRES_DB", "nasfusion")
        port = os.getenv("DB_POSTGRES_PORT") or os.getenv("POSTGRES_PORT", "5432")
        url = f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db_name}"
        print(f"使用 PostgreSQL: {user}@{server}:{port}/{db_name}")
        return url
    else:
        # SQLite
        sqlite_path = os.getenv("SQLITE_PATH", "./data/nasfusion.db")
        # 确保路径是绝对路径
        if not sqlite_path.startswith('/'):
            sqlite_path = os.path.abspath(sqlite_path)
        url = f"sqlite+aiosqlite:///{sqlite_path}"
        print(f"使用 SQLite: {sqlite_path}")
        return url


# 创建数据库引擎和会话工厂
DATABASE_URL = get_database_url()
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
engine = create_async_engine(DATABASE_URL, echo=False)
async_session_local = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def check_database_type(db: AsyncSession) -> str:
    """检测数据库类型"""
    # 直接使用环境变量配置的数据库类型
    return DB_TYPE


async def check_old_fields(table_name: str) -> bool:
    """检查是否存在旧的 votes_count 字段"""
    async with async_session_local() as db:
        try:
            db_type = await check_database_type(db)

            if db_type == "sqlite":
                result = await db.execute(
                    text(f"PRAGMA table_info({table_name})")
                )
                columns = result.fetchall()
                has_votes_count = any(col[1] == "votes_count" for col in columns)
            else:  # PostgreSQL
                result = await db.execute(
                    text(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                        AND column_name = 'votes_count'
                    """)
                )
                has_votes_count = result.fetchone() is not None

            return has_votes_count

        except Exception as e:
            print(f"  [X] 检查 {table_name} 失败: {str(e)}")
            return False


async def check_new_fields(table_name: str) -> dict:
    """检查是否已添加新字段"""
    async with async_session_local() as db:
        try:
            db_type = await check_database_type(db)

            if db_type == "sqlite":
                result = await db.execute(
                    text(f"PRAGMA table_info({table_name})")
                )
                columns = result.fetchall()
                column_names = [col[1] for col in columns]
            else:  # PostgreSQL
                result = await db.execute(
                    text(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = '{table_name}'
                    """)
                )
                column_names = [row[0] for row in result.fetchall()]

            return {
                "votes_tmdb": "votes_tmdb" in column_names,
                "votes_douban": "votes_douban" in column_names,
                "votes_imdb": "votes_imdb" in column_names,
            }

        except Exception as e:
            print(f"  [X] 检查 {table_name} 失败: {str(e)}")
            return {}


async def add_new_fields():
    """添加新的投票数字段"""
    async with async_session_local() as db:
        try:
            db_type = await check_database_type(db)
            print(f"\n检测到数据库类型: {db_type.upper()}\n")

            tables = ["unified_movies", "unified_tv_series"]

            for table in tables:
                print(f"[{table}] 检查字段...")

                # 检查新字段是否已存在
                new_fields = await check_new_fields(table)

                if all(new_fields.values()):
                    print(f"  [OK] 新字段已存在，跳过")
                    continue

                # 添加缺失的字段
                for field, exists in new_fields.items():
                    if not exists:
                        print(f"  [+] 添加字段: {field}")
                        try:
                            await db.execute(
                                text(f"ALTER TABLE {table} ADD COLUMN {field} INTEGER")
                            )
                        except Exception as e:
                            print(f"    [!] 可能已存在: {str(e)}")

                await db.commit()
                print(f"  [OK] {table} 字段添加完成")

            print("\n✅ 所有新字段添加完成！")

        except Exception as e:
            print(f"\n❌ 添加字段失败: {str(e)}")
            await db.rollback()
            raise


async def migrate_votes_data(table_name: str):
    """迁移投票数据"""
    async with async_session_local() as db:
        try:
            print(f"\n[{table_name}] 开始迁移数据...")

            # 检查是否有数据需要迁移
            result = await db.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM {table_name}
                    WHERE votes_count IS NOT NULL
                """)
            )
            count = result.scalar()

            if count == 0:
                print(f"  [OK] 没有需要迁移的数据")
                return

            print(f"  找到 {count} 条记录需要迁移")

            # 迁移 TMDB 数据
            result = await db.execute(
                text(f"""
                    UPDATE {table_name}
                    SET votes_tmdb = votes_count
                    WHERE metadata_source = 'tmdb'
                    AND votes_count IS NOT NULL
                    AND (votes_tmdb IS NULL OR votes_tmdb = 0)
                """)
            )
            tmdb_count = result.rowcount
            print(f"  [OK] 迁移 TMDB 数据: {tmdb_count} 条")

            # 迁移豆瓣数据
            result = await db.execute(
                text(f"""
                    UPDATE {table_name}
                    SET votes_douban = votes_count
                    WHERE metadata_source = 'douban'
                    AND votes_count IS NOT NULL
                    AND (votes_douban IS NULL OR votes_douban = 0)
                """)
            )
            douban_count = result.rowcount
            print(f"  [OK] 迁移豆瓣数据: {douban_count} 条")

            # 对于没有 metadata_source 的数据，默认迁移到 TMDB
            result = await db.execute(
                text(f"""
                    UPDATE {table_name}
                    SET votes_tmdb = votes_count
                    WHERE (metadata_source IS NULL OR metadata_source = '')
                    AND votes_count IS NOT NULL
                    AND (votes_tmdb IS NULL OR votes_tmdb = 0)
                """)
            )
            default_count = result.rowcount
            if default_count > 0:
                print(f"  [OK] 迁移未标记来源的数据到 TMDB: {default_count} 条")

            await db.commit()
            print(f"  [✓] {table_name} 数据迁移完成！")

        except Exception as e:
            print(f"  [X] {table_name} 迁移失败: {str(e)}")
            await db.rollback()
            raise


async def drop_old_fields():
    """删除旧的 votes_count 字段"""
    async with async_session_local() as db:
        try:
            db_type = await check_database_type(db)
            tables = ["unified_movies", "unified_tv_series"]

            print("\n⚠️  准备删除旧字段...")
            print("  此操作不可逆！请确保已备份数据库。\n")

            for table in tables:
                has_old_field = await check_old_fields(table)

                if not has_old_field:
                    print(f"[{table}] 旧字段不存在，跳过")
                    continue

                print(f"[{table}] 删除 votes_count 字段...")

                if db_type == "postgresql":
                    # PostgreSQL 可以直接删除列
                    await db.execute(
                        text(f"ALTER TABLE {table} DROP COLUMN IF EXISTS votes_count")
                    )
                    await db.commit()
                    print(f"  [OK] 已删除")
                else:
                    # SQLite 不支持直接 DROP COLUMN
                    print(f"  [!] SQLite 不支持直接删除列")
                    print(f"  提示: SQLite 需要以下步骤手动处理:")
                    print(f"  1. 备份数据库")
                    print(f"  2. 使用 SQLite 工具重建表结构")
                    print(f"  3. 或等待下次完整数据库迁移")

            if db_type == "postgresql":
                print("\n✅ 旧字段删除完成（PostgreSQL）")
            else:
                print("\n⚠️  SQLite 需要手动处理")

        except Exception as e:
            print(f"\n❌ 删除失败: {str(e)}")
            await db.rollback()
            raise


async def verify_migration():
    """验证迁移结果"""
    async with async_session_local() as db:
        try:
            print("\n" + "=" * 60)
            print("验证迁移结果")
            print("=" * 60)

            tables = ["unified_movies", "unified_tv_series"]

            for table in tables:
                print(f"\n[{table}]")

                # 检查新字段数据
                result = await db.execute(
                    text(f"""
                        SELECT
                            COUNT(*) as total,
                            COUNT(votes_tmdb) as tmdb_count,
                            COUNT(votes_douban) as douban_count,
                            COUNT(votes_imdb) as imdb_count
                        FROM {table}
                    """)
                )
                row = result.fetchone()

                print(f"  总记录数: {row[0]}")
                print(f"  包含 TMDB 投票数: {row[1]}")
                print(f"  包含豆瓣投票数: {row[2]}")
                print(f"  包含 IMDB 投票数: {row[3]}")

                # 检查是否还有旧字段
                has_old_field = await check_old_fields(table)
                if has_old_field:
                    print(f"  [!] 仍存在 votes_count 字段")
                else:
                    print(f"  [OK] votes_count 字段已删除")

            print("\n✅ 验证完成！")

        except Exception as e:
            print(f"\n❌ 验证失败: {str(e)}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="投票数字段迁移脚本")
    parser.add_argument(
        "--drop-old-fields",
        action="store_true",
        help="删除旧的 votes_count 字段"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证迁移结果，不执行迁移"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("投票数字段迁移脚本")
    print("=" * 60)
    print("\n变更:")
    print("  votes_count → votes_tmdb / votes_douban / votes_imdb")
    print("\n影响表:")
    print("  - unified_movies")
    print("  - unified_tv_series")
    print("=" * 60)

    if args.verify_only:
        await verify_migration()
        return

    if args.drop_old_fields:
        await drop_old_fields()
        await verify_migration()
        return

    # 默认：执行完整迁移流程
    try:
        # 步骤1: 添加新字段
        print("\n步骤 1/3: 添加新字段")
        print("-" * 60)
        await add_new_fields()

        # 步骤2: 迁移数据
        print("\n步骤 2/3: 迁移现有数据")
        print("-" * 60)
        await migrate_votes_data("unified_movies")
        await migrate_votes_data("unified_tv_series")

        # 步骤3: 验证
        print("\n步骤 3/3: 验证迁移结果")
        print("-" * 60)
        await verify_migration()

        print("\n" + "=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print("\n下一步:")
        print("  1. 验证数据正确性")
        print("  2. 运行: python scripts/migration/migrate_votes_fields.py --drop-old-fields")
        print("     （删除旧的 votes_count 字段）")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[!] 操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
