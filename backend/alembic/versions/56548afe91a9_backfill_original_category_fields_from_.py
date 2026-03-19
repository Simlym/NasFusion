"""backfill original category fields from raw_page_json

Revision ID: 56548afe91a9
Revises: ae7ee06b0f4f
Create Date: 2026-02-07 17:56:24.229118

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session


# revision identifiers, used by Alembic.
revision: str = '56548afe91a9'
down_revision: Union[str, None] = 'ae7ee06b0f4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """从 raw_page_json 回填原始分类字段

    - original_category_id: 从 raw_page_json 中提取 category 字段
    - original_category_name: 从 pt_categories 表中查询获取 name_chs
    - 处理所有站点类型
    """

    # 获取数据库连接
    connection = op.get_bind()

    # 检查数据库类型
    dialect_name = connection.dialect.name

    print(f"数据库类型: {dialect_name}")

    # 根据数据库类型使用不同的 JSON 提取语法
    if dialect_name == 'sqlite':
        # SQLite 使用 json_extract 函数
        # 使用子查询 + 批量更新的方式
        update_query = """
            UPDATE pt_resources
            SET original_category_id = json_extract(raw_page_json, '$.category'),
                original_category_name = (
                    SELECT c.name_chs
                    FROM pt_categories c
                    WHERE c.site_id = pt_resources.site_id
                      AND c.category_id = json_extract(pt_resources.raw_page_json, '$.category')
                      AND c.is_active = 1
                    LIMIT 1
                )
            WHERE raw_page_json IS NOT NULL
              AND json_extract(raw_page_json, '$.category') IS NOT NULL
              AND (original_category_id IS NULL OR original_category_id = '')
        """
    elif dialect_name == 'postgresql':
        # PostgreSQL 使用 ->> 运算符
        update_query = """
            UPDATE pt_resources
            SET original_category_id = raw_page_json->>'category',
                original_category_name = (
                    SELECT c.name_chs
                    FROM pt_categories c
                    WHERE c.site_id = pt_resources.site_id
                      AND c.category_id = pt_resources.raw_page_json->>'category'
                      AND c.is_active = true
                    LIMIT 1
                )
            WHERE raw_page_json IS NOT NULL
              AND raw_page_json->>'category' IS NOT NULL
              AND (original_category_id IS NULL OR original_category_id = '')
        """
    else:
        # MySQL 使用 JSON_UNQUOTE(JSON_EXTRACT())
        update_query = """
            UPDATE pt_resources
            SET original_category_id = JSON_UNQUOTE(JSON_EXTRACT(raw_page_json, '$.category')),
                original_category_name = (
                    SELECT c.name_chs
                    FROM pt_categories c
                    WHERE c.site_id = pt_resources.site_id
                      AND c.category_id = JSON_UNQUOTE(JSON_EXTRACT(pt_resources.raw_page_json, '$.category'))
                      AND c.is_active = 1
                    LIMIT 1
                )
            WHERE raw_page_json IS NOT NULL
              AND JSON_EXTRACT(raw_page_json, '$.category') IS NOT NULL
              AND (original_category_id IS NULL OR original_category_id = '')
        """

    print("开始执行批量更新...")
    result = connection.execute(sa.text(update_query))

    # 获取更新的行数
    updated_count = result.rowcount
    print(f"Migration completed: {updated_count} records updated")


def downgrade() -> None:
    """回滚：清空原始分类字段"""
    connection = op.get_bind()

    # 清空所有记录的原始分类字段
    connection.execute(
        sa.text("""
            UPDATE pt_resources
            SET original_category_id = NULL,
                original_category_name = NULL,
                subcategory = NULL
        """)
    )
