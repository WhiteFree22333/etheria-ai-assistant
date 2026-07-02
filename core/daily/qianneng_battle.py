"""
潜能/经验战斗模块 — 经验/神理/妖异/虚空/破序/恒定

全 PostMessage 后台点击，零键盘依赖。
入口模板: 经验→经验入口.png; 其余5类→潜能入口.png
难度模板: 经验→经验25难度.png; 神理→潜能难度理.png; 妖异→潜能难度异.png;
          虚空→潜能难度虚.png; 破序→潜能难度破序.png; 恒定→潜能难度恒定.png
"""
import time

from core._base.input import post_click
from core._common.battle_common import tpl, wait_for_image, enter_dungeon
from core.daily.zhike_battle import _wait_battle_or_stamina, start_battle

_ENTRY_MAP = {
    '经验': '经验入口.png',
}
_DIFF_MAP = {
    '经验': '经验25难度.png',
    '神理': '潜能难度理.png',
    '妖异': '潜能难度异.png',
    '虚空': '潜能难度虚.png',
    '破序': '潜能难度破序.png',
    '恒定': '潜能难度恒定.png',
}


def run_qianneng_battle(bot, character_name: str = '', difficulty: str = '', streak: int = 1, double_stamina: bool = False) -> bool:
    """潜能/经验战斗流程。entry_tpl/diff_tpl 根据 character_name 自动映射。"""
    hwnd = bot.game_window.hwnd
    bot._running = True

    entry_tpl = _ENTRY_MAP.get(character_name, '潜能入口.png')
    diff_tpl = _DIFF_MAP.get(character_name, '经验25难度.png')

    try:
        bot._log('=' * 40)
        extra = ' · 双倍' if double_stamina else ''
        bot._log(f'潜能/经验开始 → {character_name}{extra} · ×{streak}')
        bot._log('=' * 40)

        # ---- 第 1 步：通用进入 ----
        if not enter_dungeon(bot, entry_tpl):
            return False
        time.sleep(2)

        # ---- 第 2 步：选难度 ----
        bot._log(f'第2步：选择难度（{diff_tpl}）...')
        pos = wait_for_image(bot, diff_tpl, timeout=5)
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1]); time.sleep(0.6)

        # ---- 第 3 步：R + 双倍 + 减号 + 加号 + 开始 + 体力 + 入场 ----
        bot._log('点击连续战斗R...')
        pos = wait_for_image(bot, '连续战斗R点击.png', timeout=5)
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1])

        minus_pos = wait_for_image(bot, '减号图标.png', timeout=5)
        if minus_pos is None: return False

        double_checked = bot.find_image(tpl('双倍消耗已勾选.png'))
        currently_checked = double_checked is not None

        if double_stamina and not currently_checked:
            bot._log('双倍消耗：需要勾选...')
            dp = wait_for_image(bot, '双倍消耗未勾选.png', timeout=3)
            if dp is not None: post_click(hwnd, dp[0], dp[1]); time.sleep(0.2)
        elif not double_stamina and currently_checked:
            bot._log('双倍消耗：需要取消...')
            post_click(hwnd, bot.game_window.left + double_checked.x,
                       bot.game_window.top + double_checked.y); time.sleep(0.2)

        bot._log('减号清零...')
        for _ in range(15):
            if not bot.is_running: return False
            post_click(hwnd, minus_pos[0], minus_pos[1]); time.sleep(0.06)

        plus_pos = wait_for_image(bot, '加号图标.png', timeout=5)
        if plus_pos is None: return False
        bot._log(f'加号 ×{streak-1}...')
        for _ in range(streak - 1):
            if not bot.is_running: return False
            post_click(hwnd, plus_pos[0], plus_pos[1]); time.sleep(0.06)

        pos = wait_for_image(bot, '开始战斗.png', timeout=5)
        if pos is None: return False
        post_click(hwnd, pos[0], pos[1])

        result = _wait_battle_or_stamina(bot, timeout=15)
        if result is None: return False
        if not result:
            bot._log('[FAIL] 体力不足')
            return False

        if not start_battle(bot):
            bot._log('[FAIL] 战斗入场失败')
            return False

        bot._log(f'[OK] 潜能/经验完成: {character_name} · ×{streak}')
        bot._log('=' * 40)
        return True

    finally:
        bot._running = False
