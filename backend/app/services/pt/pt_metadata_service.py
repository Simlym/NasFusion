# -*- coding: utf-8 -*-
"""
PT元数据服务
"""
import logging
from typing import Dict, List

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pt_metadata import (
    PTAudioCodec,
    PTCountry,
    PTLanguage,
    PTSource,
    PTStandard,
    PTVideoCodec,
)
from app.models.pt_site import PTSite
from app.schemas.pt_metadata import MetadataMappings, MetadataSyncStats

logger = logging.getLogger(__name__)


class PTMetadataService:
    """PT元数据服务"""

    # ==================== 标准化映射规则 ====================

    # 视频编码映射规则（用于智能识别）
    VIDEO_CODEC_MAPPING_RULES = {
        "H.264": ["h264", "avc", "x264", "h.264"],
        "H.265": ["h265", "hevc", "x265", "h.265"],
        "VC-1": ["vc-1", "vc1"],
        "MPEG-2": ["mpeg-2", "mpeg2"],
        "MPEG-4": ["mpeg-4", "mpeg4"],
        "XVID": ["xvid", "divx"],
        "AV1": ["av1"],
    }

    # 分辨率/标准映射规则
    STANDARD_MAPPING_RULES = {
        "2160p": ["2160p", "4k", "uhd"],
        "1080p": ["1080p", "fhd"],
        "1080i": ["1080i"],
        "720p": ["720p", "hd"],
        "720i": ["720i"],
        "480p": ["480p", "sd"],
        "8K": ["8k", "7680p"],
    }

    # 来源映射规则
    SOURCE_MAPPING_RULES = {
        "BluRay": ["bluray", "blu-ray", "bd", "蓝光"],
        "WEB-DL": ["web-dl", "web dl", "webdl", "web"],
        "HDTV": ["hdtv", "tv"],
        "DVD": ["dvd"],
        "Remux": ["remux"],
        "Encode": ["encode", "压制"],
        "CD": ["cd"],
        "Other": ["other", "其他"],
    }

    # 音频编码映射规则
    AUDIO_CODEC_MAPPING_RULES = {
        "AAC": ["aac"],
        "AC3": ["ac3", "dolby digital"],
        "DTS": ["dts"],
        "TrueHD": ["truehd", "true-hd"],
        "LPCM": ["lpcm", "pcm"],
        "MP3": ["mp3"],
        "FLAC": ["flac"],
        "APE": ["ape"],
        "WAV": ["wav"],
        "DTS-HD": ["dts-hd", "dts hd"],
    }

    @staticmethod
    def auto_map_value(name: str, mapping_rules: Dict[str, List[str]]) -> str:
        """
        自动映射值到标准化值

        Args:
            name: 原始名称
            mapping_rules: 映射规则字典

        Returns:
            标准化值，如果无法识别返回原始名称
        """
        name_lower = name.lower().strip()

        for standard_value, keywords in mapping_rules.items():
            for keyword in keywords:
                if keyword.lower() in name_lower:
                    return standard_value

        # 如果无法识别，返回原始名称的清理版本
        return name.strip()

    # ==================== 视频编码 ====================

    @staticmethod
    async def sync_video_codecs(
        db: AsyncSession, site: PTSite, codecs_data: List[Dict]
    ) -> Dict[str, int]:
        """
        同步站点视频编码信息

        Args:
            db: 数据库会话
            site: 站点对象
            codecs_data: 编码数据列表，例如：[{"id": "1", "name": "H.264"}, ...]

        Returns:
            同步统计信息
        """
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            # 获取站点已有编码
            result = await db.execute(
                select(PTVideoCodec).where(PTVideoCodec.site_id == site.id)
            )
            existing_codecs = {codec.codec_id: codec for codec in result.scalars().all()}

            # 处理每个编码
            for codec_data in codecs_data:
                stats["total"] += 1
                codec_id = str(codec_data.get("id"))
                name = codec_data.get("name", "")

                # 自动映射到标准值
                mapped_value = PTMetadataService.auto_map_value(
                    name, PTMetadataService.VIDEO_CODEC_MAPPING_RULES
                )

                if codec_id in existing_codecs:
                    # 更新已有编码
                    codec = existing_codecs[codec_id]
                    codec.name = name
                    codec.mapped_value = mapped_value
                    codec.raw_data = codec_data
                    stats["updated"] += 1
                else:
                    # 创建新编码
                    codec = PTVideoCodec(
                        site_id=site.id,
                        codec_id=codec_id,
                        name=name,
                        name_chs=codec_data.get("nameChs", name),
                        name_cht=codec_data.get("nameCht"),
                        name_eng=codec_data.get("nameEng"),
                        mapped_value=mapped_value,
                        order=int(codec_data.get("order", 0)),
                        raw_data=codec_data,
                    )
                    db.add(codec)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} video codecs for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing video codecs for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 分辨率/标准 ====================

    @staticmethod
    async def sync_standards(
        db: AsyncSession, site: PTSite, standards_data: List[Dict]
    ) -> Dict[str, int]:
        """同步站点分辨率/标准信息"""
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            result = await db.execute(
                select(PTStandard).where(PTStandard.site_id == site.id)
            )
            existing_standards = {std.standard_id: std for std in result.scalars().all()}

            for std_data in standards_data:
                stats["total"] += 1
                standard_id = str(std_data.get("id"))
                name = std_data.get("name", "")

                mapped_value = PTMetadataService.auto_map_value(
                    name, PTMetadataService.STANDARD_MAPPING_RULES
                )

                if standard_id in existing_standards:
                    standard = existing_standards[standard_id]
                    standard.name = name
                    standard.mapped_value = mapped_value
                    standard.raw_data = std_data
                    stats["updated"] += 1
                else:
                    standard = PTStandard(
                        site_id=site.id,
                        standard_id=standard_id,
                        name=name,
                        name_chs=std_data.get("nameChs", name),
                        name_cht=std_data.get("nameCht"),
                        name_eng=std_data.get("nameEng"),
                        mapped_value=mapped_value,
                        order=int(std_data.get("order", 0)),
                        raw_data=std_data,
                    )
                    db.add(standard)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} standards for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing standards for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 来源 ====================

    @staticmethod
    async def sync_sources(
        db: AsyncSession, site: PTSite, sources_data: List[Dict]
    ) -> Dict[str, int]:
        """同步站点来源信息"""
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            result = await db.execute(
                select(PTSource).where(PTSource.site_id == site.id)
            )
            existing_sources = {src.source_id: src for src in result.scalars().all()}

            for src_data in sources_data:
                stats["total"] += 1
                source_id = str(src_data.get("id"))
                name = src_data.get("name", "")

                mapped_value = PTMetadataService.auto_map_value(
                    name, PTMetadataService.SOURCE_MAPPING_RULES
                )

                if source_id in existing_sources:
                    source = existing_sources[source_id]
                    source.name = name
                    source.mapped_value = mapped_value
                    source.raw_data = src_data
                    stats["updated"] += 1
                else:
                    source = PTSource(
                        site_id=site.id,
                        source_id=source_id,
                        name=name,
                        name_chs=src_data.get("nameChs", name),
                        name_cht=src_data.get("nameCht"),
                        name_eng=src_data.get("nameEng"),
                        mapped_value=mapped_value,
                        order=int(src_data.get("order", 0)),
                        raw_data=src_data,
                    )
                    db.add(source)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} sources for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing sources for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 音频编码 ====================

    @staticmethod
    async def sync_audio_codecs(
        db: AsyncSession, site: PTSite, codecs_data: List[Dict]
    ) -> Dict[str, int]:
        """同步站点音频编码信息"""
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            result = await db.execute(
                select(PTAudioCodec).where(PTAudioCodec.site_id == site.id)
            )
            existing_codecs = {codec.codec_id: codec for codec in result.scalars().all()}

            for codec_data in codecs_data:
                stats["total"] += 1
                codec_id = str(codec_data.get("id"))
                name = codec_data.get("name", "")

                mapped_value = PTMetadataService.auto_map_value(
                    name, PTMetadataService.AUDIO_CODEC_MAPPING_RULES
                )

                if codec_id in existing_codecs:
                    codec = existing_codecs[codec_id]
                    codec.name = name
                    codec.mapped_value = mapped_value
                    codec.raw_data = codec_data
                    stats["updated"] += 1
                else:
                    codec = PTAudioCodec(
                        site_id=site.id,
                        codec_id=codec_id,
                        name=name,
                        name_chs=codec_data.get("nameChs", name),
                        name_cht=codec_data.get("nameCht"),
                        name_eng=codec_data.get("nameEng"),
                        mapped_value=mapped_value,
                        order=int(codec_data.get("order", 0)),
                        raw_data=codec_data,
                    )
                    db.add(codec)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} audio codecs for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing audio codecs for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 语言 ====================

    @staticmethod
    async def sync_languages(
        db: AsyncSession, site: PTSite, languages_data: List[Dict]
    ) -> Dict[str, int]:
        """同步站点语言信息"""
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            result = await db.execute(
                select(PTLanguage).where(PTLanguage.site_id == site.id)
            )
            existing_languages = {lang.language_id: lang for lang in result.scalars().all()}

            for lang_data in languages_data:
                stats["total"] += 1
                language_id = str(lang_data.get("id"))
                # MTeam API 使用 langName 字段而不是 name
                name = lang_data.get("langName") or lang_data.get("name", "")

                # 语言使用原始名称或ISO代码作为mapped_value
                # MTeam API 可能提供 langTag 作为语言代码
                mapped_value = lang_data.get("langTag") or lang_data.get("code") or name

                if language_id in existing_languages:
                    language = existing_languages[language_id]
                    language.name = name
                    language.mapped_value = mapped_value
                    language.raw_data = lang_data
                    stats["updated"] += 1
                else:
                    language = PTLanguage(
                        site_id=site.id,
                        language_id=language_id,
                        name=name,
                        name_chs=lang_data.get("nameChs", name),
                        name_cht=lang_data.get("nameCht", name),
                        name_eng=lang_data.get("nameEng", name),
                        mapped_value=mapped_value,
                        order=int(lang_data.get("order", 0)),
                        raw_data=lang_data,
                    )
                    db.add(language)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} languages for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing languages for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 国家/地区 ====================

    @staticmethod
    async def sync_countries(
        db: AsyncSession, site: PTSite, countries_data: List[Dict]
    ) -> Dict[str, int]:
        """同步站点国家/地区信息"""
        stats = {"total": 0, "created": 0, "updated": 0}

        try:
            result = await db.execute(
                select(PTCountry).where(PTCountry.site_id == site.id)
            )
            existing_countries = {
                country.country_id: country for country in result.scalars().all()
            }

            for country_data in countries_data:
                stats["total"] += 1
                country_id = str(country_data.get("id"))
                name = country_data.get("name", "")

                # 国家使用原始名称或ISO代码作为mapped_value
                mapped_value = country_data.get("code", name)

                if country_id in existing_countries:
                    country = existing_countries[country_id]
                    country.name = name
                    country.mapped_value = mapped_value
                    country.raw_data = country_data
                    stats["updated"] += 1
                else:
                    country = PTCountry(
                        site_id=site.id,
                        country_id=country_id,
                        name=name,
                        name_chs=country_data.get("nameChs", name),
                        name_cht=country_data.get("nameCht"),
                        name_eng=country_data.get("nameEng"),
                        mapped_value=mapped_value,
                        order=int(country_data.get("order", 0)),
                        raw_data=country_data,
                    )
                    db.add(country)
                    stats["created"] += 1

            await db.commit()
            logger.info(
                f"Synced {stats['total']} countries for site {site.name}: "
                f"{stats['created']} created, {stats['updated']} updated"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing countries for site {site.name}: {str(e)}")
            await db.rollback()
            raise

    # ==================== 统一同步 ====================

    @staticmethod
    async def sync_all_metadata(
        db: AsyncSession, site: PTSite, metadata: Dict
    ) -> MetadataSyncStats:
        """
        一次性同步所有元数据

        Args:
            db: 数据库会话
            site: 站点对象
            metadata: 元数据字典，包含：
                - video_codecs: 视频编码列表
                - audio_codecs: 音频编码列表
                - standards: 分辨率/标准列表
                - sources: 来源列表
                - languages: 语言列表
                - countries: 国家/地区列表

        Returns:
            同步统计信息
        """
        logger.info(f"Starting sync_all_metadata for site {site.name}")

        stats = MetadataSyncStats()

        try:
            # 同步视频编码
            if "video_codecs" in metadata:
                result = await PTMetadataService.sync_video_codecs(
                    db, site, metadata["video_codecs"]
                )
                stats.video_codecs = result["total"]

            # 同步音频编码
            if "audio_codecs" in metadata:
                result = await PTMetadataService.sync_audio_codecs(
                    db, site, metadata["audio_codecs"]
                )
                stats.audio_codecs = result["total"]

            # 同步分辨率/标准
            if "standards" in metadata:
                result = await PTMetadataService.sync_standards(
                    db, site, metadata["standards"]
                )
                stats.standards = result["total"]

            # 同步来源
            if "sources" in metadata:
                result = await PTMetadataService.sync_sources(db, site, metadata["sources"])
                stats.sources = result["total"]

            # 同步语言
            if "languages" in metadata:
                result = await PTMetadataService.sync_languages(
                    db, site, metadata["languages"]
                )
                stats.languages = result["total"]

            # 同步国家/地区
            if "countries" in metadata:
                result = await PTMetadataService.sync_countries(
                    db, site, metadata["countries"]
                )
                stats.countries = result["total"]

            logger.info(f"Completed sync_all_metadata for site {site.name}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error in sync_all_metadata for site {site.name}: {str(e)}")
            raise

    # ==================== 获取映射字典 ====================

    @staticmethod
    async def get_metadata_mappings(db: AsyncSession, site_id: int) -> MetadataMappings:
        """
        获取站点的所有元数据映射字典

        用于适配器进行ID到标准值的转换

        Args:
            db: 数据库会话
            site_id: 站点ID

        Returns:
            MetadataMappings对象，包含各类元数据的 {id: mapped_value} 映射
        """
        mappings = MetadataMappings()

        try:
            # 视频编码映射
            result = await db.execute(
                select(PTVideoCodec).where(
                    and_(PTVideoCodec.site_id == site_id, PTVideoCodec.is_active == True)
                )
            )
            for codec in result.scalars():
                mappings.video_codecs[codec.codec_id] = codec.mapped_value

            # 音频编码映射
            result = await db.execute(
                select(PTAudioCodec).where(
                    and_(PTAudioCodec.site_id == site_id, PTAudioCodec.is_active == True)
                )
            )
            for codec in result.scalars():
                mappings.audio_codecs[codec.codec_id] = codec.mapped_value

            # 分辨率/标准映射
            result = await db.execute(
                select(PTStandard).where(
                    and_(PTStandard.site_id == site_id, PTStandard.is_active == True)
                )
            )
            for standard in result.scalars():
                mappings.standards[standard.standard_id] = standard.mapped_value

            # 来源映射
            result = await db.execute(
                select(PTSource).where(
                    and_(PTSource.site_id == site_id, PTSource.is_active == True)
                )
            )
            for source in result.scalars():
                mappings.sources[source.source_id] = source.mapped_value

            # 语言映射
            result = await db.execute(
                select(PTLanguage).where(
                    and_(PTLanguage.site_id == site_id, PTLanguage.is_active == True)
                )
            )
            for language in result.scalars():
                mappings.languages[language.language_id] = language.mapped_value

            # 国家/地区映射
            result = await db.execute(
                select(PTCountry).where(
                    and_(PTCountry.site_id == site_id, PTCountry.is_active == True)
                )
            )
            for country in result.scalars():
                mappings.countries[country.country_id] = country.mapped_value

            logger.info(
                f"Loaded metadata mappings for site {site_id}: "
                f"{len(mappings.video_codecs)} video codecs, "
                f"{len(mappings.standards)} standards, "
                f"{len(mappings.sources)} sources"
            )

            return mappings

        except Exception as e:
            logger.error(f"Error loading metadata mappings for site {site_id}: {str(e)}")
            raise
