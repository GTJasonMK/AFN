"""
语义分块算法可视化测试GUI

交互式调整分块参数，实时查看分块效果。
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "backend"))

import numpy as np
from typing import List, Optional, Callable

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QSpinBox, QDoubleSpinBox, QTextEdit, QPushButton,
    QGroupBox, QSplitter, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QComboBox, QProgressBar, QMessageBox, QScrollArea,
    QFrame, QTreeWidget, QTreeWidgetItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# 尝试导入matplotlib用于嵌入图表
try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt

    # 设置中文字体支持
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[警告] matplotlib 未安装，将无法显示图表")

# 导入语义分块器
from app.services.rag_common.semantic_chunker import (
    SemanticChunker,
    SemanticChunkConfig,
    ChunkResult,
)


# ============================================================
# 示例文本
# ============================================================

NOVEL_SAMPLE = """林逸站在悬崖边，望着远处连绵的山峦。夕阳的余晖洒在他的脸上，映出一抹淡淡的金色。他已经在这条路上走了三年，从一个默默无闻的小修士，成长为如今的金丹期强者。

"师兄，我们该回去了。"身后传来师妹苏瑶清脆的声音。

林逸转过身，看着这个陪伴自己多年的师妹。苏瑶穿着淡蓝色的道袍，手中握着一柄碧绿的长剑，剑身上流转着淡淡的灵光。她的眼中带着担忧，显然是在为即将到来的宗门大比而忧心。

"无妨，让我再看看这片山河。"林逸淡淡地说道，"三年前，我就是在这里立下誓言，要让所有看不起我们的人闭嘴。"

苏瑶轻轻叹了口气。她知道师兄心中的执念，也明白这次大比对他们意味着什么。宗门内部的争斗日益激烈，若是这次大比失利，他们清风峰恐怕再难有立足之地。

远处的天空突然泛起一阵异样的波动。林逸眉头一皱，神识探出，顿时脸色微变。那是一股极其强大的气息，至少是元婴期的修为！

"有人来了！"林逸低喝一声，一把拉过苏瑶，身形一闪，已经隐入了旁边的密林之中。

就在他们刚刚消失的瞬间，一道流光划过天际，正是一名身穿黑袍的老者。他悬停在半空，浑浊的眼睛扫视着四周，嘴角勾起一抹阴冷的笑意。

"有意思，居然能在我到来之前发现端倪。"黑袍老者自言自语道，"看来这清风峰，还真是藏龙卧虎啊。"

林逸紧紧握着苏瑶的手，感受到她掌心的汗意。他知道，这位不速之客绝非善类。而他们现在的实力，根本不是对方的对手。

"我们必须尽快回到宗门。"林逸压低声音说道，"这件事，必须禀报掌门师伯。"

苏瑶点了点头，两人悄无声息地在林中穿行。他们不敢动用灵力，生怕暴露自己的行踪。好在林逸对这片山林极为熟悉，很快就找到了一条隐蔽的小路。

然而，就在他们即将离开危险区域的时候，天空中再次传来一声冷笑。

"想走？晚了！"
"""

CODING_SAMPLE = """## 功能概述

本功能实现用户认证模块，包括登录、注册、密码重置等核心功能。系统采用JWT令牌进行身份验证，支持多种登录方式。

## 技术要求

### 1. 登录功能

用户可以通过用户名密码或第三方OAuth进行登录。登录成功后，系统生成JWT令牌返回给客户端。令牌有效期为24小时，支持刷新机制。

登录流程需要验证用户名和密码的有效性，同时检查账户是否被锁定。连续5次登录失败将触发账户锁定机制，锁定时间为30分钟。

### 2. 注册功能

新用户注册需要提供用户名、邮箱和密码。系统会发送验证邮件到用户邮箱，用户需要在24小时内完成邮箱验证。

密码强度要求：至少8位字符，包含大小写字母、数字和特殊字符。用户名要求：4-20位字符，只能包含字母、数字和下划线。

### 3. 密码重置

用户可以通过邮箱申请密码重置。系统生成唯一的重置链接发送到用户邮箱，链接有效期为1小时。

重置密码时需要验证新密码符合强度要求，且不能与最近5次使用过的密码相同。

## 数据模型

用户表(users)包含以下字段：id主键、username用户名、email邮箱、password_hash密码哈希、created_at创建时间、updated_at更新时间、is_active是否激活、locked_until锁定截止时间。

登录日志表(login_logs)记录每次登录尝试，包含用户ID、登录时间、IP地址、设备信息、登录结果等字段。

## 接口设计

POST /api/auth/login - 用户登录接口
POST /api/auth/register - 用户注册接口
POST /api/auth/refresh - 令牌刷新接口
POST /api/auth/password/reset - 申请密码重置
POST /api/auth/password/confirm - 确认密码重置

所有接口返回统一的JSON格式，包含code状态码、message消息、data数据三个字段。
"""


# ============================================================
# 嵌入函数
# ============================================================

_embedding_model = None
_embedding_func = None


def get_embedding_func():
    """获取嵌入函数（懒加载）"""
    global _embedding_model, _embedding_func

    if _embedding_func is not None:
        return _embedding_func, True

    # 尝试加载真实模型
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        async def real_embedding(sentences: list) -> np.ndarray:
            embeddings = _embedding_model.encode(sentences, convert_to_numpy=True)
            return embeddings

        _embedding_func = real_embedding
        return _embedding_func, True
    except Exception as e:
        print(f"[警告] 加载sentence-transformers失败: {e}")

        # 使用模拟嵌入
        async def mock_embedding(sentences: list) -> np.ndarray:
            dim = 384
            embeddings = []
            for text in sentences:
                features = np.zeros(dim)
                for i, char in enumerate(text[:dim]):
                    features[i % dim] += ord(char) / 1000.0
                features[0] = len(text) / 100.0
                norm = np.linalg.norm(features)
                if norm > 0:
                    features = features / norm
                embeddings.append(features)
            return np.array(embeddings)

        _embedding_func = mock_embedding
        return _embedding_func, False


# ============================================================
# 工作线程
# ============================================================

class ChunkWorker(QThread):
    """分块计算工作线程"""

    finished = pyqtSignal(object)  # 返回结果字典
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, text: str, config: SemanticChunkConfig):
        super().__init__()
        self.text = text
        self.config = config

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._process())
            loop.close()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    async def _process(self):
        self.progress.emit("加载嵌入模型...")
        embedding_func, is_real = get_embedding_func()

        self.progress.emit("初始化分块器...")
        chunker = SemanticChunker(config=self.config)

        self.progress.emit("分句处理...")
        sentences = chunker._split_sentences(self.text)

        if not sentences:
            return {"error": "未能分割出句子"}

        self.progress.emit(f"生成嵌入向量 ({len(sentences)} 句)...")
        embeddings = await embedding_func(sentences)

        self.progress.emit("构建相似度矩阵...")
        sim_matrix = chunker._build_similarity_matrix(embeddings)

        self.progress.emit("应用结构增强...")
        enhanced_matrix = chunker._apply_structure_enhancement(sim_matrix, self.config)

        self.progress.emit("执行动态规划分块...")
        chunks = await chunker.chunk_text_async(self.text, embedding_func, self.config)

        # 计算切分点
        cut_points = [0]
        for chunk in chunks:
            cut_points.append(chunk.end_sentence_idx)

        return {
            "sentences": sentences,
            "sim_matrix": sim_matrix,
            "enhanced_matrix": enhanced_matrix,
            "chunks": chunks,
            "cut_points": cut_points,
            "is_real_embedding": is_real,
        }


# ============================================================
# 图表组件
# ============================================================

class MatplotlibCanvas(FigureCanvas):
    """Matplotlib画布组件"""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)

    def clear(self):
        self.fig.clear()
        self.draw()


class SimilarityMatrixWidget(QWidget):
    """相似度矩阵可视化组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if MATPLOTLIB_AVAILABLE:
            self.canvas = MatplotlibCanvas(self, width=6, height=5, dpi=100)
            layout.addWidget(self.canvas)
        else:
            self.canvas = None
            layout.addWidget(QLabel("需要安装 matplotlib 才能显示图表"))

    def update_plot(self, matrix: np.ndarray, cut_points: list, title: str = "相似度矩阵"):
        if not self.canvas:
            return

        self.canvas.fig.clear()
        ax = self.canvas.fig.add_subplot(111)

        # 绘制热力图
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')

        # 添加分块边界线
        for cp in cut_points[1:-1]:
            ax.axhline(y=cp - 0.5, color='blue', linewidth=2, linestyle='--')
            ax.axvline(x=cp - 0.5, color='blue', linewidth=2, linestyle='--')

        # 标注分块区域
        for i in range(len(cut_points) - 1):
            start = cut_points[i]
            end = cut_points[i + 1]
            mid = (start + end) / 2
            ax.text(mid, mid, f'{i+1}',
                    ha='center', va='center', fontsize=10,
                    color='white', fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='blue', alpha=0.5))

        ax.set_xlabel('句子索引')
        ax.set_ylabel('句子索引')
        ax.set_title(title)

        self.canvas.fig.colorbar(im, ax=ax, label='余弦相似度')
        self.canvas.fig.tight_layout()
        self.canvas.draw()


class ChunkStatsWidget(QWidget):
    """分块统计可视化组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if MATPLOTLIB_AVAILABLE:
            self.canvas = MatplotlibCanvas(self, width=8, height=4, dpi=100)
            layout.addWidget(self.canvas)
        else:
            self.canvas = None
            layout.addWidget(QLabel("需要安装 matplotlib 才能显示图表"))

    def update_plot(self, chunks: List[ChunkResult]):
        if not self.canvas or not chunks:
            return

        self.canvas.fig.clear()

        # 子图1: 句子数分布
        ax1 = self.canvas.fig.add_subplot(131)
        sentence_counts = [c.sentence_count for c in chunks]
        bars1 = ax1.bar(range(1, len(chunks) + 1), sentence_counts, color='steelblue', alpha=0.8)
        ax1.set_xlabel('块索引')
        ax1.set_ylabel('句子数')
        ax1.set_title('每块句子数')
        for bar, count in zip(bars1, sentence_counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                    str(count), ha='center', va='bottom', fontsize=8)

        # 子图2: 字符长度分布
        ax2 = self.canvas.fig.add_subplot(132)
        char_lengths = [len(c.content) for c in chunks]
        bars2 = ax2.bar(range(1, len(chunks) + 1), char_lengths, color='coral', alpha=0.8)
        ax2.set_xlabel('块索引')
        ax2.set_ylabel('字符数')
        ax2.set_title('每块字符数')
        for bar, length in zip(bars2, char_lengths):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5,
                    str(length), ha='center', va='bottom', fontsize=8)

        # 子图3: 密度得分分布
        ax3 = self.canvas.fig.add_subplot(133)
        density_scores = [c.density_score for c in chunks]
        max_score = max(density_scores) if density_scores else 1
        colors = plt.cm.RdYlGn(np.array(density_scores) / max_score if max_score > 0 else density_scores)
        bars3 = ax3.bar(range(1, len(chunks) + 1), density_scores, color=colors, alpha=0.8)
        ax3.set_xlabel('块索引')
        ax3.set_ylabel('密度得分')
        ax3.set_title('块密度得分')
        avg_score = np.mean(density_scores)
        ax3.axhline(y=avg_score, color='red', linestyle='--', label=f'平均: {avg_score:.2f}')
        ax3.legend(fontsize=8)

        self.canvas.fig.tight_layout()
        self.canvas.draw()


class SentenceTreeWidget(QWidget):
    """句子树形列表组件 - 支持按块分组和展开/收起"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 工具栏
        toolbar = QHBoxLayout()
        self.expand_all_btn = QPushButton("全部展开")
        self.expand_all_btn.clicked.connect(self._expand_all)
        toolbar.addWidget(self.expand_all_btn)

        self.collapse_all_btn = QPushButton("全部收起")
        self.collapse_all_btn.clicked.connect(self._collapse_all)
        toolbar.addWidget(self.collapse_all_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 树形控件
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["块/句子", "字符数", "内容预览"])
        self.tree.setColumnWidth(0, 120)
        self.tree.setColumnWidth(1, 80)
        self.tree.header().setStretchLastSection(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)

        # 完整内容显示区
        self.detail_group = QGroupBox("完整内容 (双击句子查看)")
        detail_layout = QVBoxLayout(self.detail_group)
        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setMaximumHeight(150)
        detail_layout.addWidget(self.detail_text)
        layout.addWidget(self.detail_group)

    def update_data(self, sentences: List[str], chunks: List[ChunkResult], cut_points: List[int]):
        """更新句子数据"""
        self.tree.clear()
        self.detail_text.clear()

        if not sentences or not chunks:
            return

        # 定义颜色方案
        chunk_bg_color = QColor(70, 130, 180)  # 钢蓝色背景
        chunk_text_color = QColor(255, 255, 255)  # 白色文字
        sent_even_bg = QColor(245, 245, 245)  # 偶数行浅灰背景
        sent_odd_bg = QColor(255, 255, 255)  # 奇数行白色背景
        sent_text_color = QColor(33, 33, 33)  # 深灰色文字

        # 按块分组句子
        for chunk_idx, chunk in enumerate(chunks):
            # 创建块节点
            chunk_item = QTreeWidgetItem()
            chunk_item.setText(0, f"块 {chunk_idx + 1}")
            chunk_item.setText(1, f"{len(chunk.content)} 字")
            chunk_item.setText(2, f"[{chunk.start_sentence_idx}-{chunk.end_sentence_idx}) 共{chunk.sentence_count}句 密度:{chunk.density_score:.3f}")

            # 设置块节点样式 - 深色背景配白色文字
            for col in range(3):
                chunk_item.setBackground(col, chunk_bg_color)
                chunk_item.setForeground(col, chunk_text_color)

            font = chunk_item.font(0)
            font.setBold(True)
            chunk_item.setFont(0, font)

            # 添加句子子节点
            for sent_idx in range(chunk.start_sentence_idx, chunk.end_sentence_idx):
                if sent_idx < len(sentences):
                    sent = sentences[sent_idx]
                    sent_item = QTreeWidgetItem()
                    sent_item.setText(0, f"  句 {sent_idx}")
                    sent_item.setText(1, f"{len(sent)} 字")

                    # 内容预览（截断长句子）
                    preview = sent.replace('\n', ' ')
                    if len(preview) > 80:
                        preview = preview[:80] + "..."
                    sent_item.setText(2, preview)

                    # 设置句子节点样式 - 交替背景色配深色文字
                    local_idx = sent_idx - chunk.start_sentence_idx
                    bg_color = sent_even_bg if local_idx % 2 == 0 else sent_odd_bg
                    for col in range(3):
                        sent_item.setBackground(col, bg_color)
                        sent_item.setForeground(col, sent_text_color)

                    # 存储完整内容
                    sent_item.setData(0, Qt.ItemDataRole.UserRole, sent)

                    chunk_item.addChild(sent_item)

            self.tree.addTopLevelItem(chunk_item)

        # 默认展开所有块
        self.tree.expandAll()

    def _expand_all(self):
        """展开所有"""
        self.tree.expandAll()

    def _collapse_all(self):
        """收起所有"""
        self.tree.collapseAll()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """双击查看完整内容"""
        # 获取存储的完整内容
        full_content = item.data(0, Qt.ItemDataRole.UserRole)
        if full_content:
            self.detail_text.setPlainText(full_content)
        else:
            # 如果是块节点，显示块的完整内容
            if item.childCount() > 0:
                contents = []
                for i in range(item.childCount()):
                    child = item.child(i)
                    sent = child.data(0, Qt.ItemDataRole.UserRole)
                    if sent:
                        contents.append(sent)
                self.detail_text.setPlainText("\n\n".join(contents))


# ============================================================
# 参数面板
# ============================================================

class ParameterPanel(QGroupBox):
    """参数调整面板"""

    parameterChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("分块参数", parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # 门控阈值
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("门控阈值 (τ):"))
        self.gate_threshold = QDoubleSpinBox()
        self.gate_threshold.setRange(0.0, 1.0)
        self.gate_threshold.setSingleStep(0.05)
        self.gate_threshold.setValue(0.3)
        self.gate_threshold.setToolTip("相似度低于此值时不进行距离增强")
        self.gate_threshold.valueChanged.connect(self.parameterChanged.emit)
        row1.addWidget(self.gate_threshold)
        layout.addLayout(row1)

        # 距离增强系数
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("距离增强 (α):"))
        self.alpha = QDoubleSpinBox()
        self.alpha.setRange(0.0, 1.0)
        self.alpha.setSingleStep(0.05)
        self.alpha.setValue(0.1)
        self.alpha.setToolTip("M'[i,j] = M[i,j] + α * M[i,j] * ln(1+d)")
        self.alpha.valueChanged.connect(self.parameterChanged.emit)
        row2.addWidget(self.alpha)
        layout.addLayout(row2)

        # 长度归一化指数
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("长度归一化 (γ):"))
        self.gamma = QDoubleSpinBox()
        self.gamma.setRange(0.5, 2.0)
        self.gamma.setSingleStep(0.1)
        self.gamma.setValue(1.1)
        self.gamma.setToolTip("Score = Sum / (len)^γ")
        self.gamma.valueChanged.connect(self.parameterChanged.emit)
        row3.addWidget(self.gamma)
        layout.addLayout(row3)

        # 最小块句子数
        row4 = QHBoxLayout()
        row4.addWidget(QLabel("最小句子数:"))
        self.min_sentences = QSpinBox()
        self.min_sentences.setRange(1, 20)
        self.min_sentences.setValue(2)
        self.min_sentences.valueChanged.connect(self.parameterChanged.emit)
        row4.addWidget(self.min_sentences)
        layout.addLayout(row4)

        # 最大块句子数
        row5 = QHBoxLayout()
        row5.addWidget(QLabel("最大句子数:"))
        self.max_sentences = QSpinBox()
        self.max_sentences.setRange(5, 50)
        self.max_sentences.setValue(15)
        self.max_sentences.valueChanged.connect(self.parameterChanged.emit)
        row5.addWidget(self.max_sentences)
        layout.addLayout(row5)

        # 最小块字符数
        row6 = QHBoxLayout()
        row6.addWidget(QLabel("最小字符数:"))
        self.min_chars = QSpinBox()
        self.min_chars.setRange(0, 500)
        self.min_chars.setValue(100)
        self.min_chars.valueChanged.connect(self.parameterChanged.emit)
        row6.addWidget(self.min_chars)
        layout.addLayout(row6)

        # 最大块字符数
        row7 = QHBoxLayout()
        row7.addWidget(QLabel("最大字符数:"))
        self.max_chars = QSpinBox()
        self.max_chars.setRange(200, 5000)
        self.max_chars.setSingleStep(100)
        self.max_chars.setValue(1500)
        self.max_chars.valueChanged.connect(self.parameterChanged.emit)
        row7.addWidget(self.max_chars)
        layout.addLayout(row7)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # 重叠开关
        row8 = QHBoxLayout()
        row8.addWidget(QLabel("启用重叠:"))
        self.with_overlap = QComboBox()
        self.with_overlap.addItems(["否", "是"])
        self.with_overlap.setCurrentIndex(0)
        self.with_overlap.setToolTip("是否在块之间添加重叠句子，提高上下文连贯性")
        self.with_overlap.currentIndexChanged.connect(self.parameterChanged.emit)
        self.with_overlap.currentIndexChanged.connect(self._on_overlap_changed)
        row8.addWidget(self.with_overlap)
        layout.addLayout(row8)

        # 重叠句子数
        row9 = QHBoxLayout()
        row9.addWidget(QLabel("重叠句子数:"))
        self.overlap_sentences = QSpinBox()
        self.overlap_sentences.setRange(1, 5)
        self.overlap_sentences.setValue(1)
        self.overlap_sentences.setToolTip("每个块开头重复前一个块的最后N个句子")
        self.overlap_sentences.setEnabled(False)  # 默认禁用
        self.overlap_sentences.valueChanged.connect(self.parameterChanged.emit)
        row9.addWidget(self.overlap_sentences)
        layout.addLayout(row9)

        # 预设按钮
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("预设:"))

        btn_novel = QPushButton("小说")
        btn_novel.clicked.connect(self._apply_novel_preset)
        preset_layout.addWidget(btn_novel)

        btn_coding = QPushButton("编程")
        btn_coding.clicked.connect(self._apply_coding_preset)
        preset_layout.addWidget(btn_coding)

        layout.addLayout(preset_layout)

    def _on_overlap_changed(self, index: int):
        """重叠开关变化时启用/禁用重叠句子数"""
        self.overlap_sentences.setEnabled(index == 1)

    def _apply_novel_preset(self):
        """应用小说预设"""
        self.gate_threshold.setValue(0.3)
        self.alpha.setValue(0.1)
        self.gamma.setValue(1.1)
        self.min_sentences.setValue(3)
        self.max_sentences.setValue(15)
        self.min_chars.setValue(100)
        self.max_chars.setValue(1200)
        self.with_overlap.setCurrentIndex(0)
        self.overlap_sentences.setValue(1)

    def _apply_coding_preset(self):
        """应用编程预设"""
        self.gate_threshold.setValue(0.3)
        self.alpha.setValue(0.1)
        self.gamma.setValue(1.1)
        self.min_sentences.setValue(2)
        self.max_sentences.setValue(15)
        self.min_chars.setValue(100)
        self.max_chars.setValue(1500)
        self.with_overlap.setCurrentIndex(0)
        self.overlap_sentences.setValue(1)

    def get_config(self) -> SemanticChunkConfig:
        """获取当前配置"""
        return SemanticChunkConfig(
            gate_threshold=self.gate_threshold.value(),
            alpha=self.alpha.value(),
            gamma=self.gamma.value(),
            min_chunk_sentences=self.min_sentences.value(),
            max_chunk_sentences=self.max_sentences.value(),
            min_chunk_chars=self.min_chars.value(),
            max_chunk_chars=self.max_chars.value(),
            with_overlap=self.with_overlap.currentIndex() == 1,
            overlap_sentences=self.overlap_sentences.value(),
        )


# ============================================================
# 主窗口
# ============================================================

class SemanticChunkerGUI(QMainWindow):
    """语义分块测试GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("语义分块算法测试工具")
        self.setMinimumSize(1200, 800)

        self.worker = None
        self.last_result = None

        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # 左侧面板：参数和文本输入
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(400)

        # 参数面板
        self.param_panel = ParameterPanel()
        left_layout.addWidget(self.param_panel)

        # 示例文本选择
        sample_group = QGroupBox("示例文本")
        sample_layout = QVBoxLayout(sample_group)

        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("选择示例:"))
        self.sample_combo = QComboBox()
        self.sample_combo.addItems(["小说章节", "编程Prompt", "自定义"])
        self.sample_combo.currentIndexChanged.connect(self._on_sample_changed)
        sample_row.addWidget(self.sample_combo)
        sample_layout.addLayout(sample_row)

        left_layout.addWidget(sample_group)

        # 文本输入
        text_group = QGroupBox("输入文本")
        text_layout = QVBoxLayout(text_group)
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("请输入要分块的文本...")
        self.text_input.setPlainText(NOVEL_SAMPLE)
        text_layout.addWidget(self.text_input)
        left_layout.addWidget(text_group)

        # 运行按钮
        btn_layout = QHBoxLayout()
        self.run_btn = QPushButton("运行分块")
        self.run_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.run_btn.clicked.connect(self._run_chunking)
        btn_layout.addWidget(self.run_btn)
        left_layout.addLayout(btn_layout)

        # 进度条
        self.progress_label = QLabel("就绪")
        left_layout.addWidget(self.progress_label)

        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("运行分块后显示统计信息")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        left_layout.addWidget(stats_group)

        main_layout.addWidget(left_panel)

        # 右侧面板：结果展示
        right_panel = QTabWidget()

        # Tab 1: 相似度矩阵
        matrix_tab = QWidget()
        matrix_layout = QVBoxLayout(matrix_tab)

        matrix_tabs = QTabWidget()

        # 原始矩阵
        self.original_matrix_widget = SimilarityMatrixWidget()
        matrix_tabs.addTab(self.original_matrix_widget, "原始矩阵")

        # 增强矩阵
        self.enhanced_matrix_widget = SimilarityMatrixWidget()
        matrix_tabs.addTab(self.enhanced_matrix_widget, "增强矩阵")

        matrix_layout.addWidget(matrix_tabs)
        right_panel.addTab(matrix_tab, "相似度矩阵")

        # Tab 2: 分块统计
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        self.chunk_stats_widget = ChunkStatsWidget()
        stats_layout.addWidget(self.chunk_stats_widget)
        right_panel.addTab(stats_tab, "分块统计")

        # Tab 3: 分块详情
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)

        self.chunk_table = QTableWidget()
        self.chunk_table.setColumnCount(5)
        self.chunk_table.setHorizontalHeaderLabels(["块号", "句子范围", "句子数", "字符数", "密度得分"])
        self.chunk_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.chunk_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.chunk_table.itemSelectionChanged.connect(self._on_chunk_selected)
        detail_layout.addWidget(self.chunk_table)

        self.chunk_content = QTextEdit()
        self.chunk_content.setReadOnly(True)
        self.chunk_content.setPlaceholderText("选择一个块查看内容...")
        self.chunk_content.setMaximumHeight(200)
        detail_layout.addWidget(self.chunk_content)

        right_panel.addTab(detail_tab, "分块详情")

        # Tab 4: 句子列表（树形结构，支持展开/收起）
        self.sentence_tree_widget = SentenceTreeWidget()
        right_panel.addTab(self.sentence_tree_widget, "句子列表")

        main_layout.addWidget(right_panel, stretch=1)

    def _on_sample_changed(self, index: int):
        """示例文本切换"""
        if index == 0:
            self.text_input.setPlainText(NOVEL_SAMPLE)
            self.param_panel._apply_novel_preset()
        elif index == 1:
            self.text_input.setPlainText(CODING_SAMPLE)
            self.param_panel._apply_coding_preset()
        # index == 2 为自定义，不改变文本

    def _run_chunking(self):
        """运行分块"""
        text = self.text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要分块的文本")
            return

        self.run_btn.setEnabled(False)
        self.progress_label.setText("正在处理...")

        config = self.param_panel.get_config()
        self.worker = ChunkWorker(text, config)
        self.worker.finished.connect(self._on_chunk_finished)
        self.worker.error.connect(self._on_chunk_error)
        self.worker.progress.connect(self._on_progress)
        self.worker.start()

    def _on_progress(self, msg: str):
        """进度更新"""
        self.progress_label.setText(msg)

    def _on_chunk_finished(self, result: dict):
        """分块完成"""
        self.run_btn.setEnabled(True)

        if "error" in result:
            self.progress_label.setText(f"错误: {result['error']}")
            return

        self.last_result = result
        self.progress_label.setText("完成！" + (" (使用真实嵌入模型)" if result.get("is_real_embedding") else " (使用模拟嵌入)"))

        chunks = result["chunks"]
        sentences = result["sentences"]
        cut_points = result["cut_points"]

        # 更新统计信息
        total_chars = sum(len(c.content) for c in chunks)
        avg_density = np.mean([c.density_score for c in chunks]) if chunks else 0
        stats_text = f"""
总块数: {len(chunks)}
总句子: {len(sentences)}
总字符: {total_chars}
平均块长: {total_chars / len(chunks):.1f} 字符
平均句子: {sum(c.sentence_count for c in chunks) / len(chunks):.1f} 句/块
平均密度: {avg_density:.4f}
"""
        self.stats_label.setText(stats_text.strip())

        # 更新相似度矩阵
        self.original_matrix_widget.update_plot(
            result["sim_matrix"], cut_points, "原始相似度矩阵"
        )
        self.enhanced_matrix_widget.update_plot(
            result["enhanced_matrix"], cut_points, "结构增强相似度矩阵"
        )

        # 更新分块统计图表
        self.chunk_stats_widget.update_plot(chunks)

        # 更新分块表格
        self.chunk_table.setRowCount(len(chunks))
        for i, chunk in enumerate(chunks):
            self.chunk_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.chunk_table.setItem(i, 1, QTableWidgetItem(f"[{chunk.start_sentence_idx}, {chunk.end_sentence_idx})"))
            self.chunk_table.setItem(i, 2, QTableWidgetItem(str(chunk.sentence_count)))
            self.chunk_table.setItem(i, 3, QTableWidgetItem(str(len(chunk.content))))
            self.chunk_table.setItem(i, 4, QTableWidgetItem(f"{chunk.density_score:.4f}"))

        # 更新句子树形列表
        self.sentence_tree_widget.update_data(sentences, chunks, cut_points)

    def _on_chunk_error(self, error_msg: str):
        """分块错误"""
        self.run_btn.setEnabled(True)
        self.progress_label.setText(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"分块处理失败:\n{error_msg}")

    def _on_chunk_selected(self):
        """选中分块"""
        if not self.last_result:
            return

        selected = self.chunk_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        chunks = self.last_result["chunks"]
        if row < len(chunks):
            chunk = chunks[row]
            self.chunk_content.setPlainText(chunk.content)


# ============================================================
# 主函数
# ============================================================

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = SemanticChunkerGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
