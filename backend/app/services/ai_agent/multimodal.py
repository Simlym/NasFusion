# -*- coding: utf-8 -*-
"""
多模态支持服务

支持图片消息和多模态 LLM 交互。

支持的多模态模型：
- OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo-vision
- 智谱: glm-4v, glm-4.7v
- Ollama: 支持视觉的本地模型（如 llava）
"""
import base64
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.adapters.llm.base import ChatMessage

logger = logging.getLogger(__name__)


class ImageMimeType(str, Enum):
    """支持的图片 MIME 类型"""
    JPEG = "image/jpeg"
    PNG = "image/png"
    GIF = "image/gif"
    WEBP = "image/webp"


@dataclass
class ImageContent:
    """图片内容"""
    mime_type: ImageMimeType
    base64_data: str
    url: Optional[str] = None  # 如果图片有 URL


@dataclass
class MultimodalContent:
    """
    多模态内容
    
    包含文本和可选的图片列表
    """
    text: str
    images: List[ImageContent] = None

    def __post_init__(self):
        if self.images is None:
            self.images = []


class MultimodalMessageBuilder:
    """
    多模态消息构建器
    
    将多模态内容转换为不同 LLM 供应商需要的格式
    """

    @staticmethod
    def build_for_openai(content: MultimodalContent) -> List[Dict[str, Any]]:
        """
        构建 OpenAI 格式的消息内容
        
        OpenAI 格式：
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "..."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}},
            ]
        }
        """
        message_content = []

        # 添加文本
        if content.text:
            message_content.append({
                "type": "text",
                "text": content.text,
            })

        # 添加图片
        for img in content.images:
            if img.base64_data:
                image_url = f"data:{img.mime_type.value};base64,{img.base64_data}"
            elif img.url:
                image_url = img.url
            else:
                continue

            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "auto",  # auto, low, high
                },
            })

        return message_content

    @staticmethod
    def build_for_zhipu(content: MultimodalContent) -> str:
        """
        构建智谱格式的消息内容
        
        智谱格式（多模态）：
        [
            {"role": "user", "content": [
                {"type": "text", "text": "..."},
                {"type": "image_url", "image_url": {"url": "..."}},
            ]}
        ]
        
        注意：智谱的多模态格式与 OpenAI 类似
        """
        # 智谱使用与 OpenAI 相同的格式
        return MultimodalMessageBuilder.build_for_openai(content)

    @staticmethod
    def build_for_ollama(content: MultimodalContent) -> str:
        """
        构建 Ollama 格式的消息内容
        
        Ollama 格式：
        {
            "role": "user",
            "content": "图片描述",
            "images": ["base64data", ...]
        }
        """
        # Ollama 目前只支持单独的图片列表
        # 需要将文本和图片合并到 content 中
        if content.images:
            image_data = [img.base64_data for img in content.images if img.base64_data]
            return {
                "content": content.text or "",
                "images": image_data,
            }
        return {"content": content.text or ""}


class MultimodalAdapter:
    """
    多模态适配器
    
    检测模型是否支持多模态，并提供相应的格式转换。
    """

    # 支持多模态的模型列表
    MULTIMODAL_MODELS = {
        # OpenAI
        "gpt-4o": "openai",
        "gpt-4o-mini": "openai",
        "gpt-4-turbo": "openai",
        "gpt-4-vision-preview": "openai",
        # 智谱
        "glm-4v": "zhipu",
        "glm-4.7v": "zhipu",
        "glm-4.7": "zhipu",
        # Ollama（部分模型）
        "llava": "ollama",
        "llava-phi3": "ollama",
        "bakllava": "ollama",
        "moondream": "ollama",
    }

    @classmethod
    def is_multimodal_model(cls, model: str, provider: str) -> bool:
        """
        检查模型是否支持多模态
        
        Args:
            model: 模型名称
            provider: 供应商
            
        Returns:
            是否支持多模态
        """
        model_lower = model.lower()
        
        # 检查已知的多模态模型
        for mm_model, mm_provider in cls.MULTIMODAL_MODELS.items():
            if mm_model in model_lower and mm_provider == provider:
                return True
        
        return False

    @classmethod
    def build_multimodal_message(
        cls,
        content: MultimodalContent,
        provider: str,
    ) -> Union[str, List[Dict[str, Any]]]:
        """
        构建多模态消息
        
        Args:
            content: 多模态内容
            provider: 供应商
            
        Returns:
            对应供应商格式的消息内容
        """
        if provider == "openai" or provider == "deepseek":
            return MultimodalMessageBuilder.build_for_openai(content)
        elif provider == "zhipu":
            return MultimodalMessageBuilder.build_for_zhipu(content)
        elif provider == "ollama":
            return MultimodalMessageBuilder.build_for_ollama(content)
        else:
            # 默认使用 OpenAI 格式（大多数供应商兼容）
            return MultimodalMessageBuilder.build_for_openai(content)


class ImageProcessor:
    """
    图片处理器
    
    处理图片的上传、压缩和编码
    """

    # 最大图片尺寸（像素）
    MAX_IMAGE_SIZE = 4096
    
    # 默认压缩质量
    DEFAULT_QUALITY = 85
    
    # 最大 Base64 大小（约 5MB）
    MAX_BASE64_SIZE = 5 * 1024 * 1024

    @staticmethod
    def encode_image(file_path: str) -> Optional[ImageContent]:
        """
        将图片文件编码为 base64
        
        Args:
            file_path: 图片文件路径
            
        Returns:
            ImageContent 对象或 None
        """
        try:
            import mimetypes
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type or not mime_type.startswith("image/"):
                logger.error(f"不支持的文件类型: {file_path}")
                return None

            with open(file_path, "rb") as f:
                image_data = f.read()

            # 检查大小
            if len(image_data) > ImageProcessor.MAX_BASE64_SIZE:
                logger.warning(f"图片过大，尝试压缩: {file_path}")
                image_data = ImageProcessor.compress_image(image_data)
                if not image_data:
                    return None

            base64_data = base64.b64encode(image_data).decode("utf-8")
            
            return ImageContent(
                mime_type=ImageMimeType(mime_type),
                base64_data=base64_data,
            )

        except Exception as e:
            logger.exception(f"编码图片失败: {file_path}")
            return None

    @staticmethod
    def encode_image_bytes(image_data: bytes, mime_type: str) -> Optional[ImageContent]:
        """
        将图片字节编码为 base64
        
        Args:
            image_data: 图片字节数据
            mime_type: MIME 类型
            
        Returns:
            ImageContent 对象或 None
        """
        try:
            # 检查大小
            if len(image_data) > ImageProcessor.MAX_BASE64_SIZE:
                image_data = ImageProcessor.compress_image(image_data)
                if not image_data:
                    return None

            base64_data = base64.b64encode(image_data).decode("utf-8")
            
            return ImageContent(
                mime_type=ImageMimeType(mime_type),
                base64_data=base64_data,
            )

        except Exception as e:
            logger.exception("编码图片字节失败")
            return None

    @staticmethod
    def compress_image(image_data: bytes, quality: int = None) -> Optional[bytes]:
        """
        压缩图片
        
        Args:
            image_data: 原始图片字节
            quality: JPEG 质量（1-95）
            
        Returns:
            压缩后的图片字节或 None
        """
        try:
            from PIL import Image
            import io

            if quality is None:
                quality = ImageProcessor.DEFAULT_QUALITY

            # 打开图片
            img = Image.open(io.BytesIO(image_data))
            
            # 转换为 RGB（处理 PNG 透明通道）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 检查尺寸并缩放
            width, height = img.size
            max_size = ImageProcessor.MAX_IMAGE_SIZE
            
            if width > max_size or height > max_size:
                # 按比例缩放
                ratio = min(max_size / width, max_size / height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"图片已缩放: {width}x{height} -> {new_size[0]}x{new_size[1]}")

            # 压缩并保存
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality, optimize=True)
            compressed_data = output.getvalue()

            logger.info(
                f"图片已压缩: {len(image_data)} bytes -> {len(compressed_data)} bytes"
            )
            
            return compressed_data

        except Exception as e:
            logger.exception("压缩图片失败")
            return None


# 便捷函数
def create_image_message(
    text: str,
    image_paths: List[str] = None,
    provider: str = "openai",
) -> Dict[str, Any]:
    """
    创建包含图片的消息
    
    Args:
        text: 文本内容
        image_paths: 图片文件路径列表
        provider: LLM 供应商
        
    Returns:
        消息字典
    """
    images = []
    if image_paths:
        for path in image_paths:
            img_content = ImageProcessor.encode_image(path)
            if img_content:
                images.append(img_content)

    multimodal_content = MultimodalContent(text=text, images=images)
    content = MultimodalAdapter.build_multimodal_message(multimodal_content, provider)

    return {
        "role": "user",
        "content": content,
    }
