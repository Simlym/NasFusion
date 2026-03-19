# -*- coding: utf-8 -*-
"""
电视剧标题解析工具
用于从PT资源标题中提取季度和集数信息
"""
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def extract_tv_info(title: str, subtitle: str = "") -> Optional[Dict]:
    """
    从标题和副标题中提取电视剧季度和集数信息

    支持的格式：
    - S01E12: 单集
    - S01E01-E10 或 S01E01-10: 集数范围
    - S01: 整季包
    - S01-S05: 多季包
    - Breaking Bad S01-S05 Complete: 完整系列

    Args:
        title: PT资源标题
        subtitle: PT资源副标题（可选，用于提取总集数）

    Returns:
        {
            'seasons': [1, 2, 3],           # 包含的季度列表
            'episodes': {                   # 每季的集数信息
                '1': {'start': 1, 'end': 10},
                '2': {'start': 1, 'end': 13}
            },
            'is_complete_season': bool,     # 是否整季包
            'is_complete_series': bool,     # 是否完整系列
            'total_episodes': int           # 总集数（如果能提取）
        }
        如果不是电视剧格式，返回None
    """
    result = {
        'seasons': [],
        'episodes': {},
        'is_complete_season': False,
        'is_complete_series': False,
        'total_episodes': None,
    }

    # 1. 提取多季范围：S01-S05 或 S01-05
    multi_season_match = re.search(r'S(\d{1,2})[-~]S?(\d{1,2})', title, re.IGNORECASE)
    if multi_season_match:
        start_season = int(multi_season_match.group(1))
        end_season = int(multi_season_match.group(2))
        result['seasons'] = list(range(start_season, end_season + 1))
        result['is_complete_series'] = True
        result['is_complete_season'] = True

        # 检查是否标注"Complete"
        if re.search(r'\bcomplete\b', title, re.IGNORECASE):
            result['is_complete_series'] = True

        logger.debug(f"检测到多季包: S{start_season:02d}-S{end_season:02d}")
        return result

    # 2. 提取集数范围（必须在单集之前匹配）
    # 支持格式：S01E01-E10, S01E01-10, S01E01-S01E07
    episode_range_match = re.search(
        r'S(\d{1,2})E(\d{1,4})[-~](?:S\d{1,2})?E?(\d{1,4})',
        title,
        re.IGNORECASE
    )
    if episode_range_match:
        season = int(episode_range_match.group(1))
        start_ep = int(episode_range_match.group(2))
        end_ep = int(episode_range_match.group(3))
        result['seasons'] = [season]
        result['episodes'][str(season)] = {'start': start_ep, 'end': end_ep}
        result['total_episodes'] = end_ep - start_ep + 1

        # 判断是否为整季包：
        # 对于明确集数范围（如 S02E01-E10），我们无法确定该季总集数，
        # 不能单凭 start_ep==1 就判定为整季包（第1集开始不代表包含全季）。
        # 只有副标题明确标注"全X集"且与资源集数范围吻合时，才判定为整季包。
        is_complete = False
        if subtitle:
            total_ep_match = re.search(r'全\s*(\d+)\s*集', subtitle)
            if total_ep_match:
                total_in_subtitle = int(total_ep_match.group(1))
                # 副标题总集数与资源集数范围吻合，且起始集为1
                if start_ep == 1 and end_ep == total_in_subtitle:
                    is_complete = True

        result['is_complete_season'] = is_complete

        logger.debug(
            f"检测到集数范围: S{season:02d}E{start_ep:02d}-E{end_ep:02d}, "
            f"整季包: {is_complete}"
        )
        return result

    # 3. 提取单集：S01E12
    single_episode_match = re.search(r'S(\d{1,2})E(\d{1,4})', title, re.IGNORECASE)
    if single_episode_match:
        season = int(single_episode_match.group(1))
        episode = int(single_episode_match.group(2))
        result['seasons'] = [season]
        result['episodes'][str(season)] = {'start': episode, 'end': episode}
        result['is_complete_season'] = False

        logger.debug(f"检测到单集: S{season:02d}E{episode:02d}")
        return result

    # 4. 提取整季包或单集（标题只有S03）
    season_only_match = re.search(r'S(\d{1,2})(?![E\d])', title, re.IGNORECASE)
    if season_only_match:
        season = int(season_only_match.group(1))
        result['seasons'] = [season]

        # 优先从副标题提取集数信息
        single_episode_num = None
        total_episodes_num = None
        subtitle_range_start = None
        subtitle_range_end = None

        if subtitle:
            # 检查副标题是否有"第X-Y集"或"第X集-第Y集"（集数范围）
            # 支持格式：第25-76集、第1集-第10集、第25~76集、第25至76集
            range_ep_match = re.search(r'第\s*(\d+)\s*[-~至]\s*(\d+)\s*集', subtitle)
            if range_ep_match:
                subtitle_range_start = int(range_ep_match.group(1))
                subtitle_range_end = int(range_ep_match.group(2))
                logger.debug(f"从副标题提取集数范围: 第{subtitle_range_start}-{subtitle_range_end}集")

            # 检查副标题是否有"第X集"（单集标记）
            if not subtitle_range_start:
                single_ep_match = re.search(r'第\s*(\d+)\s*集', subtitle)
                if single_ep_match:
                    single_episode_num = int(single_ep_match.group(1))
                    logger.debug(f"从副标题提取单集信息: 第{single_episode_num}集")

            # 检查副标题是否有"全X集"（整季标记）
            if not subtitle_range_start and not single_episode_num:
                total_ep_match = re.search(r'全\s*(\d+)\s*集', subtitle)
                if total_ep_match:
                    total_episodes_num = int(total_ep_match.group(1))
                    logger.debug(f"从副标题提取总集数: {total_episodes_num}集")

        # 如果副标题有集数范围（第X-Y集）
        if subtitle_range_start and subtitle_range_end:
            result['episodes'][str(season)] = {'start': subtitle_range_start, 'end': subtitle_range_end}
            result['total_episodes'] = subtitle_range_end - subtitle_range_start + 1
            # 判断是否为整季包：起始集必须是1
            result['is_complete_season'] = (subtitle_range_start == 1)
            logger.debug(
                f"检测到集数范围（标题S{season:02d}+副标题第{subtitle_range_start}-{subtitle_range_end}集），"
                f"整季包: {result['is_complete_season']}"
            )
        # 如果副标题明确是单集
        elif single_episode_num:
            result['episodes'][str(season)] = {'start': single_episode_num, 'end': single_episode_num}
            result['is_complete_season'] = False
            logger.debug(f"检测到单集（标题S{season:02d}+副标题第{single_episode_num}集）")
        # 如果副标题明确是整季包（全X集）
        elif total_episodes_num:
            result['episodes'][str(season)] = {'start': 1, 'end': total_episodes_num}
            result['is_complete_season'] = True
            result['total_episodes'] = total_episodes_num
            logger.debug(f"检测到整季包: S{season:02d}（全{total_episodes_num}集）")
        # 否则假定为整季包（但集数不确定）
        else:
            result['episodes'][str(season)] = {'start': 1, 'end': None}
            result['is_complete_season'] = True
            logger.debug(f"检测到整季包: S{season:02d}（集数不确定）")

        return result

    # 如果没有匹配任何模式，返回None
    logger.debug(f"未检测到电视剧格式: {title}")
    return None


def get_primary_season(tv_info: Dict) -> Optional[int]:
    """
    获取主要季度（用于单季资源）

    Args:
        tv_info: extract_tv_info() 返回的结果

    Returns:
        主要季度编号，如果是多季返回第一季
    """
    if not tv_info or not tv_info.get('seasons'):
        return None

    seasons = tv_info['seasons']
    return seasons[0] if seasons else None


def get_episode_range(tv_info: Dict, season: int) -> Optional[Dict[str, int]]:
    """
    获取指定季度的集数范围

    Args:
        tv_info: extract_tv_info() 返回的结果
        season: 季度编号

    Returns:
        {'start': 1, 'end': 10} 或 None
    """
    if not tv_info or not tv_info.get('episodes'):
        return None

    return tv_info['episodes'].get(str(season))


def is_season_complete(tv_info: Dict) -> bool:
    """
    判断是否为整季包

    Args:
        tv_info: extract_tv_info() 返回的结果

    Returns:
        是否为整季包
    """
    if not tv_info:
        return False

    return tv_info.get('is_complete_season', False)


def extract_absolute_episode(tv_info: Dict) -> Optional[int]:
    """
    从tv_info中提取绝对集数（用于连续动画的集数匹配）

    对于连续动画（如仙逆），集数通常是绝对集数而非季内集数。
    例如：S01E123 表示第123集，而非第1季第123集。

    Args:
        tv_info: extract_tv_info() 返回的结果

    Returns:
        绝对集数，如果无法提取返回None
    """
    if not tv_info:
        return None

    episodes = tv_info.get('episodes', {})
    if not episodes:
        return None

    # 获取第一个季度的集数信息
    for season_num, ep_info in episodes.items():
        if ep_info:
            start_ep = ep_info.get('start')
            end_ep = ep_info.get('end')

            # 如果是单集，返回集数
            if start_ep is not None and (end_ep is None or start_ep == end_ep):
                return start_ep

            # 如果是集数范围，返回起始集数（用于判断是否在订阅范围内）
            if start_ep is not None:
                return start_ep

    return None


def extract_absolute_episode_range(tv_info: Dict) -> Optional[Dict[str, int]]:
    """
    从tv_info中提取绝对集数范围

    Args:
        tv_info: extract_tv_info() 返回的结果

    Returns:
        {'start': 起始集数, 'end': 结束集数}，单集时start==end
    """
    if not tv_info:
        return None

    episodes = tv_info.get('episodes', {})
    if not episodes:
        return None

    # 获取第一个季度的集数信息
    for season_num, ep_info in episodes.items():
        if ep_info and ep_info.get('start') is not None:
            start_ep = ep_info.get('start')
            end_ep = ep_info.get('end') or start_ep
            return {'start': start_ep, 'end': end_ep}

    return None


def match_absolute_episode(
    tv_info: Dict,
    subscription_start: int,
    subscription_end: Optional[int] = None
) -> bool:
    """
    判断PT资源是否匹配订阅的绝对集数范围

    用于连续动画（年番）的匹配，不区分季度，只看集数。

    Args:
        tv_info: PT资源的电视剧信息
        subscription_start: 订阅的起始集数
        subscription_end: 订阅的结束集数（None表示持续追更，匹配所有>=start的集数）

    Returns:
        是否匹配订阅要求

    匹配逻辑：
    - 单集资源：集数 >= subscription_start 且 <= subscription_end（如果有）
    - 整季包/范围资源：资源的集数范围与订阅范围有交集
    """
    if not tv_info:
        return False

    ep_range = extract_absolute_episode_range(tv_info)
    if not ep_range:
        return False

    resource_start = ep_range['start']
    resource_end = ep_range['end']

    # 订阅结束集数，None表示无限大
    sub_end = subscription_end if subscription_end else float('inf')

    # 检查是否有交集
    # 资源范围 [resource_start, resource_end]
    # 订阅范围 [subscription_start, sub_end]
    # 有交集的条件：resource_start <= sub_end 且 resource_end >= subscription_start

    if resource_start > sub_end:
        # 资源起始集数超过订阅结束集数
        logger.debug(f"集数不匹配: 资源起始{resource_start} > 订阅结束{sub_end}")
        return False

    if resource_end < subscription_start:
        # 资源结束集数小于订阅起始集数
        logger.debug(f"集数不匹配: 资源结束{resource_end} < 订阅起始{subscription_start}")
        return False

    logger.debug(
        f"绝对集数匹配成功: 资源[{resource_start}-{resource_end}] "
        f"与订阅[{subscription_start}-{subscription_end or '∞'}]有交集"
    )
    return True


def match_subscription_season(
    tv_info: Dict,
    subscription_season: int,
    subscription_start_episode: int = 1
) -> bool:
    """
    判断PT资源是否匹配订阅的季度和集数要求

    Args:
        tv_info: PT资源的电视剧信息
        subscription_season: 订阅的季度
        subscription_start_episode: 订阅的起始集数

    Returns:
        是否匹配订阅要求
    """
    if not tv_info:
        return False

    # 检查季度是否匹配
    if subscription_season not in tv_info.get('seasons', []):
        return False

    # 获取该季度的集数信息
    episode_info = tv_info.get('episodes', {}).get(str(subscription_season))
    if not episode_info:
        return False

    # 如果是整季包
    if tv_info.get('is_complete_season'):
        # 整季包的起始集数必须 <= 订阅起始集数
        # 例如：订阅从E05开始，整季包E01-E10可以匹配（包含E05）
        start_ep = episode_info.get('start', 1)
        end_ep = episode_info.get('end')

        # 如果没有结束集数信息，无法判断是否包含订阅集数，拒绝匹配
        if end_ep is None:
            return False

        if start_ep > subscription_start_episode:
            return False

        # 检查是否包含订阅起始集数
        if end_ep < subscription_start_episode:
            return False

        return True

    # 如果是单集
    else:
        episode_num = episode_info.get('start')
        if episode_num is None:
            return False

        # 单集编号必须 >= 订阅起始集数
        return episode_num >= subscription_start_episode


# 测试用例
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.DEBUG)

    test_cases = [
        # (标题, 副标题, 预期结果描述)
        ("Why is He Still Single S01E12 1080p TX WEB-DL AAC2.0 H.264-MWeb", "", "单集"),
        ("Renegade Immortal 2023 S01E116 2160p WEB-DL H.265 AAC 2.0-HHWEB", "", "三位数单集"),
        ("Anime Series S01E240 1080p", "", "大集数单集"),
        ("Renegade Immortal 2024 S01 2160p WEB-DL HEVC AAC 2.0-StarfallWEB", "仙逆 年番1 / 仙逆 第25-76集 / 仙逆 第二季", "副标题集数范围"),
        ("Some Show S02 1080p", "第10集", "副标题单集"),
        ("Envious S03 2160p NF WEB-DL HDR H.265 DDP5.1-ADWeb", "羡慕嫉妒恨 第3季 Envidiosa Temporada 3 全10集 | 类型: 剧情", "整季包带集数"),
        ("Game of Thrones S08E01-E06 1080p BluRay x265", "", "集数范围"),
        ("Long Series S01E100-E200 1080p", "", "大集数范围"),
        ("Breaking Bad S01-S05 Complete 1080p BluRay x264", "", "完整系列"),
        ("The Office S02 720p WEB-DL", "", "整季包无集数"),
        ("Inception 2010 1080p BluRay", "", "非电视剧"),
    ]

    print("=" * 80)
    print("电视剧标题解析测试")
    print("=" * 80)

    for title, subtitle, description in test_cases:
        print(f"\n标题: {title}")
        if subtitle:
            print(f"副标题: {subtitle}")
        print(f"场景: {description}")

        result = extract_tv_info(title, subtitle)
        if result:
            print(f"[SUCCESS] 解析成功:")
            print(f"   季度: {result['seasons']}")
            print(f"   集数信息: {result['episodes']}")
            print(f"   整季包: {result['is_complete_season']}")
            print(f"   完整系列: {result['is_complete_series']}")
            if result['total_episodes']:
                print(f"   总集数: {result['total_episodes']}")

            # 测试匹配逻辑
            if result['seasons']:
                primary_season = result['seasons'][0]
                print(f"\n   匹配测试（订阅S{primary_season:02d}从E05开始）:")
                matches = match_subscription_season(result, primary_season, 5)
                print(f"   匹配结果: {'[MATCH]' if matches else '[NO MATCH]'}")
        else:
            print(f"[INFO] 非电视剧格式")

        print("-" * 80)
