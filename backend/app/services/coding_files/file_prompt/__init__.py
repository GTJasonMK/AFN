"""
文件 Prompt 子模块

说明：
- 该目录用于承载 `FilePromptService` 的内部实现拆分，降低单文件复杂度、提升可读性。
- 目前已按职责拆分为：
  - `workflows.py`：工作流骨架（同步/流式共用）
  - `file_ops.py`：文件/版本/序列化/CRUD
  - `generation.py`：Prompt 生成（同步/流式）
  - `review.py`：审查 Prompt 生成与保存
  - `rag.py`：RAG 上下文检索
  - `ingestion.py`：向量入库（含去重模板）
  - `prompts.py`：system/user prompt 构建
- 对外导出仍由 `backend/app/services/coding_files/file_prompt_service.py` 作为聚合入口提供。
"""
