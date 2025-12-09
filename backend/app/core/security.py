"""
密码安全模块

提供密码哈希和验证功能。

注意：此模块在桌面版中使用有限（桌面版使用固定默认用户，无登录功能）。
保留此模块的原因：
1. 用于默认用户初始化时的密码哈希
2. 保持与Web版代码的一致性，便于未来可能的功能扩展
3. 如需添加本地密码保护功能，可直接复用
"""

from passlib.context import CryptContext

# 统一的密码哈希上下文，后续如需切换算法只需在此维护
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对用户密码进行哈希处理，任何时候都不要存储明文密码。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否匹配哈希值。"""
    return pwd_context.verify(plain_password, hashed_password)
