"""
源器战斗模块 — 自动化刷源器副本流程

全 PostMessage 后台点击，零键盘依赖。
"""
import time

from core._base.input import post_click
from core._common.battle_common import tpl, wait_for_image, enter_dungeon, wait_battle_end, handle_over_limit, handle_cleanup_popup
from core.daily.zhike_battle import _wait_battle_or_stamina, start_battle


def run_yuanqi_battle(bot, character_name: str, difficulty: str = '地狱四', streak: int = 1, double_stamina: bool = False) -> bool:
    """
    执行源器战斗完整流程。

    0-4:  enter_dungeon('源器掉落.png')
    5:    检查超出上限弹窗
    6:    识别角色图标并点击
    7:    选难度
    8:    连续战斗R → 等弹框 → 双倍消耗处理
    9:    减号清零 + 加号设次数
    10:   开始战斗 + 体力检查 + 战斗入场
    """
    hwnd = bot.game_window.hwnd
    bot._running = True

    try:
        bot._log('=' * 40)
        extra = ' · 双倍' if double_stamina else ''
        bot._log(
            f'源器战斗开始 → {character_name} · {difficulty}{extra} · ×{streak}')
        bot._log('=' * 40)

        # ---- 第 0-4 步 ----
        if not enter_dungeon(bot, '源器掉落.png'):
            return False

        # ---- 第 5 步：超出上限弹窗 ----
        bot._log('第5步：检查是否超出上限...')
        # if not handle_over_limit(bot):
        handle_cleanup_popup(bot)

        # ---- 第 6 步：一层层点击角色（不能滚动） ----
        bot._log(f'第6步：定位 {character_name}...')

        char_order = ['重构兵祸', '多琪', '奥洛拉', '维斯佩拉']
        if character_name not in char_order:
            bot._log(f'[FAIL] 错误：未知角色 {character_name}')
            return False
        target_idx = char_order.index(character_name)

        # 重构兵祸直接点两次；多琪/奥洛拉/维斯佩拉从多琪开始逐层翻
        start_idx = 0 if target_idx == 0 else 1
        for idx in range(start_idx, target_idx + 1):
            ch = char_order[idx]
            is_last = (idx == target_idx)
            need_double = is_last and idx != 0  # 重构兵祸只点一次，其他角色最后点两次

            pos = wait_for_image(bot, f'{ch}.png')
            if pos is None:
                bot._log(f'[FAIL] 失败：未检测到 {ch}.png')
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(0.4)

            if need_double:
                bot._log(f'再点 {ch}（选中）...')
                pos = wait_for_image(bot, f'{ch}.png')
                if pos is None:
                    bot._log(f'[FAIL] 失败：选中时未检测到 {ch}.png')
                    return False
                post_click(hwnd, pos[0], pos[1])
                time.sleep(0.4)

        bot._log(f'已选中 {character_name}')

        # ---- 第 7 步：选难度 ----
        # 两种难度都可能默认选中，先检查是否已选中
        if difficulty == '炼狱':
            selected_pos = bot.find_image(tpl('炼狱选中.png'))
            if selected_pos:
                bot._log('第7步：炼狱已默认选中，点击确认...')
                post_click(hwnd, bot.game_window.left + selected_pos.x,
                           bot.game_window.top + selected_pos.y)
            else:
                bot._log('第7步：选择炼狱（智壳炼狱.png）...')
                pos = wait_for_image(bot, '智壳炼狱.png')
                if pos is None:
                    bot._log('[FAIL] 失败：未检测到智壳炼狱.png')
                    return False
                post_click(hwnd, pos[0], pos[1])
        else:
            # 地狱四：检查是否已默认选中
            selected_pos = bot.find_image(tpl('源器地狱四已选中.png'))
            if selected_pos:
                bot._log('第7步：地狱四已默认选中，点击确认...')
                post_click(hwnd, bot.game_window.left + selected_pos.x,
                           bot.game_window.top + selected_pos.y)
            else:
                bot._log('第7步：选择地狱四（源器地狱四.png）...')
                pos = wait_for_image(bot, '源器地狱四.png')
                if pos is None:
                    bot._log('[FAIL] 失败：未检测到源器地狱四.png')
                    return False
                post_click(hwnd, pos[0], pos[1])
        time.sleep(0.6)

        # ---- 第 8 步：点击连续战斗R → 等弹框 → 处理双倍消耗 ----
        bot._log('第8步：点击连续战斗R...')
        pos = wait_for_image(bot, '连续战斗R点击.png')
        if pos is None:
            bot._log('[FAIL] 失败：未检测到连续战斗R按钮')
            return False
        post_click(hwnd, pos[0], pos[1])

        # 等弹框加载
        time.sleep(0.4)

        # --- 双倍消耗处理 ---
        # 截图检查当前是否已经勾选了双倍
        double_checked = bot.find_image(tpl('双倍消耗已勾选.png'))
        currently_checked = double_checked is not None

        if double_stamina and not currently_checked:
            # 用户要双倍，但现在没勾 → 点一下勾上
            bot._log('双倍消耗：需要勾选 → 点击双倍区域...')
            # 找双倍消耗的未勾选图标位置
            double_pos = wait_for_image(bot, '双倍消耗未勾选.png', timeout=3)
            if double_pos is None:
                bot._log('[WARN] 未找到双倍消耗未勾选按钮，跳过')
            else:
                post_click(hwnd, double_pos[0], double_pos[1])
                time.sleep(0.2)
                bot._log('双倍消耗已勾选')
        elif not double_stamina and currently_checked:
            # 用户不要双倍，但现在是勾的 → 点一下取消
            bot._log('双倍消耗：需要取消 → 点击取消...')
            post_click(hwnd, bot.game_window.left + double_checked.x,
                       bot.game_window.top + double_checked.y)
            time.sleep(0.2)
            bot._log('双倍消耗已取消')
        else:
            bot._log(
                f'双倍消耗：当前状态符合预期（要={double_stamina}，现={currently_checked}），跳过')

        # 等弹框稳定
        minus_pos = wait_for_image(bot, '减号图标.png')
        if minus_pos is None:
            bot._log('[FAIL] 失败：未弹出次数设置窗口')
            return False

        # ---- 第 9 步：减号清零 + 加号设次数 ----
        bot._log('post_click 减号 ×15 清零...')
        for _ in range(15):
            if not bot.is_running:
                return False
            post_click(hwnd, minus_pos[0], minus_pos[1])
            time.sleep(0.06)

        plus_pos = wait_for_image(bot, '加号图标.png')
        if plus_pos is None:
            bot._log('[FAIL] 失败：未检测到加号图标')
            return False
        bot._log(f'post_click 加号 ×{streak}...')
        for _ in range(streak-1):
            if not bot.is_running:
                return False
            post_click(hwnd, plus_pos[0], plus_pos[1])
            time.sleep(0.06)

        # ---- 第 10 步：开始战斗 + 体力检查 + 战斗入场 ----
        pos = wait_for_image(bot, '开始战斗.png')
        if pos is None:
            bot._log('[FAIL] 失败：未检测到开始战斗按钮')
            return False
        post_click(hwnd, pos[0], pos[1])

        result = _wait_battle_or_stamina(bot, timeout=15)
        if result is None:
            return False
        if not result:
            bot._log('[FAIL] 体力不足，停止执行')
            return False

        if not start_battle(bot):
            bot._log('[FAIL] 战斗入场失败')
            return False

        # 战斗入场后可能弹出超出上限
        bot._log('检查战斗后上限弹窗...')
        handle_cleanup_popup(bot)
        # if not handle_over_limit(bot):

        #     return False

        bot._log('等待连续战斗完成...')
        if not wait_battle_end(bot):
            bot._log('[FAIL] 战斗未在预期时间内完成')
            return False

        bot._log(f'[OK] 源器战斗完成: {character_name} · {difficulty} · ×{streak}')
        bot._log('=' * 40)
        return True

    finally:
        bot._running = False
