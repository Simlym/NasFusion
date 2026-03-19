# -*- coding: utf-8 -*-
"""
元数据标准化工具
"""
from typing import Optional


class MetadataNormalizer:
    """元数据标准化工具类"""

    # known_for_department 标准化映射表
    # 将 TMDB 英文值与豆瓣中文值统一映射为中文标准值
    # 标准值: 演员、导演、编剧、制片人、摄影、剪辑、音乐、美术、
    #          服装、特效、配音、副导演、制片管理、动作特技、动画、其他
    DEPARTMENT_MAP = {
        # --- TMDB 英文 → 中文标准值 ---
        "Acting": "演员",
        "Directing": "导演",
        "Writing": "编剧",
        "Production": "制片人",
        "Camera": "摄影",
        "Editing": "剪辑",
        "Sound": "音乐",
        "Art": "美术",
        "Costume & Make-Up": "服装",
        "Visual Effects": "特效",
        "Crew": "其他",
        "Lighting": "灯光",
        "Creator": "创作者",

        # --- 豆瓣/中文变体 → 中文标准值 ---
        "演员": "演员",
        "配音": "配音",
        "导演": "导演",
        "编剧": "编剧",
        "作者": "编剧",
        "制片人": "制片人",
        "出品人": "制片人",
        "制片": "制片人",
        "主持人": "主持人",
        "摄影": "摄影",
        "剪辑": "剪辑",
        "特效": "特效",
        "美术": "美术",
        "服装": "服装",
        "化妆": "化妆",
        "音乐": "音乐",
        "副导演": "副导演",
        "制片管理": "制片管理",
        "动作特技": "动作特技",
        "动画": "动画",
        "歌手": "歌手",
        "舞蹈": "舞蹈",
        "其他": "其他",
    }

    # ISO 3166-1 Alpha-2 国家/地区代码转换表
    COUNTRY_MAP = {
        "US": "美国", "USA": "美国", "United States of America": "美国",
        "GB": "英国", "UK": "英国", "United Kingdom": "英国",
        "CN": "中国大陆", "China": "中国大陆",
        "HK": "中国香港", "Hong Kong": "中国香港",
        "TW": "中国台湾", "Taiwan": "中国台湾",
        "JP": "日本", "Japan": "日本",
        "KR": "韩国", "South Korea": "韩国", "KP": "朝鲜",
        "DE": "德国", "Germany": "德国",
        "FR": "法国", "France": "法国",
        "IT": "意大利", "Italy": "意大利",
        "ES": "西班牙", "Spain": "西班牙",
        "RU": "俄罗斯", "Russia": "俄罗斯",
        "IN": "印度", "India": "印度",
        "CA": "加拿大", "Canada": "加拿大",
        "AU": "澳大利亚", "Australia": "澳大利亚",
        "NZ": "新西兰", "New Zealand": "新西兰",
        "BR": "巴西", "Brazil": "巴西",
        "MX": "墨西哥", "Mexico": "墨西哥",
        "AR": "阿根廷", "Argentina": "阿根廷",
        "TH": "泰国", "Thailand": "泰国",
        "VN": "越南", "Vietnam": "越南",
        "ID": "印度尼西亚", "Indonesia": "印度尼西亚",
        "SG": "新加坡", "Singapore": "新加坡",
        "MY": "马来西亚", "Malaysia": "马来西亚",
        "PH": "菲律宾", "Philippines": "菲律宾",
        "TR": "土耳其", "Turkey": "土耳其",
        "IR": "伊朗", "Iran": "伊朗",
        "IL": "以色列", "Israel": "以色列",
        "SE": "瑞典", "Sweden": "瑞典",
        "NO": "挪威", "Norway": "挪威",
        "DK": "丹麦", "Denmark": "丹麦",
        "FI": "芬兰", "Finland": "芬兰",
        "NL": "荷兰", "Netherlands": "荷兰",
        "BE": "比利时", "Belgium": "比利时",
        "CH": "瑞士", "Switzerland": "瑞士",
        "AT": "奥地利", "Austria": "奥地利",
        "PL": "波兰", "Poland": "波兰",
        "CZ": "捷克", "Czech Republic": "捷克",
        "HU": "匈牙利", "Hungary": "匈牙利",
        "IE": "爱尔兰", "Ireland": "爱尔兰",
        "PT": "葡萄牙", "Portugal": "葡萄牙",
        "GR": "希腊", "Greece": "希腊",
        "ZA": "南非", "South Africa": "南非",
        "EG": "埃及", "Egypt": "埃及",
        "RO": "罗马尼亚", "Romania": "罗马尼亚",
        "SA": "沙特阿拉伯", "Saudi Arabia": "沙特阿拉伯",
        "AE": "阿联酋", "United Arab Emirates": "阿联酋",
    }

    # 中国省份/直辖市/自治区英文名→中文名
    CHINA_PROVINCE_MAP = {
        "Beijing": "北京", "Peking": "北京",
        "Shanghai": "上海",
        "Tianjin": "天津",
        "Chongqing": "重庆",
        "Guangdong": "广东", "Kwangtung": "广东",
        "Fujian": "福建",
        "Zhejiang": "浙江",
        "Jiangsu": "江苏",
        "Shandong": "山东",
        "Henan": "河南",
        "Hebei": "河北",
        "Hubei": "湖北",
        "Hunan": "湖南",
        "Sichuan": "四川", "Szechuan": "四川",
        "Yunnan": "云南",
        "Guizhou": "贵州",
        "Shanxi": "山西",
        "Shaanxi": "陕西",
        "Gansu": "甘肃",
        "Qinghai": "青海",
        "Xinjiang": "新疆",
        "Tibet": "西藏", "Xizang": "西藏",
        "Inner Mongolia": "内蒙古",
        "Ningxia": "宁夏",
        "Guangxi": "广西",
        "Hainan": "海南",
        "Jilin": "吉林",
        "Liaoning": "辽宁",
        "Heilongjiang": "黑龙江",
        "Anhui": "安徽",
        "Jiangxi": "江西",
    }

    # 中国主要城市英文名→中文名
    CHINA_CITY_MAP = {
        "Beijing": "北京", "Peking": "北京",
        "Shanghai": "上海",
        "Guangzhou": "广州", "Canton": "广州",
        "Shenzhen": "深圳",
        "Chengdu": "成都",
        "Wuhan": "武汉",
        "Nanjing": "南京",
        "Xi'an": "西安", "Xian": "西安",
        "Hangzhou": "杭州",
        "Tianjin": "天津",
        "Chongqing": "重庆",
        "Suzhou": "苏州",
        "Qingdao": "青岛",
        "Zhengzhou": "郑州",
        "Changsha": "长沙",
        "Harbin": "哈尔滨",
        "Kunming": "昆明",
        "Dalian": "大连",
        "Xiamen": "厦门",
        "Jinan": "济南",
        "Hefei": "合肥",
        "Wuxi": "无锡",
        "Fuzhou": "福州",
        "Zhongshan": "中山",
        "Dongguan": "东莞",
        "Nanchang": "南昌",
        "Changchun": "长春",
        "Lanzhou": "兰州",
        "Nanning": "南宁",
        "Guiyang": "贵阳",
        "Taiyuan": "太原",
        "Shenyang": "沈阳",
        "Ningbo": "宁波",
        "Wuhu": "芜湖",
        "Wenzhou": "温州",
        "Urumqi": "乌鲁木齐",
        "Lhasa": "拉萨",
        "Shijiazhuang": "石家庄",
        "Nantong": "南通",
        "Changzhou": "常州",
        "Yantai": "烟台",
        "Zibo": "淄博",
        "Tangshan": "唐山",
        "Baotou": "包头",
        "Foshan": "佛山",
        "Shaoxing": "绍兴",
        "Jiaxing": "嘉兴",
        "Weifang": "潍坊",
        "Linyi": "临沂",
        "Zhuhai": "珠海",
        "Huizhou": "惠州",
        "Mianyang": "绵阳",
        "Luoyang": "洛阳",
        "Yancheng": "盐城",
        "Nanchong": "南充",
        "Taizhou": "台州",
        "Guilin": "桂林",
        "Zhuzhou": "株洲",
        "Yueyang": "岳阳",
        "Xiangtan": "湘潭",
        "Daqing": "大庆",
        "Mudanjiang": "牡丹江",
        "Haikou": "海口",
        "Sanya": "三亚",
        "Zhenjiang": "镇江",
        "Huaian": "淮安", "Huaiyin": "淮安",
        "Xuzhou": "徐州",
        "Liuzhou": "柳州",
        "Xining": "西宁",
        "Hohhot": "呼和浩特",
        "Yinchuan": "银川",
        "Taipei": "台北", "Taibei": "台北",
        "Kaohsiung": "高雄",
        "Taichung": "台中",
    }

    # ISO 639-1 语言代码转换表
    LANGUAGE_MAP = {
        "en": "英语", "English": "英语",
        "zh": "汉语普通话", "cn": "汉语普通话", "Mandarin": "汉语普通话", "普通话": "汉语普通话",
        "zh-CN": "汉语普通话", "zh-TW": "国语", "zh-HK": "粤语",
        "yue": "粤语", "Cantonese": "粤语", "广州话 / 廣州話": "粤语",
        "ja": "日语", "Japanese": "日语", '日本語': "日语",
        "ko": "韩语", "Korean": "韩语", '한국어/조선말': "韩语",
        "fr": "法语", "French": "法语", 'Français': "法语",
        "de": "德语", "German": "德语", 'Deutsch': "德语",
        "it": "意大利语", "Italian": "意大利语", 'Italiano': "意大利语",
        "es": "西班牙语", "Spanish": "西班牙语", 'Español': "西班牙语",
        "ru": "俄语", "Russian": "俄语", "Pусский": "俄语",
        "pt": "葡萄牙语", "Portuguese": "葡萄牙语", 'Português': "葡萄牙语",
        "hi": "印地语", "Hindi": "印地语",
        "th": "泰语", "Thai": "泰语",
        "vi": "越南语", "Vietnamese": "越南语", 'Tiếng Việt': "越南语",
        "id": "印尼语", "Indonesian": "印尼语",
        "ms": "马来语", "Malay": "马来语", "Bahasa melayu": "马来语",
        "ar": "阿拉伯语", "Arabic": "阿拉伯语", 'العربية': "阿拉伯语",
        "tr": "土耳其语", "Turkish": "土耳其语", "Türkçe": "土耳其语",
        "fa": "波斯语", "Persian": "波斯语", "Farsi": "波斯语",
        "he": "希伯来语", "Hebrew": "希伯来语", "עִבְרִית": "希伯来语",
        "sv": "瑞典语", "Swedish": "瑞典语", "svenska": "瑞典语",
        "no": "挪威语", "Norwegian": "挪威语", "Norsk": "挪威语",
        "da": "丹麦语", "Danish": "丹麦语", "Dansk": "丹麦语",
        "fi": "芬兰语", "Finnish": "芬兰语",
        "nl": "荷兰语", "Dutch": "荷兰语", "Nederlands": "荷兰语",
        "pl": "波兰语", "Polish": "波兰语", "Polski": "波兰语",
        "cs": "捷克语", "Czech": "捷克语",
        "hu": "匈牙利语", "Hungarian": "匈牙利语",
        "el": "希腊语", "Greek": "希腊语",
        "la": "拉丁语", "Latin": "拉丁语",
        "uk": "乌克兰语", "Ukrainian": "乌克兰语",
        "ro": "罗马尼亚语", "Romanian": "罗马尼亚语", 'Română': "罗马尼亚语",
    }

    @classmethod
    def normalize_country(cls, code_or_name: Optional[str]) -> Optional[str]:
        """
        标准化国家/地区名称

        Args:
            code_or_name: 国家代码或名称 (ISO 3166-1 alpha-2, alpha-3, or English name)

        Returns:
            中文名称，如果未匹配到则返回原值
        """
        if not code_or_name:
            return None
        
        # 尝试直接匹配
        if code_or_name in cls.COUNTRY_MAP:
            return cls.COUNTRY_MAP[code_or_name]
        
        # 尝试不区分大小写匹配（虽然字典键是规范的，但防止意外）
        # 对于大数据量可能效率略低，但这里数据量小
        # 暂时只做直接查找，如果需要可以扩展
            
        return code_or_name

    @classmethod
    def normalize_department(cls, value: Optional[str]) -> Optional[str]:
        """
        标准化 known_for_department 字段

        Args:
            value: TMDB 英文值（如 "Acting"）或豆瓣中文值（如 "演员"）

        Returns:
            中文标准值，如果未匹配到则返回原值
        """
        if not value:
            return None
        # 先去除首尾空格
        value = value.strip()
        return cls.DEPARTMENT_MAP.get(value, value)

    @classmethod
    def normalize_language(cls, code_or_name: Optional[str]) -> Optional[str]:
        """
        标准化语言名称

        Args:
            code_or_name: 语言代码或名称 (ISO 639-1 or English name)

        Returns:
            中文名称，如果未匹配到则返回原值
        """
        if not code_or_name:
            return None

        if code_or_name in cls.LANGUAGE_MAP:
            return cls.LANGUAGE_MAP[code_or_name]

        return code_or_name

    @classmethod
    def normalize_place_of_birth(cls, place: Optional[str]) -> Optional[str]:
        """
        将出生地英文描述转换为中文。

        TMDB 的 place_of_birth 字段无论 language 参数如何始终返回英文，
        此方法将其转换为中文格式。

        Examples:
            "Wuhu, Anhui, China" → "中国安徽芜湖"
            "Beijing, China" → "中国北京"
            "Hong Kong, China" → "中国香港"
            "Los Angeles, California, USA" → "洛杉矶, 加利福尼亚, 美国"
        """
        if not place:
            return None

        place = place.strip()

        # 已包含中文字符，直接返回
        if any('\u4e00' <= c <= '\u9fff' for c in place):
            return place

        # 香港
        if "Hong Kong" in place or "Hongkong" in place:
            return "中国香港"

        # 澳门
        if "Macau" in place or "Macao" in place:
            return "中国澳门"

        # 台湾（单独出现，不在"China"语境中再判断）
        if "Taiwan" in place and "China" not in place:
            return "中国台湾"

        # 中国大陆
        if "China" in place:
            if "Hong Kong" in place:
                return "中国香港"
            if "Taiwan" in place:
                return "中国台湾"
            if "Macau" in place or "Macao" in place:
                return "中国澳门"

            parts = [p.strip() for p in place.split(",")]
            # 去掉 "China" / "People's Republic of China" 等国名部分
            non_country_parts = [
                p for p in parts
                if p not in ("China", "People's Republic of China", "PRC")
            ]

            translated = []
            for part in non_country_parts:
                if part in cls.CHINA_PROVINCE_MAP:
                    translated.append(cls.CHINA_PROVINCE_MAP[part])
                elif part in cls.CHINA_CITY_MAP:
                    translated.append(cls.CHINA_CITY_MAP[part])
                else:
                    translated.append(part)

            return "中国" + "".join(translated) if translated else "中国"

        # 其他国家：翻译国名，城市/州保留原文
        parts = [p.strip() for p in place.split(",")]
        if not parts:
            return place

        country_en = parts[-1]
        country_zh = cls.normalize_country(country_en)
        if country_zh != country_en:
            # 成功翻译了国家名，其余部分保持英文
            city_parts = parts[:-1]
            if city_parts:
                return ", ".join(city_parts) + ", " + country_zh
            return country_zh

        return place
