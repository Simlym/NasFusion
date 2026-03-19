"""
PT站点管理API
"""
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.database import get_db
from app.core.dependencies import get_current_admin_user
from app.models.user import User
from app.schemas.pt_site import (
    PTSiteCreate,
    PTSiteCreateFromPreset,
    PTSiteListResponse,
    PTSiteResponse,
    PTSiteUpdate,
)
from app.services.pt.pt_site_service import PTSiteService
from app.constants.site_presets import get_site_preset, get_preset_list, get_all_presets
from app.adapters.pt_sites import get_supported_site_types

router = APIRouter(prefix="/pt-sites", tags=["PT站点管理"])


# ==================== 站点预设接口 ====================


@router.get("/presets", summary="获取站点预设列表")
async def list_site_presets(
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取所有可用的站点预设列表

    返回每个预设的基本信息，用于前端下拉选择
    """
    presets = get_preset_list()
    return {
        "total": len(presets),
        "presets": presets,
    }


@router.get("/presets/{preset_id}", summary="获取站点预设详情")
async def get_site_preset_detail(
    preset_id: str,
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取指定站点预设的详细配置

    包括默认URL、认证方式、分类映射等完整信息
    """
    preset = get_site_preset(preset_id)
    if not preset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站点预设不存在: {preset_id}",
        )

    return {
        "id": preset_id,
        **preset,
    }


@router.get("/supported-types", summary="获取支持的站点类型")
async def list_supported_site_types(
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取当前支持的站点类型列表

    返回已注册的适配器类型
    """
    site_types = get_supported_site_types()
    return {
        "total": len(site_types),
        "types": site_types,
    }


@router.post("/from-preset", response_model=PTSiteResponse, status_code=status.HTTP_201_CREATED, summary="从预设创建站点")
async def create_site_from_preset(
    site_data: PTSiteCreateFromPreset,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    从预设配置快速创建PT站点

    用户只需要：
    - **preset_id**: 选择站点预设（如 hdsky, mteam）
    - **auth_cookie**: Cookie（NexusPHP站点必填）
    - **auth_passkey**: Passkey（用于下载种子）

    其他配置会自动从预设加载，用户也可以覆盖默认值
    """
    try:
        site = await PTSiteService.create_site_from_preset(db, site_data)
        # 添加认证信息已设置标志
        site_data_dict = site.to_dict()
        site_data_dict['has_auth_cookie'] = bool(site.auth_cookie)
        site_data_dict['has_auth_passkey'] = bool(site.auth_passkey)
        site_data_dict['has_auth_password'] = bool(site.auth_password)
        return site_data_dict
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=PTSiteListResponse, summary="获取PT站点列表")
async def get_pt_sites(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query(None, description="状态过滤: active/inactive/error"),
    sync_enabled: bool = Query(None, description="是否启用同步"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取PT站点列表

    - **page**: 页码（从1开始）
    - **page_size**: 每页数量（1-100）
    - **status**: 状态过滤（可选）
    - **sync_enabled**: 同步启用状态过滤（可选）
    """
    sites, total = await PTSiteService.get_list(
        db, page=page, page_size=page_size, status=status, sync_enabled=sync_enabled
    )

    # 为每个站点添加认证信息已设置标志
    items = []
    for site in sites:
        if not site:
            continue
            
        # 获取模型的所有列
        site_data = site.to_dict()
        # 添加认证标志
        site_data['has_auth_cookie'] = bool(site.auth_cookie)
        site_data['has_auth_passkey'] = bool(site.auth_passkey)
        site_data['has_auth_password'] = bool(site.auth_password)
        items.append(site_data)

    return PTSiteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=PTSiteResponse, status_code=status.HTTP_201_CREATED, summary="创建PT站点")
async def create_pt_site(
    site_data: PTSiteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    创建新的PT站点配置

    - **name**: 站点名称
    - **type**: 站点类型（对应爬虫适配器）
    - **domain**: 站点域名
    - **base_url**: 完整URL
    - **auth_type**: 认证方式（cookie/passkey/user_pass）
    - **auth_cookie**: Cookie（可选）
    - **auth_passkey**: Passkey（可选）
    - **auth_username**: 用户名（可选）
    - **auth_password**: 密码（可选）
    - 其他配置...
    """
    try:
        site = await PTSiteService.create_site(db, site_data)
        # 添加认证信息已设置标志
        site_data_dict = site.to_dict()
        site_data_dict['has_auth_cookie'] = bool(site.auth_cookie)
        site_data_dict['has_auth_passkey'] = bool(site.auth_passkey)
        site_data_dict['has_auth_password'] = bool(site.auth_password)
        return site_data_dict
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/{site_id}", response_model=PTSiteResponse, summary="获取PT站点详情")
async def get_pt_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取指定PT站点的详细信息
    """
    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PT站点不存在",
        )

    # 添加认证信息已设置标志
    site_data = site.to_dict()
    site_data['has_auth_cookie'] = bool(site.auth_cookie)
    site_data['has_auth_passkey'] = bool(site.auth_passkey)
    site_data['has_auth_password'] = bool(site.auth_password)
    return site_data


@router.put("/{site_id}", response_model=PTSiteResponse, summary="更新PT站点")
async def update_pt_site(
    site_id: int,
    site_data: PTSiteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    更新PT站点配置

    只更新提供的字段，未提供的字段保持不变
    """
    site = await PTSiteService.update_site(db, site_id, site_data)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PT站点不存在",
        )

    # 添加认证信息已设置标志
    site_data_dict = site.to_dict()
    site_data_dict['has_auth_cookie'] = bool(site.auth_cookie)
    site_data_dict['has_auth_passkey'] = bool(site.auth_passkey)
    site_data_dict['has_auth_password'] = bool(site.auth_password)
    return site_data_dict


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除PT站点")
async def delete_pt_site(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    删除PT站点
    """
    success = await PTSiteService.delete_site(db, site_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PT站点不存在",
        )
    return None


@router.post("/{site_id}/test", summary="测试PT站点连接")
async def test_pt_site_connection(
    site_id: int,
    skip_proxy: bool = Query(False, description="跳过代理直连测试"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    测试PT站点连接是否正常

    - **skip_proxy**: 设置为 true 可以跳过代理直连测试，用于排查代理问题
    """
    success, message = await PTSiteService.test_connection(db, site_id, skip_proxy=skip_proxy)

    if not success:
        return {"success": False, "message": message}

    return {"success": True, "message": message}


@router.post("/{site_id}/sync-categories", summary="同步站点分类")
async def sync_site_categories(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    同步指定PT站点的分类列表

    该接口会：
    1. 调用站点适配器获取最新分类信息
    2. 自动映射到标准分类（movie/tv/music等）
    3. 更新数据库中的分类数据
    """
    from app.adapters.pt_sites import get_adapter
    from app.services.pt.pt_category_service import PTCategoryService
    from app.utils.encryption import encryption_util

    # 获取站点信息
    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    try:
        # 获取站点适配器
        config = {
            "name": site.name,
            "base_url": site.base_url,
            "domain": site.domain,
            "proxy_config": site.proxy_config,
            "request_interval": site.request_interval or 2,
        }

        # 添加认证信息
        if site.auth_type == "passkey" and site.auth_passkey:
            config["auth_passkey"] = encryption_util.decrypt(site.auth_passkey)

        adapter = get_adapter(site.type, config)

        # 检查适配器是否支持分类同步
        if not hasattr(adapter, "fetch_categories"):
            raise HTTPException(
                status_code=400, detail=f"站点类型 {site.type} 不支持分类同步"
            )

        # 获取分类列表
        categories_data = await adapter.fetch_categories()

        # 同步到数据库
        stats = await PTCategoryService.sync_site_categories(db, site, categories_data)

        return {
            "success": True,
            "message": "分类同步完成",
            "stats": stats,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/{site_id}/categories", summary="获取站点分类列表")
async def get_site_categories(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的分类"),
    tree: bool = Query(False, description="是否返回树结构"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取指定站点的分类列表

    - **tree**: 如果为true，返回树形结构；否则返回扁平列表
    - **include_inactive**: 是否包含未启用的分类
    """
    from app.services.pt.pt_category_service import PTCategoryService

    # 检查站点是否存在
    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    if tree:
        # 返回树结构
        categories = await PTCategoryService.get_category_tree(db, site_id)
    else:
        # 返回扁平列表
        categories = await PTCategoryService.get_site_categories(
            db, site_id, include_inactive
        )
        categories = [cat.to_dict() for cat in categories]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(categories),
        "categories": categories,
    }


@router.put("/{site_id}/categories/{category_id}", summary="更新分类映射")
async def update_category_mapping(
    site_id: int,
    category_id: str,
    mapped_category: str = Query(..., description="标准分类: movie/tv/music/book/anime/adult/game/other"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    手动更新分类到标准分类的映射

    用于修正自动映射不准确的情况
    """
    from app.services.pt.pt_category_service import PTCategoryService

    # 验证标准分类
    valid_categories = ["movie", "tv", "music", "book", "anime", "adult", "game", "other"]
    if mapped_category not in valid_categories:
        raise HTTPException(
            status_code=400, detail=f"无效的标准分类，必须是: {', '.join(valid_categories)}"
        )

    # 更新映射
    category = await PTCategoryService.update_category_mapping(
        db, site_id, category_id, mapped_category
    )

    if not category:
        raise HTTPException(status_code=404, detail="分类不存在")

    return {
        "success": True,
        "message": "分类映射已更新",
        "category": category.to_dict(),
    }


@router.post("/{site_id}/sync-all-metadata", summary="同步站点所有元数据")
async def sync_all_site_metadata(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    同步站点所有元数据（视频编码、音频编码、分辨率、来源、语言、国家等）

    该接口会：
    1. 调用站点API获取所有元数据
    2. 存储到独立的元数据表（pt_video_codecs、pt_standards等）
    3. 自动映射ID到标准化值
    4. 供前端下拉框和资源筛选使用
    """
    from app.adapters.pt_sites import get_adapter
    from app.services.pt.pt_metadata_service import PTMetadataService
    from app.schemas.pt_metadata import MetadataSyncResponse
    from app.utils.encryption import encryption_util

    # 获取站点信息
    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    try:
        # 获取站点适配器
        config = {
            "name": site.name,
            "base_url": site.base_url,
            "domain": site.domain,
            "proxy_config": site.proxy_config,
            "request_interval": site.request_interval or 2,
        }

        # 添加认证信息
        if site.auth_type == "passkey" and site.auth_passkey:
            config["auth_passkey"] = encryption_util.decrypt(site.auth_passkey)

        adapter = get_adapter(site.type, config)

        # 检查适配器是否支持元数据同步
        if not hasattr(adapter, "fetch_metadata"):
            raise HTTPException(
                status_code=400, detail=f"站点类型 {site.type} 不支持元数据同步"
            )

        # 获取元数据
        metadata = await adapter.fetch_metadata()

        # 使用PTMetadataService同步到数据库
        stats = await PTMetadataService.sync_all_metadata(db, site, metadata)

        # 构建响应
        synced_types = []
        if stats.video_codecs > 0:
            synced_types.append("video_codecs")
        if stats.audio_codecs > 0:
            synced_types.append("audio_codecs")
        if stats.standards > 0:
            synced_types.append("standards")
        if stats.sources > 0:
            synced_types.append("sources")
        if stats.languages > 0:
            synced_types.append("languages")
        if stats.countries > 0:
            synced_types.append("countries")

        return MetadataSyncResponse(
            success=True,
            message="元数据同步完成",
            stats=stats,
            synced_types=synced_types,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/{site_id}/metadata", summary="获取站点所有元数据")
async def get_site_all_metadata(
    site_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取站点的所有元数据

    包括：
    - video_codecs: 视频编码列表（H.264, H.265等）
    - audio_codecs: 音频编码列表（AAC, DTS等）
    - standards: 分辨率/标准列表（1080p, 2160p等）
    - sources: 来源列表（BluRay, WEB-DL等）
    - languages: 语言列表
    - countries: 国家/地区列表
    """
    from app.services.pt.pt_metadata_service import PTMetadataService
    from app.models.pt_metadata import (
        PTVideoCodec,
        PTAudioCodec,
        PTStandard,
        PTSource,
        PTLanguage,
        PTCountry,
    )
    from sqlalchemy import select, and_

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    # 获取所有元数据
    result = await db.execute(
        select(PTVideoCodec).where(PTVideoCodec.site_id == site_id).order_by(PTVideoCodec.order)
    )
    video_codecs = [codec.to_dict() for codec in result.scalars()]

    result = await db.execute(
        select(PTAudioCodec).where(PTAudioCodec.site_id == site_id).order_by(PTAudioCodec.order)
    )
    audio_codecs = [codec.to_dict() for codec in result.scalars()]

    result = await db.execute(
        select(PTStandard).where(PTStandard.site_id == site_id).order_by(PTStandard.order)
    )
    standards = [std.to_dict() for std in result.scalars()]

    result = await db.execute(
        select(PTSource).where(PTSource.site_id == site_id).order_by(PTSource.order)
    )
    sources = [src.to_dict() for src in result.scalars()]

    result = await db.execute(
        select(PTLanguage).where(PTLanguage.site_id == site_id).order_by(PTLanguage.order)
    )
    languages = [lang.to_dict() for lang in result.scalars()]

    result = await db.execute(
        select(PTCountry).where(PTCountry.site_id == site_id).order_by(PTCountry.order)
    )
    countries = [country.to_dict() for country in result.scalars()]

    total_count = (
        len(video_codecs)
        + len(audio_codecs)
        + len(standards)
        + len(sources)
        + len(languages)
        + len(countries)
    )

    return {
        "success": True,
        "site_id": site_id,
        "site_name": site.name,
        "video_codecs": video_codecs,
        "audio_codecs": audio_codecs,
        "standards": standards,
        "sources": sources,
        "languages": languages,
        "countries": countries,
        "total_count": total_count,
    }


# ==================== 各类元数据独立接口 ====================


@router.get("/{site_id}/video-codecs", summary="获取视频编码列表")
async def get_site_video_codecs(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的编码"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的视频编码列表"""
    from app.models.pt_metadata import PTVideoCodec
    from sqlalchemy import select, and_

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTVideoCodec).where(PTVideoCodec.site_id == site_id)
    if not include_inactive:
        query = query.where(PTVideoCodec.is_active == True)
    query = query.order_by(PTVideoCodec.order)

    result = await db.execute(query)
    codecs = [codec.to_dict() for codec in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(codecs),
        "video_codecs": codecs,
    }


@router.get("/{site_id}/audio-codecs", summary="获取音频编码列表")
async def get_site_audio_codecs(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的编码"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的音频编码列表"""
    from app.models.pt_metadata import PTAudioCodec
    from sqlalchemy import select

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTAudioCodec).where(PTAudioCodec.site_id == site_id)
    if not include_inactive:
        query = query.where(PTAudioCodec.is_active == True)
    query = query.order_by(PTAudioCodec.order)

    result = await db.execute(query)
    codecs = [codec.to_dict() for codec in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(codecs),
        "audio_codecs": codecs,
    }


@router.get("/{site_id}/standards", summary="获取分辨率/标准列表")
async def get_site_standards(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的标准"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的分辨率/质量标准列表"""
    from app.models.pt_metadata import PTStandard
    from sqlalchemy import select

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTStandard).where(PTStandard.site_id == site_id)
    if not include_inactive:
        query = query.where(PTStandard.is_active == True)
    query = query.order_by(PTStandard.order)

    result = await db.execute(query)
    standards = [std.to_dict() for std in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(standards),
        "standards": standards,
    }


@router.get("/{site_id}/sources", summary="获取来源列表")
async def get_site_sources(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的来源"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的来源列表"""
    from app.models.pt_metadata import PTSource
    from sqlalchemy import select

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTSource).where(PTSource.site_id == site_id)
    if not include_inactive:
        query = query.where(PTSource.is_active == True)
    query = query.order_by(PTSource.order)

    result = await db.execute(query)
    sources = [src.to_dict() for src in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(sources),
        "sources": sources,
    }


@router.get("/{site_id}/languages", summary="获取语言列表")
async def get_site_languages(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的语言"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的语言列表"""
    from app.models.pt_metadata import PTLanguage
    from sqlalchemy import select

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTLanguage).where(PTLanguage.site_id == site_id)
    if not include_inactive:
        query = query.where(PTLanguage.is_active == True)
    query = query.order_by(PTLanguage.order)

    result = await db.execute(query)
    languages = [lang.to_dict() for lang in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(languages),
        "languages": languages,
    }


@router.get("/{site_id}/countries", summary="获取国家/地区列表")
async def get_site_countries(
    site_id: int,
    include_inactive: bool = Query(False, description="是否包含未启用的国家/地区"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """获取指定站点的国家/地区列表"""
    from app.models.pt_metadata import PTCountry
    from sqlalchemy import select

    site = await PTSiteService.get_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="站点不存在")

    query = select(PTCountry).where(PTCountry.site_id == site_id)
    if not include_inactive:
        query = query.where(PTCountry.is_active == True)
    query = query.order_by(PTCountry.order)

    result = await db.execute(query)
    countries = [country.to_dict() for country in result.scalars()]

    return {
        "site_id": site_id,
        "site_name": site.name,
        "total": len(countries),
        "countries": countries,
    }
