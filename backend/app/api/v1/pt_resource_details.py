# -*- coding: utf-8 -*-
"""
PT资源详情API（通用接口，支持成人/音乐/电子书等媒体类型）
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.core.database import get_db
from app.models.pt_resource import PTResource
from app.models.pt_resource_detail import PTResourceDetail
from app.schemas.pt_resource_detail import (
    PTResourceDetailListResponse,
    PTResourceDetailItemResponse,
    PTResourceDetailItemBase,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/pt-resource-details", response_model=PTResourceDetailListResponse)
async def get_pt_resource_details(
    category: Optional[str] = Query(None, description="媒体分类：adult/music/ebook 等"),
    site_id: Optional[int] = Query(None, description="PT站点ID"),
    original_category_id: Optional[str] = Query(None, description="原始分类ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取 PT 资源列表（通用接口，支持多种媒体类型）

    过滤条件：
    - category: 媒体分类（可选，如 adult/music/ebook）
    - site_id: PT站点ID（可选）
    - original_category_id: 原始分类ID（可选）
    - 按 published_at 倒序
    """
    try:
        # 计算偏移量
        skip = (page - 1) * page_size

        # 构建查询条件
        filters = []
        if category:
            filters.append(PTResource.category == category)
        if site_id:
            filters.append(PTResource.site_id == site_id)
        if original_category_id:
            filters.append(PTResource.original_category_id == original_category_id)

        # 查询总数
        count_query = select(func.count()).select_from(PTResource)
        if filters:
            count_query = count_query.where(*filters)
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        # 查询资源列表
        query = select(PTResource)
        if filters:
            query = query.where(*filters)
        query = (
            query
            .order_by(desc(PTResource.published_at))
            .offset(skip)
            .limit(page_size)
        )
        result = await db.execute(query)
        resources = result.scalars().all()

        # 转换为响应格式
        items = []
        for resource in resources:
            # 提取图片列表
            image_list = []
            if resource.raw_page_json:
                image_list = resource.raw_page_json.get("imageList", [])
            elif resource.image_list:
                image_list = resource.image_list

            # 主海报（第一张图片）
            poster_url = image_list[0] if image_list else None

            items.append(
                PTResourceDetailItemBase(
                    id=resource.id,
                    title=resource.title,
                    subtitle=resource.subtitle,
                    poster_url=poster_url,
                    image_list=image_list,
                    published_at=resource.published_at,
                    size_bytes=resource.size_bytes,
                    seeders=resource.seeders,
                    leechers=resource.leechers,
                    is_free=resource.is_free,
                    promotion_type=resource.promotion_type,
                    detail_url=resource.detail_url,
                    download_url=resource.download_url,
                )
            )

        return PTResourceDetailListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error fetching PT resource details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pt-resource-details/{resource_id}", response_model=PTResourceDetailItemResponse)
async def get_pt_resource_detail(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取 PT 资源详情

    返回 PT 资源基础信息 + 详情数据（如果已加载）
    """
    try:
        # 查询 PT 资源
        resource = await db.get(PTResource, resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="Resource not found")

        # 提取图片列表
        image_list = []
        if resource.raw_page_json:
            image_list = resource.raw_page_json.get("imageList", [])
        elif resource.image_list:
            image_list = resource.image_list

        poster_url = image_list[0] if image_list else None

        # 查询详情
        detail = await db.execute(
            select(PTResourceDetail).where(
                PTResourceDetail.pt_resource_id == resource_id
            )
        )
        detail_obj = detail.scalar_one_or_none()

        # 构建响应
        response = PTResourceDetailItemResponse(
            id=resource.id,
            title=resource.title,
            subtitle=resource.subtitle,
            poster_url=poster_url,
            image_list=image_list,
            published_at=resource.published_at,
            size_bytes=resource.size_bytes,
            seeders=resource.seeders,
            leechers=resource.leechers,
            is_free=resource.is_free,
            promotion_type=resource.promotion_type,
            detail_url=resource.detail_url,
            download_url=resource.download_url,
            detail_loaded=detail_obj.detail_loaded if detail_obj else False,
            description=detail_obj.description if detail_obj else None,
            mediainfo=detail_obj.mediainfo if detail_obj else None,
        )

        # 添加 DMM 信息（成人资源专用）
        if detail_obj and detail_obj.dmm_product_number:
            response.dmm_info = {
                "productNumber": detail_obj.dmm_product_number,
                "actressList": detail_obj.dmm_actress_list,
                "keywordList": detail_obj.dmm_keyword_list,
                "director": detail_obj.dmm_director,
                "series": detail_obj.dmm_series,
                "maker": detail_obj.dmm_maker,
                "label": detail_obj.dmm_label,
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching PT resource detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pt-resource-details/{resource_id}/fetch-detail")
async def fetch_pt_resource_detail(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取资源详情（调用 MTeam API）

    适用于成人/音乐/电子书等需要详细信息的媒体类型

    Returns:
      {
        "detail_id": 123,
        "message": "详情获取成功"
      }
    """
    try:
        from app.services.pt.pt_resource_detail_service import PTResourceDetailService

        detail = await PTResourceDetailService.fetch_and_save_detail(db, resource_id)
        return {
            "detail_id": detail.id,
            "message": "详情获取成功"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching PT resource detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
