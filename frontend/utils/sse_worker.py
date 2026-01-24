"""
SSE (Server-Sent Events) Worker线程

负责监听后端SSE流并发射PyQt信号。

特性：
- 线程安全的停止机制（使用锁保护信号发射）
- 自动资源清理
- 完善的错误处理
- 防止竞态条件导致的信号发射到已销毁对象
- 支持优雅停止，确保信号不会发射到已销毁的槽
- Windows 上初始化 COM 避免线程冲突

线程安全设计说明：
- 使用 threading.Event 实现停止标志
- 使用 threading.Lock 保护"检查停止+发射信号"的原子性
- stop() 调用后会断开所有信号，防止残余emit到达已销毁对象
- 使用 _emit_allowed 标志确保finish后不再发射
"""

import json
import logging
import platform
import threading
import time
from typing import Optional, List, Callable

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from .constants import SSEConstants

logger = logging.getLogger(__name__)

# Windows COM 支持
_IS_WINDOWS = platform.system() == 'Windows'
_ole32 = None

if _IS_WINDOWS:
    try:
        import ctypes
        _ole32 = ctypes.windll.ole32
    except Exception:
        pass


def _com_initialize():
    """初始化 COM（线程内调用）

    使用 COINIT_MULTITHREADED (MTA) 模式，适合后台网络 I/O 线程。
    避免使用 COINIT_APARTMENTTHREADED (STA) 因为它需要消息循环。
    """
    if _ole32:
        # COINIT_MULTITHREADED = 0x0 (MTA, 适合后台线程)
        # COINIT_APARTMENTTHREADED = 0x2 (STA, 需要消息循环)
        hr = _ole32.CoInitializeEx(None, 0x0)
        return hr in (0, 1)
    return False


def _com_uninitialize():
    """释放 COM（线程内调用）"""
    if _ole32:
        _ole32.CoUninitialize()


class SSEWorker(QThread):
    """SSE流式监听工作线程

    线程安全设计：
    - 使用 threading.Event 实现线程安全的停止机制
    - 信号发射前检查停止状态
    - 自动在线程完成后清理资源

    用法：
        worker = SSEWorker(url, payload)
        worker.token_received.connect(self.on_token)
        worker.complete.connect(self.on_complete)
        worker.error.connect(self.on_error)
        worker.start()

        # 停止
        worker.stop()
    """

    # ===== 基础信号 =====
    token_received = pyqtSignal(str)      # 收到一个token（流式文本片段）
    progress_received = pyqtSignal(dict)  # 收到进度更新

    # 完成与错误信号
    complete = pyqtSignal(dict)           # 流式完成（包含 metadata）
    cancelled = pyqtSignal(dict)          # 流式被用户取消
    error = pyqtSignal(str)               # 简单错误消息（仅字符串，用于简单场景）
    error_data = pyqtSignal(dict)         # 完整错误数据（包含 message, saved_count, saved_parts 等）
    #                                     # 用于需要详细错误信息的场景（如部分成功时显示已保存数量）

    # ===== 结构化流式事件（用于灵感对话等场景） =====
    streaming_start = pyqtSignal(dict)    # 流式开始，前端应禁用交互
    ai_message_chunk = pyqtSignal(str)    # AI消息文本片段
    option_received = pyqtSignal(dict)    # 单个选项数据

    # ===== 通用事件信号（用于自定义事件类型） =====
    event_received = pyqtSignal(str, dict)  # (event_type, data) - 用于未预定义的事件类型

    def __init__(self, url: str, payload: dict, parent=None):
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

        # 线程安全的停止事件
        self._stop_event = threading.Event()

        # 信号发射锁 - 防止 TOCTOU 竞态条件
        # 确保检查停止状态和发射信号是原子操作
        self._emit_lock = threading.Lock()

        # 是否允许发射信号（在stop或finish后设为False）
        self._emit_allowed = True

        # 当前事件类型（仅在工作线程内使用）
        self._current_event_type: Optional[str] = None

        # Token批量发射缓冲区（性能优化）
        # 将高频token累积后批量发射，减少UI更新频率
        self._token_buffer: List[str] = []
        self._last_token_flush: float = 0.0

        # 请求会话（用于可能的取消）
        self._session: Optional[requests.Session] = None

        # 线程完成后自动清理
        self.finished.connect(self._on_finished)

    def run(self):
        """执行SSE监听"""
        # Windows 上初始化 COM，避免线程冲突错误 (0x8001010d)
        com_initialized = False
        if _IS_WINDOWS:
            try:
                com_initialized = _com_initialize()
            except Exception:
                pass

        self._session = requests.Session()

        try:
            logger.info("开始SSE连接: %s", self.url)

            # 使用requests的stream模式
            with self._session.post(
                self.url,
                json=self.payload,
                stream=True,
                headers={"Accept": "text/event-stream"},
                timeout=(SSEConstants.CONNECT_TIMEOUT, SSEConstants.READ_TIMEOUT)
            ) as response:
                # 在 with 块内检查状态码，这样可以在响应关闭前读取错误内容
                if not response.ok:
                    error_msg = self._extract_error_from_response(response)
                    if not self._stop_event.is_set():
                        logger.error("SSE HTTP错误: %d - %s", response.status_code, error_msg)
                        self._safe_emit_error(error_msg)
                    return

                logger.info("SSE连接成功，开始接收事件")

                # 解析SSE流
                for line in response.iter_lines():
                    # 线程安全检查停止状态
                    if self._stop_event.is_set():
                        logger.info("SSE worker已停止")
                        break

                    if not line:
                        continue

                    try:
                        line = line.decode('utf-8')
                        self._process_line(line)
                    except UnicodeDecodeError as e:
                        logger.warning("SSE行解码失败: %s", e)
                        continue

                logger.info("SSE流结束")

        except requests.exceptions.Timeout:
            if not self._stop_event.is_set():
                logger.error("SSE连接超时")
                self._safe_emit_error("连接超时，请检查网络")

        except requests.exceptions.ConnectionError as e:
            if not self._stop_event.is_set():
                logger.error("SSE连接错误: %s", e)
                self._safe_emit_error(f"连接失败：{str(e)}")

        except OSError as e:
            # 捕获Windows上的socket相关错误
            if not self._stop_event.is_set():
                error_code = getattr(e, 'winerror', None) or getattr(e, 'errno', None)
                logger.error("SSE系统错误: %s (code=%s)", e, error_code)
                self._safe_emit_error(f"网络错误：{str(e)}")

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error("SSE未知错误: %s", e, exc_info=True)
                self._safe_emit_error(f"发生错误：{str(e)}")

        finally:
            self._cleanup_session()
            # Windows 上释放 COM
            if com_initialized:
                try:
                    _com_uninitialize()
                except Exception:
                    pass

    def _process_line(self, line: str):
        """处理单行SSE数据"""
        # 解析SSE事件类型
        if line.startswith('event: '):
            self._current_event_type = line[7:].strip()
            logger.debug("收到事件类型: %s", self._current_event_type)
            return

        # 解析SSE数据
        if not line.startswith('data: '):
            return

        data_str = line[6:]
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError as e:
            logger.warning("解析SSE数据失败: %s, 原始数据: %s", e, data_str)
            return

        # 使用锁保护检查-发射的原子性，防止TOCTOU竞态条件
        with self._emit_lock:
            if self._stop_event.is_set() or not self._emit_allowed:
                return
            # 根据事件类型发射对应信号
            self._emit_signal_for_event(data)

    def _emit_signal_for_event(self, data: dict):
        """根据事件类型发射对应信号

        注意：此方法在 _emit_lock 保护下调用，已确保线程安全。
        额外的 try-except 用于处理接收者对象已被删除的情况。
        """
        event_type = self._current_event_type

        try:
            if event_type == 'token':
                token = data.get('token', '')
                self._buffer_token(token)

            elif event_type == 'progress':
                logger.debug("SSE进度更新: %s", data)
                self.progress_received.emit(data)

            elif event_type == 'complete':
                # 完成前先刷新剩余的token缓冲区
                self._flush_token_buffer(force=True)
                logger.info("SSE流完成，发射complete信号")
                self.complete.emit(data)

            elif event_type == 'cancelled':
                # 取消前先刷新剩余的token缓冲区
                self._flush_token_buffer(force=True)
                logger.info("SSE流被取消，发射cancelled信号")
                self.cancelled.emit(data)

            elif event_type == 'error':
                error_msg = data.get('message', '未知错误')
                logger.error("SSE错误事件: %s", error_msg)
                # 使用安全的方式发射信号，避免线程冲突
                try:
                    self.error.emit(error_msg)  # 向后兼容
                    self.error_data.emit(data)  # 完整错误数据
                except RuntimeError:
                    # 接收者对象可能已被删除
                    logger.debug("SSEWorker: receiver deleted, error signal not emitted")

            elif event_type == 'streaming_start':
                logger.debug("SSE流式开始")
                self.streaming_start.emit(data)

            elif event_type == 'ai_message_chunk':
                text = data.get('text', '')
                self.ai_message_chunk.emit(text)

            elif event_type == 'option':
                logger.debug("SSE收到选项: %s", data)
                self.option_received.emit(data)

            else:
                # 未知事件类型，通过通用信号发射
                if event_type:
                    logger.info("SSE收到自定义事件并发射信号: type=%s, data_keys=%s",
                               event_type, list(data.keys()) if data else [])
                    self.event_received.emit(event_type, data)

        except RuntimeError:
            # 接收者对象可能已被删除
            logger.debug("SSEWorker: receiver deleted, signal not emitted")

    def _buffer_token(self, token: str):
        """将token添加到缓冲区，达到时间阈值时批量发射

        性能优化：将高频token累积后批量发射，减少UI更新频率。
        原逻辑：每个token立即emit，约50-100次/秒
        优化后：每100ms批量emit一次，约10次/秒

        注意：此方法在 _emit_lock 保护下调用
        """
        self._token_buffer.append(token)
        self._flush_token_buffer(force=False)

    def _flush_token_buffer(self, force: bool = False):
        """刷新token缓冲区

        Args:
            force: 是否强制刷新（用于complete/cancelled事件）

        注意：此方法在 _emit_lock 保护下调用
        """
        if not self._token_buffer:
            return

        now = time.monotonic()
        elapsed = now - self._last_token_flush

        # 达到时间阈值或强制刷新时，批量发射
        if force or elapsed >= SSEConstants.TOKEN_FLUSH_INTERVAL:
            # 合并所有token为单个字符串
            merged_tokens = ''.join(self._token_buffer)
            self._token_buffer.clear()
            self._last_token_flush = now

            try:
                self.token_received.emit(merged_tokens)
            except RuntimeError:
                # 接收者对象可能已被删除
                logger.debug("SSEWorker: receiver deleted, token signal not emitted")

    def _safe_emit_error(self, message: str):
        """安全地发射错误信号（使用锁保护，防止竞态条件）"""
        with self._emit_lock:
            if not self._stop_event.is_set() and self._emit_allowed:
                try:
                    self.error.emit(message)
                except RuntimeError:
                    # 接收者对象可能已被删除
                    logger.debug("SSEWorker: receiver deleted, error signal not emitted")

    def _extract_error_from_response(self, response: requests.Response) -> str:
        """从HTTP响应中提取详细错误信息（在with块内调用，响应未关闭）

        Args:
            response: HTTP响应对象

        Returns:
            用户友好的错误消息
        """
        status_code = response.status_code
        try:
            # 读取响应内容
            content = response.content
            if content:
                error_data = json.loads(content.decode('utf-8'))
                # 后端返回的错误格式: {"detail": "错误消息"} 或 {"message": "错误消息"}
                if isinstance(error_data, dict):
                    detail = error_data.get("detail") or error_data.get("message")
                    if detail:
                        return detail
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            # 响应不是JSON格式，尝试获取文本
            try:
                content = response.content
                if content:
                    text = content.decode('utf-8')
                    if len(text) < SSEConstants.ERROR_TEXT_MAX_LENGTH:
                        return text
            except Exception:
                pass

        # 根据状态码返回友好消息
        if status_code == 400:
            return "请求参数错误"
        elif status_code == 401:
            return "未授权，请重新登录"
        elif status_code == 403:
            return "没有权限执行此操作"
        elif status_code == 404:
            return "请求的资源不存在"
        elif status_code >= 500:
            return f"服务器错误（{status_code}）"
        else:
            return f"请求失败（{status_code}）"

    def _cleanup_session(self):
        """清理请求会话"""
        if self._session:
            try:
                self._session.close()
            except (OSError, RuntimeError, AttributeError):
                # 关闭时的预期异常：网络错误、运行时错误、属性错误
                pass
            self._session = None

    def _on_finished(self):
        """线程完成时的清理"""
        # 禁止后续信号发射
        with self._emit_lock:
            self._emit_allowed = False

        self._cleanup_session()
        # 延迟删除，防止信号处理中删除对象
        self.deleteLater()

    def _disconnect_all_signals(self):
        """断开所有信号连接，防止发射到已销毁的槽

        在stop()时调用，确保即使有残余的emit也不会到达已删除的对象
        """
        try:
            signal_list = [
                self.token_received,
                self.progress_received,
                self.complete,
                self.cancelled,
                self.error,
                self.error_data,
                self.streaming_start,
                self.ai_message_chunk,
                self.option_received,
                self.event_received,
            ]
            for signal in signal_list:
                try:
                    signal.disconnect()
                except TypeError:
                    # 信号可能未连接
                    pass
        except RuntimeError:
            # C++对象已被删除，无需断开信号
            pass

    def stop(self):
        """停止SSE监听（线程安全）

        使用锁确保设置停止标志与信号发射检查的同步，
        防止竞态条件导致信号发射到已销毁的对象。

        调用后：
        1. 设置停止标志，阻止新的信号发射
        2. 禁用信号发射许可
        3. 断开所有信号连接（防止残余emit到达已销毁对象）
        4. 关闭网络会话以中断正在进行的请求
        """
        try:
            logger.info("请求停止SSE worker")

            # 使用锁确保设置停止标志和禁用发射是原子的
            with self._emit_lock:
                self._stop_event.set()
                self._emit_allowed = False

            # 断开所有信号，防止残余emit到达已销毁的槽
            self._disconnect_all_signals()

            # 尝试关闭session以中断正在进行的请求
            if self._session:
                try:
                    self._session.close()
                except (OSError, RuntimeError, AttributeError):
                    # 关闭时的预期异常
                    pass
        except RuntimeError:
            # C++对象已被删除
            pass

    def is_stopped(self) -> bool:
        """检查是否已停止（线程安全）"""
        return self._stop_event.is_set()


def start_sse_worker(
    url: str,
    payload: dict,
    *,
    parent=None,
    on_token: Optional[Callable[[str], None]] = None,
    on_progress: Optional[Callable[[dict], None]] = None,
    on_complete: Optional[Callable[[dict], None]] = None,
    on_error: Optional[Callable[[str], None]] = None,
    on_cancelled: Optional[Callable[[dict], None]] = None,
) -> SSEWorker:
    """创建并启动SSE Worker"""
    worker = SSEWorker(url, payload, parent)
    if on_token:
        worker.token_received.connect(on_token)
    if on_progress:
        worker.progress_received.connect(on_progress)
    if on_complete:
        worker.complete.connect(on_complete)
    if on_error:
        worker.error.connect(on_error)
    if on_cancelled:
        worker.cancelled.connect(on_cancelled)
    worker.start()
    return worker


def stop_sse_worker(worker: Optional[SSEWorker], *, delete_later: bool = False) -> None:
    """安全停止SSE Worker

    Args:
        worker: SSE Worker实例
        delete_later: 是否调用deleteLater释放对象
    """
    if not worker:
        return
    try:
        worker.stop()
        if delete_later:
            worker.deleteLater()
    except RuntimeError:
        pass


def reset_sse_generation_state(
    owner,
    *,
    delete_later: bool = False,
    flag_attr: str = "_is_generating",
) -> None:
    """重置SSE生成状态

    统一清理SSE Worker引用并重置生成状态标记，避免重复代码。

    Args:
        owner: 持有 `_sse_worker` 的对象
        delete_later: 是否在停止后调用 deleteLater
        flag_attr: 需要重置的生成状态字段名（默认 `_is_generating`）
    """
    if not owner:
        return

    if hasattr(owner, flag_attr):
        try:
            setattr(owner, flag_attr, False)
        except Exception:
            pass

    stop_sse_worker(getattr(owner, "_sse_worker", None), delete_later=delete_later)

    if hasattr(owner, "_sse_worker"):
        try:
            owner._sse_worker = None
        except Exception:
            pass
