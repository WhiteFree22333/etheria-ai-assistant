"""
鼠标和键盘自动化操作

所有会操作鼠标/键盘的函数都通过 lock_input() 上下文管理器
自动锁定用户物理输入，操作完成后立刻释放。
SendInput 注入的事件不受 BlockInput 影响。
"""
import time
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
from typing import Tuple

import pyautogui
from core.config import GAME_CONFIG

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# ====== SendInput 结构体 ======
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("mi", MOUSEINPUT),
    ]


def _send_input_mouse(flags: int, x: int = 0, y: int = 0, data: int = 0):
    """调用 Win32 SendInput 发送鼠标事件"""
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi.dx = x
    inp.mi.dy = y
    inp.mi.mouseData = data
    inp.mi.dwFlags = flags
    inp.mi.time = 0
    inp.mi.dwExtraInfo = None
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


# PeekMessage 消息结构体
class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT * 2),  # 简化，我们不读它
    ]


# 消息队列清理用
WM_MOUSEFIRST = 0x0200
WM_MOUSELAST  = 0x020E
PM_REMOVE = 1

# 消息队列中的鼠标覆盖范围（包括 WM_MOUSEFIRST ~ WM_MOUSELAST 和 WM_MOUSEWHEEL=0x020A）
_MOUSE_MSGS = (WM_MOUSEFIRST, WM_MOUSELAST)
_MOUSE_EXTRAS = (0x020A,)  # WM_MOUSEWHEEL


@contextmanager
def lock_input(hwnd: int = None):
    """
    公共锁定上下文管理器。

    in with 块内：
      - 线程挂接到游戏窗口（AttachThreadInput）
      - 清空消息队列中残留的用户鼠标事件
      - 用户物理鼠标/键盘被锁定（BlockInput，SendInput 不受影响）

    退出 with 块时自动解锁、断挂接。
    """
    our_tid = ctypes.windll.kernel32.GetCurrentThreadId()
    attached = False

    if hwnd:
        try:
            game_tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
            ctypes.windll.user32.AttachThreadInput(our_tid, game_tid, True)
            attached = True
        except Exception:
            pass

    ctypes.windll.user32.BlockInput(True)

    # 清空消息队列中已经排队的残留鼠标事件
    # 场景：用户在 lock 之前动了鼠标，事件已经在队列里，SendInput 会被它覆盖
    _flush_mouse_queue()

    try:
        yield
    finally:
        ctypes.windll.user32.BlockInput(False)
        if attached:
            try:
                ctypes.windll.user32.AttachThreadInput(our_tid, game_tid, False)
            except Exception:
                pass


def _flush_mouse_queue():
    """清空当前线程消息队列中所有残留的鼠标事件"""
    msg = MSG()
    for msg_id in _MOUSE_EXTRAS:
        while ctypes.windll.user32.PeekMessageW(
            ctypes.byref(msg), None, msg_id, msg_id, PM_REMOVE
        ):
            pass
    while ctypes.windll.user32.PeekMessageW(
        ctypes.byref(msg), None, *_MOUSE_MSGS, PM_REMOVE
    ):
        pass


def click_at(x: int, y: int, clicks: int = 1, interval: float = 0.5):
    """前台点击（鼠标可见移动）"""
    pyautogui.click(x, y, clicks=clicks, interval=interval)
    time.sleep(0.3)


def click_window(hwnd: int, screen_x: int, screen_y: int):
    """
    后台点击（~50ms）：跳转光标 → 按下 → 松开 → 恢复原位。

    锁定期间用户无法干扰，SendInput 事件路由到游戏线程。
    """
    with lock_input(hwnd):
        orig_x, orig_y = pyautogui.position()
        ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
        _send_input_mouse(MOUSEEVENTF_LEFTDOWN)
        time.sleep(0.02)
        _send_input_mouse(MOUSEEVENTF_LEFTUP)
        ctypes.windll.user32.SetCursorPos(orig_x, orig_y)


def move_cursor(hwnd: int, screen_x: int, screen_y: int):
    """
    只移动光标到指定位置（不点击），~20ms。

    用于滚轮操作前的鼠标定位。
    """
    with lock_input(hwnd):
        ctypes.windll.user32.SetCursorPos(screen_x, screen_y)
        time.sleep(0.02)


def scroll(clicks: int, hwnd: int = None):
    """
    鼠标滚轮操作（~15ms 不含参数中的 sleep）。

    正数 = 向上滚动，负数 = 向下滚动。
    每个 clicks = 滚轮的一格。
    """
    amount = clicks * WHEEL_DELTA
    with lock_input(hwnd):
        _send_input_mouse(MOUSEEVENTF_WHEEL, data=amount)


def move_to(x: int, y: int, duration: float = 0.3):
    pyautogui.moveTo(x, y, duration=duration)


def press_key(key: str):
    """按键盘按键"""
    pyautogui.press(key)
    time.sleep(0.2)


def hotkey(*keys: str):
    pyautogui.hotkey(*keys)


def get_position() -> Tuple[int, int]:
    return pyautogui.position()


# ====== PostMessage 后台点击（真正的无干扰方案） ======
# 直接往游戏窗口消息队列里塞鼠标事件，完全绕过：
#   - 系统光标路由（鼠标在哪都不影响）
#   - 窗口焦点状态（后台也能收到）
#   - BlockInput 锁（不需要锁用户）

def post_click(hwnd: int, screen_x: int, screen_y: int):
    """
    后台点击：PostMessage 异步投递鼠标事件到 Unity 子窗口的消息队列。

    PostMessage 不阻塞，消息排队后游戏在每帧的 PeekMessage 循环中顺序处理，
    比 SendMessage（同步 inline 处理）更可靠。

    Args:
        hwnd: 游戏顶层窗口句柄
        screen_x, screen_y: 屏幕绝对坐标
    """
    import win32gui
    import win32con
    import win32api

    target = _find_unity_child(hwnd)

    try:
        cx, cy = win32gui.ScreenToClient(target, (screen_x, screen_y))
    except Exception:
        print(f'[post_click] 窗口句柄失效 target={target} — 游戏可能已被关闭，点击丢弃')
        return
    if cx < 0 or cy < 0:
        print(f'[post_click] 坐标溢出 screen=({screen_x},{screen_y}) client=({cx},{cy}) — 点击被丢弃')
        return

    lparam = win32api.MAKELONG(cx, cy)

    # 窗口被遮挡时 Unity 可能忽略 PostMessage 鼠标事件。
    # 960×540 小窗口在角落，短暂提到前台用户无感知。
    fg = win32gui.GetForegroundWindow()
    if fg != hwnd and fg != target:
        try:
            import ctypes
            ctypes.windll.user32.SetForegroundWindow(target)
        except Exception:
            pass
        time.sleep(0.02)

    # 全部用 PostMessage（异步队列），游戏每帧按序处理
    win32gui.PostMessage(target, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    win32gui.PostMessage(target, win32con.WM_ACTIVATEAPP, 1, 0)
    win32gui.PostMessage(target, win32con.WM_MOUSEMOVE, 0, lparam)
    win32gui.PostMessage(target, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(GAME_CONFIG.post_click_down_delay)
    win32gui.PostMessage(target, win32con.WM_LBUTTONUP, 0, lparam)
    time.sleep(GAME_CONFIG.post_click_up_delay)


def post_scroll(hwnd: int, clicks: int):
    """
    后台滚轮：通过 PostMessage 直接往游戏窗口发滚轮事件。

    Args:
        hwnd: 游戏窗口句柄
        clicks: 滚动格数，正=上，负=下
    """
    import win32gui
    import win32con

    amount = clicks * WHEEL_DELTA
    win32gui.PostMessage(hwnd, win32con.WM_MOUSEWHEEL, amount << 16, 0)


def _find_unity_child(hwnd: int) -> int:
    """
    查找 Unity 游戏的实际渲染子窗口。
    Unity 的输入处理通常在 UnityWndClass 子窗口上。
    """
    import win32gui

    game_classes = ['UnityWndClass', 'UnityGame', 'UnrealWindow', 'SDL_app', 'GLFW']
    result = hwnd

    def callback(child_hwnd, _):
        nonlocal result
        try:
            cls = win32gui.GetClassName(child_hwnd)
            if any(gc in cls for gc in game_classes):
                result = child_hwnd
                return False
        except Exception:
            pass
        return True

    try:
        win32gui.EnumChildWindows(hwnd, callback, None)
    except Exception:
        pass
    return result


def post_drag(hwnd: int, from_x: int, from_y: int, to_x: int, to_y: int,
              steps: int = 10, step_delay: float = 0.015):
    """
    SendInput 按住拖动：光标闪现到起点 → 按住 → 分步拖到终点 → 松开 → 归位。

    每步之间等 step_delay 秒让 Unity 轮询 Input.mousePosition。

    调参指南（在 scroll_and_find 函数的调用处改）：
      - drag_px: 每次拖动距离（绝对值越大滚越多，但容易误触）
      - steps:   步数越多越平滑、越慢（数据大了总时长增加）
      - step_delay: 每步间隔秒数（太小游戏来不及读，太大拖得慢）
    """
    import pyautogui

    dx_total = to_x - from_x
    dy_total = to_y - from_y
    dx_step = dx_total // steps
    dy_step = dy_total // steps
    dx_rem = dx_total - dx_step * steps
    dy_rem = dy_total - dy_step * steps

    with lock_input(hwnd):
        orig_x, orig_y = pyautogui.position()

        # 移到起点 → 按下
        ctypes.windll.user32.SetCursorPos(from_x, from_y)
        time.sleep(0.01)
        _send_input_mouse(MOUSEEVENTF_LEFTDOWN)
        time.sleep(step_delay)

        # 分步拖动
        for _ in range(steps):
            _send_input_mouse(MOUSEEVENTF_MOVE, x=dx_step, y=dy_step)
            time.sleep(step_delay)

        # 补齐余数
        if dx_rem or dy_rem:
            _send_input_mouse(MOUSEEVENTF_MOVE, x=dx_rem, y=dy_rem)
            time.sleep(step_delay)

        # 松开 → 归位
        _send_input_mouse(MOUSEEVENTF_LEFTUP)
        time.sleep(0.01)
        ctypes.windll.user32.SetCursorPos(orig_x, orig_y)


def post_key(hwnd: int, vk_code: int):
    """
    后台按键：通过 PostMessage 直接往游戏窗口发键盘事件。

    Args:
        hwnd: 游戏窗口句柄
        vk_code: 虚拟键码（如 win32con.VK_TAB = 0x09）
    """
    import win32gui
    import win32con

    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
    time.sleep(0.03)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
