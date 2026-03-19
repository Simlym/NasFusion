#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Jellyfin 增强功能
"""
import sys
sys.path.insert(0, '.')

def test_path_mapping():
    """测试路径映射功能"""
    import os
    from app.utils.path_mapping import apply_path_mappings, normalize_path

    print("=" * 50)
    print("测试路径映射功能")
    print("=" * 50)

    # 测试1: 基本路径映射
    mappings = [{'server_path': '/media', 'local_path': 'D:/media'}]
    result = apply_path_mappings('/media/Movies/test.mkv', mappings)
    # 使用 os.path.normpath 来比较路径（忽略分隔符差异）
    expected = os.path.normpath('D:/media/Movies/test.mkv')
    assert os.path.normpath(result) == expected, f"Expected {expected}, got {result}"
    print(f"[PASS] 测试1通过: /media/Movies/test.mkv -> {result}")

    # 测试2: Windows 路径标准化
    test_path = r'D:\media\Movies'
    normalized = normalize_path(test_path)
    assert normalized == 'D:/media/Movies', f"Expected D:/media/Movies, got {normalized}"
    print(f"[PASS] 测试2通过: {test_path} -> {normalized}")

    # 测试3: 移除末尾斜杠
    test_path = '/media/Movies/'
    normalized = normalize_path(test_path)
    assert normalized == '/media/Movies', f"Expected /media/Movies, got {normalized}"
    print(f"[PASS] 测试3通过: {test_path} -> {normalized}")

    # 测试4: 多条映射规则
    mappings = [
        {'server_path': '/mnt/data', 'local_path': 'E:/data'},
        {'server_path': '/media', 'local_path': 'D:/media'}
    ]
    result = apply_path_mappings('/mnt/data/TV Shows/test.mkv', mappings)
    expected = os.path.normpath('E:/data/TV Shows/test.mkv')
    assert os.path.normpath(result) == expected, f"Expected {expected}, got {result}"
    print(f"[PASS] 测试4通过: /mnt/data/TV Shows/test.mkv -> {result}")

    print("\n[PASS] 路径映射测试全部通过!\n")


def test_constants():
    """测试任务常量"""
    from app.constants.task import (
        TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH,
        TASK_TYPES,
        TASK_TYPE_DISPLAY_NAMES
    )

    print("=" * 50)
    print("测试任务常量")
    print("=" * 50)

    # 测试常量定义
    assert TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH == 'media_server_batch_rematch'
    print(f"[PASS] 任务类型: {TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH}")

    # 测试常量在列表中
    assert TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH in TASK_TYPES
    print(f"[PASS] 已注册到 TASK_TYPES 列表")

    # 测试显示名称
    assert TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH in TASK_TYPE_DISPLAY_NAMES
    display_name = TASK_TYPE_DISPLAY_NAMES[TASK_TYPE_MEDIA_SERVER_BATCH_REMATCH]
    print(f"[PASS] 显示名称: {display_name}")

    print("\n[PASS] 任务常量测试全部通过!\n")


def test_handler_registration():
    """测试处理器注册"""
    from app.tasks.handlers import MediaServerBatchRematchHandler
    from app.tasks.base import BaseTaskHandler

    print("=" * 50)
    print("测试处理器注册")
    print("=" * 50)

    # 测试处理器类存在
    assert MediaServerBatchRematchHandler is not None
    print(f"[PASS] MediaServerBatchRematchHandler 类已定义")

    # 测试继承自 BaseTaskHandler
    assert issubclass(MediaServerBatchRematchHandler, BaseTaskHandler)
    print(f"[PASS] 继承自 BaseTaskHandler")

    # 测试有 execute 方法
    assert hasattr(MediaServerBatchRematchHandler, 'execute')
    print(f"[PASS] 包含 execute 方法")

    print("\n[PASS] 处理器注册测试全部通过!\n")


if __name__ == '__main__':
    try:
        test_path_mapping()
        test_constants()

        # 注意：test_handler_registration() 需要完整的环境配置（数据库、SECRET_KEY等）
        # 在开发环境中运行后端服务时会自动加载这些配置
        print("=" * 50)
        print("跳过处理器注册测试（需要完整环境配置）")
        print("=" * 50)
        print("提示：在运行后端服务时，处理器会自动注册和加载")
        print("")

        print("=" * 50)
        print("[SUCCESS] 核心功能测试通过!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n[FAILED] 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 测试错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
