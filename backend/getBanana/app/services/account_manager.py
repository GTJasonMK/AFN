"""
账号管理服务
- ���账号轮训
- 冷却机制
- 故障转移
"""
import asyncio
import time
import logging
from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta

from app.config import config_manager, AccountConfig
from app.models.account import Account, AccountState, CooldownReason

logger = logging.getLogger(__name__)


def seconds_until_pt_midnight() -> int:
    """计算距离下一个太平洋时间午夜的秒数（Google配额重置时间）"""
    try:
        from zoneinfo import ZoneInfo
        pt_tz = ZoneInfo("America/Los_Angeles")
        now_pt = datetime.now(pt_tz)
    except ImportError:
        # 兼容旧版Python
        now_utc = datetime.now(timezone.utc)
        now_pt = now_utc - timedelta(hours=8)

    tomorrow = (now_pt + timedelta(days=1)).date()
    midnight_pt = datetime.combine(tomorrow, datetime.min.time())
    if hasattr(now_pt, 'tzinfo') and now_pt.tzinfo:
        midnight_pt = midnight_pt.replace(tzinfo=now_pt.tzinfo)

    delta = (midnight_pt - now_pt).total_seconds()
    return max(0, int(delta))


class AccountManager:
    """
    账号管理器

    功能：
    1. 多账号轮训（负载均衡）
    2. 冷却机制（错误时临时禁用账号）
    3. 故障转移（自动切换到可用账号）
    """

    def __init__(self):
        self._accounts: List[Account] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()

    def load_accounts(self):
        """从配置加载账号"""
        config = config_manager.config
        self._accounts = []

        for i, acc_config in enumerate(config.accounts):
            account = Account(
                index=i,
                team_id=acc_config.team_id,
                csesidx=acc_config.csesidx,
                secure_c_ses=acc_config.secure_c_ses,
                host_c_oses=acc_config.host_c_oses,
                user_agent=acc_config.user_agent,
                note=acc_config.note,
                available=acc_config.available,
                state=AccountState()
            )
            self._accounts.append(account)

        logger.info(f"已加载 {len(self._accounts)} 个账号")

    def initialize_round_robin(self, account_usage: dict):
        """
        根据账号使用情况初始化轮训索引

        Args:
            account_usage: dict[team_id, count] 每个账号的会话数量
        """
        if not self._accounts:
            return

        available = self.get_available_accounts()
        if not available:
            return

        # 找到使用次数最少的账号索引
        min_count = float('inf')
        min_idx = 0

        for i, acc in enumerate(available):
            count = account_usage.get(acc.team_id, 0)
            logger.debug(f"账号 {i} (team_id={acc.team_id[:20]}...) 使用次数: {count}")
            if count < min_count:
                min_count = count
                min_idx = i

        self._current_index = min_idx
        logger.info(
            f"轮训索引初始化为 {min_idx}，可用账号数: {len(available)}，"
            f"账号使用统计: {account_usage}"
        )

    @property
    def accounts(self) -> List[Account]:
        """获取所有账号"""
        return self._accounts

    def get_account(self, index: int) -> Optional[Account]:
        """获取指定索引的账号"""
        if 0 <= index < len(self._accounts):
            return self._accounts[index]
        return None

    def get_account_by_team_id(self, team_id: str) -> Optional[Account]:
        """通过 team_id 获取账号（更可靠的方式）"""
        for acc in self._accounts:
            if acc.team_id == team_id:
                return acc
        return None

    def get_available_accounts(self) -> List[Account]:
        """获取所有可用账号"""
        return [acc for acc in self._accounts if acc.is_usable()]

    def get_account_count(self) -> Tuple[int, int]:
        """获取账号数量统计 (total, available)"""
        total = len(self._accounts)
        available = len(self.get_available_accounts())
        return total, available

    async def get_next_account(self) -> Account:
        """
        轮训获取下一个可用账号

        Raises:
            NoAvailableAccountError: 没有可用账号
        """
        async with self._lock:
            available = self.get_available_accounts()

            if not available:
                # 查找最近将解除冷却的账号
                next_cooldown = self._get_next_cooldown_info()
                if next_cooldown:
                    remaining = next_cooldown["remaining"]
                    raise NoAvailableAccountError(
                        f"没有可用账号，最近的账号将在 {remaining} 秒后解除冷却"
                    )
                raise NoAvailableAccountError("没有可用账号")

            # 轮训选择
            self._current_index = self._current_index % len(available)
            account = available[self._current_index]
            next_index = (self._current_index + 1) % len(available)

            logger.info(
                f"轮训选择账号: index={account.index}, team_id={account.team_id[:20]}..., "
                f"current_idx={self._current_index}, next_idx={next_index}, available_count={len(available)}"
            )

            self._current_index = next_index

            return account

    async def get_account_for_conversation(self, preferred_index: Optional[int] = None) -> Account:
        """
        为会话获取账号

        优先使用指定账号（粘性会话），如果不可用则轮训获取新账号

        Args:
            preferred_index: 首选账号索引

        Returns:
            可用的账号
        """
        # 如果有首选账号且可用，使用它
        if preferred_index is not None:
            account = self.get_account(preferred_index)
            if account and account.is_usable():
                return account
            logger.info(f"首选账号 {preferred_index} 不可用，切换到下一个账号")

        # 否则轮训获取
        return await self.get_next_account()

    def mark_account_cooldown(
        self,
        index: int,
        reason: CooldownReason,
        custom_seconds: Optional[int] = None
    ):
        """
        标记账号进入冷却期

        Args:
            index: 账号索引
            reason: 冷却原因
            custom_seconds: 自定义冷却时间
        """
        account = self.get_account(index)
        if not account:
            return

        config = config_manager.config.cooldown

        # 根据原因确定冷却时间
        if custom_seconds is not None:
            cooldown_seconds = custom_seconds
        elif reason == CooldownReason.AUTH_ERROR:
            cooldown_seconds = config.auth_error_seconds
        elif reason == CooldownReason.RATE_LIMIT:
            # 限额错误：等待到太平洋时间午夜
            pt_wait = seconds_until_pt_midnight()
            cooldown_seconds = max(config.rate_limit_seconds, pt_wait)
        else:
            cooldown_seconds = config.generic_error_seconds

        # 更新状态
        account.state.cooldown_until = time.time() + cooldown_seconds
        account.state.cooldown_reason = reason
        account.state.jwt = None
        account.state.jwt_expires_at = 0
        account.state.session_name = None
        account.state.failed_requests += 1

        logger.warning(
            f"账号 {index} 进入冷却期 {cooldown_seconds}秒，原因: {reason.value}"
        )

    def clear_account_cooldown(self, index: int):
        """清除账号冷却状态"""
        account = self.get_account(index)
        if account:
            account.state.cooldown_until = None
            account.state.cooldown_reason = None
            logger.info(f"账号 {index} 冷却已清除")

    def update_account_state(
        self,
        index: int,
        jwt: Optional[str] = None,
        jwt_expires_at: Optional[float] = None,
        session_name: Optional[str] = None
    ):
        """更新账号状态"""
        account = self.get_account(index)
        if not account:
            return

        if jwt is not None:
            account.state.jwt = jwt
        if jwt_expires_at is not None:
            account.state.jwt_expires_at = jwt_expires_at
        if session_name is not None:
            account.state.session_name = session_name

        account.state.last_used_at = time.time()
        account.state.total_requests += 1

    def _get_next_cooldown_info(self) -> Optional[dict]:
        """获取最近将解除冷却的账号信息"""
        now = time.time()
        candidates = []

        for acc in self._accounts:
            if acc.available and acc.state.cooldown_until:
                if acc.state.cooldown_until > now:
                    candidates.append({
                        "index": acc.index,
                        "until": acc.state.cooldown_until,
                        "remaining": int(acc.state.cooldown_until - now)
                    })

        if not candidates:
            return None

        return min(candidates, key=lambda x: x["until"])

    def get_status(self) -> dict:
        """获取账号管理器状态"""
        total, available = self.get_account_count()
        return {
            "total_accounts": total,
            "available_accounts": available,
            "accounts": [acc.to_display_dict() for acc in self._accounts]
        }


class NoAvailableAccountError(Exception):
    """没有可用账号异常"""
    pass


class AccountAuthError(Exception):
    """账号认证错误"""
    pass


class AccountRateLimitError(Exception):
    """账号限额错误"""
    pass


class AccountRequestError(Exception):
    """账号请求错误"""
    pass


# 全局账号管理器实例
account_manager = AccountManager()
