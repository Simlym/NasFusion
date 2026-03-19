"""
PT资源管理API
"""
import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.pt_resource import (
    PTResourceFilter,
    PTResourceList,
    PTResourceResponse,
    SyncRequest,
    SyncResponse,
)
from app.schemas.sync_log import SyncLogFilter, SyncLogList, SyncLogResponse
from app.services.pt.pt_resource_service import PTResourceService
from app.utils.response_helper import error_response, success_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pt-resources", tags=["PT资源管理"])


@router.get("", summary="获取资源列表", response_model=PTResourceList)
async def get_resources(
    filter_params: PTResourceFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取PT资源列表

    支持过滤条件：
    - 站点ID
    - 分类
    - 免费/促销
    - 做种数
    - 分辨率/编码/来源
    - 关键词搜索
    """
    print("=" * 80)
    print("DEBUG: get_resources API called")
    print("=" * 80)

    resources, total = await PTResourceService.get_list(db, filter_params)
    print(f"DEBUG: Got {len(resources)} resources, total: {total}")

    # 批量查询所有资源的 mapping（避免 N+1 查询）
    from app.models.resource_mapping import ResourceMapping
    from app.models.download_task import DownloadTask
    from app.models.pt_metadata import PTCategory
    from sqlalchemy import select, and_

    resource_ids = [r.id for r in resources]
    mapping_query = select(ResourceMapping).where(ResourceMapping.pt_resource_id.in_(resource_ids))
    mapping_result = await db.execute(mapping_query)
    mappings_list = mapping_result.scalars().all()

    # 构建 resource_id -> mapping 的字典
    mappings_dict = {m.pt_resource_id: m for m in mappings_list}

    # 批量查询下载状态
    download_status_map = {}
    if resource_ids:
        download_query = select(DownloadTask.pt_resource_id, DownloadTask.status).where(
            DownloadTask.pt_resource_id.in_(resource_ids)
        )
        download_result = await db.execute(download_query)
        download_status_map = {row[0]: row[1] for row in download_result.all()}

    # 批量查询原始分类名称（从 pt_categories 表关联取出）
    category_name_map = {}  # key: (site_id, original_category_id) -> name_chs
    site_category_pairs = {
        (r.site_id, r.original_category_id) for r in resources if r.original_category_id
    }
    if site_category_pairs:
        # 构建 OR 条件查询所有需要的分类
        category_conditions = [
            and_(PTCategory.site_id == site_id, PTCategory.category_id == cat_id)
            for site_id, cat_id in site_category_pairs
        ]
        from sqlalchemy import or_
        category_query = select(PTCategory).where(or_(*category_conditions))
        category_result = await db.execute(category_query)
        for cat in category_result.scalars().all():
            category_name_map[(cat.site_id, cat.category_id)] = cat.name_chs

    # 构建响应数据
    items = []
    for idx, resource in enumerate(resources):
        # 从字典中获取映射关系
        mapping = mappings_dict.get(resource.id)

        # 构建响应对象
        response_item = PTResourceResponse.model_validate(resource)

        # 调试：检查 site 关系
        if idx == 0:  # 只记录第一条
            print(f"DEBUG - resource.site: {resource.site}")
            print(f"DEBUG - resource.site.name: {resource.site.name if resource.site else 'None'}")
            print(f"DEBUG - hasattr(resource, 'site'): {hasattr(resource, 'site')}")

        # 手动设置额外字段（这些字段在ORM对象中不存在）
        response_item.has_mapping = mapping is not None
        response_item.mapping_id = mapping.id if mapping else None
        response_item.media_type = mapping.media_type if mapping else None
        response_item.site_name = resource.site.name if resource.site else None

        # 从 pt_categories 表关联取出原始分类名称
        response_item.original_category_name = category_name_map.get(
            (resource.site_id, resource.original_category_id)
        )

        # 添加下载状态
        response_item.is_downloaded = resource.id in download_status_map
        response_item.download_status = download_status_map.get(resource.id)

        # 调试：检查设置后的值
        if idx == 0:
            print(f"DEBUG - response_item.site_name after setting: {response_item.site_name}")
            print(f"DEBUG - response_item dict keys: {list(response_item.__dict__.keys())}")

        # 获取统一资源ID（多态关联）
        if mapping:
            response_item.unified_resource_id = mapping.unified_resource_id

        items.append(response_item)

    # 构建响应列表
    response_list = PTResourceList(
        total=total, page=filter_params.page, page_size=filter_params.page_size, items=items
    )

    # 调试：检查序列化结果
    result = response_list.model_dump(by_alias=True)
    if result.get("items") and len(result["items"]) > 0:
        first_item = result["items"][0]
        print(f"DEBUG - First item has siteName: {'siteName' in first_item}")
        print(f"DEBUG - First item siteName value: {first_item.get('siteName', 'NOT_FOUND')}")
        print(f"DEBUG - First item all keys: {list(first_item.keys())[:15]}")
        print("=" * 80)

    return result


@router.get("/{resource_id}", summary="获取资源详情", response_model=PTResourceResponse)
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取指定资源的详细信息"""
    resource = await PTResourceService.get_by_id(db, resource_id)

    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")

    return PTResourceResponse(
        **{
            **resource.__dict__,
            "size_gb": resource.size_gb,
            "size_human_readable": resource.size_human_readable,
            "is_promotional": resource.is_promotional,
        }
    )


@router.post("/{resource_id}/fetch-detail", summary="获取资源完整详情")
async def fetch_resource_detail(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    按需获取资源的完整详情

    该接口会调用PT站点的detail API获取：
    - IMDB/豆瓣评分
    - 完整描述（BB代码）
    - MediaInfo信息
    - 原始种子文件名
    - 图片列表

    注意：
    - 每次调用会向PT站点发起一次API请求
    - 已获取过的资源会直接返回缓存数据
    - 建议只在用户真正需要时调用（如点击查看详情）
    """
    try:
        resource = await PTResourceService.fetch_resource_detail(db, resource_id)

        return PTResourceResponse(
            **{
                **resource.__dict__,
                "size_gb": resource.size_gb,
                "size_human_readable": resource.size_human_readable,
                "is_promotional": resource.is_promotional,
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取详情失败: {str(e)}",
        )


@router.post("/{resource_id}/fetch-douban", summary="获取豆瓣详细信息")
async def fetch_douban_info(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    按需获取豆瓣详细信息

    该接口会调用站点的豆瓣API获取：
    - 导演、演员列表（带头像、IMDB ID）
    - 完整电影简介
    - 类型、国家、语言、时长
    - 别名列表
    - 格式化描述（BB代码）
    - 上映日期

    前提条件：
    - 资源必须有豆瓣ID（douban_id）

    注意：
    - 每次调用会向PT站点发起一次API请求
    - 已获取过的资源会直接返回缓存数据
    - 建议在需要完整影视信息时调用（如生成NFO、展示演员表）
    """
    try:
        resource = await PTResourceService.fetch_douban_info(db, resource_id)

        return PTResourceResponse(
            **{
                **resource.__dict__,
                "size_gb": resource.size_gb,
                "size_human_readable": resource.size_human_readable,
                "is_promotional": resource.is_promotional,
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取豆瓣信息失败: {str(e)}",
        )


@router.delete("/{resource_id}", summary="删除资源")
async def delete_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """删除资源（软删除）"""
    success = await PTResourceService.delete_resource(db, resource_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源不存在")

    return success_response(message="资源已删除")


@router.post("/sites/{site_id}/sync", summary="同步站点资源", response_model=SyncResponse)
async def sync_site_resources(
    site_id: int,
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    同步站点资源

    同步类型：
    - full: 完全同步
    - incremental: 增量同步
    - manual: 手动同步

    参数：
    - force: 强制同步（忽略上次同步时间）
    - max_pages: 限制最大页数
    - start_page: 起始页
    - mode: 资源模式（normal/adult）
    - categories: 分类列表
    - upload_date_start: 上传开始时间
    - upload_date_end: 上传结束时间
    - keyword: 关键字搜索

    注意：
    - 只会调用search接口，不会调用detail接口
    - detail信息需要通过 POST /pt-resources/{resource_id}/fetch-detail 按需获取
    """
    # 同步任务直接执行
    # TODO: 后续使用Celery实现后台执行
    try:
        # 构建过滤参数
        filters = {}
        if sync_request.mode:
            filters["mode"] = sync_request.mode
        if sync_request.categories:
            filters["categories"] = sync_request.categories
        if sync_request.upload_date_start:
            filters["upload_date_start"] = sync_request.upload_date_start
        if sync_request.upload_date_end:
            filters["upload_date_end"] = sync_request.upload_date_end
        if sync_request.keyword:
            filters["keyword"] = sync_request.keyword

        sync_log = await PTResourceService.sync_site_resources(
            db=db,
            site_id=site_id,
            sync_type=sync_request.sync_type,
            max_pages=sync_request.max_pages,
            start_page=sync_request.start_page,
            filters=filters if filters else None,
        )

        return SyncResponse(
            sync_log_id=sync_log.id, message="同步完成", status=sync_log.status
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"同步失败: {str(e)}"
        )


@router.get("/sites/{site_id}/sync-logs", summary="获取同步日志", response_model=SyncLogList)
async def get_sync_logs(
    site_id: int,
    filter_params: SyncLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取指定站点的同步日志"""
    filter_params.site_id = site_id

    # TODO: 实现SyncLogService.get_list方法
    # 目前返回空列表
    return SyncLogList(
        total=0,
        page=filter_params.page,
        page_size=filter_params.page_size,
        items=[],
    )


@router.get("/sync-logs", summary="获取所有同步日志", response_model=SyncLogList)
async def get_all_sync_logs(
    filter_params: SyncLogFilter = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取所有站点的同步日志"""
    # TODO: 实现SyncLogService.get_list方法
    # 目前返回空列表
    return SyncLogList(
        total=0,
        page=filter_params.page,
        page_size=filter_params.page_size,
        items=[],
    )


@router.post("/batch-reset-identification-status", summary="批量重置识别状态")
async def batch_reset_identification_status(
    resource_ids: List[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    批量重置PT资源的识别状态为'未识别'

    将选中资源的 identification_status 从 'failed' 重置为 'unidentified'，
    使其重新进入待识别队列

    Args:
        resource_ids: 资源ID列表
    """
    from app.models.pt_resource import PTResource
    from app.constants import IDENTIFICATION_STATUS_UNIDENTIFIED
    from sqlalchemy import update

    if not resource_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resource_ids 不能为空"
        )

    # 更新状态
    await db.execute(
        update(PTResource)
        .where(PTResource.id.in_(resource_ids))
        .values(identification_status=IDENTIFICATION_STATUS_UNIDENTIFIED)
    )
    await db.commit()

    logger.info(f"Batch reset identification status for {len(resource_ids)} resources: {resource_ids}")

    return success_response(
        message=f"成功重置 {len(resource_ids)} 个资源的识别状态",
        data={"count": len(resource_ids)}
    )
