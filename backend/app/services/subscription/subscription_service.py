# -*- coding: utf-8 -*-
"""
订阅服务层
"""
import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import (
    MEDIA_TYPE_ANIME,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TV,
    SUBSCRIPTION_STATUS_ACTIVE,
)
from app.models import Subscription, SubscriptionCheckLog, PTResource, ResourceMapping
from app.schemas.subscription import SubscriptionCreateSchema, SubscriptionUpdateSchema
from app.utils.timezone import now
from app.utils.tv_parser import match_subscription_season, match_absolute_episode

logger = logging.getLogger(__name__)


class SubscriptionService:
    """订阅服务"""

    # ==================== CRUD操作 ====================

    @staticmethod
    async def get_by_id(db: AsyncSession, subscription_id: int) -> Optional[Subscription]:
        """通过ID获取订阅"""
        result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        user_id: Optional[int] = None,
        media_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Subscription], int]:
        """
        获取订阅列表

        Args:
            db: 数据库会话
            user_id: 用户ID过滤
            media_type: 媒体类型过滤
            status: 状态过滤
            is_active: 是否激活过滤
            page: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Subscription], int]: 订阅列表和总数
        """
        # 构建查询
        query = select(Subscription)

        # 添加过滤条件
        conditions = []
        if user_id is not None:
            conditions.append(Subscription.user_id == user_id)
        if media_type:
            conditions.append(Subscription.media_type == media_type)
        if status:
            conditions.append(Subscription.status == status)
        if is_active is not None:
            conditions.append(Subscription.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # 分页
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(Subscription.created_at.desc())

        # 执行查询
        result = await db.execute(query)
        subscriptions = result.scalars().all()

        return list(subscriptions), total

    @staticmethod
    async def create_subscription(
        db: AsyncSession, user_id: int, subscription_data: SubscriptionCreateSchema
    ) -> Subscription:
        """
        创建订阅

        Args:
            db: 数据库会话
            user_id: 用户ID
            subscription_data: 订阅创建数据

        Returns:
            Subscription: 创建的订阅

        Raises:
            ValueError: 数据验证失败
        """
        # 验证资源ID是否存在
        if subscription_data.media_type == MEDIA_TYPE_MOVIE:
            if not subscription_data.unified_movie_id:
                raise ValueError("电影订阅必须提供 unified_movie_id")
        elif subscription_data.media_type == MEDIA_TYPE_TV:
            if not subscription_data.unified_tv_id:
                raise ValueError("电视剧订阅必须提供 unified_tv_id")
            if not subscription_data.current_season:
                raise ValueError("电视剧订阅必须提供 current_season")

        # 检查是否已存在相同订阅
        existing = await SubscriptionService._check_duplicate_subscription(
            db, user_id, subscription_data
        )
        if existing:
            raise ValueError("该订阅已存在")

        # 创建订阅
        subscription = Subscription(
            user_id=user_id,
            media_type=subscription_data.media_type,
            unified_movie_id=subscription_data.unified_movie_id,
            unified_tv_id=subscription_data.unified_tv_id,
            title=subscription_data.title,
            original_title=subscription_data.original_title,
            year=subscription_data.year,
            poster_url=subscription_data.poster_url,
            douban_id=subscription_data.douban_id,
            imdb_id=subscription_data.imdb_id,
            tmdb_id=subscription_data.tmdb_id,
            source=subscription_data.source,
            subscription_type=subscription_data.subscription_type,
            current_season=subscription_data.current_season,
            start_episode=subscription_data.start_episode,
            total_episodes=subscription_data.total_episodes,
            rules=subscription_data.rules.model_dump() if subscription_data.rules else None,
            status=SUBSCRIPTION_STATUS_ACTIVE,
            is_active=True,
            check_strategy=subscription_data.check_strategy,
            complete_condition=subscription_data.complete_condition,
            auto_complete_on_download=subscription_data.auto_complete_on_download,
            notify_on_match=subscription_data.notify_on_match,
            notify_on_download=subscription_data.notify_on_download,
            notification_channels=subscription_data.notification_channels,
            auto_download=subscription_data.auto_download,
            auto_organize=subscription_data.auto_organize,
            organize_config_id=subscription_data.organize_config_id,
            storage_mount_id=subscription_data.storage_mount_id,
            user_tags=subscription_data.user_tags,
            user_priority=subscription_data.user_priority,
            user_notes=subscription_data.user_notes,
            is_favorite=subscription_data.is_favorite,
        )

        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)

        logger.info(f"创建订阅成功: {subscription.id} - {subscription.title}")
        return subscription

    @staticmethod
    async def update_subscription(
        db: AsyncSession, subscription_id: int, update_data: SubscriptionUpdateSchema
    ) -> Optional[Subscription]:
        """
        更新订阅

        Args:
            db: 数据库会话
            subscription_id: 订阅ID
            update_data: 更新数据

        Returns:
            Optional[Subscription]: 更新后的订阅
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return None

        # 更新字段（只更新非None的字段）
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if key == "rules" and value is not None:
                # 转换Pydantic模型为字典
                setattr(subscription, key, value.model_dump() if hasattr(value, 'model_dump') else value)
            else:
                setattr(subscription, key, value)

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"更新订阅成功: {subscription.id}")
        return subscription

    @staticmethod
    async def delete_subscription(db: AsyncSession, subscription_id: int) -> bool:
        """
        删除订阅

        Args:
            db: 数据库会话
            subscription_id: 订阅ID

        Returns:
            bool: 是否删除成功
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return False

        await db.delete(subscription)
        await db.commit()

        logger.info(f"删除订阅成功: {subscription_id}")
        return True

    @staticmethod
    async def pause_subscription(db: AsyncSession, subscription_id: int) -> Optional[Subscription]:
        """暂停订阅"""
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return None

        subscription.is_active = False
        subscription.status = "paused"

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"暂停订阅: {subscription_id}")
        return subscription

    @staticmethod
    async def resume_subscription(db: AsyncSession, subscription_id: int) -> Optional[Subscription]:
        """恢复订阅"""
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return None

        subscription.is_active = True
        subscription.status = SUBSCRIPTION_STATUS_ACTIVE

        await db.commit()
        await db.refresh(subscription)

        logger.info(f"恢复订阅: {subscription_id}")
        return subscription

    # ==================== 订阅匹配逻辑 ====================

    @staticmethod
    async def check_resource_match(
        db: AsyncSession, subscription: Subscription, pt_resource: PTResource
    ) -> bool:
        """
        检查PT资源是否匹配订阅规则

        Args:
            db: 数据库会话
            subscription: 订阅对象
            pt_resource: PT资源对象

        Returns:
            bool: 是否匹配
        """
        # 1. 检查媒体类型
        # 允许 tv/movie 订阅匹配 anime 资源（动画也是影视内容的一种形式）
        if subscription.media_type == MEDIA_TYPE_TV:
            if pt_resource.category not in [MEDIA_TYPE_TV, MEDIA_TYPE_ANIME]:
                logger.debug(f"媒体类型不匹配: {pt_resource.category} not in [tv, anime]")
                return False
        elif subscription.media_type == MEDIA_TYPE_MOVIE:
            if pt_resource.category not in [MEDIA_TYPE_MOVIE, MEDIA_TYPE_ANIME]:
                logger.debug(f"媒体类型不匹配: {pt_resource.category} not in [movie, anime]")
                return False
        else:
            if pt_resource.category != subscription.media_type:
                logger.debug(f"媒体类型不匹配: {pt_resource.category} != {subscription.media_type}")
                return False

        # 2. 检查是否已关联到相同的统一资源
        mapping = await db.execute(
            select(ResourceMapping).where(ResourceMapping.pt_resource_id == pt_resource.id)
        )
        mapping = mapping.scalar_one_or_none()

        if not mapping:
            logger.debug(f"PT资源未识别: {pt_resource.id}")
            return False

        # 检查资源映射的unified_resource_id是否匹配
        if subscription.media_type == MEDIA_TYPE_MOVIE:
            if mapping.media_type != MEDIA_TYPE_MOVIE or mapping.unified_resource_id != subscription.unified_movie_id:
                return False
        elif subscription.media_type == MEDIA_TYPE_TV:
            # 获取所有匹配的TV ID（主资源 + 关联资源）
            matched_tv_ids = subscription.all_matched_tv_ids
            if mapping.media_type != MEDIA_TYPE_TV or mapping.unified_resource_id not in matched_tv_ids:
                logger.debug(
                    f"资源映射不匹配: 资源映射到{mapping.unified_resource_id}, "
                    f"订阅匹配ID列表{matched_tv_ids}"
                )
                return False

        # 3. 电视剧订阅：检查季度和集数
        if subscription.is_tv_subscription:
            if not pt_resource.tv_info:
                logger.debug(f"电视剧资源缺少tv_info: {pt_resource.id}")
                return False

            # 根据匹配模式选择不同的匹配逻辑
            if subscription.use_absolute_episode_match:
                # 绝对集数匹配模式（用于长篇动画/年番）
                episode_match = match_absolute_episode(
                    pt_resource.tv_info,
                    subscription.absolute_episode_start,
                    subscription.absolute_episode_end,
                )

                if not episode_match:
                    logger.debug(
                        f"绝对集数不匹配: 订阅[{subscription.absolute_episode_start}-"
                        f"{subscription.absolute_episode_end or '∞'}], "
                        f"资源tv_info={pt_resource.tv_info}"
                    )
                    return False
            else:
                # 传统季度+集数匹配模式
                season_match = match_subscription_season(
                    pt_resource.tv_info,
                    subscription.current_season,
                    subscription.start_episode or 1,
                )

                if not season_match:
                    logger.debug(
                        f"季度/集数不匹配: 订阅S{subscription.current_season:02d}E{subscription.start_episode:02d}, "
                        f"资源tv_info={pt_resource.tv_info}"
                    )
                    return False

        # 4. 检查订阅规则
        rules = subscription.rules or {}

        # 4.1 质量优先级
        quality_priority = rules.get("quality_priority")
        if quality_priority and pt_resource.resolution:
            if pt_resource.resolution not in quality_priority:
                logger.debug(f"质量不在优先级列表: {pt_resource.resolution} not in {quality_priority}")
                return False

        # 4.2 站点优先级
        site_priority = rules.get("site_priority")
        if site_priority and pt_resource.site_id not in site_priority:
            logger.debug(f"站点不在优先级列表: {pt_resource.site_id} not in {site_priority}")
            return False

        # 4.3 促销要求
        promotion_required = rules.get("promotion_required")
        if promotion_required:
            if not pt_resource.promotion_type or pt_resource.promotion_type not in promotion_required:
                logger.debug(
                    f"促销类型不符合要求: {pt_resource.promotion_type} not in {promotion_required}"
                )
                return False

        # 4.4 最小做种数
        min_seeders = rules.get("min_seeders", 0)
        if pt_resource.seeders < min_seeders:
            logger.debug(f"做种数不足: {pt_resource.seeders} < {min_seeders}")
            return False

        # 4.5 最小文件大小（MB）
        min_file_size = rules.get("min_file_size", 0)
        if min_file_size > 0 and pt_resource.size_bytes:
            # 将字节转换为MB
            size_mb = pt_resource.size_bytes / (1024 * 1024)
            if size_mb < min_file_size:
                logger.debug(f"文件大小不足: {size_mb:.2f}MB < {min_file_size}MB")
                return False

        # 4.6 集数类型偏好（仅电视剧）
        if subscription.is_tv_subscription:
            episode_type_preference = rules.get("episode_type_preference", "both")
            if episode_type_preference != "both" and pt_resource.tv_info:
                # 判断资源是单集/小合集还是季包
                is_single_episode = SubscriptionService._is_single_episode_resource(
                    pt_resource.tv_info
                )
                is_season_pack = SubscriptionService._is_season_pack_resource(
                    pt_resource.tv_info
                )

                # 根据偏好过滤
                if episode_type_preference == "single_preferred" and not is_single_episode:
                    logger.debug(f"不符合单集偏好: tv_info={pt_resource.tv_info}")
                    return False
                elif episode_type_preference == "season_preferred" and not is_season_pack:
                    logger.debug(f"不符合季包偏好: tv_info={pt_resource.tv_info}")
                    return False

        logger.debug(f"资源匹配成功: 订阅{subscription.id} - PT资源{pt_resource.id}")
        return True

    @staticmethod
    async def find_matched_resources(
        db: AsyncSession, subscription_id: int
    ) -> List[PTResource]:
        """
        查找匹配订阅规则的PT资源

        Args:
            db: 数据库会话
            subscription_id: 订阅ID

        Returns:
            List[PTResource]: 匹配的PT资源列表
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return []

        # 构建基础查询：通过resource_mappings关联
        if subscription.media_type == MEDIA_TYPE_MOVIE:
            query = (
                select(PTResource)
                .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
                .where(
                    and_(
                        ResourceMapping.media_type == MEDIA_TYPE_MOVIE,
                        ResourceMapping.unified_resource_id == subscription.unified_movie_id,
                        PTResource.is_active == True,
                    )
                )
            )
        elif subscription.media_type == MEDIA_TYPE_TV:
            # 获取所有匹配的TV ID（主资源 + 关联资源）
            matched_tv_ids = subscription.all_matched_tv_ids
            query = (
                select(PTResource)
                .join(ResourceMapping, ResourceMapping.pt_resource_id == PTResource.id)
                .where(
                    and_(
                        ResourceMapping.media_type == MEDIA_TYPE_TV,
                        ResourceMapping.unified_resource_id.in_(matched_tv_ids),
                        PTResource.is_active == True,
                    )
                )
            )
        else:
            return []

        # 执行查询
        result = await db.execute(query)
        all_resources = result.scalars().all()

        # 逐个检查是否匹配订阅规则
        matched_resources = []
        for resource in all_resources:
            if await SubscriptionService.check_resource_match(db, subscription, resource):
                matched_resources.append(resource)

        logger.info(f"订阅{subscription_id}找到{len(matched_resources)}个匹配资源")
        return matched_resources

    # ==================== 辅助方法 ====================

    @staticmethod
    async def _check_duplicate_subscription(
        db: AsyncSession, user_id: int, subscription_data: SubscriptionCreateSchema
    ) -> Optional[Subscription]:
        """检查是否存在重复订阅"""
        query = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.media_type == subscription_data.media_type,
            )
        )

        if subscription_data.media_type == MEDIA_TYPE_MOVIE:
            query = query.where(Subscription.unified_movie_id == subscription_data.unified_movie_id)
        elif subscription_data.media_type == MEDIA_TYPE_TV:
            query = query.where(
                and_(
                    Subscription.unified_tv_id == subscription_data.unified_tv_id,
                    Subscription.current_season == subscription_data.current_season,
                )
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_active_subscriptions_for_check(db: AsyncSession) -> List[Subscription]:
        """
        获取需要检查的活跃订阅列表

        统一调度模式：直接返回所有活跃且未完成的订阅，由全局任务调度控制检查频率

        Returns:
            List[Subscription]: 需要检查的订阅列表
        """
        query = select(Subscription).where(
            and_(
                Subscription.is_active == True,
                Subscription.status == SUBSCRIPTION_STATUS_ACTIVE,
            )
        )

        result = await db.execute(query)
        subscriptions = result.scalars().all()

        logger.info(f"找到{len(subscriptions)}个需要检查的订阅")
        return list(subscriptions)

    @staticmethod
    async def update_subscription_stats(
        db: AsyncSession, subscription_id: int, check_result: dict
    ) -> None:
        """
        更新订阅统计信息

        Args:
            db: 数据库会话
            subscription_id: 订阅ID
            check_result: 检查结果字典
        """
        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription:
            return

        # 更新统计信息
        subscription.total_checks += 1
        if check_result.get("matched_count", 0) > 0:
            subscription.total_matches += check_result.get("matched_count", 0)
        if check_result.get("downloaded", False):
            subscription.total_downloads += 1

        # 更新资源状态
        subscription.has_resources = check_result.get("has_resources", False)

        if subscription.has_resources and not subscription.first_resource_found_at:
            subscription.first_resource_found_at = now()

        # 更新检查时间
        subscription.last_check_at = now()

        await db.commit()

        logger.info(f"更新订阅{subscription_id}统计信息完成")

    @staticmethod
    async def check_subscription_completion(
        db: AsyncSession, subscription_id: int
    ) -> bool:
        """
        检查订阅是否应该标记为完成

        Args:
            db: 数据库会话
            subscription_id: 订阅ID

        Returns:
            bool: 是否应该完成
        """
        from app.constants.subscription import (
            COMPLETE_CONDITION_BEST_QUALITY,
            COMPLETE_CONDITION_FIRST_MATCH,
            COMPLETE_CONDITION_MANUAL,
            COMPLETE_CONDITION_SEASON_COMPLETE,
            EPISODE_STATUS_DOWNLOADED,
            SUBSCRIPTION_STATUS_COMPLETED,
        )

        subscription = await SubscriptionService.get_by_id(db, subscription_id)
        if not subscription or not subscription.is_active:
            return False

        should_complete = False

        # 1. first_match: 只要有一次成功下载就完成
        if subscription.complete_condition == COMPLETE_CONDITION_FIRST_MATCH:
            should_complete = subscription.total_downloads > 0

        # 2. best_quality: 获得最高质量的资源
        elif subscription.complete_condition == COMPLETE_CONDITION_BEST_QUALITY:
            if subscription.rules and "quality_priority" in subscription.rules:
                best_quality = subscription.rules["quality_priority"][0]
                # 检查最新检查日志中的 best_match 质量
                from app.services.subscription.subscription_check_log_service import (
                    SubscriptionCheckLogService,
                )

                latest_log = await SubscriptionCheckLogService.get_latest_log(
                    db, subscription_id
                )
                if latest_log and latest_log.best_match:
                    match_quality = latest_log.best_match.get("quality")
                    should_complete = match_quality == best_quality and subscription.total_downloads > 0

        # 3. season_complete: 本季所有集数都已下载
        elif subscription.complete_condition == COMPLETE_CONDITION_SEASON_COMPLETE:
            if subscription.is_tv_subscription:
                episodes_status = subscription.episodes_status or {}
                if episodes_status:
                    downloaded_count = sum(
                        1
                        for e in episodes_status.values()
                        if e.get("status") == EPISODE_STATUS_DOWNLOADED
                    )
                    total_needed = len(episodes_status)
                    should_complete = downloaded_count >= total_needed and total_needed > 0
            else:
                # 电影：有下载即完成
                should_complete = subscription.total_downloads > 0

        # 4. manual: 不自动完成
        elif subscription.complete_condition == COMPLETE_CONDITION_MANUAL:
            should_complete = False

        # 如果应该完成，更新状态
        if should_complete:
            subscription.status = SUBSCRIPTION_STATUS_COMPLETED
            subscription.is_active = False
            subscription.completed_at = now()
            await db.commit()
            logger.info(f"订阅{subscription_id}已自动标记为完成")

        return should_complete

    # ==================== 辅助方法 ====================

    @staticmethod
    def _is_single_episode_resource(tv_info: dict) -> bool:
        """
        判断是否为单集或小合集资源（1-3集）

        Args:
            tv_info: PT资源的tv_info

        Returns:
            bool: 是否为单集/小合集
        """
        from app.constants.subscription import SINGLE_EPISODE_MAX_COUNT

        if not tv_info:
            return False

        # 检查是否为完整季度
        if tv_info.get("is_complete_season") or tv_info.get("is_complete_series"):
            return False

        # 获取集数信息
        episodes = tv_info.get("episodes", {})
        if not episodes:
            return False

        # 遍历所有季度的集数
        for season_key, episode_range in episodes.items():
            if isinstance(episode_range, dict):
                start = episode_range.get("start", 0)
                end = episode_range.get("end", 0)
                # 计算集数范围
                episode_count = end - start + 1
                # 如果任何一个季度的集数 > 3，则不是单集
                if episode_count > SINGLE_EPISODE_MAX_COUNT:
                    return False

        # 所有季度的集数都 <= 3，算作单集/小合集
        return True

    @staticmethod
    def _is_season_pack_resource(tv_info: dict) -> bool:
        """
        判断是否为季包资源（完整季度）

        Args:
            tv_info: PT资源的tv_info

        Returns:
            bool: 是否为季包
        """
        if not tv_info:
            return False

        # 直接检查完整季度标记
        return tv_info.get("is_complete_season", False) or tv_info.get("is_complete_series", False)
