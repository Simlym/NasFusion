"""
IP 地理位置解析工具

提供两种方式解析 IP 地址的地理位置:
1. 离线数据库: 使用 ip2region（轻量级、无需外部依赖，推荐）
2. 在线 API 回退: 使用免费 API 作为备选方案

使用方法:
    from app.utils.ip_location import get_ip_location
    location = await get_ip_location("1.2.3.4")  # 返回 "中国|上海|上海"
"""
import ipaddress
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 内网/保留 IP 段
_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


def is_private_ip(ip: str) -> bool:
    """判断是否为内网/保留 IP"""
    try:
        addr = ipaddress.ip_address(ip)
        return any(addr in network for network in _PRIVATE_NETWORKS)
    except ValueError:
        return False


async def _query_ip_api(ip: str) -> Optional[str]:
    """使用 ip-api.com 免费 API 查询 IP 地理位置"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,city", "lang": "zh-CN"},
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    parts = [
                        data.get("country", ""),
                        data.get("regionName", ""),
                        data.get("city", ""),
                    ]
                    # 去重并过滤空值（例如 "中国|北京|北京" -> "中国|北京"）
                    seen = set()
                    unique_parts = []
                    for part in parts:
                        if part and part not in seen:
                            seen.add(part)
                            unique_parts.append(part)
                    return "|".join(unique_parts) if unique_parts else None
    except Exception as e:
        logger.debug(f"ip-api.com 查询失败: {e}")
    return None


async def get_ip_location(ip: Optional[str]) -> Optional[str]:
    """
    获取 IP 地址的地理位置信息

    Args:
        ip: IP 地址字符串

    Returns:
        地理位置字符串（如 "中国|上海"），内网 IP 返回 "局域网"，无法解析返回 None
    """
    if not ip:
        return None

    # 去掉 IPv6 映射前缀
    if ip.startswith("::ffff:"):
        ip = ip[7:]

    # 内网 IP 直接返回
    if is_private_ip(ip):
        return "局域网"

    # 使用在线 API 查询
    location = await _query_ip_api(ip)
    if location:
        return location

    return None
