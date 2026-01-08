- [x] 清晰的接口契约：贡献指南将覆盖 run_app.py 启动、backend/frontend 分别启动命令、日志路径与目录结构。
- [x] 技术选型理解：已确认 Python/FastAPI/PyQt6 及 Mixin 架构是既定方案，指南将强调复用现有模式。
- [x] 主要风险识别：缺少自动化测试、需手动验证并检查 storage 日志，指南会将其列为风险与要求。
- [x] 验证方式掌握：通过 `python run_app.py` 一键冒烟、分别运行后端与前端，并访问 http://localhost:8123/docs + PyQt UI，自测结果需记录到 `.codex/testing.md` 与 `verification.md`。

## 小说章节生成工作流排查
- [x] 清晰的接口契约：掌握 ChapterGenerationWorkflow 五阶段流程、retry 端点及 NovelService/ChapterVersionService 的职责与输入输出。
- [x] 技术选型理解：明确该模块依赖 AsyncSession + LLMService + 可选 VectorStoreService，重试/并行模式均在 Router 层触发。
- [x] 主要风险识别：空白项目、失败回滚、vector_store 关闭、重复点击导致的并发均可能破坏生成链路。
- [x] 验证方式掌握：通过阅读 `docs/BUG_REPORT.md` + 源码审查来验证假设，结果记录到 BUG_REPORT、operations-log，并在 `verification.md` 说明本轮仅为静态分析。
