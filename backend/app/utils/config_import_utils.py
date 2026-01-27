"""
配置导入通用工具

集中处理“导入配置时名称重名”以及“导入循环模板”的统一策略，避免在多个 Service 中重复维护。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable, List, Set, Tuple, TypeVar

from ..exceptions import InvalidParameterError

T = TypeVar("T")


def parse_import_data(
    model_cls: type[T],
    import_data: dict,
    *,
    parameter_name: str = "import_data",
) -> T:
    """通用导入数据解析（Pydantic 校验失败统一报错）

    Args:
        model_cls: Pydantic 模型类（如 LLMConfigExportData）
        import_data: 原始导入数据（dict）
        parameter_name: 参数名（用于 InvalidParameterError.detail）
    """
    try:
        return model_cls(**import_data)
    except Exception as exc:
        raise InvalidParameterError(
            f"导入数据格式错误: {str(exc)}",
            parameter=parameter_name,
        )


def ensure_export_data_version(
    version: str,
    *,
    supported_version: str = "1.0",
    parameter_name: str = "version",
) -> None:
    """校验导入数据的导出格式版本号

    目标：在多个配置 Service 中复用统一的版本校验策略，避免报错信息与参数名漂移。

    Args:
        version: 导入数据中的版本号
        supported_version: 当前支持的版本号（默认 1.0）
        parameter_name: 参数名（用于 InvalidParameterError.detail）
    """
    if version != supported_version:
        raise InvalidParameterError(
            f"不支持的导出格式版本: {version}，当前仅支持 {supported_version}",
            parameter=parameter_name,
        )


def resolve_unique_name(original_name: str, existing_names: Set[str]) -> Tuple[str, bool]:
    """
    生成不与现有集合冲突的名称（suffix 递增）。

    Args:
        original_name: 原始名称
        existing_names: 已存在名称集合（会被用于查重）

    Returns:
        (resolved_name, renamed)：
        - resolved_name：可用名称
        - renamed：是否发生重命名
    """
    config_name = original_name
    suffix = 1

    while config_name in existing_names:
        config_name = f"{original_name} ({suffix})"
        suffix += 1

    return config_name, config_name != original_name


@dataclass
class ConfigImportLoopResult:
    """配置导入循环的统计结果"""

    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    details: List[str] = field(default_factory=list)


async def import_configs_with_unique_names(
    *,
    user_id: int,
    configs: Iterable[Any],
    existing_names: Set[str],
    add_one: Callable[[str, Any], Awaitable[None]],
    logger: Any,
    log_error_message: str,
) -> ConfigImportLoopResult:
    """通用导入循环（重名处理 + 计数 + details + logger）

    说明：
    - 只负责“循环模板”，不负责 commit/flush/缓存失效等事务边界
    - `add_one` 由调用方实现（构建 ORM + add 到 session/repo）
    """
    result = ConfigImportLoopResult()

    for config_data in configs:
        original_name = getattr(config_data, "config_name", "")
        try:
            config_name, renamed = resolve_unique_name(original_name, existing_names)
            if renamed:
                result.details.append(
                    f"配置 '{original_name}' 已重命名为 '{config_name}'（避免重名）"
                )

            await add_one(config_name, config_data)
            existing_names.add(config_name)
            result.imported_count += 1
            result.details.append(f"成功导入配置 '{config_name}'")

        except Exception as exc:
            result.failed_count += 1
            result.details.append(
                f"导入配置 '{original_name}' 失败: {str(exc)}"
            )
            logger.error(
                "%s: user_id=%s, config_name=%s, error=%s",
                log_error_message,
                user_id,
                original_name,
                str(exc),
                exc_info=True,
            )

    return result
