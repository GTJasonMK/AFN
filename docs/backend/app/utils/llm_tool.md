
# LLM 工具模块 (llm_tool.py)

## 文件概述

**路径**: `backend/app/utils/llm_tool.py`  
**行数**: 260 行  
**用途**: OpenAI 兼容型 LLM 客户端封装，提供统一的流式请求、响应收集和错误处理机制

该模块是整个应用与 LLM 交互的核心工具，支持：
- OpenAI、DeepSeek、Gemini 等兼容 OpenAI SDK 的模型
- 流式响应处理
- 思考过程收集（DeepSeek R1 等推理模型）
- 浏览器请求头模拟（绕过 Cloudflare）
- 灵活的配置管理

## 核心组件

### 1. 内容收集模式 (ContentCollectMode)

```python
class ContentCollectMode(Enum):
    """流式响应收集模式"""
    CONTENT_ONLY = "content_only"          # 仅收集最终答案
    WITH_REASONING = "with_reasoning"       # 收集答案+思考过程
    REASONING_ONLY = "reasoning_only"       # 仅收集思考过程
```

**使用场景**:
- **CONTENT_ONLY**: 结构化输出、章节生成等常规任务
- **WITH_REASONING**: DeepSeek R1 推理模型，需要展示思考过程
- **REASONING_ONLY**: 仅分析推理过程，不需要最终答案

### 2. 聊天消息 (ChatMessage)

```python
@dataclass
class ChatMessage:
    """聊天消息数据类"""
    role: str      # "system", "user", "assistant"
    content: str   # 消息内容
```

**功能方法**:
```python
# 转换为字典
message.to_dict()  # {"role": "user", "content": "..."}

# 从字典创建
ChatMessage.from_dict({"role": "user", "content": "..."})

# 批量转换
ChatMessage.from_list([{"role": "user", "content": "..."}])
```

**使用示例**:
```python
messages = [
    ChatMessage(role="system", content="你是小说写作助手"),
    ChatMessage(role="user", content="请生成第一章大纲")
]

# 转换为 API 格式
api_messages = [msg.to_dict() for msg in messages]
```

### 3. 流式收集结果 (StreamCollectResult)

```python
@dataclass
class StreamCollectResult:
    """流式收集结果"""
    content: str                    # 最终答案
    reasoning: str                  # 思考过程（如有）
    finish_reason: Optional[str]    # 完成原因（"stop", "length"）
    chunk_count: int                # 收到的 chunk 数量
```

**完成原因说明**:
- `"stop"`: 正常完成
- `"length"`: 达到最大 token 限制
- `"content_filter"`: 内容被过滤
- `None`: 流式传输中断

## LLMClient 类

### 初始化配置

```python
class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        strict_mode: bool = False,
        simulate_browser: bool = False
    ):
```

**参数说明**:
- **api_key**: API 密钥
  - 严格模式: 必须提供
  - 兼容模式: 回退到 `OPENAI_API_KEY` 环境变量
- **base_url**: API 端点
  - 例如: `https://api.openai.com/v1`
  - 兼容模式: 回退到 `OPENAI_API_BASE` 环境变量
- **strict_mode**: 严格模式
  - `True`: 必须明确提供参数，用于测试配置有效性
  - `False`: 允许回退到环境变量
- **simulate_browser**: 模拟浏览器
  - `True`: 添加浏览器请求头，绕过 Cloudflare 检测
  - `False`: 使用标准 API 请求头

**初始化示例**:
```python
# 场景1: 使用配置（常规模式）
client = LLMClient(
    api_key="sk-xxx",
    base_url="https://api.deepseek.com/v1"
)

# 场景2: 严格模式（测试配置）
try:
    client = LLMClient(
        api_key=user_config.api_key,
        base_url=user_config.base_url,
        strict_mode=True
    )
    # 配置有效
except ValueError as e:
    # 配置无效
    print(f"配置错误: {e}")

# 场景3: 模拟浏览器（绕过防护）
client = LLMClient(
    api_key="sk-xxx",
    simulate_browser=True  # 添加浏览器 User-Agent
)
```

**浏览器请求头**:
```python
default_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}
```

### 核心方法

#### 1. 流式聊天 (stream_chat)

```python
async def stream_chat(
    self,
    messages: List[ChatMessage],
    model: Optional[str] = None,
    response_format: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 120,
    **kwargs,
) -> AsyncGenerator[Dict[str, str], None]:
```

**功能说明**:
- 异步生成器，逐块返回流式响应
- 支持 DeepSeek R1 的 `reasoning_content` 字段
- 自动处理超时设置

**返回格式**:
```python
{
    "content": "章节内容...",           # 主要内容
    "reasoning_content": "思考过程...", # 推理过程（可选）
    "finish_reason": "stop"             # 完成原因
}
```

**使用示例**:
```python
# 基础用法
messages = [ChatMessage(role="user", content="写一段开场白")]
async for chunk in client.stream_chat(messages=messages, model="gpt-4"):
    if chunk.get("content"):
        print(chunk["content"], end="", flush=True)

# JSON 模式
async for chunk in client.stream_chat(
    messages=messages,
    model="gpt-4",
    response_format="json_object"  # 强制返回 JSON
):
    # 处理 chunk
    pass

# 带推理过程（DeepSeek R1）
async for chunk in client.stream_chat(
    messages=messages,
    model="deepseek-reasoner"
):
    if chunk.get("reasoning_content"):
        print(f"[思考] {chunk['reasoning_content']}")
    if chunk.get("content"):
        print(f"[回答] {chunk['content']}")
```

**参数详解**:
- **response_format**: `"json_object"` 强制 JSON 输出
- **temperature**: 0.0-2.0，控制随机性
  - 0.0: 确定性输出
  - 1.0: 平衡
  - 2.0: 高度创造性
- **top_p**: 0.0-1.0，核采样
  - 0.1: 保守
  - 0.9: 常用
- **max_tokens**: 最大生成 token 数
- **timeout**: 请求超时（秒）

#### 2. 流式收集 (stream_and_collect)

```python
async def stream_and_collect(
    self,
    messages: List[ChatMessage],
    model: Optional[str] = None,
    response_format: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: int = 120,
    collect_mode: ContentCollectMode = ContentCollectMode.CONTENT_ONLY,
    log_chunks: bool = False,
    **kwargs,
) -> StreamCollectResult:
```

**功能说明**:
- 自动收集完整响应，无需手动拼接
- 支持三种收集模式
- 可选的 chunk 日志记录（调试用）

**使用示例**:
```python
# 场景1: 常规任务（仅收集内容）
result = await client.stream_and_collect(
    messages=[ChatMessage(role="user", content="写一段描写")],
    model="gpt-4",
    collect_mode=ContentCollectMode.CONTENT_ONLY
)
print(result.content)  # 完整的生成内容
print(f"共收到 {result.chunk_count} 个 chunk")

# 场景2: 推理模型（收集内容+思考）
result = await client.stream_and_collect(
    messages=[ChatMessage(role="user", content="分析人物性格")],
    model="deepseek-reasoner",
    collect_mode=ContentCollectMode.WITH_REASONING
)
print("思考过程:", result.reasoning)
print("最终答案:", result.content)

# 场景3: JSON 输出
result = await client.stream_and_collect(
    messages=[ChatMessage(role="user", content="生成大纲")],
    response_format="json_object",
    log_chunks=True  # 记录前3个chunk（调试）
)
import json
data = json.loads(result.content)

# 场景4: 检查完成状态
result = await client.stream_and_collect(...)
if result.finish_reason == "length":
    print("警告: 达到最大token限制，内容可能不完整")
elif result.finish_reason == "stop":
    print("正常完成")
```

**收集模式对比**:
```python
# CONTENT_ONLY - 仅内容
result = await client.stream_and_collect(
    messages=messages,
    collect_mode=ContentCollectMode.CONTENT_ONLY
)
# result.content: "章节内容..."
# result.reasoning: ""

# WITH_REASONING - 内容+推理
result = await client.stream_and_collect(
    messages=messages,
    collect_mode=ContentCollectMode.WITH_REASONING
)
# result.content: "章节内容..."
# result.reasoning: "我需要考虑..."

# REASONING_ONLY - 仅推理
result = await client.stream_and_collect(
    messages=messages,
    collect_mode=ContentCollectMode.REASONING_ONLY
)
# result.content: ""
# result.reasoning: "思考过程..."
```

#### 3. 工厂方法 (create_from_config)

```python
@classmethod
def create_from_config(
    cls,
    config: Dict[str, Optional[str]],
    strict_mode: bool = False,
    simulate_browser: bool = True,
) -> "LLMClient":
```

**功能说明**:
- 从配置字典创建客户端
- 简化配置管理
- 默认启用浏览器模拟

**使用示例**:
```python
# 从数据库配置创建
config = {
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4"
}
client = LLMClient.create_from_config(config)

# 严格模式测试配置
try:
    client = LLMClient.create_from_config(
        config=user_input_config,
        strict_mode=True
    )
    return {"status": "valid"}
except ValueError:
    return {"status": "invalid", "error": "配置无效"}

# 禁用浏览器模拟
client = LLMClient.create_from_config(
    config=config,
    simulate_browser=False  # 使用标准请求头
)
```

## 集成示例

### 在 LLM 服务中使用

```python
# backend/app/services/llm_service.py
from backend.app.utils.llm_tool import (
    LLMClient,
    ChatMessage,
    ContentCollectMode,
    StreamCollectResult
)

class LLMService:
    def __init__(self, llm_config: LLMConfig):
        # 创建客户端
        self.client = LLMClient.create_from_config({
            "api_key": llm_config.api_key,
            "base_url": llm_config.base_url,
        })
        self.model = llm_config.model_name
    
    async def generate_chapter(
        self,
        prompt: str,
        context: str = ""
    ) -> str:
        """生成章节内容"""
        messages = [
            ChatMessage(role="system", content="你是专业的小说作家"),
        ]
        if context:
            messages.append(ChatMessage(role="user", content=f"背景: {context}"))
        messages.append(ChatMessage(role="user", content=prompt))
        
        result = await self.client.stream_and_collect(
            messages=messages,
            model=self.model,
            temperature=0.7,
            max_tokens=4000,
            collect_mode=ContentCollectMode.CONTENT_ONLY
        )
        
        return result.content
    
    async def generate_outline_json(self, prompt: str) -> dict:
        """生成大纲（JSON格式）"""
        messages = [
            ChatMessage(role="system", content="返回JSON格式的大纲"),
            ChatMessage(role="user", content=prompt)
        ]
        
        result = await self.client.stream_and_collect(
            messages=messages,
            model=self.model,
            response_format="json_object",
            temperature=0.3  # 结构化输出用低温度
        )
        
        # 配合 json_utils 清洗
        from backend.app.utils.json_utils import (
            remove_think_tags,
            unwrap_markdown_json,
            sanitize_json_like_text
        )
        cleaned = remove_think_tags(result.content)
        json_text = unwrap_markdown_json(cleaned)
        sanitized = sanitize_json_like_text(json_text)
        
        import json
        return json.loads(sanitized)
```

### 流式输出到前端

```python
async def stream_writing(
    self,
    prompt: str,
    websocket  # WebSocket 连接
):
    """流式生成并推送到前端"""
    messages = [ChatMessage(role="user", content=prompt)]
    
    full_content = ""
    async for chunk in self.client.stream_chat(
        messages=messages,
        model=self.model
    ):
        if chunk.get("content"):
            content = chunk["content"]
            full_content += content
            
            # 实时推送到前端
            await websocket.send_json({
                "type": "chunk",
                "content": content
            })
        
        if chunk.get("finish_reason"):
            await websocket.send_json({
                "type": "complete",
                "full_content": full_content,
                "reason": chunk["finish_reason"]
            })
```

### 多版本并发生成

```python
