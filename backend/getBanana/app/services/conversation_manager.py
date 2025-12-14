"""
会话管理服务
- 会话-账号绑定
- 会话持久化
- 图片目录管理
- 按来源分离存储（web/cli 存储在 conversations，api 存储在 api_sessions）
"""
import asyncio
import time
import uuid
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List

from app.config import config_manager, IMAGES_DIR, CONVERSATIONS_DIR, API_SESSIONS_DIR
from app.models.conversation import Conversation, ConversationBinding, ConversationSource
from app.services.account_manager import account_manager, NoAvailableAccountError

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    会话管理器

    功能：
    1. 会话-账号绑定（新会话分配账号，同一会话固定账号）
    2. 会话持久化（按来源分离存储）
    3. 图片目录管理（每个会话独立目录）

    存储策略：
    - web/cli 来源：存储在 data/conversations/
    - api 来源：存储在 data/api_sessions/
    """

    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._bindings: Dict[str, ConversationBinding] = {}
        self._lock = asyncio.Lock()

    def _get_storage_dir(self, source: ConversationSource) -> Path:
        """根据来源获取存储目录"""
        if source == "api":
            return API_SESSIONS_DIR
        return CONVERSATIONS_DIR

    def load_conversations(self):
        """从磁盘加载会话（只加载 web/cli 来源的会话）"""
        if not CONVERSATIONS_DIR.exists():
            return

        for conv_dir in CONVERSATIONS_DIR.iterdir():
            if conv_dir.is_dir():
                json_file = conv_dir / f"{conv_dir.name}.json"
                if json_file.exists():
                    conv = Conversation.load(json_file)
                    if conv:
                        self._conversations[conv.id] = conv
                        if conv.binding:
                            self._bindings[conv.id] = conv.binding

        logger.info(f"已加载 {len(self._conversations)} 个会话")

    async def create_conversation(
        self,
        name: str = "",
        model: str = "gemini-2.5-flash",
        system_prompt: Optional[str] = None,
        lazy: bool = False,
        source: ConversationSource = "web"
    ) -> Conversation:
        """
        创建新会话

        1. 轮训获取下一个可用账号
        2. 创建会话专属图片目录
        3. 绑定会话与账号

        Args:
            lazy: 如果为True，不立即持久化（等第一条消息时再保存）
            source: 会话来源（web, cli, api）
        """
        async with self._lock:
            # 生成会话ID
            conv_id = f"conv_{uuid.uuid4().hex[:12]}"

            # 轮训获取账号
            logger.info(f"创建新会话，准备轮训获取账号...")
            account = await account_manager.get_next_account()
            logger.info(f"新会话分配账号: index={account.index}, team_id={account.team_id[:20]}...")

            # 创建图片目录（仅在非lazy模式或已有消息时创建）
            image_dir = IMAGES_DIR / conv_id
            if not lazy:
                image_dir.mkdir(parents=True, exist_ok=True)

            # 创建绑定
            binding = ConversationBinding(
                conversation_id=conv_id,
                account_index=account.index,
                team_id=account.team_id,  # 保存账号唯一标识
                session_name="",  # 稍后由 ChatService 创建
                image_dir=str(image_dir)
            )

            # 创建会话
            conversation = Conversation(
                id=conv_id,
                name=name or conv_id,
                model=model,
                system_prompt=system_prompt,
                source=source,
                binding=binding
            )

            # 保存到内存
            self._conversations[conv_id] = conversation
            self._bindings[conv_id] = binding

            # 非lazy模式才立即持久化
            if not lazy:
                self._save_conversation(conversation)
                logger.info(
                    f"创建会话 {conv_id}（来源: {source}），绑定账号 {account.index}，"
                    f"图片目录: {image_dir}"
                )
            else:
                logger.info(f"创建会话 {conv_id}（来源: {source}，延迟保存），绑定账号 {account.index}")

            return conversation

    async def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        """获取会话"""
        return self._conversations.get(conv_id)

    async def get_or_create_conversation(
        self,
        conv_id: Optional[str] = None,
        name: str = "",
        model: str = "gemini-2.5-flash",
        source: ConversationSource = "web"
    ) -> Conversation:
        """
        获取或创建会话

        如果 conv_id 存在且有效，返回现有会话
        否则创建新会话（延迟保存，等第一条消息时再持久化）

        Args:
            source: 会话来源（web, cli, api），仅在创建新会话时使用
        """
        if conv_id and conv_id in self._conversations:
            conv = self._conversations[conv_id]

            # 检查绑定的账号是否仍可用
            if conv.binding:
                # 优先使用 team_id 查找账号（更可靠）
                account = None
                if conv.binding.team_id:
                    account = account_manager.get_account_by_team_id(conv.binding.team_id)
                if not account:
                    # 回退到使用 index（兼容旧数据）
                    account = account_manager.get_account(conv.binding.account_index)

                if account and account.is_usable():
                    # 更新绑定信息（确保 index 和 team_id 一致）
                    conv.binding.account_index = account.index
                    conv.binding.team_id = account.team_id
                    conv.binding.touch()
                    return conv

                # 账号不可用，需要迁移
                logger.info(f"会话 {conv_id} 绑定的账号不可用，迁移到新账号")
                return await self._migrate_conversation(conv)

        # 创建新会话（延迟保存）
        return await self.create_conversation(name=name, model=model, lazy=True, source=source)

    async def _migrate_conversation(self, conv: Conversation) -> Conversation:
        """
        迁移会话到新账号

        保留会话ID和图片目录，但绑定到新账号
        """
        async with self._lock:
            # 获取新账号
            account = await account_manager.get_next_account()

            # 更新绑定
            conv.binding.account_index = account.index
            conv.binding.team_id = account.team_id  # 保存新账号的 team_id
            conv.binding.session_name = ""  # 需要重新创建 Gemini Session
            conv.binding.touch()

            # 持久化
            self._save_conversation(conv)

            logger.info(f"会话 {conv.id} 迁移到账号 {account.index} (team_id: {account.team_id[:20]}...)")

            return conv

    def update_binding_session(self, conv_id: str, session_name: str):
        """更新会话的 Gemini Session 名称"""
        if conv_id in self._conversations:
            conv = self._conversations[conv_id]
            if conv.binding:
                conv.binding.session_name = session_name
                self._save_conversation(conv)

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        images: List[str] = None
    ):
        """添加消息到会话"""
        logger.info(f"添加消息: conv_id={conv_id}, role={role}, content_len={len(content)}")

        if conv_id in self._conversations:
            conv = self._conversations[conv_id]

            # 如果是第一条消息，确保图片目录存在
            if len(conv.messages) == 0 and conv.binding:
                image_dir = Path(conv.binding.image_dir)
                if not image_dir.exists():
                    image_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"会话 {conv_id} 首条消息，创建图片目录: {image_dir}")

            conv.add_message(role, content, images)
            self._save_conversation(conv)
            logger.info(f"消息已保存，当前消息数: {len(conv.messages)}")
        else:
            logger.warning(f"会话 {conv_id} 不存在，无法添加消息")

    def add_image(self, conv_id: str, filename: str):
        """记录会话生成的图片"""
        if conv_id in self._conversations:
            conv = self._conversations[conv_id]
            if conv.binding:
                conv.binding.image_count += 1
                self._save_conversation(conv)

    def get_image_dir(self, conv_id: str) -> Optional[Path]:
        """获取会话的图片目录"""
        if conv_id in self._bindings:
            return Path(self._bindings[conv_id].image_dir)
        return None

    def _save_conversation(self, conv: Conversation):
        """保存会话到磁盘（根据来源选择存储目录）"""
        storage_dir = self._get_storage_dir(conv.source)
        conv_dir = storage_dir / conv.id
        conv_dir.mkdir(parents=True, exist_ok=True)

        filepath = conv_dir / f"{conv.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(conv.model_dump(), f, indent=2, ensure_ascii=False)

    def delete_conversation(self, conv_id: str) -> bool:
        """删除会话"""
        if conv_id not in self._conversations:
            return False

        conv = self._conversations.pop(conv_id)
        self._bindings.pop(conv_id, None)

        # 根据来源删除会话目录
        storage_dir = self._get_storage_dir(conv.source)
        conv_dir = storage_dir / conv_id
        if conv_dir.exists():
            import shutil
            shutil.rmtree(conv_dir)

        # 删除图片目录（可选）
        if conv.binding:
            image_dir = Path(conv.binding.image_dir)
            if image_dir.exists():
                import shutil
                shutil.rmtree(image_dir)

        logger.info(f"删除会话 {conv_id}（来源: {conv.source}）")
        return True

    def list_conversations(self, include_api: bool = False) -> List[dict]:
        """
        获取会话列表

        Args:
            include_api: 是否包含 API 来源的会话（默认不包含）
        """
        result = []
        for conv in self._conversations.values():
            if include_api or conv.source != "api":
                result.append(conv.to_summary_dict())
        return result

    def cleanup_expired(self, max_age_seconds: int = 86400):
        """清理过期会话"""
        now = time.time()
        expired = []

        for conv_id, conv in self._conversations.items():
            if conv.binding and conv.binding.is_expired(max_age_seconds):
                expired.append(conv_id)

        for conv_id in expired:
            self.delete_conversation(conv_id)

        if expired:
            logger.info(f"清理了 {len(expired)} 个过期会话")

    def get_account_usage(self) -> dict:
        """
        获取账号使用统计

        Returns:
            dict[team_id, count]: 每个账号绑定的会话数量
        """
        usage = {}
        for conv in self._conversations.values():
            if conv.binding and conv.binding.team_id:
                team_id = conv.binding.team_id
                usage[team_id] = usage.get(team_id, 0) + 1
        return usage

    def get_status(self) -> dict:
        """获取会话管理器状态"""
        return {
            "total_conversations": len(self._conversations),
            "conversations": self.list_conversations()
        }


# 全局会话管理器实例
conversation_manager = ConversationManager()
