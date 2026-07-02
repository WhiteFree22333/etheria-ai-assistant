"""
游戏画面截图 - 支持多种后台截图方案
"""
import time
import os
from datetime import datetime
from typing import Optional

import numpy as np
from PIL import Image
import mss
import win32gui
import win32con

from core._base.window import GameWindow


def capture_mss(game_window: GameWindow) -> Optional[Image.Image]:
    """
    MSS 前台截图（窗口必须可见，不能被遮挡）

    Args:
        game_window: 目标窗口

    Returns:
        PIL.Image 或 None
    """
    try:
        with mss.mss() as sct:
            monitor = {
                "top": game_window.top,
                "left": game_window.left,
                "width": game_window.width,
                "height": game_window.height,
            }
            screenshot = sct.grab(monitor)
            return Image.frombytes(
                "RGB", screenshot.size, screenshot.bgra, "raw", "BGRX"
            )
    except Exception:
        return None


def capture_dxcam(game_window: GameWindow) -> Optional[Image.Image]:
    """DXCam 游戏截图（需要 dxcam 库）"""
    try:
        import dxcam
        camera = dxcam.create(output_color="RGB")
        frame = camera.grab(region=(
            game_window.left, game_window.top,
            game_window.right, game_window.bottom,
        ))
        if frame is not None:
            return Image.fromarray(frame)
        return None
    except ImportError:
        return None
    except Exception:
        return None


def capture_printwindow_pca(hwnd: int, game_window: GameWindow) -> Optional[Image.Image]:
    """
    PrintWindow with PW_RENDERFULLCONTENT (方法1)
    尝试从 DWM 获取完整窗口内容
    """
    try:
        import win32ui
        from ctypes import windll

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        result = windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)

        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)

        img = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1,
        )

        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return img if result == 1 else None
    except Exception:
        return None


def capture_bitblt(hwnd: int, game_window: GameWindow) -> Optional[Image.Image]:
    """BitBlt 截图（窗口可被遮挡但需可见）"""
    try:
        import win32ui

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        hwnd_dc = win32gui.GetWindowDC(hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        save_bitmap = win32ui.CreateBitmap()
        save_bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(save_bitmap)

        save_dc.BitBlt((0, 0), (width, height), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmpinfo = save_bitmap.GetInfo()
        bmpstr = save_bitmap.GetBitmapBits(True)

        img = Image.frombuffer(
            "RGB",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRX", 0, 1,
        )

        win32gui.DeleteObject(save_bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwnd_dc)

        return img
    except Exception:
        return None


def is_black_image(image: Image.Image, threshold: float = 10.0) -> bool:
    """检查截图是否为全黑（后台截图失败的标志）"""
    arr = np.array(image)
    return float(arr.mean()) < threshold


def capture_game_screen(
    game_window: GameWindow,
    background_mode: bool = True,
    auto_focus: bool = True,
) -> Optional[Image.Image]:
    """
    截取游戏窗口画面（主入口）

    优先尝试后台截图，失败则回退到前台截图

    Args:
        game_window: 目标窗口
        background_mode: 是否先尝试后台截图
        auto_focus: 后台失败时是否自动切换窗口

    Returns:
        PIL.Image 或 None
    """
    if background_mode:
        # 按优先级尝试各种后台截图方法
        # PrintWindow 直接从 DWM 抓窗口内容，被遮挡也能截到 → 排最前
        methods = [
            lambda: capture_printwindow_pca(game_window.hwnd, game_window),
            lambda: capture_dxcam(game_window),
            lambda: capture_bitblt(game_window.hwnd, game_window),
        ]

        for method in methods:
            try:
                img = method()
                if img is not None and not is_black_image(img):
                    return img
            except Exception:
                continue

        if not auto_focus:
            return capture_mss(game_window)

    # 前台截图 - 自动切换到游戏窗口
    return _capture_with_auto_focus(game_window)


def _capture_with_auto_focus(game_window: GameWindow) -> Optional[Image.Image]:
    """切换到游戏窗口，截图后恢复"""
    from .window import focus_window

    current_hwnd = win32gui.GetForegroundWindow()

    try:
        focus_window(game_window.hwnd)
        time.sleep(0.3)
        img = capture_mss(game_window)

        if current_hwnd and current_hwnd != game_window.hwnd:
            time.sleep(0.1)
            try:
                win32gui.SetForegroundWindow(current_hwnd)
            except Exception:
                pass

        return img
    except Exception:
        return capture_mss(game_window)


def save_screenshot(image: Image.Image, directory: str = "screenshots") -> str:
    """保存截图到文件，返回文件路径"""
    os.makedirs(directory, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(directory, filename)
    image.save(filepath)
    return filepath


def save_template(image: Image.Image, name: str, directory: str = "templates") -> str:
    """保存图标模板到文件，返回文件路径"""
    os.makedirs(directory, exist_ok=True)
    filename = f"{name}.png"
    filepath = os.path.join(directory, filename)
    image.save(filepath)
    return filepath
