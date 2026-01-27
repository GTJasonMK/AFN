"""
依赖图工具

集中维护“循环依赖检测”等纯算法逻辑，避免多个模块并行维护导致策略漂移。
"""

from __future__ import annotations

from typing import Dict, List


def detect_cycles(edges: Dict[str, List[str]], *, max_cycles: int) -> List[List[str]]:
    """检测依赖图中的循环（基于 DFS + 递归栈）。"""
    cycles: List[List[str]] = []
    visited = set()
    rec_stack = set()

    def dfs(node: str, path: List[str]) -> None:
        if len(cycles) >= max_cycles:
            return

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in edges.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                try:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:]
                    if len(cycle) > 1:
                        cycles.append(cycle.copy())
                except ValueError:
                    pass

        path.pop()
        rec_stack.remove(node)

    for node in edges:
        if node not in visited:
            dfs(node, [])

    return cycles[:max_cycles]

