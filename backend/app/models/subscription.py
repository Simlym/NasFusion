# -*- coding: utf-8 -*-
"""
订阅管理数据模型
"""
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.json_types import JSON

from app.constants.subscription import (
    DEFAULT_CHECK_INTERVAL,
    DEFAULT_CHECK_STRATEGY,
    DEFAULT_COMPLETE_CONDITION,
    DEFAULT_START_EPISODE,
    SUBSCRIPTION_PRIORITY_DEFAULT,
    SUBSCRIPTION_STATUS_ACTIVE,
)
from app.models.base import BaseModel


class Subscription(BaseModel):
    """订阅管理表"""

    __tablename__ = "subscriptions"

    # 用户关联
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        default=1,
        index=True,
        comment="用户ID",
    )

    # 媒体类型和资源关联
    media_type = Column(
        String(20), nullable=False, index=True, comment="媒体类型: movie/tv/music/book/anime/adult"
    )

    # 统一资源关联（多态设计）
    unified_movie_id = Column(
        Integer,
        ForeignKey("unified_movies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="电影资源ID（仅当media_type='movie'时有值）",
    )
    unified_tv_id = Column(
        Integer,
        ForeignKey("unified_tv_series.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="电视剧资源ID（仅当media_type='tv'时有值）",
    )

    # 订阅来源和类型
    source = Column(
        String(20),
        nullable=True,
        comment="订阅来源: from_tmdb/from_pt_resource/manual",
    )
    subscription_type = Column(
        String(20),
        nullable=True,
        comment="订阅类型: movie_release/tv_season/movie_upgrade",
    )

    # 基础信息
    title = Column(String(500), nullable=False, comment="订阅标题")
    original_title = Column(String(500), nullable=True, comment="原始标题")
    year = Column(Integer, nullable=True, comment="年份")
    poster_url = Column(Text, nullable=True, comment="海报URL")

    # 外部ID（可选）
    douban_id = Column(String(20), nullable=True, index=True, comment="豆瓣ID")
    imdb_id = Column(String(20), nullable=True, index=True, comment="IMDB ID")
    tmdb_id = Column(Integer, nullable=True, index=True, comment="TMDB ID")

    # 电视剧季度和集数追踪
    current_season = Column(Integer, nullable=True, comment="订阅的季度（如3表示S03）")
    start_episode = Column(
        Integer, nullable=True, default=DEFAULT_START_EPISODE, comment="起始集数（从第几集开始）"
    )
    current_episode = Column(Integer, nullable=True, comment="当前已匹配到的集数")
    total_episodes = Column(Integer, nullable=True, comment="本季总集数（可选，用于判断是否完成）")

    # 集数状态追踪（仅电视剧）
    episodes_status = Column(
        JSON,
        nullable=True,
        comment="集数状态追踪JSON对象，key为集数，value为状态详情：{\"1\": {\"status\": \"downloaded\", \"file_id\": 123, \"quality\": \"1080p\"}}"
    )

    # ===== 多资源关联（解决长篇动画跨年番匹配问题）=====
    related_tv_ids = Column(
        JSON,
        nullable=True,
        comment="关联的TV资源ID列表（同一系列的不同年番/季度），例如: [123, 456, 789]"
    )
    absolute_episode_start = Column(
        Integer,
        nullable=True,
        comment="绝对集数起始（不区分季度），例如: 77 表示从第77集开始"
    )
    absolute_episode_end = Column(
        Integer,
        nullable=True,
        comment="绝对集数结束（null表示持续追更），例如: 128 表示追到第128集"
    )

    # ===== 展示信息覆写（用于NFO生成和文件整理）=====
    override_title = Column(
        String(500),
        nullable=True,
        comment="覆写标题（用于NFO的title字段），例如: '仙逆' 而非 '仙逆 年番2'"
    )
    override_year = Column(
        Integer,
        nullable=True,
        comment="覆写年份（用于NFO和文件整理）"
    )
    override_folder = Column(
        String(500),
        nullable=True,
        comment="覆写存储目录名，例如: '仙逆 (2023)'"
    )
    use_override_for_sync = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="是否使用覆写标题进行PT资源同步（解决如'仙逆 年番2'需要用'仙逆'搜索的问题）"
    )

    # 订阅规则（JSON格式）
    rules = Column(
        JSON,
        nullable=True,
        comment="订阅规则JSON: {quality_priority: ['2160p', '1080p'], quality_mode: 'first_match', site_priority: [1,3], promotion_required: ['free'], min_seeders: 5}",
    )

    # 订阅状态
    status = Column(
        String(20),
        nullable=False,
        default=SUBSCRIPTION_STATUS_ACTIVE,
        index=True,
        comment="订阅状态: active/paused/completed/cancelled",
    )
    is_active = Column(Boolean, nullable=False, default=True, comment="是否激活")

    # 检查策略
    check_strategy = Column(
        String(20),
        nullable=False,
        default=DEFAULT_CHECK_STRATEGY,
        comment="检查策略: aggressive/normal/relaxed（允许用户选择，实际调度由全局任务控制）",
    )
    last_check_at = Column(DateTime(timezone=True), nullable=True, comment="最后检查时间")

    # 完成条件
    complete_condition = Column(
        String(20),
        nullable=False,
        default=DEFAULT_COMPLETE_CONDITION,
        comment="完成条件: first_match/best_quality/season_complete/manual",
    )
    auto_complete_on_download = Column(
        Boolean, nullable=False, default=False, comment="下载后自动完成"
    )

    # 资源状态
    has_resources = Column(Boolean, nullable=False, default=False, comment="当前是否有PT资源（用于列表过滤）")
    first_resource_found_at = Column(
        DateTime(timezone=True), nullable=True, comment="首次发现资源时间"
    )

    # 通知设置
    notify_on_match = Column(Boolean, nullable=False, default=True, comment="匹配时通知")
    notify_on_download = Column(Boolean, nullable=False, default=True, comment="下载时通知")
    notification_channels = Column(JSON, nullable=True, comment="通知渠道JSON数组")

    # 下载设置
    auto_download = Column(Boolean, nullable=False, default=False, comment="是否自动下载")

    # 整理设置
    auto_organize = Column(Boolean, nullable=False, default=True, comment="下载完成后是否自动整理（True=整理，False=跳过）")
    organize_config_id = Column(
        Integer,
        ForeignKey("organize_configs.id", ondelete="SET NULL"),
        nullable=True,
        comment="整理配置ID（空=使用全局默认配置）",
    )
    storage_mount_id = Column(
        Integer,
        ForeignKey("storage_mounts.id", ondelete="SET NULL"),
        nullable=True,
        comment="存储挂载点ID（空=使用全局默认挂载点）",
    )


    # 用户设置
    user_tags = Column(JSON, nullable=True, comment="用户标签")
    user_priority = Column(
        Integer, nullable=False, default=SUBSCRIPTION_PRIORITY_DEFAULT, comment="用户优先级(1-10)"
    )
    user_notes = Column(Text, nullable=True, comment="用户备注")
    is_favorite = Column(Boolean, nullable=False, default=False, comment="是否收藏")

    # 统计信息
    total_checks = Column(Integer, nullable=False, default=0, comment="总检查次数")
    total_matches = Column(Integer, nullable=False, default=0, comment="总匹配次数")
    total_downloads = Column(Integer, nullable=False, default=0, comment="总下载数")

    # 完成时间
    completed_at = Column(DateTime(timezone=True), nullable=True, comment="完成时间")

    # 关系
    user = relationship("User", backref="subscriptions")
    unified_movie = relationship("UnifiedMovie", backref="subscriptions", foreign_keys=[unified_movie_id])
    unified_tv = relationship("UnifiedTVSeries", backref="subscriptions", foreign_keys=[unified_tv_id])
    check_logs = relationship(
        "SubscriptionCheckLog",
        back_populates="subscription",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # 约束：确保media_type与外键一致
    __table_args__ = (
        CheckConstraint(
            "(media_type = 'movie' AND unified_movie_id IS NOT NULL AND unified_tv_id IS NULL) OR "
            "(media_type = 'tv' AND unified_tv_id IS NOT NULL AND unified_movie_id IS NULL) OR "
            "(media_type NOT IN ('movie', 'tv'))",
            name="check_media_type_foreign_key_consistency",
        ),
        CheckConstraint(
            "user_priority >= 1 AND user_priority <= 10",
            name="check_user_priority_range",
        ),
    )

    def __repr__(self):
        return (
            f"<Subscription(id={self.id}, title={self.title}, "
            f"media_type={self.media_type}, status={self.status})>"
        )

    @property
    def is_tv_subscription(self) -> bool:
        """是否为电视剧订阅"""
        return self.media_type == "tv"

    @property
    def is_movie_subscription(self) -> bool:
        """是否为电影订阅"""
        return self.media_type == "movie"

    @property
    def use_absolute_episode_match(self) -> bool:
        """是否使用绝对集数匹配模式"""
        return self.absolute_episode_start is not None

    @property
    def all_matched_tv_ids(self) -> list:
        """获取所有匹配的TV ID列表（主资源 + 关联资源）"""
        ids = []
        if self.unified_tv_id:
            ids.append(self.unified_tv_id)
        if self.related_tv_ids:
            ids.extend(self.related_tv_ids)
        return ids

    @property
    def success_rate(self) -> float:
        """匹配成功率"""
        if self.total_checks == 0:
            return 0.0
        return (self.total_matches / self.total_checks) * 100
