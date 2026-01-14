"""
目录结构质量评估器

阶段三（后半）：多维度评估生成的目录结构质量。
提供覆盖率、内聚性、耦合度、可理解性、架构一致性等指标。
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

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

logger = logging.getLogger(__name__)


class QualityEvaluator:
    """
    目录结构质量评估器

    多维度评估生成的目录结构，提供综合质量评分和改进建议。
    """

    def __init__(
        self,
        profile: ProjectProfile,
        decision: ArchitectureDecision,
        output: BruteForceOutput,
    ):
        """
        初始化质量评估器

        Args:
            profile: 项目画像
            decision: 架构决策
            output: 生成的目录结构
        """
        self.profile = profile
        self.decision = decision
        self.output = output

        # 构建索引
        self._dir_by_path: Dict[str, DirectorySpec] = {
            d.path: d for d in output.directories
        }
        self._file_by_path: Dict[str, FileSpec] = {
            f.path: f for f in output.files
        }
        self._files_by_dir: Dict[str, List[FileSpec]] = defaultdict(list)
        for f in output.files:
            dir_path = "/".join(f.path.split("/")[:-1])
            self._files_by_dir[dir_path].append(f)

        # 问题收集
        self._issues: List[StructureIssue] = []

    def evaluate(self) -> QualityMetrics:
        """
        执行完整的质量评估

        Returns:
            QualityMetrics: 质量指标
        """
        logger.info("开始评估目录结构质量")

        # 重置问题列表
        self._issues = []

        # 1. 评估覆盖率
        module_coverage = self._evaluate_module_coverage()
        file_completeness = self._evaluate_file_completeness()

        # 2. 评估内聚性
        directory_cohesion = self._evaluate_directory_cohesion()
        module_cohesion = self._evaluate_module_cohesion()

        # 3. 评估耦合度
        coupling_score, circular_deps, cross_layer = self._evaluate_coupling()

        # 4. 评估可理解性
        depth_score = self._evaluate_depth()
        naming_consistency = self._evaluate_naming_consistency()
        structure_clarity = self._evaluate_structure_clarity()

        # 5. 评估架构一致性
        pattern_adherence = self._evaluate_pattern_adherence()

        # 6. 统计信息
        total_directories = len(self.output.directories)
        total_files = len(self.output.files)
        max_depth = self._calculate_max_depth()
        avg_files = total_files / total_directories if total_directories > 0 else 0

        metrics = QualityMetrics(
            # 覆盖率
            module_coverage=module_coverage,
            file_completeness=file_completeness,
            # 内聚性
            directory_cohesion=directory_cohesion,
            module_cohesion=module_cohesion,
            # 耦合度
            coupling_score=coupling_score,
            circular_dependencies=circular_deps,
            cross_layer_violations=cross_layer,
            # 可理解性
            depth_score=depth_score,
            naming_consistency=naming_consistency,
            structure_clarity=structure_clarity,
            # 架构一致性
            pattern_adherence=pattern_adherence,
            # 问题
            issues=[i.to_dict() for i in self._issues],
            # 统计
            total_directories=total_directories,
            total_files=total_files,
            max_depth=max_depth,
            avg_files_per_dir=avg_files,
        )

        logger.info(
            "质量评估完成: 综合评分=%.2f, 等级=%s, 问题数=%d",
            metrics.overall_score,
            metrics.get_grade(),
            len(self._issues),
        )

        return metrics

    def _evaluate_module_coverage(self) -> float:
        """
        评估模块覆盖率

        检查所有模块是否都有对应的目录/文件
        """
        all_modules = self.profile.get_all_modules()
        if not all_modules:
            return 1.0

        covered_modules = set()

        # 检查每个文件关联的模块
        for f in self.output.files:
            if f.module_number and f.module_number > 0:
                covered_modules.add(f.module_number)

        # 检查每个目录关联的模块
        for d in self.output.directories:
            for mn in d.module_numbers:
                if mn > 0:
                    covered_modules.add(mn)

        # 找出未覆盖的模块
        all_module_numbers = {m.module_number for m in all_modules}
        uncovered = all_module_numbers - covered_modules

        if uncovered:
            # 记录问题
            uncovered_names = [
                m.name for m in all_modules if m.module_number in uncovered
            ]
            self._issues.append(StructureIssue(
                issue_type=IssueType.MISSING_MODULE,
                severity=IssueSeverity.WARNING,
                description=f"有{len(uncovered)}个模块未被覆盖",
                affected_modules=list(uncovered),
                suggestion=f"缺少模块: {', '.join(uncovered_names[:5])}",
            ))

        coverage = len(covered_modules) / len(all_module_numbers)
        return coverage

    def _evaluate_file_completeness(self) -> float:
        """
        评估文件信息完整度

        检查文件是否有完整的描述、目的、依赖等信息
        """
        if not self.output.files:
            return 1.0

        completeness_scores = []

        for f in self.output.files:
            score = 0.0
            total_fields = 5

            # 检查各字段
            if f.description and len(f.description) > 10:
                score += 1
            if f.purpose and len(f.purpose) > 10:
                score += 1
            if f.file_type:
                score += 1
            if f.language:
                score += 1
            if f.module_number is not None:
                score += 1

            completeness_scores.append(score / total_fields)

        # 找出信息不完整的文件
        incomplete_files = [
            f.path for f, s in zip(self.output.files, completeness_scores)
            if s < 0.6
        ]

        if incomplete_files:
            self._issues.append(StructureIssue(
                issue_type=IssueType.INCOMPLETE_FILE_INFO,
                severity=IssueSeverity.INFO,
                description=f"有{len(incomplete_files)}个文件信息不完整",
                affected_paths=incomplete_files[:10],
                suggestion="建议补充文件的description和purpose字段",
            ))

        return sum(completeness_scores) / len(completeness_scores)

    def _evaluate_directory_cohesion(self) -> float:
        """
        评估目录内聚性

        检查同一目录下的文件是否功能相关
        """
        if not self._files_by_dir:
            return 1.0

        cohesion_scores = []

        for dir_path, files in self._files_by_dir.items():
            if len(files) <= 1:
                cohesion_scores.append(1.0)
                continue

            # 统计文件类型
            file_types = Counter(f.file_type for f in files)
            # 统计关联的模块
            module_numbers = set(f.module_number for f in files if f.module_number)

            # 计算内聚性分数
            # 1. 文件类型一致性（类型越少越好）
            type_cohesion = 1.0 / len(file_types) if file_types else 0

            # 2. 模块关联性（关联模块越少越好，最好只关联一个）
            if len(module_numbers) == 0:
                module_cohesion = 0.5  # 无关联模块，中等分数
            elif len(module_numbers) == 1:
                module_cohesion = 1.0  # 只关联一个模块，高分
            else:
                module_cohesion = 1.0 / len(module_numbers)

            cohesion = (type_cohesion + module_cohesion) / 2
            cohesion_scores.append(cohesion)

        return sum(cohesion_scores) / len(cohesion_scores)

    def _evaluate_module_cohesion(self) -> float:
        """
        评估模块职责一致性

        检查每个模块的文件是否都在相关目录下
        """
        # 按模块分组文件
        files_by_module: Dict[int, List[FileSpec]] = defaultdict(list)
        for f in self.output.files:
            if f.module_number and f.module_number > 0:
                files_by_module[f.module_number].append(f)

        if not files_by_module:
            return 1.0

        cohesion_scores = []

        for module_number, files in files_by_module.items():
            if len(files) <= 1:
                cohesion_scores.append(1.0)
                continue

            # 检查文件是否在同一目录或相邻目录
            dirs = set()
            for f in files:
                dir_path = "/".join(f.path.split("/")[:-1])
                dirs.add(dir_path)

            # 目录越少，内聚性越高
            if len(dirs) == 1:
                cohesion_scores.append(1.0)
            elif len(dirs) <= 2:
                cohesion_scores.append(0.8)
            elif len(dirs) <= 3:
                cohesion_scores.append(0.6)
            else:
                cohesion_scores.append(0.4)

        return sum(cohesion_scores) / len(cohesion_scores)

    def _evaluate_coupling(self) -> Tuple[float, int, int]:
        """
        评估耦合度

        Returns:
            (耦合度评分, 循环依赖数, 跨层违规数)
        """
        # 循环依赖数（从项目画像获取）
        circular_deps = len(self.profile.dependency_graph.cycles)

        # 跨层违规检测
        cross_layer_violations = self._detect_cross_layer_violations()

        # 计算耦合度评分（越低越好，转换为越高越好）
        # 基础分 1.0，每个循环依赖 -0.1，每个跨层违规 -0.05
        base_score = 1.0
        penalty = circular_deps * 0.1 + cross_layer_violations * 0.05
        coupling_score = max(0.0, base_score - penalty)

        if circular_deps > 0:
            self._issues.append(StructureIssue(
                issue_type=IssueType.CIRCULAR_DEPENDENCY,
                severity=IssueSeverity.WARNING,
                description=f"存在{circular_deps}个循环依赖",
                suggestion="检查依赖关系，打破循环依赖",
            ))

        if cross_layer_violations > 0:
            self._issues.append(StructureIssue(
                issue_type=IssueType.LAYER_VIOLATION,
                severity=IssueSeverity.WARNING,
                description=f"存在{cross_layer_violations}个跨层违规",
                suggestion="检查层级依赖关系，确保遵循架构约定",
            ))

        return coupling_score, circular_deps, cross_layer_violations

    def _detect_cross_layer_violations(self) -> int:
        """
        检测跨层违规

        检查文件是否违反了架构层级的依赖规则
        """
        violations = 0

        # 构建层级路径映射
        layer_by_path: Dict[str, str] = {}
        for layer in self.decision.layers:
            layer_by_path[layer.path] = layer.name

        # 获取层级允许的依赖
        allowed_deps: Dict[str, Set[str]] = {}
        for layer in self.decision.layers:
            allowed_deps[layer.name] = set(layer.allowed_dependencies)

        # 检查每个文件的依赖是否违规
        for f in self.output.files:
            if not f.dependencies:
                continue

            # 确定文件所在层级
            file_layer = None
            for path, layer_name in layer_by_path.items():
                if f.path.startswith(path):
                    file_layer = layer_name
                    break

            if not file_layer:
                continue

            # 检查依赖的模块是否在允许的层级
            # （简化实现：只检查依赖数量是否合理）
            if len(f.dependencies) > 5:
                violations += 1

        return violations

    def _evaluate_depth(self) -> float:
        """
        评估层级深度

        目录层级越浅越好（更易理解）
        """
        max_depth = self._calculate_max_depth()

        # 根据架构模式设置推荐深度
        recommended_depth = 4
        if self.decision.pattern == ArchitecturePattern.SIMPLE:
            recommended_depth = 3
        elif self.decision.pattern == ArchitecturePattern.FEATURE_BASED:
            recommended_depth = 4

        if max_depth <= recommended_depth:
            score = 1.0
        elif max_depth <= recommended_depth + 1:
            score = 0.8
        elif max_depth <= recommended_depth + 2:
            score = 0.6
        else:
            score = 0.4
            self._issues.append(StructureIssue(
                issue_type=IssueType.DEEP_NESTING,
                severity=IssueSeverity.WARNING,
                description=f"目录层级过深（{max_depth}层），推荐不超过{recommended_depth}层",
                suggestion="考虑扁平化目录结构",
            ))

        return score

    def _calculate_max_depth(self) -> int:
        """计算最大目录深度"""
        if not self.output.directories:
            return 0

        max_depth = 0
        for d in self.output.directories:
            depth = d.path.count("/") + 1
            max_depth = max(max_depth, depth)

        return max_depth

    def _evaluate_naming_consistency(self) -> float:
        """
        评估命名一致性

        检查文件和目录命名是否符合约定
        """
        expected_convention = self.decision.naming_convention
        violations = 0
        total = len(self.output.directories) + len(self.output.files)

        if total == 0:
            return 1.0

        # 检查目录命名
        for d in self.output.directories:
            dir_name = d.path.split("/")[-1]
            if not self._check_naming_convention(dir_name, expected_convention):
                violations += 1

        # 检查文件命名（不含扩展名）
        for f in self.output.files:
            file_name = f.filename.rsplit(".", 1)[0] if "." in f.filename else f.filename
            # __init__.py 等特殊文件跳过
            if file_name.startswith("__"):
                continue
            if not self._check_naming_convention(file_name, expected_convention):
                violations += 1

        if violations > 0:
            self._issues.append(StructureIssue(
                issue_type=IssueType.NAMING_VIOLATION,
                severity=IssueSeverity.INFO,
                description=f"有{violations}个命名不符合{expected_convention}约定",
                suggestion=f"建议统一使用{expected_convention}命名风格",
            ))

        return 1.0 - (violations / total)

    def _check_naming_convention(self, name: str, convention: str) -> bool:
        """检查名称是否符合命名约定"""
        if convention == "snake_case":
            # 全小写，用下划线分隔
            return bool(re.match(r'^[a-z][a-z0-9_]*$', name))
        elif convention == "kebab-case":
            # 全小写，用连字符分隔
            return bool(re.match(r'^[a-z][a-z0-9-]*$', name))
        elif convention == "camelCase":
            # 首字母小写，后续单词首字母大写
            return bool(re.match(r'^[a-z][a-zA-Z0-9]*$', name))
        elif convention == "PascalCase":
            # 每个单词首字母大写
            return bool(re.match(r'^[A-Z][a-zA-Z0-9]*$', name))
        return True

    def _evaluate_structure_clarity(self) -> float:
        """
        评估结构清晰度

        检查目录结构是否清晰、易于理解
        """
        clarity_score = 1.0

        # 1. 检查是否有过大的目录（文件过多）
        large_dirs = []
        for dir_path, files in self._files_by_dir.items():
            if len(files) > 15:
                large_dirs.append((dir_path, len(files)))
                clarity_score -= 0.05

        if large_dirs:
            self._issues.append(StructureIssue(
                issue_type=IssueType.LARGE_DIRECTORY,
                severity=IssueSeverity.INFO,
                description=f"有{len(large_dirs)}个目录文件过多",
                affected_paths=[d[0] for d in large_dirs[:5]],
                suggestion="考虑将大目录拆分为子目录",
            ))

        # 2. 检查是否有重复的目录名
        dir_names = [d.path.split("/")[-1] for d in self.output.directories]
        name_counts = Counter(dir_names)
        duplicates = [name for name, count in name_counts.items() if count > 1]

        if duplicates:
            self._issues.append(StructureIssue(
                issue_type=IssueType.DUPLICATE_STRUCTURE,
                severity=IssueSeverity.INFO,
                description=f"存在重复的目录名: {', '.join(duplicates[:5])}",
                suggestion="考虑使用更具描述性的目录名",
            ))
            clarity_score -= 0.05 * len(duplicates)

        return max(0.0, clarity_score)

    def _evaluate_pattern_adherence(self) -> float:
        """
        评估架构模式符合度

        检查生成的结构是否符合选定的架构模式
        """
        pattern = self.decision.pattern
        adherence_score = 1.0

        # 检查必要的层级目录是否存在
        expected_layers = {layer.path for layer in self.decision.layers}
        existing_paths = {d.path for d in self.output.directories}

        missing_layers = []
        for layer_path in expected_layers:
            # 检查是否存在该层级或其子目录
            has_layer = any(
                p == layer_path or p.startswith(layer_path + "/")
                for p in existing_paths
            )
            if not has_layer:
                missing_layers.append(layer_path)

        if missing_layers:
            adherence_score -= 0.1 * len(missing_layers)
            self._issues.append(StructureIssue(
                issue_type=IssueType.LAYER_VIOLATION,
                severity=IssueSeverity.WARNING,
                description=f"缺少架构层级目录: {', '.join(missing_layers)}",
                suggestion=f"按照{pattern.value}架构模式添加缺失的层级",
            ))

        # 检查模块是否放置在正确的层级
        misplaced_modules = 0
        for placement in self.decision.module_placements:
            # 检查目标路径是否存在
            if placement.target_path not in existing_paths:
                # 可能是子目录
                has_path = any(
                    p.startswith(placement.target_path)
                    for p in existing_paths
                )
                if not has_path:
                    misplaced_modules += 1

        if misplaced_modules > 0:
            adherence_score -= 0.02 * misplaced_modules

        return max(0.0, adherence_score)

    def get_improvement_suggestions(self) -> List[str]:
        """
        获取改进建议

        Returns:
            改进建议列表
        """
        suggestions = []

        # 根据问题生成建议
        for issue in self._issues:
            if issue.severity == IssueSeverity.CRITICAL:
                suggestions.append(f"[严重] {issue.suggestion}")
            elif issue.severity == IssueSeverity.WARNING:
                suggestions.append(f"[警告] {issue.suggestion}")

        # 添加通用建议
        if not suggestions:
            suggestions.append("目录结构质量良好，无需特别改进")

        return suggestions
