"""
超能二十一活动模块

全 PostMessage 后台点击，零键盘依赖。
"""
import os
import time

from core._base.input import post_click
from core._common.battle_common import tpl, wait_for_image, open_sidebar, enter_and_wait_battle, exit_battle


def _bare_click(hwnd, screen_x, screen_y):
    """最小点击——仅发一组 PostMessage，无 retry。用于 toggle 按钮。
    保留焦点检测：窗口被遮挡时短暂提到前台，保证 Unity 处理点击。"""
    import win32gui
    import win32con
    import win32api
    import ctypes
    import time as _t
    target = None
    try:
        def _fc(ch, _):
            nonlocal target
            try:
                if 'Unity' in win32gui.GetClassName(ch):
                    target = ch
                    return False
            except Exception:
                pass
            return True
        win32gui.EnumChildWindows(hwnd, _fc, None)
    except Exception:
        pass
    if not target:
        target = hwnd
    cx, cy = win32gui.ScreenToClient(target, (screen_x, screen_y))
    if cx < 0 or cy < 0:
        return

    # 焦点检测：被遮挡时短暂提到前台
    fg = win32gui.GetForegroundWindow()
    if fg != hwnd and fg != target:
        try:
            ctypes.windll.user32.SetForegroundWindow(target)
        except Exception:
            pass
        _t.sleep(0.02)

    lp = win32api.MAKELONG(cx, cy)
    win32gui.PostMessage(target, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    win32gui.PostMessage(target, win32con.WM_ACTIVATEAPP, 1, 0)
    win32gui.PostMessage(target, win32con.WM_LBUTTONDOWN,
                         win32con.MK_LBUTTON, lp)
    win32gui.PostMessage(target, win32con.WM_LBUTTONUP, 0, lp)


_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_HUODONG_TPL = os.path.join(_BASE_DIR, 'templates', 'huodong')


def _htpl(name: str) -> str:
    """活动模板路径 — templates/huodong/"""
    return os.path.join(_HUODONG_TPL, name)


def run_chaoneng_battle(bot, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
    """
    超能二十一流程。

    1. 回主界面 + 开侧边栏
    2. 点挑战 → 点限时活动 → 点超能二十一图标 → 点匹配
    3. 循环 streak 次：等托管 → 等再来一局
    4. 退出
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log(f'超能二十一开始 → {difficulty} ×{streak}')
        bot._log('=' * 40)

        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot):
            return False

        bot._log('点击挑战...')
        pos = wait_for_image(bot, '挑战.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        bot._log('点击限时活动...')
        pos = wait_for_image(bot, '限时活动.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        bot._log('点击超能二十一图标...')
        pos = wait_for_image(bot, _htpl('超能二十一图标.png'))
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        bot._log('点击超能二十一匹配...')
        pos = wait_for_image(bot, _htpl('超能二十一匹配.png'))
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        for r in range(streak):
            if not bot.is_running:
                return False
            bot._log(f'=== 第 {r+1}/{streak} 局 ===')

            # 第一阶段：循环识别"继续"，直到等到
            bot._log('等待超能继续...')
            while bot.is_running:
                pos = wait_for_image(bot, _htpl('超能继续.png'), timeout=30)
                if pos is not None:
                    break

            # 识别"托管"并点击
            bot._log('点击超能二十一托管...')
            pos = wait_for_image(bot, _htpl('超能二十一托管.png'), timeout=30)
            if pos is None:
                bot._log('[FAIL] 超时：未检测到超能二十一托管')
                return False
            _bare_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            # 第二阶段：等"再来一局"弹出（最后一局不点，直接退出）
            bot._log('等待本局结束（超能再来一局）...')
            while bot.is_running:
                pos = wait_for_image(bot, _htpl('超能再来一局.png'), timeout=600)
                if pos is not None:
                    break
            is_last = (r == streak - 1)
            if not is_last:
                post_click(hwnd, pos[0], pos[1])
                bot._log(f'第 {r+1}/{streak} 局完成')
            else:
                bot._log(f'第 {r+1}/{streak} 局完成（最后一局，跳过点击）')
            time.sleep(2)

        # exit_battle(bot, 30, 30)

        bot._log('[OK] 超能二十一完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
