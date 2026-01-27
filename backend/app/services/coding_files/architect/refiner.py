"""
目录结构精化Agent

阶段三（精化）：基于质量评估结果，对生成的目录结构进行精化。
最多执行5轮精化，每轮解决一类问题。
"""

import logging
from copy import deepcopy
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from ..directory_generator.schemas import (
    BruteForceOutput,
    DirectorySpec,
    FileSpec,
)
from .schemas import (
    ArchitectureDecision,
    ArchitecturePattern,
    IssueType,
    IssueSeverity,
    ProjectProfile,
    QualityMetrics,
    StructureIssue,
)
from .quality_evaluator import QualityEvaluator

logger = logging.getLogger(__name__)


class RefinementAgent:
    """
    目录结构精化Agent

    根据质量评估结果，对生成的目录结构进行精化。
    使用规则优先、LLM辅助的策略，最多执行5轮精化。
    """

    MAX_ROUNDS = 5
    QUALITY_THRESHOLD = 0.8  # 质量达标阈值

    def __init__(
        self,
        profile: ProjectProfile,
        decision: ArchitectureDecision,
        output: BruteForceOutput,
        llm_service=None,
        user_id: int = 1,
        prompt_service=None,
    ):
        """
        初始化精化Agent

        Args:
            profile: 项目画像
            decision: 架构决策
            output: 初始生成的目录结构
            llm_service: LLM服务（可选，用于增强描述）
            user_id: 用户ID
            prompt_service: 提示词服务
        """
        self.profile = profile
        self.decision = decision
        self.output = deepcopy(output)  # 深拷贝，避免修改原始数据
        self.llm_service = llm_service
        self.user_id = user_id
        self.prompt_service = prompt_service

        # 精化状态
        self._current_round = 0
        self._history: List[Dict[str, Any]] = []

    def refine(self) -> Tuple[BruteForceOutput, QualityMetrics]:
        """
        执行精化流程（同步版本）

        Returns:
            (精化后的目录结构, 最终质量指标)
        """
        logger.info("开始目录结构精化流程")

        for round_num in range(1, self.MAX_ROUNDS + 1):
            self._current_round = round_num

            # 1. 评估当前质量（并记录历史）
            metrics = self._evaluate_and_record(round_num)

            logger.info(
                "精化轮次 %d/%d: 质量评分=%.2f, 等级=%s, 问题数=%d",
                round_num,
                self.MAX_ROUNDS,
                metrics.overall_score,
                metrics.get_grade(),
                len(metrics.issues),
            )

            stop_reason, fixable_issues, fixed_count = self._decide_or_apply_fixes(metrics)
            if stop_reason == "quality_threshold_met":
                logger.info("质量达标，结束精化流程")
                return self.output, metrics
            if stop_reason == "no_fixable_issues":
                logger.info("无可修复的问题，结束精化流程")
                return self.output, metrics
            if stop_reason == "no_fixes_applied":
                logger.info("本轮未修复任何问题，结束精化流程")
                return self.output, metrics

            logger.info("本轮修复了 %d 个问题", fixed_count)

        # 最终评估
        evaluator = QualityEvaluator(self.profile, self.decision, self.output)
        final_metrics = evaluator.evaluate()

        logger.info(
            "精化流程完成: 执行了%d轮, 最终评分=%.2f",
            self._current_round,
            final_metrics.overall_score,
        )

        return self.output, final_metrics

    async def refine_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行精化流程

        Yields:
            SSE事件
        """
        yield {
            "event": "progress",
            "data": {
                "stage": "refinement_start",
                "message": "开始目录结构精化...",
            }
        }

        for round_num in range(1, self.MAX_ROUNDS + 1):
            self._current_round = round_num

            yield {
                "event": "progress",
                "data": {
                    "stage": "refinement_round",
                    "message": f"精化轮次 {round_num}/{self.MAX_ROUNDS}",
                    "round": round_num,
                }
            }

            # 1. 评估当前质量（并记录历史）
            metrics = self._evaluate_and_record(round_num)

            yield {
                "event": "quality_evaluated",
                "data": {
                    "round": round_num,
                    "score": metrics.overall_score,
                    "grade": metrics.get_grade(),
                    "issues_count": len(metrics.issues),
                }
            }

            stop_reason, fixable_issues, fixed_count = self._decide_or_apply_fixes(metrics)
            if stop_reason in ("quality_threshold_met", "no_fixable_issues", "no_fixes_applied"):
                messages = {
                    "quality_threshold_met": "质量达标，精化完成",
                    "no_fixable_issues": "无可修复的问题，精化完成",
                    "no_fixes_applied": "本轮未修复任何问题，精化完成",
                }
                yield {
                    "event": "progress",
                    "data": {
                        "stage": "refinement_complete",
                        "message": messages[stop_reason],
                        "reason": stop_reason,
                    }
                }
                break

            yield {
                "event": "fixes_applied",
                "data": {
                    "round": round_num,
                    "fixed_count": fixed_count,
                    "issues_fixed": [i["issue_type"] for i in fixable_issues[:5]],
                }
            }

        # 最终评估
        evaluator = QualityEvaluator(self.profile, self.decision, self.output)
        final_metrics = evaluator.evaluate()

        yield {
            "event": "refinement_complete",
            "data": {
                "total_rounds": self._current_round,
                "final_score": final_metrics.overall_score,
                "final_grade": final_metrics.get_grade(),
                "history": self._history,
            }
        }

    def _evaluate_and_record(self, round_num: int) -> QualityMetrics:
        """评估当前质量并记录历史（同步/流式共用）"""
        evaluator = QualityEvaluator(self.profile, self.decision, self.output)
        metrics = evaluator.evaluate()

        self._history.append({
            "round": round_num,
            "score": metrics.overall_score,
            "grade": metrics.get_grade(),
            "issues": len(metrics.issues),
        })
        return metrics

    def _decide_or_apply_fixes(
        self, metrics: QualityMetrics
    ) -> Tuple[Optional[str], List[Dict[str, Any]], int]:
        """判断是否应停止；若可继续则应用修复并返回结果。"""
        if metrics.overall_score >= self.QUALITY_THRESHOLD:
            return "quality_threshold_met", [], 0

        fixable_issues = self._get_fixable_issues(metrics)
        if not fixable_issues:
            return "no_fixable_issues", [], 0

        fixed_count = self._apply_fixes(fixable_issues)
        if fixed_count == 0:
            return "no_fixes_applied", fixable_issues, 0

        return None, fixable_issues, fixed_count

    def _get_fixable_issues(self, metrics: QualityMetrics) -> List[Dict[str, Any]]:
        """
        获取可修复的问题列表

        按优先级排序：严重程度 > 问题类型
        """
        fixable_types = {
            IssueType.INCOMPLETE_FILE_INFO.value,
            IssueType.MISSING_MODULE.value,
            IssueType.NAMING_VIOLATION.value,
            IssueType.LARGE_DIRECTORY.value,
        }

        fixable = []
        for issue in metrics.issues:
            issue_type = issue.get("issue_type", "")
            if issue_type in fixable_types:
                fixable.append(issue)

        # 按严重程度排序
        severity_order = {
            IssueSeverity.CRITICAL.value: 0,
            IssueSeverity.WARNING.value: 1,
            IssueSeverity.INFO.value: 2,
        }
        fixable.sort(key=lambda x: severity_order.get(x.get("severity", ""), 3))

        return fixable

    def _apply_fixes(self, issues: List[Dict[str, Any]]) -> int:
        """
        应用修复

        Returns:
            修复的问题数量
        """
        fixed_count = 0

        for issue in issues:
            issue_type = issue.get("issue_type", "")

            if issue_type == IssueType.INCOMPLETE_FILE_INFO.value:
                if self._fix_incomplete_file_info(issue):
                    fixed_count += 1

            elif issue_type == IssueType.MISSING_MODULE.value:
                if self._fix_missing_module(issue):
                    fixed_count += 1

            elif issue_type == IssueType.NAMING_VIOLATION.value:
                if self._fix_naming_violation(issue):
                    fixed_count += 1

            elif issue_type == IssueType.LARGE_DIRECTORY.value:
                # 大目录问题需要结构重组，暂不自动修复
                pass

        return fixed_count

    def _fix_incomplete_file_info(self, issue: Dict[str, Any]) -> bool:
        """
        修复文件信息不完整问题

        为缺少描述的文件生成默认描述
        """
        affected_paths = issue.get("affected_paths", [])
        if not affected_paths:
            return False

        fixed = False
        for path in affected_paths:
            for f in self.output.files:
                if f.path == path:
                    # 补充缺失的信息
                    if not f.description or len(f.description) < 10:
                        f.description = self._generate_default_description(f)
                        fixed = True
                    if not f.purpose or len(f.purpose) < 10:
                        f.purpose = self._generate_default_purpose(f)
                        fixed = True
                    break

        return fixed

    def _generate_default_description(self, file: FileSpec) -> str:
        """生成默认文件描述"""
        base_name = file.filename.rsplit(".", 1)[0] if "." in file.filename else file.filename

        # 根据文件名推断功能
        descriptions = {
            "service": "实现业务服务逻辑",
            "repository": "实现数据访问层",
            "controller": "处理API请求",
            "routes": "定义路由配置",
            "models": "定义数据模型",
            "entity": "定义领域实体",
            "interface": "定义接口规范",
            "types": "定义类型声明",
            "utils": "通用工具函数",
            "constants": "常量定义",
            "config": "配置管理",
            "__init__": "Python包初始化",
        }

        for key, desc in descriptions.items():
            if key in base_name.lower():
                return desc

        return f"实现{base_name}相关功能"

    def _generate_default_purpose(self, file: FileSpec) -> str:
        """生成默认文件存在理由"""
        file_type = file.file_type or "source"

        purposes = {
            "source": "实现核心业务功能",
            "test": "验证功能正确性",
            "config": "管理应用配置",
            "doc": "提供使用文档",
            "interface": "定义模块契约",
            "model": "表达数据结构",
        }

        return purposes.get(file_type, "支持模块功能实现")

    def _fix_missing_module(self, issue: Dict[str, Any]) -> bool:
        """
        修复缺失模块问题

        为未覆盖的模块创建基本目录和文件
        """
        affected_modules = issue.get("affected_modules", [])
        if not affected_modules:
            return False

        fixed = False
        for module_number in affected_modules:
            # 获取模块信息
            module = self.profile.get_module_by_number(module_number)
            if not module:
                continue

            # 查找对应的放置计划
            placement = self.decision.get_placement_by_module(module_number)
            if not placement:
                continue

            # 检查目录是否已存在
            existing_paths = {d.path for d in self.output.directories}
            if placement.target_path not in existing_paths:
                # 创建目录
                new_dir = DirectorySpec(
                    path=placement.target_path,
                    description=f"{module.name}: {module.description[:100]}",
                    module_numbers=[module_number],
                )
                self.output.directories.append(new_dir)
                fixed = True

            # 检查文件是否已存在
            existing_files = {f.path for f in self.output.files}
            for filename in placement.files_to_create:
                file_path = f"{placement.target_path}/{filename}"
                if file_path not in existing_files:
                    # 创建文件
                    new_file = FileSpec(
                        path=file_path,
                        filename=filename,
                        file_type="source",
                        language=self.profile.primary_language,
                        description=self._generate_default_description(
                            FileSpec(path=file_path, filename=filename,
                                    file_type="source", language="",
                                    description="", purpose="",
                                    module_number=module_number, priority="medium",
                                    dependencies=[], dependency_reasons="",
                                    implementation_notes="")
                        ),
                        purpose="支持模块功能实现",
                        module_number=module_number,
                        priority="medium",
                        dependencies=[],
                        dependency_reasons="",
                        implementation_notes="",
                    )
                    self.output.files.append(new_file)
                    fixed = True

        return fixed

    def _fix_naming_violation(self, issue: Dict[str, Any]) -> bool:
        """
        修复命名违规问题

        将不符合约定的名称转换为正确格式
        （注意：只修复元数据，不修改实际路径）
        """
        # 命名修复较为复杂，涉及路径变更
        # 当前版本仅记录问题，不自动修复
        # 未来版本可以添加重命名功能
        return False

    def get_refinement_summary(self) -> Dict[str, Any]:
        """
        获取精化摘要

        Returns:
            精化过程的详细摘要
        """
        if not self._history:
            return {"rounds": 0, "history": []}

        initial_score = self._history[0]["score"] if self._history else 0
        final_score = self._history[-1]["score"] if self._history else 0

        return {
            "rounds": len(self._history),
            "initial_score": initial_score,
            "final_score": final_score,
            "improvement": final_score - initial_score,
            "history": self._history,
        }
