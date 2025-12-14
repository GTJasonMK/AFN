"""
会话数据模型
"""
import time
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime


# 会话来源类型: web(网页), cli(命令行), api(外部API调用)
ConversationSource = Literal["web", "cli", "api"]


class ConversationBinding(BaseModel):
    """会话与账号的绑定关系"""
    conversation_id: str
    account_index: int
    team_id: str = ""                  # 账号唯一标识（比index更可靠）
    session_name: str              # Gemini Session 名称
    image_dir: str                 # 图片保存目录
    created_at: float = Field(default_factory=time.time)
    last_active_at: float = Field(default_factory=time.time)

    # 统计
    message_count: int = 0
    image_count: int = 0

    def touch(self):
        """更新最后活跃时间"""
        self.last_active_at = time.time()

    def is_expired(self, max_age_seconds: int = 3600) -> bool:
        """检查会话是否过期"""
        return time.time() - self.last_active_at > max_age_seconds


class ConversationMessage(BaseModel):
    """对话消息"""
    role: str  # user / assistant / system
    content: str
    timestamp: float = Field(default_factory=time.time)
    images: List[str] = Field(default_factory=list)  # 图片文件名列表


class Conversation(BaseModel):
    """完整对话记录"""
    id: str
    name: str = ""
    model: str = "gemini-2.5-flash"
    system_prompt: Optional[str] = None
    messages: List[ConversationMessage] = Field(default_factory=list)

    # 会话来源: web, cli, api
    source: ConversationSource = "web"

    # 绑定信息
    binding: Optional[ConversationBinding] = None

    # 元数据
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)

    def add_message(self, role: str, content: str, images: List[str] = None):
        """添加消息"""
        msg = ConversationMessage(
            role=role,
            content=content,
            images=images or []
        )
        self.messages.append(msg)
        self.updated_at = time.time()
        if self.binding:
            self.binding.message_count = len(self.messages)
            self.binding.touch()

    def get_last_user_message(self) -> Optional[str]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg.content
        return None

    def to_openai_messages(self) -> List[Dict[str, str]]:
        """转换为OpenAI格式的消息列表"""
        result = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def save(self, base_dir: Path):
        """保存对话到文件"""
        if not self.binding:
            return

        conv_dir = Path(self.binding.image_dir).parent
        conv_dir.mkdir(parents=True, exist_ok=True)

        filepath = conv_dir / f"{self.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: Path) -> Optional["Conversation"]:
        """从文件加载对话"""
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except Exception:
            return None

    def get_display_name(self, max_length: int = 30) -> str:
        """获取显示名称（优先使用第一条用户消息）"""
        # 如果已有自定义名称且不是默认值，使用它
        if self.name and self.name != self.id and not self.name.startswith("conv_"):
            return self.name

        # 尝试从第一条用户消息生成名称
        for msg in self.messages:
            if msg.role == "user" and msg.content:
                content = msg.content.strip()
                if len(content) > max_length:
                    return content[:max_length] + "..."
                return content

        # 回退到 ID
        return self.id

    def to_summary_dict(self) -> dict:
        """转换为摘要字典"""
        return {
            "id": self.id,
            "name": self.get_display_name(),
            "model": self.model,
            "message_count": len(self.messages),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "updated_at": datetime.fromtimestamp(self.updated_at).isoformat(),
            "has_binding": self.binding is not None,
            "image_count": self.binding.image_count if self.binding else 0
        }
