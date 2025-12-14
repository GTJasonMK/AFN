# 正文优化提示词模板

## Agent模式说明

正文优化Agent采用"思考-决策-行动-观察"循环模式：
1. **思考 (Thinking)**: 分析当前段落和上下文
2. **决策 (Decision)**: 选择要使用的工具
3. **行动 (Action)**: 执行工具调用
4. **观察 (Observation)**: 分析工具返回结果
5. **反馈 (Feedback)**: 根据观察决定下一步

Agent可用工具：
- `rag_retrieve`: RAG检索相关内容
- `get_character_state`: 获取角色状态
- `get_foreshadowing`: 获取伏笔信息
- `analyze_paragraph`: 分析段落元素
- `check_coherence`: 检查逻辑连贯性
- `generate_suggestion`: 生成修改建议
- `finish_analysis`: 完成段落分析
- `complete_workflow`: 完成工作流

---

## 段落分析提示词（旧版线性模式）

你是一个专业的小说编辑，正在审查章节内容的质量和连贯性。

### 当前段落（第{paragraph_index}段）
{paragraph}

### 前文段落
{prev_paragraphs}

### 已知信息
{context_info}

### 检查维度
{dimensions_to_check}

### 任务
请仔细检查当前段落，找出可能存在的问题。对于每个问题，请提供：
1. 问题类型（coherence/character/foreshadow/timeline/style/scene）
2. 问题描述
3. 严重程度（high/medium/low）
4. 具体修改建议

请以JSON格式输出，格式如下：
```json
{
  "issues": [
    {
      "type": "问题类型",
      "description": "问题描述",
      "severity": "严重程度",
      "original_text": "原文片段",
      "suggested_text": "建议修改后的文本",
      "reason": "修改理由"
    }
  ],
  "summary": "整体评价"
}
```

如果没有发现问题，返回空的issues数组。

---

## 检查维度说明

### 逻辑连贯性 (coherence)
- 事件因果是否合理
- 行为动机是否充分
- 情节推进是否自然
- 前后逻辑是否矛盾

### 角色一致性 (character)
- 角色位置是否与前文一致
- 角色状态（情绪、体力等）是否合理
- 角色性格表现是否一致
- 角色行为是否符合其设定

### 伏笔呼应 (foreshadow)
- 是否有未回应的伏笔应该在此处回应
- 新埋下的伏笔是否自然
- 伏笔回收是否合理

### 时间线一致性 (timeline)
- 时间流逝是否合理
- 日夜变化是否正确
- 事件顺序是否正确

### 风格一致性 (style)
- 叙述视角是否一致
- 用词风格是否统一
- 节奏是否与整体协调

### 场景描写 (scene)
- 场景转换是否自然
- 环境描述是否与前文一致
- 空间感是否清晰

---

## 优化建议生成提示词

基于以下分析结果，为这个段落生成具体的修改建议：

### 发现的问题
{issues}

### 原文
{original_text}

### 要求
1. 保持原文风格和语气
2. 只修改有问题的部分
3. 给出修改理由
4. 修改后的文本应该与上下文自然衔接

以JSON格式输出建议：
```json
{
  "original_text": "原文片段",
  "suggested_text": "建议修改后的文本",
  "reason": "修改理由",
  "category": "问题类别",
  "priority": "优先级"
}
```

---

## Agent工具调用格式

Agent响应应遵循以下格式：

```
<thinking>
当前分析的思考过程...
</thinking>

<tool_call>
{
    "tool": "工具名称",
    "parameters": {
        "param1": "value1"
    },
    "reasoning": "选择这个工具的理由"
}
</tool_call>
```

工具执行结果会以以下格式返回：

```
<tool_result>
工具执行结果...
</tool_result>
```

Agent根据工具执行结果决定下一步行动，直到完成所有段落分析。
