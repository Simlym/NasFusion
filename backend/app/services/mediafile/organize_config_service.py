# -*- coding: utf-8 -*-
"""
整理配置服务
管理媒体文件整理规则的CRUD操作
"""
import logging
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    DEFAULT_ADULT_DIR_TEMPLATE,
    DEFAULT_ADULT_FILENAME_TEMPLATE,
    DEFAULT_ANIME_DIR_TEMPLATE,
    DEFAULT_ANIME_FILENAME_TEMPLATE,
    DEFAULT_BOOK_DIR_TEMPLATE,
    DEFAULT_BOOK_FILENAME_TEMPLATE,
    DEFAULT_MOVIE_DIR_TEMPLATE,
    DEFAULT_MOVIE_FILENAME_TEMPLATE,
    DEFAULT_MUSIC_DIR_TEMPLATE,
    DEFAULT_MUSIC_FILENAME_TEMPLATE,
    DEFAULT_TV_DIR_TEMPLATE,
    DEFAULT_TV_FILENAME_TEMPLATE,
    MEDIA_TYPE_ADULT,
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_BOOK,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_TV,
    MEDIA_TYPE_DIRS,
    NFO_FORMAT_JELLYFIN,
    ORGANIZE_MODE_HARDLINK,
)
from app.models.organize_config import OrganizeConfig

logger = logging.getLogger(__name__)


class OrganizeConfigService:
    """整理配置服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, config_id: int) -> Optional[OrganizeConfig]:
        """
        根据ID获取配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            配置对象，不存在返回None
        """
        result = await db.execute(select(OrganizeConfig).where(OrganizeConfig.id == config_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_name(db: AsyncSession, name: str) -> Optional[OrganizeConfig]:
        """
        根据名称获取配置

        Args:
            db: 数据库会话
            name: 配置名称

        Returns:
            配置对象，不存在返回None
        """
        result = await db.execute(select(OrganizeConfig).where(OrganizeConfig.name == name))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_default(db: AsyncSession, media_type: str) -> Optional[OrganizeConfig]:
        """
        获取指定媒体类型的默认配置

        Args:
            db: 数据库会话
            media_type: 媒体类型

        Returns:
            默认配置对象，不存在返回None
        """
        result = await db.execute(
            select(OrganizeConfig)
            .where(OrganizeConfig.media_type == media_type, OrganizeConfig.is_default == True)
            .order_by(OrganizeConfig.id.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        media_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> Dict:
        """
        查询配置列表

        Args:
            db: 数据库会话
            skip: 跳过数量
            limit: 返回数量
            media_type: 媒体类型过滤
            is_enabled: 是否启用过滤

        Returns:
            包含total和items的字典
        """
        query = select(OrganizeConfig)

        # 添加过滤条件
        if media_type:
            query = query.where(OrganizeConfig.media_type == media_type)
        if is_enabled is not None:
            query = query.where(OrganizeConfig.is_enabled == is_enabled)

        # 统计总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页查询
        query = query.order_by(OrganizeConfig.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return {"total": total, "items": items}

    @staticmethod
    async def create_default_configs(db: AsyncSession) -> List[OrganizeConfig]:
        """
        创建默认配置（电影、电视剧、动漫、电子书、音乐、成人）

        Args:
            db: 数据库会话

        Returns:
            创建的配置列表
        """
        configs = []

        # 定义所有默认配置模板
        config_templates = {
            MEDIA_TYPE_MOVIE: {
                "name": "电影库-默认",
                "dir_template": DEFAULT_MOVIE_DIR_TEMPLATE,
                "filename_template": DEFAULT_MOVIE_FILENAME_TEMPLATE,
                "description": "默认电影库配置，使用硬链接模式"
            },
            MEDIA_TYPE_TV: {
                "name": "剧集库-默认",
                "dir_template": DEFAULT_TV_DIR_TEMPLATE,
                "filename_template": DEFAULT_TV_FILENAME_TEMPLATE,
                "description": "默认电视剧库配置，使用硬链接模式"
            },
            MEDIA_TYPE_ANIME: {
                "name": "动漫库-默认",
                "dir_template": DEFAULT_ANIME_DIR_TEMPLATE,
                "filename_template": DEFAULT_ANIME_FILENAME_TEMPLATE,
                "description": "默认动漫库配置，使用硬链接模式"
            },
            MEDIA_TYPE_BOOK: {
                "name": "电子书库-默认",
                "dir_template": DEFAULT_BOOK_DIR_TEMPLATE,
                "filename_template": DEFAULT_BOOK_FILENAME_TEMPLATE,
                "description": "默认电子书库配置，使用硬链接模式",
                "generate_nfo": False,
                "download_backdrop": False,
                "organize_subtitles": False
            },
            MEDIA_TYPE_MUSIC: {
                "name": "音乐库-默认",
                "dir_template": DEFAULT_MUSIC_DIR_TEMPLATE,
                "filename_template": DEFAULT_MUSIC_FILENAME_TEMPLATE,
                "description": "默认音乐库配置，使用硬链接模式",
                "generate_nfo": False,
                "download_backdrop": False,
                "organize_subtitles": False
            },
            MEDIA_TYPE_ADULT: {
                "name": "成人库-默认",
                "dir_template": DEFAULT_ADULT_DIR_TEMPLATE,
                "filename_template": DEFAULT_ADULT_FILENAME_TEMPLATE,
                "description": "默认成人内容库配置，使用硬链接模式"
            }
        }

        # 生成完整的配置列表
        # 注意：library_root 字段已被挂载点系统取代，实际整理时由 StorageMountService 动态选择目标路径
        # 此处的 library_root 仅用于 UI 显示和兼容性，不影响实际整理逻辑
        default_configs = []
        for media_type, template in config_templates.items():
            if media_type in MEDIA_TYPE_DIRS:
                library_dir = MEDIA_TYPE_DIRS[media_type]
                config = {
                    "media_type": media_type,
                    "library_root": f"由挂载点系统动态选择",  # 占位符，不再使用固定路径
                    **template
                }
                default_configs.append(config)

        # 为每种媒体类型创建配置，如果不存在的话
        for config_data in default_configs:
            # 检查是否已存在该媒体类型的配置
            existing = await db.execute(
                select(OrganizeConfig).where(
                    OrganizeConfig.media_type == config_data["media_type"]
                )
            )
            if existing.scalar_one_or_none():
                logger.debug(f"{config_data['name']}已存在，跳过创建")
                continue

            # 创建新配置
            config = OrganizeConfig(
                name=config_data["name"],
                media_type=config_data["media_type"],
                is_enabled=True,
                is_default=True,
                library_root=config_data["library_root"],
                dir_template=config_data["dir_template"],
                filename_template=config_data["filename_template"],
                organize_mode=ORGANIZE_MODE_HARDLINK,
                generate_nfo=config_data.get("generate_nfo", True),
                nfo_format=NFO_FORMAT_JELLYFIN,
                download_poster=config_data.get("download_poster", True),
                download_backdrop=config_data.get("download_backdrop", True),
                organize_subtitles=config_data.get("organize_subtitles", True),
                skip_existed=True,
                description=config_data["description"]
            )
            db.add(config)
            configs.append(config)
            logger.info(f"创建默认配置: {config_data['name']}")

        if configs:
            await db.commit()
            for config in configs:
                await db.refresh(config)
            logger.info(f"成功创建了 {len(configs)} 个默认整理配置")
        else:
            logger.info("所有配置都已存在，无需创建")

        return configs

    @staticmethod
    async def create(db: AsyncSession, config_data: dict) -> OrganizeConfig:
        """
        创建配置

        Args:
            db: 数据库会话
            config_data: 配置数据

        Returns:
            创建的配置对象
        """
        # 检查名称是否重复
        existing = await OrganizeConfigService.get_by_name(db, config_data.get("name"))
        if existing:
            raise ValueError(f"配置名称已存在: {config_data.get('name')}")

        config = OrganizeConfig(**config_data)
        db.add(config)
        await db.commit()
        await db.refresh(config)

        logger.info(f"创建整理配置: {config.name}, ID: {config.id}")
        return config

    @staticmethod
    async def update(db: AsyncSession, config_id: int, config_data: dict) -> Optional[OrganizeConfig]:
        """
        更新配置

        Args:
            db: 数据库会话
            config_id: 配置ID
            config_data: 配置数据

        Returns:
            更新后的配置对象
        """
        config = await OrganizeConfigService.get_by_id(db, config_id)
        if not config:
            return None

        # 检查名称是否与其他配置重复
        if "name" in config_data and config_data["name"] != config.name:
            existing = await OrganizeConfigService.get_by_name(db, config_data["name"])
            if existing:
                raise ValueError(f"配置名称已存在: {config_data['name']}")

        # 更新字段
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)

        await db.commit()
        await db.refresh(config)

        logger.info(f"更新整理配置: {config.name}, ID: {config.id}")
        return config

    @staticmethod
    async def delete(db: AsyncSession, config_id: int) -> bool:
        """
        删除配置

        Args:
            db: 数据库会话
            config_id: 配置ID

        Returns:
            是否成功
        """
        config = await OrganizeConfigService.get_by_id(db, config_id)
        if not config:
            return False

        await db.delete(config)
        await db.commit()

        logger.info(f"删除整理配置: {config.name}, ID: {config_id}")
        return True

    @staticmethod
    def parse_template(
        template: str,
        variables: dict,
    ) -> str:
        """
        解析模板字符串

        Args:
            template: 模板字符串（如 "{title} ({year})"）
            variables: 变量字典（如 {"title": "电影名", "year": 2023}）

        Returns:
            解析后的字符串
        """
        try:
            return template.format(**variables)
        except KeyError as e:
            logger.warning(f"模板变量缺失: {e}, 模板: {template}")
            return template
        except Exception as e:
            logger.error(f"解析模板失败: {e}, 模板: {template}")
            return template
