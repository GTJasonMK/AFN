"""
语义分块算法可视化测试

测试语义动态规划分块算法的效果，包括：
1. 分块结果展示
2. 相似度矩阵热力图
3. 分块边界可视化
4. 与传统分块方法对比
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root / "backend"))

import numpy as np

# 尝试导入可视化库
try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[警告] matplotlib 未安装，将跳过图表生成")

# 导入语义分块器
from app.services.rag_common.semantic_chunker import (
    SemanticChunker,
    SemanticChunkConfig,
    ChunkResult,
)

# ============================================================
# 测试数据
# ============================================================

# 小说章节示例文本
NOVEL_SAMPLE = """
林逸站在悬崖边，望着远处连绵的山峦。夕阳的余晖洒在他的脸上，映出一抹淡淡的金色。他已经在这条路上走了三年，从一个默默无闻的小修士，成长为如今的金丹期强者。

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

# 编程Prompt示例文本
CODING_SAMPLE = """
## 功能概述

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
# 模拟嵌入函数
# ============================================================

def create_mock_embedding_func(dim: int = 384):
    """
    创建模拟嵌入函数

    使用简单的文本特征生成伪嵌入向量，用于测试分块算法逻辑。
    实际使用时应替换为真实的嵌入模型。
    """
    def get_text_features(text: str) -> np.ndarray:
        """从文本提取简单特征"""
        features = np.zeros(dim)

        # 基于字符的特征
        for i, char in enumerate(text[:dim]):
            features[i % dim] += ord(char) / 1000.0

        # 基于长度的特征
        features[0] = len(text) / 100.0

        # 基于标点的特征
        features[1] = text.count('。') / 10.0
        features[2] = text.count('，') / 10.0
        features[3] = text.count('！') / 10.0
        features[4] = text.count('？') / 10.0

        # 归一化
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        return features

    async def mock_embedding(sentences: list) -> np.ndarray:
        """模拟异步嵌入函数"""
        embeddings = []
        for sent in sentences:
            emb = get_text_features(sent)
            embeddings.append(emb)
        return np.array(embeddings)

    return mock_embedding


def try_load_sentence_transformer():
    """尝试加载sentence-transformers模型"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

        async def real_embedding(sentences: list) -> np.ndarray:
            embeddings = model.encode(sentences, convert_to_numpy=True)
            return embeddings

        return real_embedding, True
    except ImportError:
        return None, False
    except Exception as e:
        print(f"[警告] 加载sentence-transformers失败: {e}")
        return None, False


# ============================================================
# 可视化函数
# ============================================================

def visualize_similarity_matrix(
    sim_matrix: np.ndarray,
    sentences: list,
    cut_points: list,
    output_path: str
):
    """
    可视化相似度矩阵和分块边界

    Args:
        sim_matrix: 相似度矩阵
        sentences: 句子列表
        cut_points: 分块切分点
        output_path: 输出路径
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # 绘制热力图
    im = ax.imshow(sim_matrix, cmap='YlOrRd', aspect='auto')

    # 添加分块边界线
    for cp in cut_points[1:-1]:  # 跳过首尾
        ax.axhline(y=cp - 0.5, color='blue', linewidth=2, linestyle='--')
        ax.axvline(x=cp - 0.5, color='blue', linewidth=2, linestyle='--')

    # 标注分块区域
    for i in range(len(cut_points) - 1):
        start = cut_points[i]
        end = cut_points[i + 1]
        mid = (start + end) / 2
        ax.text(mid, mid, f'Chunk {i+1}',
                ha='center', va='center', fontsize=10,
                color='white', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='blue', alpha=0.5))

    # 设置标签
    ax.set_xlabel('Sentence Index', fontsize=12)
    ax.set_ylabel('Sentence Index', fontsize=12)
    ax.set_title('Similarity Matrix with Chunk Boundaries', fontsize=14)

    # 添加颜色条
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Cosine Similarity', fontsize=12)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[图表] 相似度矩阵已保存: {output_path}")


def visualize_chunk_lengths(
    chunks: list,
    output_path: str
):
    """
    可视化分块长度分布

    Args:
        chunks: ChunkResult列表
        output_path: 输出路径
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 1. 句子数分布
    sentence_counts = [c.sentence_count for c in chunks]
    ax1 = axes[0]
    bars1 = ax1.bar(range(1, len(chunks) + 1), sentence_counts, color='steelblue', alpha=0.8)
    ax1.set_xlabel('Chunk Index', fontsize=12)
    ax1.set_ylabel('Sentence Count', fontsize=12)
    ax1.set_title('Sentences per Chunk', fontsize=14)
    ax1.set_xticks(range(1, len(chunks) + 1))

    # 添加数值标签
    for bar, count in zip(bars1, sentence_counts):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(count), ha='center', va='bottom', fontsize=10)

    # 2. 字符长度分布
    char_lengths = [len(c.content) for c in chunks]
    ax2 = axes[1]
    bars2 = ax2.bar(range(1, len(chunks) + 1), char_lengths, color='coral', alpha=0.8)
    ax2.set_xlabel('Chunk Index', fontsize=12)
    ax2.set_ylabel('Character Count', fontsize=12)
    ax2.set_title('Characters per Chunk', fontsize=14)
    ax2.set_xticks(range(1, len(chunks) + 1))

    # 添加数值标签
    for bar, length in zip(bars2, char_lengths):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10,
                str(length), ha='center', va='bottom', fontsize=10)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[图表] 分块长度分布已保存: {output_path}")


def visualize_density_scores(
    chunks: list,
    output_path: str
):
    """
    可视化分块密度得分

    Args:
        chunks: ChunkResult列表
        output_path: 输出路径
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(10, 5))

    density_scores = [c.density_score for c in chunks]
    colors = plt.cm.RdYlGn(np.array(density_scores) / max(density_scores) if max(density_scores) > 0 else density_scores)

    bars = ax.bar(range(1, len(chunks) + 1), density_scores, color=colors, alpha=0.8)
    ax.set_xlabel('Chunk Index', fontsize=12)
    ax.set_ylabel('Density Score', fontsize=12)
    ax.set_title('Chunk Density Scores (Higher = More Coherent)', fontsize=14)
    ax.set_xticks(range(1, len(chunks) + 1))

    # 添加数值标签
    for bar, score in zip(bars, density_scores):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                f'{score:.3f}', ha='center', va='bottom', fontsize=9)

    # 添加平均线
    avg_score = np.mean(density_scores)
    ax.axhline(y=avg_score, color='red', linestyle='--', label=f'Average: {avg_score:.3f}')
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[图表] 密度得分分布已保存: {output_path}")


# ============================================================
# 测试函数
# ============================================================

async def test_semantic_chunking(
    text: str,
    text_type: str,
    embedding_func,
    config: SemanticChunkConfig,
    output_dir: Path
):
    """
    测试语义分块并生成可视化

    Args:
        text: 测试文本
        text_type: 文本类型标识（用于文件命名）
        embedding_func: 嵌入函数
        config: 分块配置
        output_dir: 输出目录
    """
    print(f"\n{'='*60}")
    print(f"测试: {text_type}")
    print(f"{'='*60}")

    # 创建分块器
    chunker = SemanticChunker(config=config)

    # 分句
    sentences = chunker._split_sentences(text)
    print(f"\n[分句结果] 共 {len(sentences)} 个句子")
    for i, sent in enumerate(sentences[:5]):
        print(f"  {i+1}. {sent[:50]}..." if len(sent) > 50 else f"  {i+1}. {sent}")
    if len(sentences) > 5:
        print(f"  ... (还有 {len(sentences) - 5} 个句子)")

    # 获取嵌入
    print("\n[嵌入] 正在生成句子嵌入...")
    embeddings = await embedding_func(sentences)
    print(f"  嵌入维度: {embeddings.shape}")

    # 构建相似度矩阵
    sim_matrix = chunker._build_similarity_matrix(embeddings)
    print(f"\n[相似度矩阵] 形状: {sim_matrix.shape}")
    print(f"  最大值: {sim_matrix.max():.4f}")
    print(f"  最小值: {sim_matrix.min():.4f}")
    print(f"  平均值: {sim_matrix.mean():.4f}")

    # 应用结构增强
    enhanced_matrix = chunker._apply_structure_enhancement(sim_matrix, config)
    print(f"\n[结构增强后]")
    print(f"  最大值: {enhanced_matrix.max():.4f}")
    print(f"  最小值: {enhanced_matrix.min():.4f}")
    print(f"  平均值: {enhanced_matrix.mean():.4f}")

    # 执行分块
    print("\n[分块] 正在执行语义分块...")
    chunks = await chunker.chunk_text_async(text, embedding_func, config)

    # 计算切分点
    cut_points = [0]
    for chunk in chunks:
        cut_points.append(chunk.end_sentence_idx)

    # 打印分块结果
    print(f"\n[分块结果] 共 {len(chunks)} 个块")
    print("-" * 60)

    total_chars = 0
    for i, chunk in enumerate(chunks):
        content_preview = chunk.content[:100].replace('\n', ' ')
        if len(chunk.content) > 100:
            content_preview += "..."

        print(f"\n块 {i+1}:")
        print(f"  句子范围: [{chunk.start_sentence_idx}, {chunk.end_sentence_idx})")
        print(f"  句子数量: {chunk.sentence_count}")
        print(f"  字符长度: {len(chunk.content)}")
        print(f"  密度得分: {chunk.density_score:.4f}")
        print(f"  内容预览: {content_preview}")

        total_chars += len(chunk.content)

    print(f"\n[统计]")
    print(f"  总块数: {len(chunks)}")
    print(f"  总字符: {total_chars}")
    print(f"  平均块长: {total_chars / len(chunks):.1f} 字符")
    print(f"  平均句子: {sum(c.sentence_count for c in chunks) / len(chunks):.1f} 句/块")
    print(f"  平均密度: {sum(c.density_score for c in chunks) / len(chunks):.4f}")

    # 生成可视化
    if MATPLOTLIB_AVAILABLE:
        print("\n[可视化] 正在生成图表...")

        # 相似度矩阵热力图
        visualize_similarity_matrix(
            enhanced_matrix,
            sentences,
            cut_points,
            str(output_dir / f"{text_type}_similarity_matrix.png")
        )

        # 分块长度分布
        visualize_chunk_lengths(
            chunks,
            str(output_dir / f"{text_type}_chunk_lengths.png")
        )

        # 密度得分分布
        visualize_density_scores(
            chunks,
            str(output_dir / f"{text_type}_density_scores.png")
        )

    return chunks, sim_matrix, enhanced_matrix, cut_points


def print_config(config: SemanticChunkConfig):
    """打印配置信息"""
    print("\n[配置参数]")
    print(f"  门控阈值 (gate_threshold): {config.gate_threshold}")
    print(f"  距离增强系数 (alpha): {config.alpha}")
    print(f"  长度归一化指数 (gamma): {config.gamma}")
    print(f"  最小块句子数: {config.min_chunk_sentences}")
    print(f"  最大块句子数: {config.max_chunk_sentences}")
    print(f"  最小块字符数: {config.min_chunk_chars}")
    print(f"  最大块字符数: {config.max_chunk_chars}")


async def main():
    """主测试函数"""
    print("=" * 60)
    print("语义分块算法可视化测试")
    print("=" * 60)

    # 创建输出目录
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    print(f"\n输出目录: {output_dir}")

    # 尝试加载真实嵌入模型
    real_embedding_func, use_real = try_load_sentence_transformer()

    if use_real:
        print("\n[嵌入模型] 使用 sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)")
        embedding_func = real_embedding_func
    else:
        print("\n[嵌入模型] 使用模拟嵌入函数 (仅测试算法逻辑)")
        embedding_func = create_mock_embedding_func(dim=384)

    # 配置参数（与OPTIMIZED_STRATEGIES中的配置一致）
    novel_config = SemanticChunkConfig(
        gate_threshold=0.3,
        alpha=0.1,
        gamma=1.1,
        min_chunk_sentences=3,
        max_chunk_sentences=15,
        min_chunk_chars=100,
        max_chunk_chars=1200,
    )

    coding_config = SemanticChunkConfig(
        gate_threshold=0.3,
        alpha=0.1,
        gamma=1.1,
        min_chunk_sentences=2,
        max_chunk_sentences=15,
        min_chunk_chars=100,
        max_chunk_chars=1500,
    )

    # 测试小说文本
    print_config(novel_config)
    await test_semantic_chunking(
        text=NOVEL_SAMPLE,
        text_type="novel",
        embedding_func=embedding_func,
        config=novel_config,
        output_dir=output_dir
    )

    # 测试编程Prompt
    print_config(coding_config)
    await test_semantic_chunking(
        text=CODING_SAMPLE,
        text_type="coding",
        embedding_func=embedding_func,
        config=coding_config,
        output_dir=output_dir
    )

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

    if MATPLOTLIB_AVAILABLE:
        print(f"\n可视化图表已保存到: {output_dir}")
        print("  - novel_similarity_matrix.png  (小说相似度矩阵)")
        print("  - novel_chunk_lengths.png      (小说分块长度)")
        print("  - novel_density_scores.png     (小说密度得分)")
        print("  - coding_similarity_matrix.png (编程相似度矩阵)")
        print("  - coding_chunk_lengths.png     (编程分块长度)")
        print("  - coding_density_scores.png    (编程密度得分)")


if __name__ == "__main__":
    asyncio.run(main())
