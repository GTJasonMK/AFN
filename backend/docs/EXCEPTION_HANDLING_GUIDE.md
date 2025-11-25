# 异常处理改进指南

本文档说明如何使用 `utils/exception_helpers.py` 提供的工具改善异常处理一致性。

## 问题背景

当前代码库存在以下异常处理不一致问题：

1. **日志格式不统一**：有的异常记录包含堆栈，有的不包含
2. **上下文信息缺失**：异常日志中缺少关键业务上下文（project_id, user_id等）
3. **重复代码**：异常转换逻辑散布在多处

## 解决方案

### 1. 统一异常日志记录

**旧代码示例**（不一致）：
```python
# part_outline_service.py Line 496-498
except Exception as exc:
    logger.error("为第 %d 部分生成章节大纲失败: %s", part_number, exc)
    raise
```

**改进后**：
```python
from ..utils.exception_helpers import log_exception

except Exception as exc:
    log_exception(
        exc,
        "生成章节大纲",
        project_id=project_id,
        part_number=part_number,
        user_id=user_id
    )
    raise
```

**收益**：
- ✅ 自动包含完整堆栈跟踪（exc_info=True）
- ✅ 统一的日志格式：`{context}失败 [{ExceptionType}]: {message} (project_id=xxx, part_number=1)`
- ✅ 更丰富的调试信息

---

### 2. 统一异常转换

**旧代码示例**（重复逻辑）：
```python
# llm_service.py Line 305-307
except Exception as exc:
    logger.error("查询用户 LLM 配置失败: user_id=%s error=%s", user_id, exc, exc_info=True)
    raise
```

**改进后**：
```python
from ..utils.exception_helpers import convert_to_http_exception

except Exception as exc:
    raise convert_to_http_exception(
        exc,
        default_status_code=500,
        default_message="查询LLM配置失败",
        context="查询LLM配置",
        user_id=user_id
    )
```

**收益**：
- ✅ 自动记录日志
- ✅ 统一的HTTPException转换逻辑
- ✅ 保留了已经是HTTPException的异常

---

### 3. 异常上下文管理器（高级用法）

**旧代码示例**：
```python
try:
    result = await complex_operation(project_id)
except Exception as exc:
    logger.error("复杂操作失败: project=%s error=%s", project_id, exc, exc_info=True)
    raise
```

**改进后**：
```python
from ..utils.exception_helpers import ExceptionContext

async with ExceptionContext("复杂操作", project_id=project_id, user_id=user_id):
    result = await complex_operation(project_id)
# 异常会自动记录日志并重新抛出
```

**收益**：
- ✅ 更简洁的代码
- ✅ 自动异常日志记录
- ✅ 减少try-except嵌套

---

### 4. 异常链格式化（调试工具）

**使用场景**：复杂异常链的详细日志

```python
from ..utils.exception_helpers import format_exception_chain

try:
    await multi_layer_operation()
except Exception as exc:
    logger.error("操作失败，异常链: %s", format_exception_chain(exc))
    raise
```

**输出示例**：
```
JSONDecodeError: Expecting value -> ValueError: Invalid input -> LLMServiceError: AI服务错误
```

---

## 迁移策略

### 阶段1：新代码强制使用（当前阶段）

- 所有新Service方法必须使用exception_helpers
- Code Review中检查异常处理一致性

### 阶段2：渐进式重构（未来）

优先级顺序：
1. **P0**: 核心业务Service（NovelService, PartOutlineService等）
2. **P1**: LLM调用相关（LLMService）
3. **P2**: 配置和辅助Service

预估工作量：
- P0: 约15处异常处理需要改进
- P1: 约10处
- P2: 约20处

### 阶段3：HTTPException迁移（长期）

将Service层40+处HTTPException迁移到自定义异常类：
- 使用exceptions.py中定义的ArborisException子类
- 保持全局异常处理器的优势
- 预估工作量：2-3天

---

## 最佳实践

### ✅ 推荐做法

```python
# 1. 业务异常：使用自定义异常
from ..exceptions import ResourceNotFoundError

if not project:
    raise ResourceNotFoundError("项目", project_id)

# 2. 意外异常：使用log_exception记录并重抛
from ..utils.exception_helpers import log_exception

try:
    result = await risky_operation()
except Exception as exc:
    log_exception(exc, "高风险操作", project_id=project_id)
    raise

# 3. 可选功能异常：静默失败
from ..utils.exception_helpers import log_exception

try:
    await optional_feature()
except Exception as exc:
    log_exception(exc, "可选功能", level="warning", include_traceback=False)
    # 不重新抛出，继续执行
```

### ❌ 避免做法

```python
# 1. 避免：裸except Exception不记录日志
except Exception:
    pass  # ❌ 静默失败且无日志

# 2. 避免：日志格式不统一
except Exception as exc:
    logger.error(f"错误: {exc}")  # ❌ 缺少上下文和堆栈

# 3. 避免：在Service层使用HTTPException
from fastapi import HTTPException

if not config:
    raise HTTPException(status_code=404, detail="配置不存在")  # ❌ 应使用自定义异常
```

---

## 参考文档

- **异常体系设计**: `backend/app/exceptions.py`
- **全局异常处理器**: `backend/app/main.py` Line 118-136
- **工具函数**: `backend/app/utils/exception_helpers.py`

---

## 示例：重构前后对比

### 示例1：章节生成异常处理

**重构前** (chapter_generation_service.py Line 123-130):
```python
except Exception as exc:
    logger.warning(
        "项目 %s 第 %s 章摘要生成失败: %s",
        project_id,
        chapter.chapter_number,
        exc
    )
    return (chapter, "摘要生成失败，请稍后手动生成", exc)
```

**重构后**:
```python
from ..utils.exception_helpers import log_exception

except Exception as exc:
    log_exception(
        exc,
        "生成章节摘要",
        level="warning",
        include_traceback=False,
        project_id=project_id,
        chapter_number=chapter.chapter_number
    )
    return (chapter, "摘要生成失败，请稍后手动生成", exc)
```

---

### 示例2：蓝图清理异常处理

**重构前** (blueprint_service.py Line 178-192):
```python
except Exception as exc:
    # 区分向量库不可用和其他错误
    error_msg = str(exc)
    if "not enabled" in error_msg.lower() or "not configured" in error_msg.lower():
        logger.info("向量库未启用，跳过向量数据清理")
    else:
        logger.warning(
            "项目 %s 向量库清理失败（类型: %s）: %s\n"
            "数据库记录已删除，但向量数据可能残留，建议手动清理",
            project_id,
            type(exc).__name__,
            exc,
            exc_info=True
        )
```

**重构后**:
```python
from ..utils.exception_helpers import log_exception

except Exception as exc:
    error_msg = str(exc)
    if "not enabled" in error_msg.lower() or "not configured" in error_msg.lower():
        logger.info("向量库未启用，跳过向量数据清理")
    else:
        log_exception(
            exc,
            "清理向量库",
            level="warning",
            project_id=project_id,
            note="数据库记录已删除，但向量数据可能残留"
        )
```

---

## 总结

通过使用exception_helpers工具：
- ✅ **统一日志格式**：所有异常日志包含完整上下文
- ✅ **减少重复代码**：异常转换逻辑集中管理
- ✅ **改善可维护性**：统一的异常处理模式
- ✅ **渐进式改进**：可以逐步迁移现有代码

建议在后续PR中逐步采用这些工具，优先处理核心业务逻辑。
