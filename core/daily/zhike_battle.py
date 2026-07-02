"""
智壳战斗模块 — 自动化刷智壳副本流程

全 PostMessage 后台点击，零键盘依赖。
"""
import time

from core._base.input import post_click, post_drag
from core._base.window import focus_window
from core._common.battle_common import tpl, wait_for_image, enter_dungeon, wait_battle_end, handle_cleanup_popup


def scroll_and_find(bot, template_name: str,
                    max_drags: int = 30,
                    drag_px: int = -130,
                    drag_steps: int = 10,
                    drag_delay: float = 0.015,
                    inertia_wait: float = 0.3
                    ) -> bool:
    """
    SendInput 拖动列表查找目标图标，找到后 PostMessage 点击。

    拖动开始前短暂聚焦游戏窗口（<200ms），结束后恢复当前窗口。
    Unity 游戏通过 Raw Input 读取鼠标事件，被遮挡时 SendInput 失效，
    因此需要暂时把游戏窗口提到前台。

    Args:
        template_name:  目标模板文件名
        max_drags:       最多拖动次数，防死循环
        drag_px:         每次拖动 X 方向像素，负=左，正=右
        drag_steps:      每次拖动切多少步，越大越平滑
        drag_delay:      每步间隔秒数，0.015=15ms
        inertia_wait:    拖动惯性等待秒数
    """
    hwnd = bot.game_window.hwnd
    gw = bot.game_window

    # 拖动开始前保存前台窗口，聚焦游戏（<200ms），结束后恢复
    import win32gui as _wg
    prev = _wg.GetForegroundWindow()
    if prev != hwnd:
        focus_window(hwnd)
        time.sleep(0.15)

    try:
        cx = gw.left + gw.width // 2
        anchor_y = gw.top + gw.height // 2
        bot._log('定位拖动锚点: 亚克位置.png...')
        anchor = bot.find_image(tpl('亚克位置.png'))
        if anchor:
            anchor_y = gw.top + anchor.y
            bot._log(f'锚点 Y={anchor_y}')
        else:
            bot._log('警告: 未找到亚克位置.png，使用窗口中心')

        for i in range(max_drags):
            if not bot.is_running:
                return False

            match = bot.find_image(tpl(template_name))
            if match:
                time.sleep(0.15)
                match2 = bot.find_image(tpl(template_name))
                if match2 is not None:
                    abs_x = gw.left + match2.x
                    abs_y = gw.top + match2.y
                    bot._log(
                        f"找到 {template_name}（稳定），post_click ({abs_x}, {abs_y})")
                    post_click(hwnd, abs_x, abs_y)
                    return True
                else:
                    bot._log(f"{template_name} 首次匹配但在惯量中丢失，继续...")

            bot._log(f"← 拖动寻找 {template_name} ({i+1}/{max_drags}) "
                     f"[{abs(drag_px)}px ×{drag_steps}步]")
            post_drag(hwnd, cx, anchor_y, cx + drag_px, anchor_y,
                      steps=drag_steps, step_delay=drag_delay)
            time.sleep(inertia_wait)

        bot._log(f"拖动 {max_drags} 次后仍未找到 {template_name}")
        return False
    finally:
        # 恢复之前的前台窗口
        if prev and prev != hwnd:
            try:
                _wg.SetForegroundWindow(prev)
            except Exception:
                pass


def _wait_battle_or_stamina(bot, timeout: float = 15, interval: float = 0.5):
    """点完开始战斗后，等进入战斗画面 or 体力弹窗。"""
    hwnd = bot.game_window.hwnd

    bot._log('等待加载（2秒后开始检查...）')
    time.sleep(2)

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not bot.is_running:
            return None

        if bot.find_image(tpl('体力兑换.png')):
            bot._log('[WARN] 检测到体力不足弹窗！')
            bot._log('[WARN] STAMINA_MISSING: 亲，您的体力不足请先使用体力后再开始哦！')
            close_pos = wait_for_image(bot, '咔嚓.png', timeout=3)
            if close_pos:
                post_click(hwnd, close_pos[0], close_pos[1])
                bot._log('已点击咔嚓关闭体力弹窗')
            return False

        if bot.find_image(tpl('F战斗.png')):
            bot._log('战斗画面已加载')
            return True

        time.sleep(interval)

    bot._log('超时：未检测到战斗画面或体力弹窗')
    return None


def start_battle(bot) -> bool:
    """战斗入场：选预设 → 装备占用 → 开始战斗。"""
    hwnd = bot.game_window.hwnd

    def _click(pos):
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.05)

    bot._log('战斗入场：等待进入战斗准备画面...')
    pos = wait_for_image(bot, 'F战斗.png', timeout=10)
    if pos is None:
        bot._log('[FAIL] 失败：F 确认后未能进入战斗准备画面')
        return False
    bot._log('已进入战斗准备画面')

    bot._log('点击预设按钮...')
    pos = wait_for_image(bot, '预设.png', timeout=5)
    if pos is None:
        bot._log('[FAIL] 失败：未找到预设按钮')
        return False
    _click(pos)
    time.sleep(0.5)

    use_pos = wait_for_image(bot, '使用预设.png', timeout=5)
    if use_pos is None:
        bot._log('[FAIL] 未找到「使用预设」按钮')
        bot._log('[WARN] PRESET_MISSING: 亲，您没有设置预设阵容哦，请设置后回到主页重新开始。')
        return False

    bot._log('点击使用预设...')
    _click(use_pos)
    time.sleep(0.5)

    equipment_pos = wait_for_image(bot, '预设装备占用.png', timeout=3)
    if equipment_pos is not None:
        bot._log('检测到装备占用弹窗，点击确定...')
        confirm_pos = wait_for_image(bot, '确定.png', timeout=5)
        if confirm_pos is None:
            bot._log('[FAIL] 失败：未找到确定按钮')
            return False
        _click(confirm_pos)
        time.sleep(0.5)

    bot._log('点击 F战斗 开始战斗...')
    pos = wait_for_image(bot, 'F战斗.png', timeout=5)
    if pos is None:
        bot._log('[FAIL] 失败：未找到 F战斗 按钮')
        return False
    _click(pos)
    time.sleep(0.8)

    bot._log('点击连续战斗返回...')
    pos = wait_for_image(bot, '连续战斗返回.png', timeout=5)
    if pos is not None:
        _click(pos)
        time.sleep(0.5)

    bot._log('[OK] 战斗已开始！')
    return True


def run_zhike_battle(bot, character_name: str, difficulty: str = '炼狱', streak: int = 1) -> bool:
    """执行智壳战斗完整流程。"""
    hwnd = bot.game_window.hwnd
    bot._running = True

    try:
        bot._log('=' * 40)
        bot._log(f'智壳战斗开始 → {character_name} · {difficulty} · ×{streak}')
        bot._log('=' * 40)

        # ---- 第 0-4 步：通用进入流程 ----
        if not enter_dungeon(bot, '智壳掉落.png'):
            return False

        # ---- 清理弹窗检查 ----
        handle_cleanup_popup(bot)

        # ---- 第 5 步：滚轮找角色 ----
        bot._log(f'第5步：滚动查找 {character_name} 图标...')
        if not scroll_and_find(bot, f'{character_name}图标.png'):
            bot._log(f'[FAIL] 失败：未找到 {character_name} 图标')
            return False
        time.sleep(0.6)

        # ---- 第 6 步：选难度 ----
        diff_template = f'智壳{difficulty}.png'
        bot._log(f'第6步：选择难度 → {difficulty}（{diff_template}）...')
        pos = wait_for_image(bot, diff_template, timeout=5)
        if pos is None:
            bot._log(f'[FAIL] 失败：未检测到难度按钮 {diff_template}')
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.6)

        # ---- 第 7 步：点击连续战斗R ----
        bot._log('第7步：点击连续战斗R...')
        pos = wait_for_image(bot, '连续战斗R点击.png', timeout=5)
        if pos is None:
            bot._log('[FAIL] 失败：未检测到连续战斗R按钮')
            return False
        post_click(hwnd, pos[0], pos[1])

        minus_pos = wait_for_image(bot, '减号图标.png', timeout=5)
        if minus_pos is None:
            bot._log('[FAIL] 失败：R点击后未弹出次数设置窗口')
            return False

        # ---- 第 8-9 步：减号清零 + 加号设次数 ----
        bot._log('post_click 减号 ×15 清零...')
        for _ in range(15):
            if not bot.is_running:
                return False
            post_click(hwnd, minus_pos[0], minus_pos[1])
            time.sleep(0.06)

        plus_pos = wait_for_image(bot, '加号图标.png', timeout=5)
        if plus_pos is None:
            bot._log('[FAIL] 失败：未检测到加号图标')
            return False
        bot._log(f'post_click 加号 ×{streak}...')
        for _ in range(streak-1):
            if not bot.is_running:
                return False
            post_click(hwnd, plus_pos[0], plus_pos[1])
            time.sleep(0.06)

        # ---- 第 10 步：开始战斗 ----
        pos = wait_for_image(bot, '开始战斗.png', timeout=5)
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

        # ---- 战斗入场 ----
        if not start_battle(bot):
            bot._log('[FAIL] 战斗入场失败')
            return False

        handle_cleanup_popup(bot)

        bot._log('等待连续战斗完成...')
        if not wait_battle_end(bot):
            bot._log('[FAIL] 战斗未在预期时间内完成')
            return False

        bot._log(f'[OK] 智壳战斗完成: {character_name} · {difficulty} · ×{streak}')
        bot._log('=' * 40)
        return True

    finally:
        bot._running = False
