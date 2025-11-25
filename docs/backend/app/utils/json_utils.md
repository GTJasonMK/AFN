
# JSON 工具模块 (json_utils.py)

## 文件概述

**路径**: `backend/app/utils/json_utils.py`  
**行数**: 91 行  
**用途**: 提供 JSON 文本清洗和提取工具，专门处理 LLM 返回的不规范 JSON 响应

该模块专门解决 LLM 响应中常见的 JSON 格式问题，包括：
- Markdown 代码块包裹
- 中文引号污染
- 思考标签干扰
- 未转义的换行符

## 核心功能

### 1. 移除思考标签

```python
def remove_think_tags(raw_text: str) -> str:
    """移除 <think></think> 标签，避免污染结果。"""
```

**功能说明**:
- 使用正则表达式移除 `<think>...</think>` 标签及其内容
- 支持多行匹配（`re.DOTALL` 标志）
- 返回清洗后的文本

**使用场景**:
```python
# DeepSeek R1 等模型会在响应中包含思考过程
response = """
<think>
这是内部思考...
</think>
{"title": "我的小说"}
"""

cleaned = remove_think_tags(response)
# 结果: '{"title": "我的小说"}'
```

### 2. 提取 Markdown 中的 JSON

```python
def unwrap_markdown_json(raw_text: str) -> str:
    """从 Markdown 或普通文本中提取 JSON 字符串，并替换中文引号。"""
```

**功能说明**:
- **优先级1**: 提取 Markdown 代码块中的 JSON（支持 ```json 或 ```）
- **优先级2**: 查找第一个 `{` 或 `[` 到最后一个 `}` 或 `]` 之间的内容
- **优先级3**: 返回原文本
- 所有结果都会进行中文引号标准化

**使用场景**:
```python
# 场景1: Markdown 代码块
markdown_response = """
这是一个JSON响应：
```json
{"title": "测试"}
```
"""
result = unwrap_markdown_json(markdown_response)
# 结果: '{"title": "测试"}'

# 场景2: 混合文本
mixed_response = "前面的说明 {\"data\": \"value\"} 后面的说明"
result = unwrap_markdown_json(mixed_response)
# 结果: '{"data": "value"}'

# 场景3: 中文引号
chinese_quotes = '{"title": "我的小说"}'
result = unwrap_markdown_json(chinese_quotes)
# 结果: '{"title": "我的小说"}'
```

**实现细节**:
```python
# 1. 提取代码块
fence_match = re.search(r"```(?:json|JSON)?\s*(.*?)\s*```", trimmed, re.DOTALL)

# 2. 查找 JSON 边界
json_start_candidates = [idx for idx in (trimmed.find("{"), trimmed.find("[")) if idx != -1]
start_idx = min(json_start_candidates)
closing_brace = trimmed.rfind("}")
closing_bracket = trimmed.rfind("]")
end_idx = max(closing_brace, closing_bracket)
```

### 3. 标准化中文引号

```python
def normalize_chinese_quotes(text: str) -> str:
    """将中文引号（""''）替换为英文引号。"""
```

**功能说明**:
- 将中文双引号 `"` 和 `"` 替换为 `"`
- 将中文单引号 `'` 和 `'` 替换为 `'`
- 确保 JSON 能被标准解析器识别

**使用场景**:
```python
# 中文输入法容易产生中文引号
chinese_json = '{"name": "张三", "age": 30}'
english_json = normalize_chinese_quotes(chinese_json)
# 结果: '{"name": "张三", "age": 30}'

# 可以正常解析
import json
data = json.loads(english_json)  # 成功
```

### 4. 清洗未转义的 JSON 文本

```python
def sanitize_json_like_text(raw_text: str) -> str:
    """对可能含有未转义换行/引号的 JSON 文本进行清洗。"""
```

**功能说明**:
- 逐字符遍历，识别字符串内外状态
- 自动转义字符串内的特殊字符：
  - `\n` → `\\n`
  - `\r` → `\\r`
  - `\t` → `\\t`
  - 未闭合的 `"` → `\"`
- 智能判断引号是字符串结束还是内容的一部分

**使用场景**:
```python
# LLM 生成的 JSON 可能包含未转义的换行
bad_json = '''{
  "content": "这是第一行
这是第二行"
}'''

good_json = sanitize_json_like_text(bad_json)
# 结果: '{"content": "这是第一行\\n这是第二行"}'

import json
data = json.loads(good_json)  # 现在可以正常解析
```

**核心算法**:
```python
# 状态机实现
in_string = False  # 是否在字符串内
escape_next = False  # 下一个字符是否已转义

while i < length:
    ch = raw_text[i]
    if in_string:
        if escape_next:
            # 已转义字符，直接添加
            result.append(ch)
        elif ch == "\\":
            # 转义符号
            escape_next = True
        elif ch == '"':
            # 判断是字符串结束还是内容
            # 向前查找，如果后面是 }]， 则是结束
            j = i + 1
            while j < length and raw_text[j] in " \t\r\n":
                j += 1
            if j >= length or raw_text[j] in "}]," :
                in_string = False
            else:
                # 转义引号
                result.extend(["\\", '"'])
        elif ch in "\n\r\t":
            # 转义换行/制表符
            result.extend(["\\", escape_char])
    else:
        if ch == '"':
            in_string = True
```

## 集成示例

### 在 LLM 服务中使用

```python
from backend.app.utils.json_utils import (
    remove_think_tags,
    unwrap_markdown_json,
    sanitize_json_like_text
)
import json

async def parse_llm_json_response(raw_response: str) -> dict:
    """解析 LLM 返回的 JSON 响应"""
    try:
        # 步骤1: 移除思考标签
        cleaned = remove_think_tags(raw_response)
        
        # 步骤2: 提取 JSON 内容
        json_text = unwrap_markdown_json(cleaned)
        
        # 步骤3: 清洗未转义字符
        sanitized = sanitize_json_like_text(json_text)
        
        # 步骤4: 解析 JSON
        data = json.loads(sanitized)
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        logger.debug(f"原始响应: {raw_response}")
        logger.debug(f"清洗后: {sanitized}")
        raise
```

### 在写作服务中使用

```python
# 在 backend/app/services/llm_service.py 中
async def generate_outline(self, prompt: str) -> dict:
    """生成大纲（返回 JSON）"""
    response = await self.llm_client.stream_and_collect(
        messages=[ChatMessage(role="user", content=prompt)],
        response_format="json_object"
    )
    
    # 使用工具清洗响应
    from backend.app.utils.json_utils import (
        remove_think_tags,
        unwrap_markdown_json,
        sanitize_json_like_text
    )
    
    cleaned = remove_think_tags(response.content)
    json_text = unwrap_markdown_json(cleaned)
    sanitized = sanitize_json_like_text(json_text)
    
    return json.loads(sanitized)
```

## 典型问题场景

### 问题1: Markdown 包裹

**问题**:
```
LLM 返回：
这是生成的大纲：
```json
{"chapters": [{"title": "第一章"}]}
```
```

**解决**:
```python
result = unwrap_markdown_json(response)
# 自动提取代码块内容
```

### 问题2: 中文引号

**问题**:
```python
# LLM 使用中文输入法生成
'{"title": "我的小说"}'
# json.loads() 会报错
```

**解决**:
```python
normalized = normalize_chinese_quotes(raw_json)
# 转换为标准引号
```

### 问题3: 未转义换行

**问题**:
```json
{
  "content": "第一行
第二行"
}
// JSON 解析失败
```

**解决**:
```python
sanitized = sanitize_json_like_text(raw_json)
# 自动转义换行符
```

### 问题4: 思考标签干扰

**问题**:
```
<think>
我需要生成一个章节大纲...
</think>
{"title": "第一章"}
```

**解决**:
```python
cleaned = remove_think_tags(response)
# 移除思考过程
```

## 工具组合策略

### 完整的清洗流程

```python
def complete_json_cleanup(raw_text: str) -> str:
    """完整的 JSON 清洗流程"""
    # 1. 移除思考标签（DeepSeek R1 等模型）
    text = remove_think_tags(raw_text)
    
    # 2. 提取 JSON 内容（去除 Markdown 包裹）
    text = unwrap_markdown_json(text)
    
    # 3. 清洗未转义字符
    text = sanitize_json_like_text(text)
    
    return text
```

### 宽容解析策略

```python
def lenient_json_parse(raw_text: str, default=None):
    """宽容的 JSON 解析，失败时返回默认值"""
    try:
        cleaned = complete_json_cleanup(raw_text)
        return json.loads(cleaned)
    except Exception as e:
        logger.warning(f"JSON 解析失败，使用默认值: {e}")
        return default
```

## 性能考虑

### 正则表达式优化

- 使用 `re.DOTALL` 支持多行匹配
- 非贪婪匹配 `.*?` 避免过度匹配
- 编译频繁使用的正则表达式（可选优化）

### 字符串构建优化

```python
# sanitize_json_like_text 使用列表拼接
result = []  # 而不是 result = ""
result.append(ch)  # 而不是 result += ch
return "".join(result)  # 最后一次性拼接
```

## 测试建议

### 单元测试用例

```python
import pytest
from backend.app.utils.json_utils import *

def test_remove_think_tags():
    """测试移除思考标签"""
    text = "<think>思考</think>{\"data\": 1}"
    assert remove_think_tags(text) == '{"data": 1}'

def test_unwrap_markdown_json():
    """测试提取 Markdown JSON"""
    markdown = "```json\n{\"test\": 1}\n```"
    assert unwrap_markdown_json(markdown) == '{"test": 1}'

def test_normalize_chinese_quotes():
    """测试中文引号标准化"""
    text = '{"name": "张三"}'
    result = normalize_chinese_quotes(text)
    assert '"' not in result
    assert '"' not in result

def test_sanitize_json_like_text():
    """测试清洗未转义字符"""
    bad_json = '{"text": "line1\nline2"}'
    good_json = sanitize_json_like_text(bad_json)
    assert '\\n' in good_json
```

## 最佳实践

### 1. 按顺序使用工具

```python
# 推荐顺序
text = remove_think_tags(raw)      # 1. 移除干扰标签
text = unwrap_markdown_json(text)   # 2. 提取 JSON
text = sanitize_json_like_text(text) # 3. 清洗格式
data = json.loads(text)             # 4. 解析
```

### 2. 记录原始响应

```python
try:
    data = parse_json(raw_response)
except Exception as e:
    logger.error(f"解析失败: {e}")
    logger.debug(f"原始响应: {raw_response}")  # 便于调试
    raise
```

### 3. 提供降级方案

```python
def safe_parse_json(raw: str, fallback: dict = None) -> dict:
    """安全的 JSON 解析，带降级方案"""
    try:
        return parse_json(raw)
    except Exception:
        return fallback or {}
```

## 依赖关系

**标准库**:
- `re` - 正则表达式
- `json` - JSON 解析（调用方使用）

**被依赖模块**:
- [`backend.app.services.llm_service`](../services/llm_service.md) - LLM 服务
- 