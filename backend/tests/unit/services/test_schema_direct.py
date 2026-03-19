# -*- coding: utf-8 -*-
"""
直接测试Schema的camelCase支持
"""
import json
import sys
from app.schemas.subscription import SubscriptionCreateSchema

# 模拟前端发送的完整数据
frontend_data = {
    "mediaType": "tv",
    "unifiedTvId": 1,
    "title": "勿扰飞升",
    "originalTitle": "",
    "year": 2025,
    "posterUrl": "https://img1.doubanio.com/view/photo/m_ratio_poster/public/p2927195150.webp",
    "tmdbId": None,
    "imdbId": None,
    "doubanId": "35896172",
    "source": "manual",
    "subscriptionType": "tv_season",
    "currentSeason": 1,
    "startEpisode": 1,
    "rules": {
        "qualityPriority": ["2160p", "1080p"],
        "qualityMode": "first_match",
        "sitePriority": [],
        "promotionRequired": [],
        "minSeeders": 0
    },
    "checkStrategy": "normal",
    "completeCondition": "first_match",
    "autoCompleteOnDownload": False,
    "notifyOnMatch": True,
    "notifyOnDownload": True,
    "autoDownload": False,
    "isFavorite": False,
    "userPriority": 5
}

print("=" * 60)
print("Testing SubscriptionCreateSchema with camelCase input")
print("=" * 60)

try:
    # 测试1: 直接实例化
    print("\n[Test 1] Direct instantiation:")
    obj1 = SubscriptionCreateSchema(**frontend_data)
    print(f"[OK] Success - media_type: {obj1.media_type}, unified_tv_id: {obj1.unified_tv_id}")
except Exception as e:
    print(f"[FAIL] Failed: {e}")
    sys.exit(1)

try:
    # 测试2: model_validate (FastAPI使用的方法)
    print("\n[Test 2] model_validate (FastAPI method):")
    obj2 = SubscriptionCreateSchema.model_validate(frontend_data)
    print(f"[OK] Success - media_type: {obj2.media_type}, unified_tv_id: {obj2.unified_tv_id}")
except Exception as e:
    print(f"[FAIL] Failed: {e}")
    sys.exit(1)

try:
    # 测试3: 从JSON解析
    print("\n[Test 3] Parse from JSON string:")
    json_str = json.dumps(frontend_data)
    obj3 = SubscriptionCreateSchema.model_validate_json(json_str)
    print(f"[OK] Success - media_type: {obj3.media_type}, unified_tv_id: {obj3.unified_tv_id}")
except Exception as e:
    print(f"[FAIL] Failed: {e}")
    sys.exit(1)

# 测试4: 检查model_config
print("\n[Test 4] Check model_config:")
config = SubscriptionCreateSchema.model_config
print(f"  populate_by_name: {config.get('populate_by_name')}")
print(f"  alias_generator: {config.get('alias_generator')}")
print(f"  from_attributes: {config.get('from_attributes')}")

# 测试5: 检查字段别名
print("\n[Test 5] Check field aliases:")
for field_name, field_info in SubscriptionCreateSchema.model_fields.items():
    if field_info.alias:
        print(f"  {field_name} -> alias: {field_info.alias}")

print("\n" + "=" * 60)
print("All tests passed!")
print("=" * 60)
