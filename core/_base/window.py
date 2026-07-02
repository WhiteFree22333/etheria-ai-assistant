"""
游戏窗口查找和管理
"""
import os
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple

import win32gui
import win32con
import win32process


# 当前进程 PID，用于排除助手自身窗口
_OWN_PID = os.getpid()


@dataclass
class GameWindow:
    hwnd: int
    title: str
    left: int
    top: int
    right: int
    bottom: int
    pid: int = 0

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> Tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)


def _get_window_pid(hwnd: int) -> int:
    """获取窗口所属进程 PID"""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception:
        return 0


def get_all_windows() -> List[Tuple[int, str]]:
    """获取所有可见窗口列表"""
    windows = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, None)
    return windows


def find_game_window(keyword: str) -> Optional[GameWindow]:
    """
    根据标题关键词查找游戏窗口（自动排除助手自身窗口）。

    先找标题含关键词的顶层窗口，再递归搜索其所有后代子窗口找 UnityWndClass。
    浏览器标题也可能含关键词，但不会有 Unity 子窗口 → 被排除。

    Args:
        keyword: 窗口标题关键词

    Returns:
        GameWindow 或 None
    """
    candidates = []
    for hwnd, title in get_all_windows():
        if keyword not in title:
            continue
        pid = _get_window_pid(hwnd)
        if pid == _OWN_PID:
            continue
        # 过滤掉非正常尺寸的窗口（最小化/隐藏窗口坐标=(-32000,-32000)）
        rect = win32gui.GetWindowRect(hwnd)
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w < 200 or h < 100:
            continue
        candidates.append((hwnd, title, pid))

    if not candidates:
        return None

    # 在候选窗口的子树中递归搜索 UnityWndClass
    def _find_unity_descendant(top_hwnd):
        found = []
        def _enum(hwnd, _lparam):
            try:
                cls = win32gui.GetClassName(hwnd)
                if 'Unity' in cls or 'unity' in cls.lower():
                    found.append(hwnd)
                    return False  # 找到了，停止
            except Exception:
                pass
            # 递归枚举子窗口的子窗口
            try:
                win32gui.EnumChildWindows(hwnd, _enum, None)
            except Exception:
                pass
            return True
        try:
            win32gui.EnumChildWindows(top_hwnd, _enum, None)
        except Exception:
            pass
        return found[0] if found else None

    for hwnd, title, pid in candidates:
        unity_hwnd = _find_unity_descendant(hwnd)
        if unity_hwnd is not None:
            rect = win32gui.GetWindowRect(hwnd)
            return GameWindow(hwnd=hwnd, title=title,
                              left=rect[0], top=rect[1],
                              right=rect[2], bottom=rect[3], pid=pid)

    # 完全没有 Unity 子窗口 → 取第一个（兜底兼容非 Unity 游戏）
    hwnd, title, pid = candidates[0]
    rect = win32gui.GetWindowRect(hwnd)
    return GameWindow(hwnd=hwnd, title=title,
                      left=rect[0], top=rect[1],
                      right=rect[2], bottom=rect[3], pid=pid)


def focus_window(hwnd: int) -> bool:
    """
    强制将窗口带到前台。

    利用 AttachThreadInput 技法绕过 Windows 的防抢焦点限制：
    先挂接到当前前台窗口的线程，再调用 SetForegroundWindow。

    Args:
        hwnd: 窗口句柄

    Returns:
        是否成功聚焦
    """
    import ctypes

    try:
        # 如果已经是最小化，先恢复
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        fg_hwnd = win32gui.GetForegroundWindow()
        fg_tid = ctypes.windll.user32.GetWindowThreadProcessId(fg_hwnd, None)

        # 挂接到前台窗口线程 → 绕过焦点锁定
        attached = bool(ctypes.windll.user32.AttachThreadInput(our_tid, fg_tid, True))

        try:
            # 把窗口推到 Z 序最前面
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            # 短暂置顶后取消（防止永远挡在其他窗口前面）
            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                ctypes.windll.user32.AttachThreadInput(our_tid, fg_tid, False)

        # 确认拿到了焦点
        for _ in range(20):
            if win32gui.GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.05)
        return False
    except Exception:
        return False


def get_client_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """获取窗口客户区坐标（相对于屏幕）"""
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    point = win32gui.ClientToScreen(hwnd, (left, top))
    return (point[0], point[1], point[0] + right - left, point[1] + bottom - top)
