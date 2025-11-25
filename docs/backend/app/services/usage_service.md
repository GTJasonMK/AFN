# Usage Service - 使用统计服务

## 文件概述

**文件路径**: `backend/app/services/usage_service.py`  
**代码行数**: 21行  
**核心职责**: 通用计数服务，用于统计API请求次数等各类使用指标

## 核心功能

### 1. 递增计数器

```python
async def increment(self, key: str) -> None
```

**使用示例**：
```python
usage_service = UsageService(session)

# 统计API调用次数
await usage_service.increment("api.total_requests")

# 统计特定功能使用次数
await usage_service.increment("feature.chapter_generation")
await usage_service.increment("feature.outline_creation")
```

### 2. 获取计数值

```python
async def get_value(self, key: str) -> int
```

**使用示例**：
```python
# 获取总请求数
total_requests = await usage_service.get_value("api.total_requests")
print(f"总请求数: {total_requests}")

# 获取功能使用次数
chapter_count = await usage_service.get_value("feature.chapter_generation")
print(f"章节生成次数: {chapter_count}")
```

## 完整使用示例

### API请求统计

```python
@router.post("/api/generate")
async def generate_content(
    session: AsyncSession = Depends(get_session)
):
    usage_service = UsageService(session)
    
    # 统计请求次数
    await usage_service.increment("api.generate_requests")
    
    # 执行业务逻辑
    result = await do_generation()
    
    return result
```

### 功能使用统计

```python
async def track_feature_usage(feature_name: str):
    """追踪功能使用情况"""
    usage_service = UsageService(session)
    
    # 记录功能使用
    await usage_service.increment(f"feature.{feature_name}")
    
    # 同时记录总使用次数
    await usage_service.increment("feature.total")
```

### 统计报表生成

```python
async def generate_usage_report():
    """生成使用统计报表"""
    usage_service = UsageService(session)
    
    metrics = [
        "api.total_requests",
        "feature.chapter_generation",
        "feature.outline_creation",
        "feature.concept_extraction",
    ]
    
    report = {}
    for metric in metrics:
        count = await usage_service.get_value(metric)
        report[metric] = count
    
    return report

# 输出示例
{
    "api.total_requests": 1500,
    "feature.chapter_generation": 230,
    "feature.outline_creation": 45,
    "feature.concept_extraction": 120
}
```

## 推荐的Key命名规范

```python
# API类统计
"api.total_requests"              # 总请求数
"api.generate_requests"           # 生成类请求
"api.error_count"                 # 错误次数

# 功能类统计
"feature.chapter_generation"      # 章节生成
"feature.outline_creation"        # 大纲创建
"feature.concept_extraction"      # 概念提取
"feature.evaluation"              # 评估

# 用户类统计
"user.registrations"              # 注册用户数
"user.active_daily"               # 日活用户

# LLM类统计
"llm.tokens_used"                 # Token使用量
"llm.api_calls"                   # API调用次数
```

## 依赖关系

- [`UsageMetricRepository`](../repositories/usage_metric_repository.md) - 数据库操作
- [`UsageMetric`](../models/usage_metric.md) - 数据模型

## 相关文件

- **数据模型**: `backend/app/models/usage_metric.py`
- **仓储层**: `backend/app/repositories/usage_metric_repository.py`