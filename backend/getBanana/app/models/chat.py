"""
聊天请求/响应数据模型
"""
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ChatImage(BaseModel):
    """聊天图片"""
    url: Optional[str] = None           # 图片URL
    base64_data: Optional[str] = None   # Base64数据
    mime_type: str = "image/png"
    file_name: Optional[str] = None     # 本地文件名
    file_path: Optional[str] = None     # 本地完整路径
    file_id: Optional[str] = None       # Gemini文件ID


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str  # user / assistant / system
    content: Union[str, List[Dict[str, Any]]]  # 文本或多模态内容

    def get_text_content(self) -> str:
        """提取纯文本内容"""
        if isinstance(self.content, str):
            return self.content

        texts = []
        for item in self.content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)

    def get_images(self) -> List[Dict[str, Any]]:
        """提取图片内容"""
        if isinstance(self.content, str):
            return []

        images = []
        for item in self.content:
            if item.get("type") == "image_url":
                image_url = item.get("image_url", {})
                if isinstance(image_url, str):
                    images.append({"type": "url", "url": image_url})
                else:
                    url = image_url.get("url", "")
                    if url.startswith("data:"):
                        # Base64 data URL
                        import re
                        match = re.match(r"data:([^;]+);base64,(.+)", url)
                        if match:
                            images.append({
                                "type": "base64",
                                "mime_type": match.group(1),
                                "data": match.group(2)
                            })
                    else:
                        images.append({"type": "url", "url": url})
            elif item.get("type") == "file":
                file_id = item.get("file_id") or item.get("file", {}).get("file_id")
                if file_id:
                    images.append({"type": "file_id", "file_id": file_id})
        return images


class ChatRequest(BaseModel):
    """聊天请求（OpenAI兼容格式）"""
    model: str = "gemini-2.5-flash"
    messages: List[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # 扩展字段
    conversation_id: Optional[str] = None  # 会话ID（用于绑定账号）

    def get_last_user_message(self) -> Optional[ChatMessage]:
        """获取最后一条用户消息"""
        for msg in reversed(self.messages):
            if msg.role == "user":
                return msg
        return None


class ChatChoice(BaseModel):
    """聊天响应选项"""
    index: int = 0
    message: Optional[Dict[str, Any]] = None
    delta: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class ChatUsage(BaseModel):
    """Token使用统计"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """聊天响应（OpenAI兼容格式）"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice] = Field(default_factory=list)
    usage: Optional[ChatUsage] = None

    # 扩展字段
    images: List[ChatImage] = Field(default_factory=list)
    conversation_id: Optional[str] = None


class ChatResult(BaseModel):
    """内部聊天结果"""
    text: str = ""
    images: List[ChatImage] = Field(default_factory=list)
    thoughts: List[str] = Field(default_factory=list)  # 思维链
    raw_response: Optional[Dict[str, Any]] = None
    prompt_tokens: int = 0       # 输入 token 数
    completion_tokens: int = 0   # 输出 token 数


def estimate_tokens(text: str) -> int:
    """
    估算文本的 token 数量

    估算规则：
    - 中文字符：每个字符约 1.5 tokens
    - 英文和其他字符：每 4 个字符约 1 token
    """
    if not text:
        return 0

    chinese_count = 0
    other_count = 0

    for char in text:
        # 检查是否是中文字符（CJK统一汉字范围）
        if '\u4e00' <= char <= '\u9fff':
            chinese_count += 1
        else:
            other_count += 1

    # 中文每字符约1.5 token，其他每4字符约1 token
    tokens = int(chinese_count * 1.5) + (other_count // 4)
    return max(1, tokens)  # 至少返回1
