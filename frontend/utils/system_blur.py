"""
Windows系统级模糊效果管理器

提供Windows Acrylic和Mica效果的支持。
仅在Windows 10 1803+和Windows 11上生效。
"""

import sys
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SystemBlurManager:
    """Windows系统级模糊效果管理器

    支持:
    - Windows 10 1803+: Acrylic效果
    - Windows 11: Mica效果

    使用方式:
        from utils.system_blur import SystemBlurManager

        # 检查是否支持
        if SystemBlurManager.is_supported():
            # 获取窗口句柄（PyQt6）
            hwnd = int(window.winId())
            # 启用Acrylic效果
            SystemBlurManager.enable_acrylic(hwnd)

        # 禁用效果
        SystemBlurManager.disable_blur(hwnd)
    """

    # Windows版本常量
    WINDOWS_10_1803 = (10, 0, 17134)  # Acrylic支持起始版本
    WINDOWS_11 = (10, 0, 22000)       # Mica支持起始版本

    # Windows API常量
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    DWMWA_MICA_EFFECT = 1029
    DWMWA_SYSTEMBACKDROP_TYPE = 38

    # 系统背景类型
    DWMSBT_AUTO = 0
    DWMSBT_NONE = 1
    DWMSBT_MAINWINDOW = 2        # Mica
    DWMSBT_TRANSIENTWINDOW = 3   # Acrylic
    DWMSBT_TABBEDWINDOW = 4      # Mica Alt

    @staticmethod
    def is_supported() -> bool:
        """检查系统是否支持Acrylic/Mica效果

        Returns:
            bool: 是否支持
        """
        if sys.platform != "win32":
            return False

        try:
            version = SystemBlurManager._get_windows_version()
            if version is None:
                return False

            # Windows 10 1803+支持Acrylic
            return version >= SystemBlurManager.WINDOWS_10_1803
        except Exception as e:
            logger.warning(f"检查Windows版本失败: {e}")
            return False

    @staticmethod
    def is_mica_supported() -> bool:
        """检查是否支持Mica效果（Windows 11专属）

        Returns:
            bool: 是否支持Mica
        """
        if sys.platform != "win32":
            return False

        try:
            version = SystemBlurManager._get_windows_version()
            if version is None:
                return False

            return version >= SystemBlurManager.WINDOWS_11
        except Exception as e:
            logger.warning(f"检查Windows版本失败: {e}")
            return False

    @staticmethod
    def _get_windows_version() -> Optional[tuple]:
        """获取Windows版本

        Returns:
            (major, minor, build) 元组，失败返回None
        """
        try:
            import ctypes
            from ctypes import wintypes

            # 使用RtlGetVersion获取真实版本号
            ntdll = ctypes.windll.ntdll

            class OSVERSIONINFOW(ctypes.Structure):
                _fields_ = [
                    ("dwOSVersionInfoSize", wintypes.DWORD),
                    ("dwMajorVersion", wintypes.DWORD),
                    ("dwMinorVersion", wintypes.DWORD),
                    ("dwBuildNumber", wintypes.DWORD),
                    ("dwPlatformId", wintypes.DWORD),
                    ("szCSDVersion", wintypes.WCHAR * 128),
                ]

            version_info = OSVERSIONINFOW()
            version_info.dwOSVersionInfoSize = ctypes.sizeof(OSVERSIONINFOW)

            if ntdll.RtlGetVersion(ctypes.byref(version_info)) == 0:
                return (
                    version_info.dwMajorVersion,
                    version_info.dwMinorVersion,
                    version_info.dwBuildNumber
                )
        except Exception as e:
            logger.warning(f"获取Windows版本失败: {e}")

        return None

    @staticmethod
    def enable_acrylic(
        hwnd: int,
        color: str = "#000000",
        opacity: float = 0.7
    ) -> bool:
        """启用Acrylic效果

        Args:
            hwnd: 窗口句柄
            color: 背景色（十六进制）
            opacity: 透明度 (0.0-1.0)

        Returns:
            bool: 是否成功
        """
        if sys.platform != "win32":
            return False

        try:
            import ctypes
            from ctypes import wintypes

            # 解析颜色
            color = color.lstrip('#')
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            a = int(opacity * 255)

            # 组合ARGB颜色值
            argb_color = (a << 24) | (b << 16) | (g << 8) | r

            # 定义结构体
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint),
                    ("AnimationId", ctypes.c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.POINTER(ACCENT_POLICY)),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            # Accent状态
            ACCENT_ENABLE_ACRYLICBLURBEHIND = 4

            # 设置Accent
            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
            accent.AccentFlags = 2  # 绘制所有边框
            accent.GradientColor = argb_color

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)

            # 调用API
            user32 = ctypes.windll.user32
            user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

            logger.info(f"已启用Acrylic效果: hwnd={hwnd}, color={color}, opacity={opacity}")
            return True

        except Exception as e:
            logger.error(f"启用Acrylic效果失败: {e}")
            return False

    @staticmethod
    def enable_mica(hwnd: int, dark_mode: bool = False) -> bool:
        """启用Mica效果（Windows 11专属）

        Args:
            hwnd: 窗口句柄
            dark_mode: 是否使用深色模式

        Returns:
            bool: 是否成功
        """
        if not SystemBlurManager.is_mica_supported():
            logger.warning("当前系统不支持Mica效果")
            return False

        try:
            import ctypes
            from ctypes import wintypes

            dwmapi = ctypes.windll.dwmapi

            # 设置深色模式
            value = ctypes.c_int(1 if dark_mode else 0)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                SystemBlurManager.DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )

            # 设置Mica效果
            backdrop_type = ctypes.c_int(SystemBlurManager.DWMSBT_MAINWINDOW)
            result = dwmapi.DwmSetWindowAttribute(
                hwnd,
                SystemBlurManager.DWMWA_SYSTEMBACKDROP_TYPE,
                ctypes.byref(backdrop_type),
                ctypes.sizeof(backdrop_type)
            )

            if result == 0:
                logger.info(f"已启用Mica效果: hwnd={hwnd}, dark_mode={dark_mode}")
                return True
            else:
                logger.warning(f"启用Mica效果返回非零值: {result}")
                return False

        except Exception as e:
            logger.error(f"启用Mica效果失败: {e}")
            return False

    @staticmethod
    def disable_blur(hwnd: int) -> bool:
        """禁用系统模糊效果

        Args:
            hwnd: 窗口句柄

        Returns:
            bool: 是否成功
        """
        if sys.platform != "win32":
            return False

        try:
            import ctypes

            # 定义结构体
            class ACCENT_POLICY(ctypes.Structure):
                _fields_ = [
                    ("AccentState", ctypes.c_int),
                    ("AccentFlags", ctypes.c_int),
                    ("GradientColor", ctypes.c_uint),
                    ("AnimationId", ctypes.c_int),
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
                _fields_ = [
                    ("Attribute", ctypes.c_int),
                    ("Data", ctypes.POINTER(ACCENT_POLICY)),
                    ("SizeOfData", ctypes.c_size_t),
                ]

            # 禁用Accent
            ACCENT_DISABLED = 0

            accent = ACCENT_POLICY()
            accent.AccentState = ACCENT_DISABLED

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)

            user32 = ctypes.windll.user32
            user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

            # 同时禁用Mica（如果是Windows 11）
            if SystemBlurManager.is_mica_supported():
                dwmapi = ctypes.windll.dwmapi
                backdrop_type = ctypes.c_int(SystemBlurManager.DWMSBT_NONE)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    SystemBlurManager.DWMWA_SYSTEMBACKDROP_TYPE,
                    ctypes.byref(backdrop_type),
                    ctypes.sizeof(backdrop_type)
                )

            logger.info(f"已禁用系统模糊效果: hwnd={hwnd}")
            return True

        except Exception as e:
            logger.error(f"禁用系统模糊效果失败: {e}")
            return False

    @staticmethod
    def apply_transparency_config(hwnd: int, config: dict) -> bool:
        """根据透明效果配置应用系统模糊

        Args:
            hwnd: 窗口句柄
            config: 透明效果配置字典

        Returns:
            bool: 是否成功
        """
        if not config.get("enabled") or not config.get("system_blur"):
            return SystemBlurManager.disable_blur(hwnd)

        # 根据系统版本选择效果
        if SystemBlurManager.is_mica_supported():
            # Windows 11优先使用Mica
            return SystemBlurManager.enable_mica(hwnd, dark_mode=False)
        elif SystemBlurManager.is_supported():
            # Windows 10使用Acrylic
            # 使用get_component_opacity获取透明度，自动应用主控透明度系数
            from themes.theme_manager import theme_manager
            opacity = theme_manager.get_component_opacity("sidebar")
            return SystemBlurManager.enable_acrylic(hwnd, opacity=opacity)
        else:
            return False
