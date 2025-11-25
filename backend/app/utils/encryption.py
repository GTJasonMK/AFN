"""
API Key加密工具

使用Fernet对称加密（AES-128-CBC）保护API密钥。
加密密钥从应用的SECRET_KEY派生，确保数据库泄露时密钥不会暴露。
"""

import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# 加密前缀，用于识别已加密的值
ENCRYPTED_PREFIX = "enc:v1:"


def _derive_key(secret_key: str) -> bytes:
    """从SECRET_KEY派生Fernet兼容的加密密钥（32字节base64编码）"""
    # 使用SHA256哈希生成32字节密钥
    key_bytes = hashlib.sha256(secret_key.encode()).digest()
    # Fernet要求base64编码的32字节密钥
    return base64.urlsafe_b64encode(key_bytes)


def encrypt_api_key(api_key: Optional[str], secret_key: str) -> Optional[str]:
    """
    加密API密钥

    Args:
        api_key: 原始API密钥
        secret_key: 应用密钥（用于派生加密密钥）

    Returns:
        加密后的字符串（带前缀），或None
    """
    if not api_key:
        return api_key

    # 如果已经加密，直接返回
    if api_key.startswith(ENCRYPTED_PREFIX):
        return api_key

    try:
        fernet = Fernet(_derive_key(secret_key))
        encrypted = fernet.encrypt(api_key.encode())
        return ENCRYPTED_PREFIX + encrypted.decode()
    except Exception as exc:
        logger.error("API Key加密失败: %s", exc)
        # 加密失败时返回原值，避免数据丢失
        return api_key


def decrypt_api_key(encrypted_key: Optional[str], secret_key: str) -> Optional[str]:
    """
    解密API密钥

    Args:
        encrypted_key: 加密后的API密钥（带前缀）
        secret_key: 应用密钥（用于派生加密密钥）

    Returns:
        解密后的原始API密钥，或原值（如果未加密或解密失败）
    """
    if not encrypted_key:
        return encrypted_key

    # 如果没有加密前缀，说明是明文，直接返回
    if not encrypted_key.startswith(ENCRYPTED_PREFIX):
        return encrypted_key

    try:
        fernet = Fernet(_derive_key(secret_key))
        encrypted_data = encrypted_key[len(ENCRYPTED_PREFIX):]
        decrypted = fernet.decrypt(encrypted_data.encode())
        return decrypted.decode()
    except InvalidToken:
        logger.error("API Key解密失败：密钥不匹配或数据损坏")
        return None
    except Exception as exc:
        logger.error("API Key解密失败: %s", exc)
        return None


def is_encrypted(value: Optional[str]) -> bool:
    """检查值是否已加密"""
    return bool(value and value.startswith(ENCRYPTED_PREFIX))
