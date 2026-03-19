"""
加密工具
用于加密敏感数据（如PT站点的Cookie、密码等）
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


class EncryptionUtil:
    """加密工具类"""

    def __init__(self):
        # 使用 SHA-256 从 SECRET_KEY 派生固定长度的高熵密钥
        # 比直接截取/零填充更安全，始终产生 32 字节高熵输出
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        self.fernet = Fernet(base64.urlsafe_b64encode(key))

    def encrypt(self, plain_text: str) -> str:
        """
        加密文本

        Args:
            plain_text: 明文

        Returns:
            str: 加密后的文本
        """
        if not plain_text:
            return ""
        encrypted = self.fernet.encrypt(plain_text.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        解密文本

        Args:
            encrypted_text: 加密文本

        Returns:
            str: 解密后的明文
        """
        if not encrypted_text:
            return ""
        try:
            decrypted = self.fernet.decrypt(encrypted_text.encode())
            return decrypted.decode()
        except Exception:
            # 解密失败返回空字符串
            return ""


# 全局加密工具实例
encryption_util = EncryptionUtil()
