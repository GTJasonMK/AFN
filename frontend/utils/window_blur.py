"""
系统级窗口透明/模糊效果管理器

支持：
- Windows 10 1803+: Acrylic 效果
- Windows 11: Mica 效果
- 通用: 基本透明效果

注意：Windows DWM API 调用可能与 Qt 事件循环冲突，
需要特别注意调用时机以避免 COM 错误 (0x8001010d)。
"""

import sys
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# 标记是否有待处理的 DWM 操作
_pending_dwm_operation = False


def _safe_dwm_call(func: Callable, *args, **kwargs):
    """安全地执行 DWM API 调用

    捕获 COM 相关错误并优雅降级。
    """
    global _pending_dwm_operation

    if _pending_dwm_operation:
        logger.debug("跳过 DWM 调用：有待处理的操作")
        return False

    try:
        _pending_dwm_operation = True
        return func(*args, **kwargs)
    except OSError as e:
        # 处理 Windows COM 错误
        error_code = getattr(e, 'winerror', None)
        if error_code == 0x8001010d:  # RPC_E_CANTCALLOUT_ININPUTSYNCCALL
            logger.warning("DWM 调用被跳过：COM 线程冲突")
            return False
        raise
    finally:
        _pending_dwm_operation = False


class WindowBlurManager:
    """窗口透明/模糊效果管理器"""

    @staticmethod
    def is_windows() -> bool:
        """检查是否是Windows系统"""
        return sys.platform == "win32"

    @staticmethod
    def get_windows_build() -> int:
        """获取Windows构建版本号"""
        if not WindowBlurManager.is_windows():
            return 0
        try:
            import platform
            version = platform.version()
            # version 格式如 "10.0.22631"
            parts = version.split('.')
            if len(parts) >= 3:
                return int(parts[2])
            return 0
        except Exception:
            return 0

    @staticmethod
    def is_windows_11() -> bool:
        """检查是否是Windows 11 (build >= 22000)"""
        return WindowBlurManager.get_windows_build() >= 22000

    @staticmethod
    def is_acrylic_supported() -> bool:
        """检查是否支持Acrylic效果 (Windows 10 1803, build >= 17134)"""
        return WindowBlurManager.get_windows_build() >= 17134

    @staticmethod
    def enable_blur_behind(window, enable: bool = True) -> bool:
        """启用 DWM Blur Behind 效果（基础毛玻璃）

        这是最基础的透明效果，兼容性最好。
        """
        if not WindowBlurManager.is_windows():
            return False

        try:
            import ctypes
            from ctypes import wintypes, Structure, byref, sizeof

            class DWM_BLURBEHIND(Structure):
                _fields_ = [
                    ("dwFlags", wintypes.DWORD),
                    ("fEnable", wintypes.BOOL),
                    ("hRgnBlur", wintypes.HRGN),
                    ("fTransitionOnMaximized", wintypes.BOOL),
                ]

            DWM_BB_ENABLE = 0x00000001
            DWM_BB_BLURREGION = 0x00000002

            hwnd = int(window.winId())
            dwmapi = ctypes.windll.dwmapi

            bb = DWM_BLURBEHIND()
            bb.dwFlags = DWM_BB_ENABLE
            bb.fEnable = enable
            bb.hRgnBlur = None
            bb.fTransitionOnMaximized = False

            result = dwmapi.DwmEnableBlurBehindWindow(hwnd, byref(bb))
            logger.info(f"DwmEnableBlurBehindWindow result: {result}")
            return result == 0

        except OSError as e:
            # 捕获 COM 错误
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:  # RPC_E_CANTCALLOUT_ININPUTSYNCCALL
                logger.warning("BlurBehind 被跳过：COM 线程冲突")
                return False
            logger.error(f"启用 BlurBehind 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启用 BlurBehind 失败: {e}")
            return False

    @staticmethod
    def enable_transparent_gradient(window, color: int = 0x80000000) -> bool:
        """启用透明渐变效果（不带模糊）

        使用 ACCENT_ENABLE_TRANSPARENTGRADIENT (2) 实现透明但不模糊的效果。
        注意：这种效果在某些Windows版本上可能显示为带色调的透明。

        Args:
            window: QMainWindow
            color: AARRGGBB 格式的颜色
        """
        if not WindowBlurManager.is_windows():
            return False

        try:
            import ctypes
            from ctypes import wintypes, Structure, POINTER, byref, sizeof, c_int

            hwnd = int(window.winId())
            user32 = ctypes.windll.user32

            class ACCENT_POLICY(Structure):
                _fields_ = [
                    ("AccentState", c_int),
                    ("AccentFlags", c_int),
                    ("GradientColor", wintypes.DWORD),
                    ("AnimationId", c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attrib", c_int),
                    ("pvData", ctypes.c_void_p),
                    ("cbData", ctypes.c_size_t),
                ]

            WCA_ACCENT_POLICY = 19
            ACCENT_ENABLE_TRANSPARENTGRADIENT = 2

            # 转换颜色格式: AARRGGBB -> AABBGGRR
            a = (color >> 24) & 0xFF
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            gradient_color = (a << 24) | (b << 16) | (g << 8) | r

            logger.info(f"TransparentGradient参数: 输入颜色=0x{color:08X}, 转换后=0x{gradient_color:08X}, alpha={a}")

            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT
            accent.AccentFlags = 2
            accent.GradientColor = gradient_color
            accent.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attrib = WCA_ACCENT_POLICY
            data.pvData = ctypes.cast(byref(accent), ctypes.c_void_p)
            data.cbData = sizeof(accent)

            SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
            SetWindowCompositionAttribute.argtypes = [wintypes.HWND, POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
            SetWindowCompositionAttribute.restype = wintypes.BOOL

            result = SetWindowCompositionAttribute(hwnd, byref(data))
            logger.info(f"SetWindowCompositionAttribute (TransparentGradient) result: {result}")
            return bool(result)

        except OSError as e:
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:
                logger.warning("TransparentGradient 被跳过：COM 线程冲突")
                return False
            logger.error(f"启用 TransparentGradient 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启用 TransparentGradient 失败: {e}")
            return False

    @staticmethod
    def enable_acrylic(window, color: int = 0x99000000) -> bool:
        """启用 Windows 10 Acrylic 效果

        Args:
            window: QMainWindow
            color: AARRGGBB 格式的颜色（AA=透明度, RR/GG/BB=颜色）
                   例如: 0x80000000 = 50%透明黑色
                        0x80FFFFFF = 50%透明白色
        """
        if not WindowBlurManager.is_windows():
            return False

        if not WindowBlurManager.is_acrylic_supported():
            logger.warning("系统不支持 Acrylic 效果")
            return False

        try:
            import ctypes
            from ctypes import wintypes, Structure, POINTER, byref, sizeof, c_int

            hwnd = int(window.winId())
            user32 = ctypes.windll.user32

            # 定义结构体
            class ACCENT_POLICY(Structure):
                _fields_ = [
                    ("AccentState", c_int),
                    ("AccentFlags", c_int),
                    ("GradientColor", wintypes.DWORD),
                    ("AnimationId", c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attrib", c_int),
                    ("pvData", ctypes.c_void_p),
                    ("cbData", ctypes.c_size_t),
                ]

            # 常量
            WCA_ACCENT_POLICY = 19
            ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
            ACCENT_ENABLE_HOSTBACKDROP = 5  # Windows 11

            # 设置 Accent Policy
            # 使用 ACCENT_ENABLE_ACRYLICBLURBEHIND 需要传入颜色
            # GradientColor 格式为 AABBGGRR（注意是BGR不是RGB）
            # 将 AARRGGBB 转换为 AABBGGRR
            a = (color >> 24) & 0xFF
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            gradient_color = (a << 24) | (b << 16) | (g << 8) | r

            logger.info(f"Acrylic参数: 输入颜色=0x{color:08X}, 转换后=0x{gradient_color:08X}, alpha={a}")

            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.AccentFlags = 2  # 绘制所有边框
            accent.GradientColor = gradient_color
            accent.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attrib = WCA_ACCENT_POLICY
            data.pvData = ctypes.cast(byref(accent), ctypes.c_void_p)
            data.cbData = sizeof(accent)

            # 获取函数
            SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
            SetWindowCompositionAttribute.argtypes = [wintypes.HWND, POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
            SetWindowCompositionAttribute.restype = wintypes.BOOL

            result = SetWindowCompositionAttribute(hwnd, byref(data))
            logger.info(f"SetWindowCompositionAttribute (Acrylic) result: {result}")
            return bool(result)

        except OSError as e:
            # 捕获 COM 错误
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:  # RPC_E_CANTCALLOUT_ININPUTSYNCCALL
                logger.warning("Acrylic 被跳过：COM 线程冲突")
                return False
            logger.error(f"启用 Acrylic 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启用 Acrylic 失败: {e}")
            return False

    @staticmethod
    def enable_mica(window, is_dark: bool = False) -> bool:
        """启用 Windows 11 Mica 效果"""
        if not WindowBlurManager.is_windows():
            return False

        if not WindowBlurManager.is_windows_11():
            logger.warning("系统不支持 Mica 效果（需要 Windows 11）")
            return False

        try:
            import ctypes

            hwnd = int(window.winId())
            dwmapi = ctypes.windll.dwmapi

            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            # DWMWA_SYSTEMBACKDROP_TYPE = 38
            # DWMWA_MICA_EFFECT = 1029 (undocumented)

            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            DWMWA_MICA_EFFECT = 1029
            DWMWA_SYSTEMBACKDROP_TYPE = 38

            # 设置深色模式
            dark_value = ctypes.c_int(1 if is_dark else 0)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark_value),
                ctypes.sizeof(dark_value)
            )

            # 尝试使用 DWMWA_MICA_EFFECT（Windows 11 21H2）
            mica_value = ctypes.c_int(1)
            result = dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_MICA_EFFECT,
                ctypes.byref(mica_value),
                ctypes.sizeof(mica_value)
            )

            if result != 0:
                # 尝试使用 DWMWA_SYSTEMBACKDROP_TYPE（Windows 11 22H2+）
                # 2 = Mica, 3 = Acrylic, 4 = Tabbed
                backdrop_type = ctypes.c_int(2)  # Mica
                result = dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(backdrop_type),
                    ctypes.sizeof(backdrop_type)
                )

            logger.info(f"Mica effect result: {result}")
            return result == 0

        except OSError as e:
            # 捕获 COM 错误
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:  # RPC_E_CANTCALLOUT_ININPUTSYNCCALL
                logger.warning("Mica 被跳过：COM 线程冲突")
                return False
            logger.error(f"启用 Mica 失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启用 Mica 失败: {e}")
            return False

    @staticmethod
    def enable_window_transparency(window, opacity: float = 0.8, blur: bool = True, is_dark: bool = False) -> bool:
        """启用窗口透明效果

        Args:
            window: QMainWindow或QWidget
            opacity: 透明度 (0.0-1.0)，越小越透明
            blur: 是否启用模糊效果
                  - True: 使用DWM Acrylic/BlurBehind效果（毛玻璃）
                  - False: 纯透明，可以清晰看到桌面
            is_dark: 是否深色模式

        Returns:
            是否成功启用
        """
        from PyQt6.QtCore import Qt

        try:
            # 1. 设置Qt窗口属性 - 这是必须的
            window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

            build = WindowBlurManager.get_windows_build()
            logger.info(f"Windows build: {build}, opacity: {opacity}, blur: {blur}")

            if not WindowBlurManager.is_windows():
                return True

            # 2. 根据blur参数决定效果
            if blur:
                # 启用模糊效果（毛玻璃）
                # 计算颜色（带透明度）
                alpha = max(10, int(opacity * 255))  # 最少 10，确保效果可见

                # 使用中性灰色，避免深色背景导致整体太暗
                if is_dark:
                    # 深色模式：使用稍暗的灰色
                    color = (alpha << 24) | 0x404040  # AARRGGBB
                else:
                    # 浅色模式：使用亮灰色
                    color = (alpha << 24) | 0xE0E0E0  # AARRGGBB

                logger.info(f"Acrylic color: 0x{color:08X} (alpha={alpha}, is_dark={is_dark})")

                # 优先使用 Acrylic（可以看到窗口后面的内容 + 模糊）
                if WindowBlurManager.is_acrylic_supported():
                    success = WindowBlurManager.enable_acrylic(window, color)
                    if success:
                        logger.info("Acrylic 效果已启用（毛玻璃）")
                        return True

                # 降级到基础 BlurBehind
                success = WindowBlurManager.enable_blur_behind(window, True)
                if success:
                    logger.info("BlurBehind 效果已启用（毛玻璃）")
                    return True

                logger.warning("模糊效果启用失败，回退到纯透明")

            # blur=False 或模糊失败时：尝试不同的透明效果
            # 方案1：使用 ACCENT_ENABLE_TRANSPARENTGRADIENT（透明但不模糊）
            # 方案2：使用低透明度 Acrylic（有轻微模糊但更可靠）

            # 使用用户设置的透明度值
            # opacity 范围是 0.0-1.0，转换为 0-255
            # 注意：alpha 值不能太低（<10），否则Windows可能忽略效果导致黑屏
            user_alpha = max(10, int(opacity * 255))

            if is_dark:
                transparent_color = (user_alpha << 24) | 0x000000  # 透明黑
            else:
                transparent_color = (user_alpha << 24) | 0xFFFFFF  # 透明白

            logger.info(f"尝试无模糊透明模式: opacity={opacity}, alpha={user_alpha}, color=0x{transparent_color:08X}")

            # 方案1：尝试 TransparentGradient（不带模糊的透明）
            success = WindowBlurManager.enable_transparent_gradient(window, transparent_color)
            if success:
                logger.info("TransparentGradient 效果已启用（透明无模糊）")
                return True

            logger.warning("TransparentGradient 失败，尝试低透明度 Acrylic")

            # 方案2：使用 Acrylic 作为回退（会有轻微模糊）
            # 同样使用用户设置的透明度
            if is_dark:
                acrylic_color = (user_alpha << 24) | 0x202020
            else:
                acrylic_color = (user_alpha << 24) | 0xF0F0F0

            if WindowBlurManager.is_acrylic_supported():
                success = WindowBlurManager.enable_acrylic(window, acrylic_color)
                if success:
                    logger.info("Acrylic 效果已启用（作为回退，有轻微模糊）")
                    return True

            # 最后回退：BlurBehind
            logger.info("尝试 BlurBehind 作为最后回退")
            WindowBlurManager.enable_blur_behind(window, True)
            return True

        except OSError as e:
            # 捕获 COM 错误
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:  # RPC_E_CANTCALLOUT_ININPUTSYNCCALL
                logger.warning("窗口透明效果被跳过：COM 线程冲突")
                return False
            logger.error(f"启用窗口透明效果失败: {e}")
            return False
        except Exception as e:
            logger.error(f"启用窗口透明效果失败: {e}")
            return False

    @staticmethod
    def _apply_low_transparency(window, is_dark: bool = False) -> bool:
        """应用低透明度效果（备用方法）

        使用低透明度的 Acrylic 效果，可以透过去看到桌面内容。
        这是一个备用方法，主要用于 TransparentGradient 失败时的回退。

        Args:
            window: QMainWindow
            is_dark: 是否深色模式

        参考：
        - https://forum.qt.io/topic/155091/transparent-window-with-qt-widgets
        - https://forum.qt.io/topic/135217/pyqt-blur-behind-window-desktop-in-2022
        """
        if not WindowBlurManager.is_windows():
            return True

        try:
            import ctypes
            from ctypes import wintypes, Structure, POINTER, byref, sizeof, c_int

            hwnd = int(window.winId())
            user32 = ctypes.windll.user32

            class ACCENT_POLICY(Structure):
                _fields_ = [
                    ("AccentState", c_int),
                    ("AccentFlags", c_int),
                    ("GradientColor", wintypes.DWORD),
                    ("AnimationId", c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attrib", c_int),
                    ("pvData", ctypes.c_void_p),
                    ("cbData", ctypes.c_size_t),
                ]

            # 使用 Acrylic 效果但配合非常低的 alpha 值
            # 这样可以实现"接近透明"的效果，能透过去看到桌面
            # ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
            ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

            # 使用非常低的 alpha 值（10/255 ≈ 4%）使其接近透明
            # 颜色格式: AABBGGRR
            # 使用深色时用深灰，浅色时用浅灰
            alpha = 10  # 非常低的透明度
            color = (alpha << 24) | 0x000000  # 几乎完全透明

            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.AccentFlags = 2  # 绘制边框
            accent.GradientColor = color
            accent.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attrib = 19  # WCA_ACCENT_POLICY
            data.pvData = ctypes.cast(byref(accent), ctypes.c_void_p)
            data.cbData = sizeof(accent)

            SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
            SetWindowCompositionAttribute.argtypes = [wintypes.HWND, POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
            SetWindowCompositionAttribute.restype = wintypes.BOOL
            result = SetWindowCompositionAttribute(hwnd, byref(data))
            logger.info(f"设置低透明度 Acrylic 效果（接近纯透明）: {result}")

            return bool(result)

        except OSError as e:
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:
                logger.debug("设置透明效果被跳过：COM 线程冲突")
            return False
        except Exception as e:
            logger.warning(f"设置透明效果时出错: {e}")
            return False

    @staticmethod
    def disable_window_transparency(window, bg_color: str = None) -> bool:
        """禁用窗口透明效果

        注意：使用 ACCENT_DISABLED (0) 会导致黑色窗口，
        因此使用 ACCENT_ENABLE_GRADIENT (1) 来恢复正常不透明窗口。

        Args:
            window: QMainWindow或QWidget
            bg_color: 背景颜色字符串（如 '#FFFFFF' 或 '#1A1A2E'），
                      用于设置渐变色以匹配主题。如果未提供，默认使用白色。
        """
        from PyQt6.QtCore import Qt

        try:
            # 禁用Qt透明属性
            window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

            if WindowBlurManager.is_windows():
                # 禁用 BlurBehind
                WindowBlurManager.enable_blur_behind(window, False)

                # 恢复正常窗口（不使用 ACCENT_DISABLED 因为会导致黑色）
                try:
                    import ctypes
                    from ctypes import wintypes, Structure, POINTER, byref, sizeof, c_int

                    hwnd = int(window.winId())
                    user32 = ctypes.windll.user32

                    class ACCENT_POLICY(Structure):
                        _fields_ = [
                            ("AccentState", c_int),
                            ("AccentFlags", c_int),
                            ("GradientColor", wintypes.DWORD),
                            ("AnimationId", c_int),
                        ]

                    class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                        _fields_ = [
                            ("Attrib", c_int),
                            ("pvData", ctypes.c_void_p),
                            ("cbData", ctypes.c_size_t),
                        ]

                    # 使用 ACCENT_ENABLE_GRADIENT (1) 替代 ACCENT_DISABLED (0)
                    # ACCENT_DISABLED 会导致黑色窗口，而 ACCENT_ENABLE_GRADIENT 恢复正常
                    ACCENT_ENABLE_GRADIENT = 1

                    # 解析背景颜色并转换为 AABBGGRR 格式
                    gradient_color = 0xFFFFFFFF  # 默认白色
                    if bg_color:
                        try:
                            # 解析 #RRGGBB 格式
                            if bg_color.startswith('#'):
                                hex_color = bg_color[1:]
                                if len(hex_color) == 6:
                                    r = int(hex_color[0:2], 16)
                                    g = int(hex_color[2:4], 16)
                                    b = int(hex_color[4:6], 16)
                                    # 转换为 AABBGGRR 格式（完全不透明）
                                    gradient_color = (0xFF << 24) | (b << 16) | (g << 8) | r
                                    logger.info(f"使用主题背景色: {bg_color} -> 0x{gradient_color:08X}")
                        except Exception as e:
                            logger.warning(f"解析背景颜色失败: {e}，使用默认白色")

                    accent = ACCENT_POLICY()
                    accent.AccentState = ACCENT_ENABLE_GRADIENT
                    accent.AccentFlags = 0
                    accent.GradientColor = gradient_color
                    accent.AnimationId = 0

                    data = WINDOWCOMPOSITIONATTRIBDATA()
                    data.Attrib = 19  # WCA_ACCENT_POLICY
                    data.pvData = ctypes.cast(byref(accent), ctypes.c_void_p)
                    data.cbData = sizeof(accent)

                    SetWindowCompositionAttribute = user32.SetWindowCompositionAttribute
                    SetWindowCompositionAttribute.argtypes = [wintypes.HWND, POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
                    SetWindowCompositionAttribute.restype = wintypes.BOOL
                    SetWindowCompositionAttribute(hwnd, byref(data))

                    logger.info("窗口透明效果已禁用（使用ACCENT_ENABLE_GRADIENT）")

                except OSError as e:
                    # 捕获 COM 错误，静默处理
                    error_code = getattr(e, 'winerror', None)
                    if error_code == 0x8001010d:
                        logger.debug("禁用 Acrylic 被跳过：COM 线程冲突")
                except Exception as ex:
                    logger.warning(f"禁用Acrylic效果时出错: {ex}")

            return True

        except OSError as e:
            # 捕获 COM 错误
            error_code = getattr(e, 'winerror', None)
            if error_code == 0x8001010d:
                logger.warning("禁用窗口透明效果被跳过：COM 线程冲突")
                return False
            logger.error(f"禁用窗口透明效果失败: {e}")
            return False
        except Exception as e:
            logger.error(f"禁用窗口透明效果失败: {e}")
            return False
