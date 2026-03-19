"""
安全相关工具函数
包括密码哈希、JWT Token生成和验证
"""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
import bcrypt

from app.core.config import settings

# 密码加密上下文 - 禁用自动检测以避免初始化问题
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码

    Returns:
        bool: 密码是否匹配
    """
    try:
        # 确保密码不超过72字节限制
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = password_bytes[:72]

        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # 如果bcrypt验证失败，回退到passlib
        return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希

    Args:
        password: 明文密码

    Returns:
        str: 哈希后的密码
    """
    # 确保密码不超过72字节限制
    password_bytes = password.encode('utf-8')

    if len(password_bytes) > 72:
        # 截断到72字节
        password_bytes = password_bytes[:72]

    # 使用salt生成哈希
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)

    # 将bytes转换为字符串
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT令牌
    """
    from app.utils.timezone import utc_now

    to_encode = data.copy()
    current_utc = utc_now()

    if expires_delta:
        expire = current_utc + expires_delta
    else:
        expire = current_utc + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": current_utc, "type": "access"})

    # 使用JWT_SECRET_KEY，如果没有设置则使用SECRET_KEY
    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    algorithm = settings.JWT_ALGORITHM

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT刷新令牌

    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT刷新令牌
    """
    from app.utils.timezone import utc_now

    to_encode = data.copy()
    current_utc = utc_now()

    if expires_delta:
        expire = current_utc + expires_delta
    else:
        expire = current_utc + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "iat": current_utc, "type": "refresh"})

    # 使用JWT_SECRET_KEY，如果没有设置则使用SECRET_KEY
    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    algorithm = settings.JWT_ALGORITHM

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码JWT访问令牌

    Args:
        token: JWT令牌

    Returns:
        Optional[dict]: 解码后的数据，失败返回None
    """
    try:
        secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
        payload = jwt.decode(token, secret_key, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        return None


def generate_random_password(length: int = 12) -> str:
    """
    生成随机密码

    Args:
        length: 密码长度

    Returns:
        str: 随机密码
    """
    # 只使用字母和数字，避免特殊字符导致的编码问题
    # 确保生成的密码在UTF-8编码下不超过72字节
    # 12个字符的字母数字组合在UTF-8下最多12字节，远小于72字节限制
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def generate_token(length: int = 32) -> str:
    """
    生成随机token

    Args:
        length: token长度（字节数）

    Returns:
        str: 随机token（十六进制）
    """
    return secrets.token_hex(length)
