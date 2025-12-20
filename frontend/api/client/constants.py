"""
API客户端常量定义

包含超时配置等常量。
"""


class TimeoutConfig:
    """超时配置"""
    # 连接超时：建立TCP连接的超时时间
    CONNECT = 10
    # 读取超时配置（根据操作类型）
    READ_DEFAULT = 60       # 默认读取超时
    READ_QUICK = 30         # 快速操作（健康检查、获取配置等）
    READ_NORMAL = 120       # 普通操作（获取数据、更新等）
    READ_GENERATION = 300   # 生成操作（蓝图、大纲生成）
    READ_LONG = 600         # 长时间操作（章节生成、批量操作）
