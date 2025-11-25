"""
SSE (Server-Sent Events) Worker线程

负责监听后端SSE流并发射PyQt信号。
"""

import json
import logging
import requests
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class SSEWorker(QThread):
    """SSE流式监听工作线程"""

    token_received = pyqtSignal(str)  # 收到一个token
    complete = pyqtSignal(dict)  # 流式完成（metadata）
    error = pyqtSignal(str)  # 错误

    def __init__(self, url, payload, parent=None):
        """
        初始化SSE Worker

        Args:
            url: SSE端点URL
            payload: POST请求负载
            parent: 父对象
        """
        super().__init__(parent)
        self.url = url
        self.payload = payload
        self._stopped = False
        self._current_event_type = None

    def run(self):
        """执行SSE监听"""
        try:
            logger.info("开始SSE连接: %s", self.url)

            # 使用requests的stream模式
            with requests.post(
                self.url,
                json=self.payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=(10, 300)  # 连接10秒超时，读取5分钟超时
            ) as response:
                response.raise_for_status()

                logger.info("SSE连接成功，开始接收事件")

                # 解析SSE流
                for line in response.iter_lines():
                    if self._stopped:
                        logger.info("SSE worker已停止")
                        break

                    if not line:
                        continue

                    line = line.decode('utf-8')

                    # 解析SSE事件
                    if line.startswith('event: '):
                        self._current_event_type = line[7:].strip()
                        logger.debug("收到事件类型: %s", self._current_event_type)

                    elif line.startswith('data: '):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)

                            if self._current_event_type == 'token':
                                # 发射token信号
                                token = data.get('token', '')
                                self.token_received.emit(token)

                            elif self._current_event_type == 'complete':
                                # 发射完成信号
                                logger.info("SSE流完成，发射complete信号")
                                self.complete.emit(data)

                            elif self._current_event_type == 'error':
                                # 发射错误信号
                                error_msg = data.get('message', '未知错误')
                                logger.error("SSE错误事件: %s", error_msg)
                                self.error.emit(error_msg)

                        except json.JSONDecodeError as e:
                            logger.warning("解析SSE数据失败: %s, 原始数据: %s", e, data_str)

                logger.info("SSE流结束")

        except requests.exceptions.Timeout:
            logger.error("SSE连接超时")
            self.error.emit("连接超时，请检查网络")

        except requests.exceptions.ConnectionError as e:
            logger.error("SSE连接错误: %s", e)
            self.error.emit(f"连接失败：{str(e)}")

        except requests.exceptions.HTTPError as e:
            logger.error("SSE HTTP错误: %s", e)
            self.error.emit(f"服务器错误：{e.response.status_code}")

        except Exception as e:
            logger.error("SSE未知错误: %s", e, exc_info=True)
            self.error.emit(f"发生错误：{str(e)}")

    def stop(self):
        """停止SSE监听"""
        logger.info("请求停止SSE worker")
        self._stopped = True
