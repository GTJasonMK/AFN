"""
Logo调试工具 - 将txt文件内容打印到控制台

用法:
    python print_logo.py <文件路径>
    python print_logo.py              # 默认打印 ../tools/logo.txt
"""

import sys
from pathlib import Path


def print_file(file_path: str):
    """打印文件内容到控制台"""
    path = Path(file_path)

    if not path.exists():
        print(f"错误: 文件不存在 - {path}")
        return

    print(f"\n{'=' * 60}")
    print(f"文件: {path.absolute()}")
    print(f"{'=' * 60}\n")

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 打印内容
    print(content)

    # 打印统计信息
    lines = content.split('\n')
    max_width = max(len(line) for line in lines) if lines else 0

    print(f"\n{'=' * 60}")
    print(f"统计: {len(lines)} 行, 最大宽度 {max_width} 字符")
    print(f"{'=' * 60}\n")


def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 默认路径
        file_path = Path(__file__).parent.parent / "tools" / "logo.txt"

    print_file(str(file_path))


if __name__ == "__main__":
    main()
