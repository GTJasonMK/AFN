"""
API Token 管理服务
- Token CRUD 操作
- 用量统计
- 持久化存储
"""
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.models.api_token import ApiToken, ApiTokenStats
from app.config import DATA_DIR

logger = logging.getLogger(__name__)

# Token 存储文件
TOKENS_FILE = DATA_DIR / "api_tokens.json"


class TokenManager:
    """API Token 管理器"""

    def __init__(self):
        self._tokens: Dict[str, ApiToken] = {}
        self._legacy_tokens: set = set()  # 兼容旧配置中的静态 token

    def load(self, legacy_tokens: List[str] = None):
        """
        加载 Token 数据

        Args:
            legacy_tokens: 旧配置中的静态 token 列表（用于兼容）
        """
        # 加载旧配置中的静态 token
        if legacy_tokens:
            self._legacy_tokens = set(legacy_tokens)
            logger.info(f"加载 {len(self._legacy_tokens)} 个静态 Token（兼容模式）")

        # 加载持久化的 token
        if TOKENS_FILE.exists():
            try:
                with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for token_data in data.get("tokens", []):
                    token = ApiToken(**token_data)
                    self._tokens[token.token] = token

                logger.info(f"加载 {len(self._tokens)} 个动态 Token")
            except Exception as e:
                logger.error(f"加载 Token 数据失败: {e}")

    def save(self):
        """保存 Token 数据"""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "tokens": [t.model_dump() for t in self._tokens.values()]
            }
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存 Token 数据失败: {e}")

    def create_token(self, name: str = "", expires_days: int = None) -> ApiToken:
        """
        创建新 Token

        Args:
            name: Token 名称/备注
            expires_days: 有效天数（None 表示永不过期）

        Returns:
            新创建的 Token
        """
        token = ApiToken(
            name=name or f"Token-{len(self._tokens) + 1}",
            expires_at=time.time() + expires_days * 86400 if expires_days else None
        )
        self._tokens[token.token] = token
        self.save()
        logger.info(f"创建 Token: {token.name}")
        return token

    def get_token(self, token_str: str) -> Optional[ApiToken]:
        """获取 Token 对象"""
        return self._tokens.get(token_str)

    def verify_token(self, token_str: str) -> bool:
        """
        验证 Token 是否有效

        Returns:
            True 如果 Token 有效
        """
        if not token_str:
            return False

        # 检查动态 Token
        token = self._tokens.get(token_str)
        if token and token.is_valid():
            return True

        # 检查静态 Token（兼容旧配置）
        if token_str in self._legacy_tokens:
            return True

        return False

    def record_usage(self, token_str: str, tokens: int = 0):
        """
        记录 Token 使用

        Args:
            token_str: Token 字符串
            tokens: 消耗的 token 数量（估算）
        """
        token = self._tokens.get(token_str)
        if token:
            token.record_usage(tokens)
            # 定期保存（每 10 次请求保存一次）
            if token.request_count % 10 == 0:
                self.save()

    def list_tokens(self, include_legacy: bool = False) -> List[dict]:
        """
        列出所有 Token

        Args:
            include_legacy: 是否包含静态 Token

        Returns:
            Token 列表（隐藏完整 token）
        """
        result = [t.to_dict(hide_token=True) for t in self._tokens.values()]

        if include_legacy:
            for legacy in self._legacy_tokens:
                result.append({
                    "token": legacy[:4] + "****" + legacy[-4:] if len(legacy) > 8 else "****",
                    "name": "(静态配置)",
                    "created_at": None,
                    "last_used_at": None,
                    "enabled": True,
                    "request_count": 0,
                    "token_count": 0,
                    "is_legacy": True
                })

        return result

    def delete_token(self, token_str: str) -> bool:
        """删除 Token"""
        if token_str in self._tokens:
            del self._tokens[token_str]
            self.save()
            logger.info(f"删除 Token: {token_str[:8]}...")
            return True
        return False

    def disable_token(self, token_str: str) -> bool:
        """禁用 Token"""
        token = self._tokens.get(token_str)
        if token:
            token.enabled = False
            self.save()
            logger.info(f"禁用 Token: {token.name}")
            return True
        return False

    def enable_token(self, token_str: str) -> bool:
        """启用 Token"""
        token = self._tokens.get(token_str)
        if token:
            token.enabled = True
            self.save()
            logger.info(f"启用 Token: {token.name}")
            return True
        return False

    def get_stats(self) -> ApiTokenStats:
        """获取统计信息"""
        stats = ApiTokenStats()
        stats.total_tokens = len(self._tokens) + len(self._legacy_tokens)
        stats.enabled_tokens = sum(1 for t in self._tokens.values() if t.is_valid())
        stats.enabled_tokens += len(self._legacy_tokens)
        stats.total_requests = sum(t.request_count for t in self._tokens.values())
        stats.total_token_usage = sum(t.token_count for t in self._tokens.values())
        return stats

    def get_token_by_prefix(self, prefix: str) -> Optional[ApiToken]:
        """通过前缀查找 Token（用于管理操作）"""
        for token_str, token in self._tokens.items():
            if token_str.startswith(prefix):
                return token
        return None


# 全局 Token 管理器
token_manager = TokenManager()
