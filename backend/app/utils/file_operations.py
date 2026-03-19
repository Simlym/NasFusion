# -*- coding: utf-8 -*-
"""
文件操作工具模块
提供安全的文件移动、复制、硬链接等操作
"""
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional

from app.constants import (
    ORGANIZE_MODE_COPY,
    ORGANIZE_MODE_HARDLINK,
    ORGANIZE_MODE_MOVE,
    ORGANIZE_MODE_REFLINK,
    ORGANIZE_MODE_SYMLINK,
)


class FileOperationError(Exception):
    """文件操作异常"""

    pass


def ensure_dir(directory: str | Path) -> Path:
    """
    确保目录存在，不存在则创建

    Args:
        directory: 目录路径

    Returns:
        Path对象

    Raises:
        FileOperationError: 创建目录失败
    """
    dir_path = Path(directory)
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    except Exception as e:
        raise FileOperationError(f"创建目录失败: {directory}, 错误: {e}")


def calculate_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """
    计算文件哈希值

    Args:
        file_path: 文件路径
        algorithm: 哈希算法（sha256, md5等）

    Returns:
        哈希值字符串

    Raises:
        FileOperationError: 计算失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileOperationError(f"文件不存在: {file_path}")

    try:
        hash_obj = hashlib.new(algorithm)
        with open(path, "rb") as f:
            # 分块读取，避免大文件占用过多内存
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except Exception as e:
        raise FileOperationError(f"计算文件哈希失败: {file_path}, 错误: {e}")


def get_file_size(file_path: str | Path) -> int:
    """
    获取文件大小（字节）

    Args:
        file_path: 文件路径

    Returns:
        文件大小（字节）

    Raises:
        FileOperationError: 获取失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileOperationError(f"文件不存在: {file_path}")

    try:
        return path.stat().st_size
    except Exception as e:
        raise FileOperationError(f"获取文件大小失败: {file_path}, 错误: {e}")


def organize_file(
    source_path: str | Path,
    dest_path: str | Path,
    mode: str = ORGANIZE_MODE_HARDLINK,
    overwrite: bool = False,
) -> bool:
    """
    整理文件（移动/复制/硬链接/软链接/reflink）

    Args:
        source_path: 源文件路径
        dest_path: 目标文件路径
        mode: 整理模式（hardlink/reflink/symlink/move/copy）
        overwrite: 是否覆盖已存在的文件

    Returns:
        是否成功

    Raises:
        FileOperationError: 操作失败
    """
    import subprocess

    src = Path(source_path)
    dest = Path(dest_path)

    # 检查源文件
    if not src.exists():
        raise FileOperationError(f"源文件不存在: {source_path}")

    if not src.is_file():
        raise FileOperationError(f"源路径不是文件: {source_path}")

    # 检查目标文件
    if dest.exists():
        if not overwrite:
            raise FileOperationError(f"目标文件已存在: {dest_path}")
        try:
            dest.unlink()
        except Exception as e:
            raise FileOperationError(f"删除已存在的目标文件失败: {dest_path}, 错误: {e}")

    # 确保目标目录存在
    ensure_dir(dest.parent)

    try:
        if mode == ORGANIZE_MODE_HARDLINK:
            # 硬链接（推荐，节省空间且不影响做种）
            # 限制：必须在同一文件系统内
            os.link(src, dest)
        elif mode == ORGANIZE_MODE_REFLINK:
            # Reflink（CoW克隆，适用于Btrfs文件系统，可跨共享目录）
            # 使用 cp --reflink=always 命令实现
            result = subprocess.run(
                ["cp", "--reflink=always", str(src), str(dest)],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise FileOperationError(
                    f"Reflink失败: {result.stderr.strip()}。"
                    "请确认文件系统支持reflink（如Btrfs），或改用其他整理模式"
                )
        elif mode == ORGANIZE_MODE_SYMLINK:
            # 软链接（符号链接）
            os.symlink(src, dest)
        elif mode == ORGANIZE_MODE_MOVE:
            # 移动文件
            shutil.move(str(src), str(dest))
        elif mode == ORGANIZE_MODE_COPY:
            # 复制文件
            shutil.copy2(str(src), str(dest))
        else:
            raise FileOperationError(f"不支持的整理模式: {mode}")

        return True
    except FileOperationError:
        raise
    except OSError as e:
        # 提供更友好的错误信息
        if e.errno == 18:
            raise FileOperationError(
                f"跨文件系统无法创建硬链接: {source_path} -> {dest_path}。"
                "请使用reflink（Btrfs）、软链接或复制模式"
            )
        raise FileOperationError(f"文件整理失败: {source_path} -> {dest_path}, 模式: {mode}, 错误: {e}")
    except Exception as e:
        raise FileOperationError(f"文件整理失败: {source_path} -> {dest_path}, 模式: {mode}, 错误: {e}")


def remove_file(file_path: str | Path, force: bool = False) -> bool:
    """
    删除文件

    Args:
        file_path: 文件路径
        force: 是否强制删除（忽略错误）

    Returns:
        是否成功

    Raises:
        FileOperationError: 删除失败（force=False时）
    """
    path = Path(file_path)

    if not path.exists():
        if force:
            return True
        raise FileOperationError(f"文件不存在: {file_path}")

    try:
        path.unlink()
        return True
    except Exception as e:
        if force:
            return False
        raise FileOperationError(f"删除文件失败: {file_path}, 错误: {e}")


def is_video_file(file_path: str | Path) -> bool:
    """
    判断是否为视频文件（根据扩展名）

    Args:
        file_path: 文件路径

    Returns:
        是否为视频文件
    """
    from app.constants import VIDEO_EXTENSIONS

    ext = Path(file_path).suffix.lower()
    return ext in VIDEO_EXTENSIONS


def is_subtitle_file(file_path: str | Path) -> bool:
    """
    判断是否为字幕文件（根据扩展名）

    Args:
        file_path: 文件路径

    Returns:
        是否为字幕文件
    """
    from app.constants import SUBTITLE_EXTENSIONS

    ext = Path(file_path).suffix.lower()
    return ext in SUBTITLE_EXTENSIONS


def is_audio_file(file_path: str | Path) -> bool:
    """
    判断是否为音频文件（根据扩展名）

    Args:
        file_path: 文件路径

    Returns:
        是否为音频文件
    """
    from app.constants import AUDIO_EXTENSIONS

    ext = Path(file_path).suffix.lower()
    return ext in AUDIO_EXTENSIONS


def get_file_type(file_path: str | Path) -> str:
    """
    获取文件类型

    Args:
        file_path: 文件路径

    Returns:
        文件类型：video/audio/subtitle/other
    """
    from app.constants import FILE_TYPE_AUDIO, FILE_TYPE_OTHER, FILE_TYPE_SUBTITLE, FILE_TYPE_VIDEO

    if is_video_file(file_path):
        return FILE_TYPE_VIDEO
    elif is_audio_file(file_path):
        return FILE_TYPE_AUDIO
    elif is_subtitle_file(file_path):
        return FILE_TYPE_SUBTITLE
    else:
        return FILE_TYPE_OTHER


def sanitize_filename(filename: str, replacement: str = "_") -> str:
    """
    清理文件名中的非法字符

    Args:
        filename: 原始文件名
        replacement: 替换字符

    Returns:
        清理后的文件名
    """
    # Windows和Linux共同的非法字符
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']

    result = filename
    for char in illegal_chars:
        result = result.replace(char, replacement)

    # 移除前后空格和点
    result = result.strip('. ')

    return result


def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的字符串（如 "1.23 GB"）
    """
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} EB"


# ==================== 蓝光原盘处理 ====================

# 蓝光原盘标识目录
BLURAY_MARKERS = ["BDMV", "CERTIFICATE"]


def is_bluray_directory(dir_path: str | Path) -> bool:
    """
    判断是否为蓝光原盘目录

    蓝光原盘特征：
    - 包含 BDMV 目录（必须）
    - 可能包含 CERTIFICATE 目录

    Args:
        dir_path: 目录路径

    Returns:
        是否为蓝光原盘目录
    """
    path = Path(dir_path)
    if not path.is_dir():
        return False

    # BDMV 目录是必须的，CERTIFICATE 是可选的
    bdmv_path = path / "BDMV"
    return bdmv_path.exists() and bdmv_path.is_dir()


def organize_directory(
    source_dir: str | Path,
    dest_dir: str | Path,
    mode: str = ORGANIZE_MODE_HARDLINK,
    overwrite: bool = False,
) -> bool:
    """
    整理整个目录（递归处理所有文件）

    适用于蓝光原盘等需要保持完整目录结构的场景。
    保持原始目录结构，对每个文件创建硬链接/软链接/复制。

    Args:
        source_dir: 源目录路径
        dest_dir: 目标目录路径
        mode: 整理模式（hardlink/reflink/symlink/move/copy）
        overwrite: 是否覆盖已存在的文件

    Returns:
        是否成功

    Raises:
        FileOperationError: 操作失败
    """
    import subprocess

    src = Path(source_dir)
    dest = Path(dest_dir)

    # 检查源目录
    if not src.exists():
        raise FileOperationError(f"源目录不存在: {source_dir}")

    if not src.is_dir():
        raise FileOperationError(f"源路径不是目录: {source_dir}")

    # 检查目标目录
    if dest.exists():
        if not overwrite:
            raise FileOperationError(f"目标目录已存在: {dest_dir}")

    try:
        # 遍历源目录中的所有文件和子目录
        for item in src.rglob("*"):
            rel_path = item.relative_to(src)
            target = dest / rel_path

            if item.is_dir():
                # 创建目录结构
                target.mkdir(parents=True, exist_ok=True)
            else:
                # 确保目标目录存在
                target.parent.mkdir(parents=True, exist_ok=True)

                # 检查目标文件是否存在
                if target.exists():
                    if not overwrite:
                        continue  # 跳过已存在的文件
                    target.unlink()

                # 根据模式处理文件
                if mode == ORGANIZE_MODE_HARDLINK:
                    os.link(str(item), str(target))
                elif mode == ORGANIZE_MODE_REFLINK:
                    result = subprocess.run(
                        ["cp", "--reflink=always", str(item), str(target)],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode != 0:
                        raise FileOperationError(
                            f"Reflink失败: {result.stderr.strip()}"
                        )
                elif mode == ORGANIZE_MODE_SYMLINK:
                    os.symlink(item, target)
                elif mode == ORGANIZE_MODE_MOVE:
                    shutil.move(str(item), str(target))
                elif mode == ORGANIZE_MODE_COPY:
                    shutil.copy2(str(item), str(target))
                else:
                    raise FileOperationError(f"不支持的整理模式: {mode}")

        # 如果是移动模式，删除源目录
        if mode == ORGANIZE_MODE_MOVE:
            shutil.rmtree(str(src))

        return True

    except FileOperationError:
        raise
    except OSError as e:
        if e.errno == 18:
            raise FileOperationError(
                f"跨文件系统无法创建硬链接: {source_dir} -> {dest_dir}。"
                "请使用reflink（Btrfs）、软链接或复制模式"
            )
        raise FileOperationError(f"目录整理失败: {source_dir} -> {dest_dir}, 模式: {mode}, 错误: {e}")
    except Exception as e:
        raise FileOperationError(f"目录整理失败: {source_dir} -> {dest_dir}, 模式: {mode}, 错误: {e}")


# ==================== 附属文件处理 ====================

# 预览视频关键词
SAMPLE_KEYWORDS = ["sample", "trailer", "preview", "预告"]


def is_sample_file(file_path: str | Path) -> bool:
    """
    判断是否为预览/样本视频

    Args:
        file_path: 文件路径

    Returns:
        是否为预览视频
    """
    name = Path(file_path).stem.lower()
    return any(keyword in name for keyword in SAMPLE_KEYWORDS)


def find_associated_files(
    video_path: str | Path,
    include_subtitles: bool = True,
    include_samples: bool = False,
    include_nfo: bool = False,
    same_directory_only: bool = True,
) -> dict[str, list[Path]]:
    """
    查找视频文件的附属文件（字幕、预览、NFO等）

    查找规则：
    1. 与视频同名的字幕文件（如 movie.mkv -> movie.srt, movie.chs.srt）
    2. 同目录下的字幕文件夹（Subs/Subtitles）中的字幕
    3. 同目录下的预览视频（含 sample/trailer 关键词）
    4. NFO 文件

    Args:
        video_path: 视频文件路径
        include_subtitles: 是否包含字幕文件
        include_samples: 是否包含预览视频
        include_nfo: 是否包含 NFO 文件
        same_directory_only: 是否只搜索同目录

    Returns:
        分类的附属文件字典 {
            "subtitles": [Path, ...],
            "samples": [Path, ...],
            "nfo": [Path, ...],
            "other": [Path, ...]
        }
    """
    from app.constants import SUBTITLE_EXTENSIONS, VIDEO_EXTENSIONS

    video = Path(video_path)
    if not video.exists():
        raise FileOperationError(f"视频文件不存在: {video_path}")

    result = {
        "subtitles": [],
        "samples": [],
        "nfo": [],
        "other": [],
    }

    video_dir = video.parent
    video_stem = video.stem  # 不含扩展名的文件名

    # 搜索范围
    search_dirs = [video_dir]

    # 常见的字幕目录
    subtitle_subdirs = ["Subs", "Subtitles", "Sub", "字幕"]
    for subdir in subtitle_subdirs:
        sub_path = video_dir / subdir
        if sub_path.exists() and sub_path.is_dir():
            search_dirs.append(sub_path)

    for search_dir in search_dirs:
        try:
            for item in search_dir.iterdir():
                if not item.is_file():
                    continue

                item_ext = item.suffix.lower()
                item_stem = item.stem.lower()

                # 字幕文件
                if include_subtitles and item_ext in SUBTITLE_EXTENSIONS:
                    # 检查是否与视频文件关联
                    # 支持 movie.srt, movie.chs.srt, movie.zh-CN.srt 等
                    if item_stem.startswith(video_stem.lower()):
                        result["subtitles"].append(item)

                # 预览视频
                elif include_samples and item_ext in VIDEO_EXTENSIONS:
                    if is_sample_file(item) and item != video:
                        result["samples"].append(item)

                # NFO 文件
                elif include_nfo and item_ext == ".nfo":
                    if item_stem.startswith(video_stem.lower()) or item_stem == video_stem.lower():
                        result["nfo"].append(item)

        except PermissionError:
            continue

    return result


def organize_with_associated_files(
    video_path: str | Path,
    dest_dir: str | Path,
    dest_filename_base: str,
    mode: str = ORGANIZE_MODE_HARDLINK,
    include_subtitles: bool = True,
    include_samples: bool = False,
    overwrite: bool = False,
) -> dict[str, list[str]]:
    """
    整理视频文件及其附属文件

    Args:
        video_path: 视频文件路径
        dest_dir: 目标目录
        dest_filename_base: 目标文件名（不含扩展名）
        mode: 整理模式
        include_subtitles: 是否整理字幕
        include_samples: 是否整理预览视频
        overwrite: 是否覆盖

    Returns:
        整理结果 {
            "video": "目标视频路径",
            "subtitles": ["字幕路径1", ...],
            "samples": ["预览路径1", ...],
            "errors": ["错误信息", ...]
        }
    """
    video = Path(video_path)
    dest = Path(dest_dir)

    result = {
        "video": "",
        "subtitles": [],
        "samples": [],
        "errors": [],
    }

    # 确保目标目录存在
    ensure_dir(dest)

    # 1. 整理主视频文件
    video_dest = dest / f"{dest_filename_base}{video.suffix}"
    try:
        organize_file(video, video_dest, mode, overwrite)
        result["video"] = str(video_dest)
    except FileOperationError as e:
        result["errors"].append(f"视频整理失败: {e}")
        return result  # 视频失败则中止

    # 2. 查找并整理附属文件
    associated = find_associated_files(
        video,
        include_subtitles=include_subtitles,
        include_samples=include_samples,
    )

    # 整理字幕
    for subtitle in associated["subtitles"]:
        # 保持字幕的语言后缀，如 .chs.srt, .zh-CN.srt
        sub_suffix = subtitle.name[len(video.stem):]  # 获取视频名之后的部分
        sub_dest = dest / f"{dest_filename_base}{sub_suffix}"
        try:
            organize_file(subtitle, sub_dest, mode, overwrite)
            result["subtitles"].append(str(sub_dest))
        except FileOperationError as e:
            result["errors"].append(f"字幕整理失败 {subtitle.name}: {e}")

    # 整理预览视频
    for sample in associated["samples"]:
        sample_dest = dest / sample.name  # 保持原名
        try:
            organize_file(sample, sample_dest, mode, overwrite)
            result["samples"].append(str(sample_dest))
        except FileOperationError as e:
            result["errors"].append(f"预览整理失败 {sample.name}: {e}")

    return result


def find_files_in_directory(
    directory: str | Path,
    extensions: Optional[list[str]] = None,
    recursive: bool = True,
) -> list[Path]:
    """
    在目录中查找文件

    Args:
        directory: 目录路径
        extensions: 文件扩展名列表（如 ['.mkv', '.mp4']），None表示所有文件
        recursive: 是否递归查找子目录

    Returns:
        文件路径列表

    Raises:
        FileOperationError: 目录不存在或不可访问
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileOperationError(f"目录不存在: {directory}")

    if not dir_path.is_dir():
        raise FileOperationError(f"路径不是目录: {directory}")

    try:
        pattern = "**/*" if recursive else "*"
        all_files = dir_path.glob(pattern)

        if extensions:
            # 转换为小写以进行不区分大小写的比较
            extensions_lower = [ext.lower() for ext in extensions]
            return [f for f in all_files if f.is_file() and f.suffix.lower() in extensions_lower]
        else:
            return [f for f in all_files if f.is_file()]
    except Exception as e:
        raise FileOperationError(f"查找文件失败: {directory}, 错误: {e}")
