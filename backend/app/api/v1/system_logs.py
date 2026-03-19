# -*- coding: utf-8 -*-
"""
系统日志API
"""
import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.dependencies import get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/system-logs", tags=["系统日志"])


class LogEntry(BaseModel):
    """日志条目"""

    line_number: int = Field(..., description="行号")
    timestamp: Optional[str] = Field(None, description="时间戳")
    level: Optional[str] = Field(None, description="日志级别")
    logger: Optional[str] = Field(None, description="Logger名称")
    message: str = Field(..., description="日志消息")
    raw: str = Field(..., description="原始日志行")


class LogListResponse(BaseModel):
    """日志列表响应"""

    items: List[LogEntry]
    total: int = Field(..., description="总日志行数")
    page: int
    page_size: int
    total_pages: int


def parse_log_line(line: str, line_number: int) -> LogEntry:
    """
    解析日志行（兼容 JSON 和 TEXT 格式）

    Args:
        line: 日志行内容
        line_number: 行号

    Returns:
        LogEntry: 解析后的日志条目
    """
    line = line.strip()
    if not line:
        return LogEntry(
            line_number=line_number,
            message="",
            raw=line,
        )

    # 尝试解析为 JSON 格式
    if line.startswith("{"):
        try:
            log_data = json.loads(line)
            return LogEntry(
                line_number=line_number,
                timestamp=log_data.get("timestamp"),
                level=log_data.get("level"),
                logger=log_data.get("name"),
                message=log_data.get("message", ""),
                raw=line,
            )
        except json.JSONDecodeError:
            pass

    # TEXT 格式解析（格式：2025-12-18 10:30:00 - logger_name - LEVEL - message）
    parts = line.split(" - ", 3)
    if len(parts) >= 4:
        return LogEntry(
            line_number=line_number,
            timestamp=parts[0].strip(),
            logger=parts[1].strip(),
            level=parts[2].strip(),
            message=parts[3].strip(),
            raw=line,
        )
    elif len(parts) >= 3:
        return LogEntry(
            line_number=line_number,
            timestamp=parts[0].strip(),
            level=parts[1].strip(),
            message=parts[2].strip(),
            raw=line,
        )
    else:
        # 无法解析的格式，直接返回原始内容
        return LogEntry(
            line_number=line_number,
            message=line,
            raw=line,
        )


@router.get("", response_model=LogListResponse, summary="获取系统日志列表")
async def get_system_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=1000, description="每页数量"),
    level: Optional[str] = Query(None, description="日志级别过滤(INFO/WARNING/ERROR/DEBUG)"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    reverse: bool = Query(True, description="是否倒序（最新日志在前）"),
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取系统日志列表 (优化版 - 使用反向读取)
    """
    log_path = Path(settings.LOG_PATH)
    log_file = log_path / f"{settings.APP_NAME.lower()}.log"

    if not log_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日志文件不存在: {log_file}",
        )

    # 简单的倒序读取实现
    # 注意：完全分页（获取准确的总数）在大文件中是非常昂贵的
    # 这里我们采用一种折衷方案：
    # 1. 总是计算总行数（对于几十MB的日志文件，wc -l 速度还可以接受，如果特别大可能需要缓存）
    # 2. 读取时按需读取，不一次性加载所有内容
    
    try:
        # 获取文件总行数（简单优化：分块读取计数）
        total_lines = 0
        with open(log_file, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                total_lines += chunk.count(b'\n')
        
        # 如果文件非空且末尾没有换行符，行数+1（但这通常不影响）
        # 这里简化处理
        
        # 计算需要读取的范围
        # 如果是倒序：
        # total_lines = 1000, page = 1, page_size = 100
        # need lines: [901, 1000]
        # skip = 0
        
        # 优化策略：
        # 如果有过滤条件（level/keyword），我们必须扫描文件（或大部分文件）来找到匹配项
        # 如果没有过滤条件，且是倒序（默认情况），我们可以直接从文件末尾读取
        
        has_filter = bool(level or keyword)
        
        items = []
        result_total = total_lines
        
        if not has_filter and reverse:
            # 最优化路径：无过滤且倒序，直接从后往前读
            # 这里的 total就是文件总行数
            
            # 计算需要跳过的行数(从末尾开始数)
            skip_count = (page - 1) * page_size
            target_count = page_size
            
            matched_lines = []
            
            # 使用反向读取生成器
            line_gen = reverse_readline(log_file)
            
            # 跳过
            for _ in range(skip_count):
                try:
                    next(line_gen)
                except StopIteration:
                    break
            
            # 读取
            for _ in range(target_count):
                try:
                    line = next(line_gen)
                    # 修正行号：总行数 - skip - index
                    current_line_num = total_lines - skip_count - len(matched_lines)
                    matched_lines.append((current_line_num, line))
                except StopIteration:
                    break
            
            # 解析
            for line_num, line_content in matched_lines:
                try:
                    items.append(parse_log_line(line_content, line_num))
                except:
                    pass
                    
        else:
            # 慢速路径：需要过滤或正序
            # 为了避免内存爆炸，我们还是得流式读取，但无法利用文件偏移量跳过（因为不知道哪些行匹配）
            # 如果是倒序 + 过滤，我们仍然可以用 reverse_readline
            
            matching_lines = []
            
            # 读取方向
            if reverse:
                reader = reverse_readline(log_file)
                # 倒序时，起始行号是 total_lines
                current_line_num = total_lines
                step = -1
            else:
                reader = open(log_file, "r", encoding="utf-8")
                current_line_num = 1
                step = 1

            if not reverse:
                # 正序读取
                try:
                    with reader as f:
                        for line in f:
                            if check_filter(line, level, keyword):
                                matching_lines.append((current_line_num, line))
                            current_line_num += 1
                except Exception:
                    pass
            else:
                # 倒序读取
                try:
                    for line in reader:
                        if check_filter(line, level, keyword):
                            matching_lines.append((current_line_num, line))
                        current_line_num += step
                except StopIteration:
                    pass

            # 过滤后的总数
            result_total = len(matching_lines)
            
            # 内存分页
            start = (page - 1) * page_size
            end = start + page_size
            page_data = matching_lines[start:end]
            
            for line_num, line_content in page_data:
                try:
                    items.append(parse_log_line(line_content, line_num))
                except:
                    pass

        return LogListResponse(
            items=items,
            total=result_total,
            page=page,
            page_size=page_size,
            total_pages=(result_total + page_size - 1) // page_size if result_total > 0 else 0,
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取日志失败: {str(e)}",
        )


def check_filter(line: str, level: Optional[str], keyword: Optional[str]) -> bool:
    """检查行是否符合过滤条件"""
    if not line.strip():
        return False
    
    # 关键词过滤 (大小写不敏感)
    if keyword:
        if keyword.lower() not in line.lower():
            return False

    # 日志级别过滤 (精确匹配)
    if level:
        target_level = level.lower()
        line_stripped = line.strip()
        
        if line_stripped.startswith('{'):
            try:
                # JSON 格式，通过解析获取准确的 level
                # 简单的字符串匹配会导致误判 (例如 "env": "debug" 会匹配 level=DEBUG)
                log_data = json.loads(line_stripped)
                log_level = log_data.get('level', '').lower()
                if log_level != target_level:
                    return False
            except json.JSONDecodeError:
                # 如果 JSON 解析失败，回退到简单的字符串包含检查
                # 但为了减少误判，尝试匹配 "level": "value" 结构
                key_pattern = f'"level": "{target_level}"'
                key_pattern_s = f'"level":"{target_level}"'
                line_lower = line_stripped.lower()
                if key_pattern not in line_lower and key_pattern_s not in line_lower:
                     # 最后的兜底，只要包含这个词且不是 JSON 格式（解析失败），也许是文本混杂？
                     # 实际上如果 JSON 解析失败，它可能就是坏数据或者文本日志偶然以 { 开头
                     # 让我们保守一点，如果连 level 单词都不存在肯定不行
                     if target_level not in line_lower:
                        return False
        else:
            # 文本格式: date - logger - LEVEL - message
            # 检查 " - LEVEL - "
            # 或者简单的 " LEVEL "，但要有边界
            # 我们的 CustomJsonFormatter 在非 JSON 模式下格式是:
            # "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            if f' - {level.upper()} - ' not in line:
                return False
            
    return True


def reverse_readline(filename, buf_size=8192):
    """
    生成器：从文件末尾开始逐行读取
    """
    with open(filename, 'rb') as f:
        segment = None
        offset = 0
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        total_size = file_size
        remaining_size = file_size
        
        while remaining_size > 0:
            offset = min(total_size, offset + buf_size)
            f.seek(file_size - offset)
            buffer = f.read(min(remaining_size, buf_size))
            
            # 手动处理换行
            # 注意：这是二进制读取，需要 decode
            remaining_size -= buf_size
            
            # 拼接上一次的剩余部分
            lines = buffer.split(b'\n')
            
            # 如果这是第一块（文件末尾），最后一个元素可能是空（文件以换行结束）
            if segment is not None:
                # 这一块的最后一行 + 上一块的第一行
                lines[-1] += segment
            
            segment = lines[0]
            
            # 倒序 yield 除了第一个元素外的所有行（第一个元素是不完整的，留给下一块）
            for i in range(len(lines) - 1, 0, -1):
                line = lines[i]
                if line: # 跳过空行
                    yield line.decode('utf-8', errors='ignore')
                    
        # yield 剩余的最后一行（实际上是文件的第一行）
        if segment:
            yield segment.decode('utf-8', errors='ignore')


@router.get("/file-info", summary="获取日志文件信息")
async def get_log_file_info(
    current_user: User = Depends(get_current_admin_user),
):
    """获取日志文件的基本信息（大小、行数、最后修改时间）"""
    log_path = Path(settings.LOG_PATH)
    log_file = log_path / f"{settings.APP_NAME.lower()}.log"

    if not log_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日志文件不存在: {log_file}",
        )

    try:
        file_stat = os.stat(log_file)
        
        # 快速计算行数（不读入内存）
        line_count = 0
        with open(log_file, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                line_count += chunk.count(b'\n')

        return {
            "file_path": str(log_file),
            "file_size": file_stat.st_size,
            "file_size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "line_count": line_count,
            "last_modified": file_stat.st_mtime,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志文件信息失败: {str(e)}",
        )


@router.delete("", summary="清空系统日志")
async def clean_system_logs(
    current_user: User = Depends(get_current_admin_user),
):
    """
    清空系统日志文件
    """
    log_path = Path(settings.LOG_PATH)
    log_file = log_path / f"{settings.APP_NAME.lower()}.log"

    if not log_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"日志文件不存在: {log_file}",
        )

    try:
        # 清空文件内容
        with open(log_file, "w", encoding="utf-8") as f:
            f.truncate(0)

        return {"success": True, "message": "系统日志已清空"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空日志失败: {str(e)}",
        )


class LogLevelResponse(BaseModel):
    """日志级别响应"""

    config_level: str = Field(..., description="配置文件中的默认日志级别")
    runtime_level: str = Field(..., description="当前运行时日志级别")
    available_levels: List[str] = Field(..., description="可用的日志级别列表")


class LogLevelUpdate(BaseModel):
    """更新日志级别请求"""

    level: str = Field(..., description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")


@router.get("/level", response_model=LogLevelResponse, summary="获取日志级别信息")
async def get_log_level(
    current_user: User = Depends(get_current_admin_user),
):
    """
    获取日志级别信息
    包括配置文件默认级别和当前运行时级别
    """
    import logging

    # 配置文件中的默认级别
    config_level = settings.LOG_LEVEL

    # 当前运行时的级别
    runtime_level = logging.getLevelName(logging.getLogger().level)

    # 可用的日志级别列表
    available_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    return LogLevelResponse(
        config_level=config_level,
        runtime_level=runtime_level,
        available_levels=available_levels,
    )


@router.put("/level", summary="设置运行时日志级别")
async def set_log_level(
    request: LogLevelUpdate,
    current_user: User = Depends(get_current_admin_user),
):
    """
    设置运行时日志级别（临时生效，应用重启后恢复为配置文件设置）

    Args:
        request: 日志级别更新请求

    Returns:
        更新结果
    """
    import logging

    # 验证日志级别
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    level_upper = request.level.upper()

    if level_upper not in valid_levels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的日志级别: {request.level}，有效值为: {', '.join(valid_levels)}",
        )

    try:
        # 获取日志级别常量
        log_level = getattr(logging, level_upper)

        # 更新 root logger 级别
        logger = logging.getLogger()
        logger.setLevel(log_level)

        # 同时更新所有 handler 的级别
        for handler in logger.handlers:
            handler.setLevel(log_level)

        return {
            "success": True,
            "message": f"日志级别已设置为 {level_upper}",
            "config_level": settings.LOG_LEVEL,
            "runtime_level": level_upper,
            "note": "此设置在应用重启后将恢复为配置文件默认值",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"设置日志级别失败: {str(e)}",
        )
