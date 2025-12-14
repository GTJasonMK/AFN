"""
加密工具函数
- JWT生成
- Base64编码
- HMAC签名
"""
import hmac
import hashlib
import base64
import json
import time
from typing import Tuple


def url_safe_b64encode(data: bytes) -> str:
    """URL安全的Base64编码，不带padding"""
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def url_safe_b64decode(data: str) -> bytes:
    """URL安全的Base64解码"""
    padding = 4 - len(data) % 4
    if padding != 4:
        data += '=' * padding
    return base64.urlsafe_b64decode(data)


def kq_encode(s: str) -> str:
    """
    模拟 Gemini JS 的 kQ 函数
    将字符串编码为特殊的Base64格式
    """
    byte_arr = bytearray()
    for char in s:
        val = ord(char)
        if val > 255:
            byte_arr.append(val & 255)
            byte_arr.append(val >> 8)
        else:
            byte_arr.append(val)
    return url_safe_b64encode(bytes(byte_arr))


def decode_xsrf_token(xsrf_token: str) -> bytes:
    """将 xsrfToken 解码为字节数组（用于HMAC签名）"""
    return url_safe_b64decode(xsrf_token)


def create_jwt_token(key_bytes: bytes, key_id: str, csesidx: str,
                     expires_in: int = 300) -> Tuple[str, float]:
    """
    创建 Gemini Business JWT token

    Args:
        key_bytes: HMAC签名密钥（从xsrfToken解码）
        key_id: 密钥ID
        csesidx: 会话索引
        expires_in: 有效期（秒）

    Returns:
        (jwt_token, expires_at)
    """
    now = int(time.time())
    expires_at = now + expires_in

    header = {
        "alg": "HS256",
        "typ": "JWT",
        "kid": key_id
    }

    payload = {
        "iss": "https://business.gemini.google",
        "aud": "https://biz-discoveryengine.googleapis.com",
        "sub": f"csesidx/{csesidx}",
        "iat": now,
        "exp": expires_at,
        "nbf": now
    }

    # 编码 header 和 payload
    header_b64 = kq_encode(json.dumps(header, separators=(',', ':')))
    payload_b64 = kq_encode(json.dumps(payload, separators=(',', ':')))

    # 签名
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(key_bytes, message.encode('utf-8'), hashlib.sha256).digest()
    signature_b64 = url_safe_b64encode(signature)

    jwt_token = f"{message}.{signature_b64}"
    return jwt_token, float(expires_at)


def parse_jwt_payload(token: str) -> dict:
    """解析JWT payload（不验证签名）"""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        payload_json = url_safe_b64decode(payload_b64).decode('utf-8')
        return json.loads(payload_json)
    except Exception:
        return {}
