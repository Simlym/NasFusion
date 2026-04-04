# -*- coding: utf-8 -*-
"""
MCP Prompts 提供者

预定义的提示词模板，供外部 MCP Client（如 Claude Desktop）使用。

这些 Prompt 封装了 NasFusion 的常见使用场景：
- 智能下载助手
- 媒体整理专家
- 订阅管理顾问
- PT 站点分析师
- 系统诊断专家
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPPromptProvider:
    """MCP 提示词提供者"""

    @classmethod
    def list_prompts(cls) -> List[Dict[str, str]]:
        """
        列出所有可用提示词
        
        Returns:
            提示词列表，每个包含 name, description
        """
        return [
            {
                "name": "smart_download_assistant",
                "description": "智能下载助手 - 帮助搜索、筛选和下载影视资源",
            },
            {
                "name": "media_organize_expert",
                "description": "媒体整理专家 - 协助整理媒体库文件和元数据",
            },
            {
                "name": "subscription_advisor",
                "description": "订阅管理顾问 - 管理追剧订阅和自动下载",
            },
            {
                "name": "pt_site_analyst",
                "description": "PT 站点分析师 - 分析 PT 站点数据和上传下载情况",
            },
            {
                "name": "system_diagnostic",
                "description": "系统诊断专家 - 诊断系统问题和优化建议",
            },
            {
                "name": "media_recommendation",
                "description": "影视推荐助手 - 根据喜好推荐电影和剧集",
            },
        ]

    @classmethod
    def get_prompt(cls, name: str, arguments: Optional[Dict] = None) -> Optional[Dict]:
        """
        获取提示词内容
        
        Args:
            name: 提示词名称
            arguments: 可选的参数
            
        Returns:
            提示词内容字典，包含 messages 列表
        """
        arguments = arguments or {}
        
        prompt_methods = {
            "smart_download_assistant": cls._smart_download_assistant,
            "media_organize_expert": cls._media_organize_expert,
            "subscription_advisor": cls._subscription_advisor,
            "pt_site_analyst": cls._pt_site_analyst,
            "system_diagnostic": cls._system_diagnostic,
            "media_recommendation": cls._media_recommendation,
        }
        
        method = prompt_methods.get(name)
        if not method:
            return None
            
        return method(arguments)

    @classmethod
    def _smart_download_assistant(cls, args: Dict) -> Dict:
        """智能下载助手"""
        media_name = args.get("media_name", "")
        media_type = args.get("media_type", "电影/剧集")
        
        system_prompt = """你是 NasFusion 的智能下载助手，专门帮助用户搜索、筛选和下载影视资源。

你的能力包括：
1. **资源搜索**：在 PT 站点搜索特定影视资源
2. **质量筛选**：根据用户偏好筛选最佳资源（清晰度、大小、字幕等）
3. **下载管理**：创建下载任务，监控下载进度
4. **智能推荐**：如果找不到精确匹配，推荐相似资源

使用工具时：
- 先使用 resource_search 搜索资源
- 根据搜索结果分析最佳选项
- 使用 download_create 创建下载任务
- 提供清晰的下载进度反馈

请用中文回复，保持友好专业的语气。"""

        messages = [{"role": "system", "content": system_prompt}]
        
        if media_name:
            messages.append({
                "role": "user",
                "content": f"我想下载 {media_type}《{media_name}》，请帮我搜索并选择合适的资源。"
            })
        else:
            messages.append({
                "role": "user",
                "content": "我想下载一些影视资源，请帮我搜索。"
            })
        
        return {
            "description": "智能下载助手 - 帮助搜索、筛选和下载影视资源",
            "messages": messages,
        }

    @classmethod
    def _media_organize_expert(cls, args: Dict) -> Dict:
        """媒体整理专家"""
        system_prompt = """你是 NasFusion 的媒体整理专家，专门协助用户整理媒体库文件和元数据。

你的能力包括：
1. **文件整理**：分析文件名，整理到正确的目录结构
2. **元数据刮削**：获取 TMDB、豆瓣等平台的影视信息
3. **重复检测**：找出重复的文件并建议处理方案
4. **命名规范**：将文件重命名为标准格式
5. **库优化**：分析媒体库结构，提出整理建议

使用工具时：
- 使用 media_query 查看当前媒体库状态
- 使用 resource_identify 识别未知文件
- 分析整理需求后制定整理计划

请用中文回复，提供清晰的整理步骤和建议。"""

        return {
            "description": "媒体整理专家 - 协助整理媒体库文件和元数据",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请帮我检查媒体库状态，看看有哪些需要整理的地方。"},
            ],
        }

    @classmethod
    def _subscription_advisor(cls, args: Dict) -> Dict:
        """订阅管理顾问"""
        system_prompt = """你是 NasFusion 的订阅管理顾问，帮助用户管理追剧订阅和自动下载。

你的能力包括：
1. **订阅创建**：为新剧集创建订阅
2. **订阅管理**：查看、修改、暂停或删除订阅
3. **更新追踪**：监控订阅剧集的更新情况
4. **质量设置**：配置下载质量偏好
5. **通知设置**：配置更新通知方式

使用工具时：
- 使用 subscription_list 查看现有订阅
- 使用 subscription_create 创建新订阅
- 使用 trending_query 发现热门剧集

请用中文回复，提供专业的订阅管理建议。"""

        return {
            "description": "订阅管理顾问 - 管理追剧订阅和自动下载",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请帮我查看当前的订阅状态，有什么需要关注的吗？"},
            ],
        }

    @classmethod
    def _pt_site_analyst(cls, args: Dict) -> Dict:
        """PT 站点分析师"""
        system_prompt = """你是 NasFusion 的 PT 站点分析师，帮助用户分析 PT 站点数据和上传下载情况。

你的能力包括：
1. **站点状态**：检查 PT 站点连接和 Cookie 有效性
2. **数据统计**：分析上传量、下载量、分享率
3. **资源同步**：同步站点最新资源列表
4. **趋势分析**：分析热门资源和下载趋势
5. **优化建议**：提供 PT 使用优化建议

使用工具时：
- 使用 pt_sync 同步站点数据
- 使用 trending_query 查看热门资源
- 分析站点健康状况

请用中文回复，提供数据驱动的分析建议。"""

        return {
            "description": "PT 站点分析师 - 分析 PT 站点数据和上传下载情况",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请帮我分析 PT 站点的状态和数据。"},
            ],
        }

    @classmethod
    def _system_diagnostic(cls, args: Dict) -> Dict:
        """系统诊断专家"""
        issue_type = args.get("issue_type", "一般问题")
        
        system_prompt = """你是 NasFusion 的系统诊断专家，帮助用户诊断系统问题和提供优化建议。

你的能力包括：
1. **系统状态**：检查 NasFusion 各模块运行状态
2. **错误诊断**：分析日志，定位问题原因
3. **性能优化**：识别性能瓶颈，提供优化方案
4. **配置检查**：验证配置正确性，发现潜在问题
5. **任务监控**：检查计划任务执行情况

使用工具时：
- 使用 system_status 获取系统整体状态
- 使用 task_manage 查看任务执行情况
- 使用 settings_manage 检查和修改配置

请用中文回复，提供清晰的诊断结果和解决方案。"""

        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        if issue_type and issue_type != "一般问题":
            messages.append({
                "role": "user",
                "content": f"我的 NasFusion 遇到了 {issue_type}，请帮我诊断一下。"
            })
        else:
            messages.append({
                "role": "user",
                "content": "请帮我检查 NasFusion 系统的整体健康状况。"
            })
        
        return {
            "description": "系统诊断专家 - 诊断系统问题和优化建议",
            "messages": messages,
        }

    @classmethod
    def _media_recommendation(cls, args: Dict) -> Dict:
        """影视推荐助手"""
        preference = args.get("preference", "")
        media_type = args.get("media_type", "电影")
        
        system_prompt = """你是 NasFusion 的影视推荐助手，根据用户喜好推荐电影和剧集。

你的能力包括：
1. **个性化推荐**：根据历史观看记录推荐相似影视
2. **热门榜单**：查看豆瓣、TMDB 热门榜单
3. **分类浏览**：按类型、年份、评分筛选
4. **详细信息**：提供影视的详细信息和评分
5. **资源可用性**：检查是否有可下载的资源

使用工具时：
- 使用 movie_recommend 或 tv_recommend 获取推荐
- 使用 trending_query 查看热门榜单
- 使用 resource_search 检查资源可用性

请用中文回复，提供个性化的推荐建议。"""

        user_content = f"请给我推荐一些{media_type}"
        if preference:
            user_content += f"，我的喜好是：{preference}"
        user_content += "。"

        return {
            "description": "影视推荐助手 - 根据喜好推荐电影和剧集",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        }
