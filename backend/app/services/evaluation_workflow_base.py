"""
评估工作流基类

提供非流式与流式的通用执行模板，子类负责上下文准备、提示词构建、
LLM 调用与结果保存/入库细节。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, Optional


@dataclass
class EvaluationPromptContext:
    """评估提示词上下文"""

    system_prompt: str
    user_prompt: str
    rag_context: Optional[Dict[str, Any]] = None


class EvaluationWorkflowBase:
    """评估工作流基类"""

    async def run(self) -> Any:
        """执行非流式评估流程"""
        prompt_context = await self._prepare_context()

        try:
            raw_result = await self._call_llm(
                prompt_context.system_prompt,
                prompt_context.user_prompt,
            )
            result = await self._post_process(raw_result)
        except Exception as exc:
            return await self._handle_llm_error(exc)

        await self._save_result(result)
        await self._ingest_result(result)
        return result

    async def run_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """执行流式评估流程"""
        messages = self._get_progress_messages()
        yield {
            "event": "progress",
            "data": {"stage": "preparing", "message": messages["preparing"]},
        }

        prompt_context = await self._prepare_context()

        if self._should_emit_rag_stage(prompt_context):
            yield {
                "event": "progress",
                "data": {"stage": "rag", "message": messages["rag"]},
            }

        yield {
            "event": "progress",
            "data": {"stage": "generating", "message": messages["generating"]},
        }

        full_content = ""
        async for token in self._iter_llm_tokens(
            prompt_context.system_prompt,
            prompt_context.user_prompt,
        ):
            full_content += token
            yield {"event": "token", "data": {"token": token}}

        yield {
            "event": "progress",
            "data": {"stage": "saving", "message": messages["saving"]},
        }

        result = await self._post_process(full_content)
        await self._save_result(result)

        if self._should_emit_indexing():
            yield {
                "event": "progress",
                "data": {"stage": "indexing", "message": messages["indexing"]},
            }

        await self._ingest_result(result)
        complete_payload = await self._build_complete_payload(result)
        yield {"event": "complete", "data": complete_payload}

    async def _prepare_context(self) -> EvaluationPromptContext:
        """准备提示词上下文"""
        raise NotImplementedError

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """调用LLM并返回原始内容"""
        raise NotImplementedError

    async def _post_process(self, raw_content: str) -> Any:
        """对LLM返回内容进行清理或转换"""
        return raw_content

    async def _save_result(self, result: Any) -> None:
        """保存评估结果"""
        return None

    async def _ingest_result(self, result: Any) -> None:
        """入库评估结果（可选）"""
        return None

    async def _handle_llm_error(self, exc: Exception) -> Any:
        """处理LLM调用异常"""
        raise exc

    async def _iter_llm_tokens(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> AsyncGenerator[str, None]:
        """流式迭代LLM输出token"""
        raise NotImplementedError

    def _get_progress_messages(self) -> Dict[str, str]:
        """获取流式进度消息"""
        raise NotImplementedError

    async def _build_complete_payload(self, result: Any) -> Dict[str, Any]:
        """构建完成事件payload"""
        raise NotImplementedError

    def _should_emit_rag_stage(self, prompt_context: EvaluationPromptContext) -> bool:
        """是否需要输出RAG阶段进度"""
        return bool(prompt_context.rag_context)

    def _should_emit_indexing(self) -> bool:
        """是否需要输出索引阶段进度"""
        return False
