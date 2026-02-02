"""
本地嵌入模型冒烟测试脚本

用途：
- 快速验证 sentence-transformers 本地模型是否能在当前环境稳定加载与生成向量
- 排查 torch/transformers/sentence-transformers 组合导致的 “meta tensor” 兼容性问题

日期：2026-02-02
维护者：Codex

用法（在仓库根目录执行）：
  python backend/scripts/smoke_local_embedding.py
  python backend/scripts/smoke_local_embedding.py --model BAAI/bge-base-zh-v1.5 --text "你好，世界"
  python backend/scripts/smoke_local_embedding.py --device cpu

说明：
- 脚本会尽量复用 run_app.py 的目录约定：若未设置 HF_HOME/SENTENCE_TRANSFORMERS_HOME，
  会自动指向 `storage/models`，并以离线模式加载。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path


def _ensure_model_env(repo_root: Path) -> None:
    storage_dir = repo_root / "storage"
    models_dir = storage_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(models_dir))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(models_dir))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def main() -> int:
    parser = argparse.ArgumentParser(description="AFN 本地嵌入模型冒烟测试")
    parser.add_argument("--model", default="BAAI/bge-base-zh-v1.5", help="模型名称（如 BAAI/bge-base-zh-v1.5）")
    parser.add_argument("--text", default="你好，世界。", help="要生成嵌入的文本")
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="加载/推理设备（auto=自动优先 GPU）",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    _ensure_model_env(repo_root)

    try:
        from backend.app.services.embedding_service import _get_torch_device, _load_sentence_transformer
    except Exception as exc:
        print(f"[FAIL] 无法导入 embedding_service：{exc}", file=sys.stderr)
        return 2

    device = args.device
    if device == "auto":
        try:
            device = _get_torch_device()
        except Exception as exc:
            print(f"[WARN] 自动检测设备失败，回退 cpu：{exc}", file=sys.stderr)
            device = "cpu"

    print(f"[INFO] model={args.model}")
    print(f"[INFO] device={device}")
    print(f"[INFO] HF_HOME={os.environ.get('HF_HOME')}")
    print(f"[INFO] SENTENCE_TRANSFORMERS_HOME={os.environ.get('SENTENCE_TRANSFORMERS_HOME')}")

    started = time.time()
    try:
        model = _load_sentence_transformer(args.model, device)
    except Exception as exc:
        print(f"[FAIL] 加载模型失败：{exc}", file=sys.stderr)
        return 1

    load_cost = time.time() - started
    print(f"[OK] 模型加载完成，用时 {load_cost:.2f}s")

    started = time.time()
    try:
        vec = model.encode(args.text, normalize_embeddings=True)
    except Exception as exc:
        print(f"[FAIL] 生成嵌入失败：{exc}", file=sys.stderr)
        return 1

    encode_cost = time.time() - started
    dim = len(vec) if hasattr(vec, "__len__") else None
    print(f"[OK] 嵌入生成完成，用时 {encode_cost:.2f}s，维度={dim}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

