"""
API Token 数据模型
"""
import time
import secrets
from typing import Optional
from pydantic import BaseModel, Field


class ApiToken(BaseModel):
    """API Token"""
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    name: str = ""                          # Token 名称/备注
    created_at: float = Field(default_factory=time.time)
    last_used_at: Optional[float] = None    # 最后使用时间
    expires_at: Optional[float] = None      # 过期时间（None表示永不过期）
    enabled: bool = True                    # 是否启用

    # 用量统计
    request_count: int = 0                  # 总请求次数
    token_count: int = 0                    # 总 Token 消耗（估算）

    def is_valid(self) -> bool:
        """检查 Token 是否有效"""
        if not self.enabled:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True

    def record_usage(self, tokens: int = 0):
        """记录使用"""
        self.last_used_at = time.time()
        self.request_count += 1
        self.token_count += tokens

    def to_dict(self, hide_token: bool = True) -> dict:
        """转换为字典（可隐藏完整 token）"""
        data = self.model_dump()
        if hide_token and len(self.token) > 8:
            data["token"] = self.token[:4] + "****" + self.token[-4:]
        return data


class ApiTokenStats(BaseModel):
    """Token 统计信息"""
    total_tokens: int = 0
    enabled_tokens: int = 0
    total_requests: int = 0
    total_token_usage: int = 0
