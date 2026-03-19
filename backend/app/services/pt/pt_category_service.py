"""
PT分类服务
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pt_metadata import PTCategory
from app.models.pt_site import PTSite

logger = logging.getLogger(__name__)


class PTCategoryService:
    """PT分类服务"""

    # 标准分类映射规则（基于关键词匹配）
    CATEGORY_MAPPING_RULES = {
        "movie": ["电影", "movie", "電影", "film"],
        "tv": ["电视", "剧集", "综艺", "tv", "series", "電視", "劇集", "綜藝"],
        "music": ["music", "音乐", "音樂", "mv", "演唱"],
        "book": ["电子书", "有声书", "電子書", "有聲書", "ebook", "audiobook"],
        "anime": ["动画", "动漫", "動畫", "動漫", "anime"],
        "game": ["游戏", "遊戲", "game"],
        "adult": ["av", "adult", "成人", "iv", "h-"],
        "documentary": ["纪录", "紀錄", "documentary", "bbc"],
        "sport": ["运动", "體育", "運動", "sports"],
        "software": ["软件", "軟體", "software"],
    }

    @staticmethod
    def auto_map_category(category_name: str) -> str:
        """
        自动映射分类名称到标准分类

        Args:
            category_name: 原始分类名称

        Returns:
            标准分类名称
        """
        name_lower = category_name.lower()

        # 成人内容具有最高优先级
        for keyword in PTCategoryService.CATEGORY_MAPPING_RULES["adult"]:
            if keyword in name_lower:
                return "adult"

        # 匹配其他分类
        for std_cat, keywords in PTCategoryService.CATEGORY_MAPPING_RULES.items():
            if std_cat == "adult":
                continue
            for keyword in keywords:
                if keyword in name_lower:
                    return std_cat

        return "other"

    @staticmethod
    async def sync_site_categories(
        db: AsyncSession, site: PTSite, categories_data: List[Dict]
    ) -> Dict[str, int]:
        """
        同步站点分类信息

        Args:
            db: 数据库会话
            site: 站点对象
            categories_data: 分类数据列表

        Returns:
            同步统计信息
        """
        stats = {"total": 0, "created": 0, "updated": 0, "skipped": 0}

        try:
            # 获取站点已有分类
            result = await db.execute(
                select(PTCategory).where(PTCategory.site_id == site.id)
            )
            existing_categories = {cat.category_id: cat for cat in result.scalars().all()}

            # 处理每个分类
            for cat_data in categories_data:
                stats["total"] += 1
                category_id = str(cat_data.get("id"))

                # 优先使用预设中指定的 mapped_category，否则自动映射
                name_chs = cat_data.get("nameChs", "")
                name_eng = cat_data.get("nameEng", "")
                mapped_category = cat_data.get("_mapped_category")
                if not mapped_category:
                    mapped_category = PTCategoryService.auto_map_category(f"{name_chs} {name_eng}")

                # 判断是否成人内容
                is_adult = mapped_category == "adult"

                if category_id in existing_categories:
                    # 更新已有分类
                    category = existing_categories[category_id]
                    category.name_chs = name_chs
                    category.name_cht = cat_data.get("nameCht")
                    category.name_eng = name_eng
                    category.parent_id = cat_data.get("parent")
                    category.order = int(cat_data.get("order", 0))
                    category.image = cat_data.get("image")
                    category.mapped_category = mapped_category
                    category.is_adult = is_adult
                    category.raw_data = cat_data
                    stats["updated"] += 1
                else:
                    # 创建新分类
                    category = PTCategory(
                        site_id=site.id,
                        category_id=category_id,
                        name_chs=name_chs,
                        name_cht=cat_data.get("nameCht"),
                        name_eng=name_eng,
                        parent_id=cat_data.get("parent"),
                        order=int(cat_data.get("order", 0)),
                        image=cat_data.get("image"),
                        mapped_category=mapped_category,
                        is_adult=is_adult,
                        raw_data=cat_data,
                    )
                    db.add(category)
                    stats["created"] += 1

            await db.flush()
            await db.commit()

            logger.info(
                f"Synced {stats['total']} categories for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing categories for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    @staticmethod
    async def get_site_categories(
        db: AsyncSession, site_id: int, include_inactive: bool = False
    ) -> List[PTCategory]:
        """
        获取站点的所有分类

        Args:
            db: 数据库会话
            site_id: 站点ID
            include_inactive: 是否包含未启用的分类

        Returns:
            分类列表
        """
        query = select(PTCategory).where(PTCategory.site_id == site_id)

        if not include_inactive:
            query = query.where(PTCategory.is_active == True)

        query = query.order_by(PTCategory.order, PTCategory.category_id)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_category_by_id(
        db: AsyncSession, site_id: int, category_id: str
    ) -> Optional[PTCategory]:
        """
        获取指定站点的指定分类

        Args:
            db: 数据库会话
            site_id: 站点ID
            category_id: 分类ID

        Returns:
            分类对象或None
        """
        result = await db.execute(
            select(PTCategory).where(
                and_(PTCategory.site_id == site_id, PTCategory.category_id == category_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_categories_by_mapped_type(
        db: AsyncSession, site_id: int, mapped_category: str
    ) -> List[PTCategory]:
        """
        根据映射标准分类获取站点分类

        Args:
            db: 数据库会话
            site_id: 站点ID
            mapped_category: 标准分类（movie/tv/music等）

        Returns:
            分类列表
        """
        result = await db.execute(
            select(PTCategory).where(
                and_(
                    PTCategory.site_id == site_id,
                    PTCategory.mapped_category == mapped_category,
                    PTCategory.is_active == True,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_category_tree(db: AsyncSession, site_id: int) -> List[Dict]:
        """
        获取分类树结构

        Args:
            db: 数据库会话
            site_id: 站点ID

        Returns:
            分类树（嵌套字典列表）
        """
        # 获取所有分类
        categories = await PTCategoryService.get_site_categories(db, site_id)

        # 构建分类字典
        cat_dict = {cat.category_id: cat.to_dict() for cat in categories}

        # 构建树结构
        tree = []
        for cat in categories:
            cat_data = cat_dict[cat.category_id]
            cat_data["children"] = []

            if cat.is_root_category:
                tree.append(cat_data)
            else:
                parent = cat_dict.get(cat.parent_id)
                if parent:
                    if "children" not in parent:
                        parent["children"] = []
                    parent["children"].append(cat_data)

        return tree

    @staticmethod
    async def update_category_mapping(
        db: AsyncSession, site_id: int, category_id: str, mapped_category: str
    ) -> Optional[PTCategory]:
        """
        手动更新分类映射

        Args:
            db: 数据库会话
            site_id: 站点ID
            category_id: 分类ID
            mapped_category: 新的标准分类

        Returns:
            更新后的分类对象
        """
        category = await PTCategoryService.get_category_by_id(db, site_id, category_id)
        if not category:
            return None

        category.mapped_category = mapped_category
        category.is_adult = mapped_category == "adult"

        await db.commit()
        await db.refresh(category)

        return category

    @staticmethod
    def get_category_ids_for_search(
        categories: List[PTCategory], mapped_category: Optional[str] = None
    ) -> List[str]:
        """
        获取用于搜索的分类ID列表

        Args:
            categories: 分类列表
            mapped_category: 可选的标准分类过滤

        Returns:
            分类ID列表
        """
        if mapped_category:
            return [
                cat.category_id
                for cat in categories
                if cat.mapped_category == mapped_category and cat.is_active
            ]
        return [cat.category_id for cat in categories if cat.is_active]
