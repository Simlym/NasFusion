# -*- coding: utf-8 -*-
"""
元数据迁移脚本

用途：
1. 对所有现有PT站点重新同步元数据到新表
2. 从旧的metadata_cache字段迁移到新的独立表
3. 可选：删除旧的metadata_cache字段

使用方法：
    python scripts/migrate_metadata.py
    python scripts/migrate_metadata.py --drop-old-fields  # 删除旧字段
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_local
from app.models.pt_site import PTSite
from app.services.pt.pt_site_service import PTSiteService


async def migrate_all_sites():
    """对所有站点重新同步元数据"""
    async with async_session_local() as db:
        try:
            # 获取所有活跃站点
            result = await db.execute(
                select(PTSite).where(PTSite.status == "active")
            )
            sites = result.scalars().all()

            if not sites:
                print("[X] 没有找到活跃的站点")
                return

            print(f"\n找到 {len(sites)} 个活跃站点，开始迁移...")
            print("=" * 60)

            success_count = 0
            failed_count = 0

            for i, site in enumerate(sites, 1):
                print(f"\n[{i}/{len(sites)}] 正在处理站点: {site.name}")
                print(f"  - 类型: {site.type}")
                print(f"  - 域名: {site.domain}")

                try:
                    # 调用自动同步方法
                    await PTSiteService._auto_sync_metadata(db, site)
                    print(f"  [OK] 元数据同步成功")
                    success_count += 1

                except Exception as e:
                    print(f"  [X] 同步失败: {str(e)}")
                    failed_count += 1

                print("-" * 60)

            print(f"\n[OK] 迁移完成！")
            print(f"  - 成功: {success_count} 个站点")
            print(f"  - 失败: {failed_count} 个站点")

        except Exception as e:
            print(f"\n[X] 迁移过程出错: {str(e)}")
            raise


from app.core.config import settings


async def check_old_fields():
    """检查是否还有旧的metadata_cache字段"""
    async with async_session_local() as db:
        try:
            # 检查表结构
            if settings.database.DB_TYPE == "sqlite":
                result = await db.execute(
                    text("PRAGMA table_info(pt_sites)")
                )
                columns = result.fetchall()
                has_metadata_cache = any(col[1] == "metadata_cache" for col in columns)
                has_metadata_updated_at = any(col[1] == "metadata_updated_at" for col in columns)
            else:
                # PostgreSQL
                result = await db.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'pt_sites'"
                ))
                column_names = [row[0] for row in result.fetchall()]
                has_metadata_cache = "metadata_cache" in column_names
                has_metadata_updated_at = "metadata_updated_at" in column_names

            if has_metadata_cache or has_metadata_updated_at:
                print("\n[!] 检测到旧字段:")
                if has_metadata_cache:
                    print("  - metadata_cache")
                if has_metadata_updated_at:
                    print("  - metadata_updated_at")
                print("\n建议运行: python scripts/migrate_metadata.py --drop-old-fields")
                return True
            else:
                print("\n[OK] 未检测到旧字段，数据库结构已是最新")
                return False

        except Exception as e:
            print(f"\n[X] 检查失败: {str(e)}")
            return False


async def drop_old_fields():
    """删除旧的metadata_cache和metadata_updated_at字段"""
    async with async_session_local() as db:
        try:
            print("\n⚠️  准备删除旧字段...")
            print("  此操作不可逆！请确保已备份数据库。")

            # SQLite不支持直接DROP COLUMN，需要重建表
            # 但由于我们已经在模型中删除了这些字段，
            # 下次运行create_all()时会自动重建表结构

            print("\n💡 提示:")
            print("  由于SQLite限制，需要重新创建数据库表来删除字段。")
            print("  建议:")
            print("  1. 备份当前数据库")
            print("  2. 删除pt_sites表中的metadata_cache和metadata_updated_at列")
            print("  3. 或者等待下次数据库迁移时自动更新")

            # 对于PostgreSQL，可以直接删除
            try:
                await db.execute(text("ALTER TABLE pt_sites DROP COLUMN IF EXISTS metadata_cache"))
                await db.execute(text("ALTER TABLE pt_sites DROP COLUMN IF EXISTS metadata_updated_at"))
                await db.commit()
                print("\n✅ 旧字段已删除（PostgreSQL）")
            except Exception as e:
                print(f"\n⚠️  无法删除字段（可能是SQLite）: {str(e)}")
                print("  SQLite需要手动处理或等待下次完整迁移")

        except Exception as e:
            print(f"\n❌ 删除失败: {str(e)}")
            await db.rollback()
            raise


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="元数据迁移脚本")
    parser.add_argument(
        "--drop-old-fields",
        action="store_true",
        help="删除旧的metadata_cache和metadata_updated_at字段"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查是否有旧字段，不执行迁移"
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("PT站点元数据迁移脚本")
    print("=" * 60)

    if args.check_only:
        await check_old_fields()
        return

    if args.drop_old_fields:
        await drop_old_fields()
        return

    # 默认：执行元数据迁移
    await migrate_all_sites()

    # 迁移后检查
    print("\n" + "=" * 60)
    print("检查旧字段...")
    print("=" * 60)
    await check_old_fields()


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
