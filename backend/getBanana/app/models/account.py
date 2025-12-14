"""
账号数据模型
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class CooldownReason(str, Enum):
    """冷却原因"""
    AUTH_ERROR = "auth_error"       # 认证错误
    RATE_LIMIT = "rate_limit"       # 触发限额
    GENERIC_ERROR = "generic_error" # 其他错误


class AccountState(BaseModel):
    """账号运行时状态"""
    jwt: Optional[str] = None
    jwt_expires_at: float = 0
    session_name: Optional[str] = None

    # 冷却状态
    cooldown_until: Optional[float] = None
    cooldown_reason: Optional[CooldownReason] = None

    # 统计信息
    total_requests: int = 0
    failed_requests: int = 0
    last_used_at: Optional[float] = None

    def is_jwt_valid(self, buffer_seconds: int = 30) -> bool:
        """检查JWT是否有效"""
        if not self.jwt:
            return False
        import time
        return time.time() < (self.jwt_expires_at - buffer_seconds)

    def is_in_cooldown(self) -> bool:
        """检查是否在冷却期"""
        if not self.cooldown_until:
            return False
        import time
        return time.time() < self.cooldown_until

    def get_cooldown_remaining(self) -> int:
        """获取剩余冷却时间（秒）"""
        if not self.cooldown_until:
            return 0
        import time
        remaining = int(self.cooldown_until - time.time())
        return max(0, remaining)


class Account(BaseModel):
    """账号完整信息（配置+状态）"""
    index: int
    team_id: str
    csesidx: str
    secure_c_ses: str
    host_c_oses: str = ""
    user_agent: str = ""
    note: str = ""

    # 配置状态
    available: bool = True

    # 运行时状态
    state: AccountState = Field(default_factory=AccountState)

    def is_usable(self) -> bool:
        """检查账号是否可用"""
        return self.available and not self.state.is_in_cooldown()

    def to_display_dict(self) -> dict:
        """转换为显示用的字典（隐藏敏感信息）"""
        return {
            "index": self.index,
            "team_id": self.team_id[:20] + "..." if len(self.team_id) > 20 else self.team_id,
            "csesidx": self.csesidx,
            "available": self.available,
            "is_usable": self.is_usable(),
            "has_jwt": self.state.jwt is not None,
            "has_session": self.state.session_name is not None,
            "cooldown_remaining": self.state.get_cooldown_remaining(),
            "cooldown_reason": self.state.cooldown_reason.value if self.state.cooldown_reason else None,
            "total_requests": self.state.total_requests,
            "failed_requests": self.state.failed_requests,
            "note": self.note
        }
