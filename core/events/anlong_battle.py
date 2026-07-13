"""
暗笼激斗活动模块

全 PostMessage 后台点击，零键盘依赖。
"""
import time

from core._base.input import post_click
from core._common.battle_common import tpl, wait_for_image, open_sidebar, enter_and_wait_battle, exit_battle


def run_anlong_battle(bot, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
    """
    暗笼激斗流程。

    1. 回主界面 + 开侧边栏
    2. 点挑战 → 点限时活动 → 点暗笼激斗图标 → 点前往挑战
    3. 进战斗 + 等结束 → 退出
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log(f'暗笼激斗开始 → {difficulty} ×{streak}')
        bot._log('=' * 40)

        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot): return False

        bot._log('点击挑战...')
        pos = wait_for_image(bot, '挑战.png')
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1]); time.sleep(2)

        bot._log('点击限时活动...')
        pos = wait_for_image(bot, '限时活动.png')
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1]); time.sleep(2)

        bot._log('点击暗笼激斗图标...')
        pos = wait_for_image(bot, '暗笼激斗图标.png')
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1]); time.sleep(2)

        bot._log('点击暗笼激斗前往挑战...')
        pos = wait_for_image(bot, '暗笼激斗前往挑战.png')
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1]); time.sleep(2)

        if not enter_and_wait_battle(bot, 'Buff.png'):
            return False
        exit_battle(bot, 30, 30)

        bot._log(f'[OK] 暗笼激斗完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
