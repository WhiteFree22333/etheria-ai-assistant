"""
虚烬探索活动模块

全 PostMessage 后台点击，零键盘依赖。
"""
import os
import re
import time

import numpy as np

from core._base.input import post_click, lock_input
from core._common.battle_common import tpl, wait_for_image, open_sidebar, exit_battle, _find_manual_button, setup_preset
from core.config import GAME_CONFIG

# OCR 引擎（懒加载）
_ocr_reader_xujin = None


def _get_ocr():
    global _ocr_reader_xujin
    if _ocr_reader_xujin is None:
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            _tl = os.path.join(_sys._MEIPASS, 'torch', 'lib')
            if os.path.isdir(_tl):
                os.add_dll_directory(_tl)
        import easyocr
        _ocr_reader_xujin = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader_xujin


_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_SHILIAN_TPL = os.path.join(_BASE_DIR, 'templates', 'shilian')


def _stpl(name: str) -> str:
    """试炼模板路径 — templates/shilian/"""
    return os.path.join(_SHILIAN_TPL, name)


def _xujin_wait_battle(bot, timeout=None):
    """虚烬专用战斗等待 — 和 enter_and_wait_battle 相同逻辑，
    但最后等待条件改为：每 10s 识别一次"虚烬异常排除.png"，识别到则结束。"""
    hwnd = bot.game_window.hwnd
    time.sleep(1.5)
    bot._log('检查手动模式...')
    manual_pos = None
    for attempt in range(2):
        time.sleep(2)
        manual_pos = _find_manual_button(bot, attempt + 1)
        if manual_pos is not None:
            bot._log(f'第 {attempt+1} 次检测到手动')
            break
        bot._log(f'第 {attempt+1} 次未检测到手动（可能还在加载）')

    if manual_pos is not None:
        post_click(hwnd, manual_pos[0], manual_pos[1])
        time.sleep(0.5)
    else:
        bot._log('未检测到手动按钮，直接进入预设')
    if not setup_preset(bot):
        return False
    bot._log('点击 F战斗...')
    pos = wait_for_image(bot, 'F战斗.png')
    if pos is None:
        bot._log('[FAIL] 失败：未检测到 F战斗')
        return False
    post_click(hwnd, pos[0], pos[1])
    time.sleep(2)

    # F战斗点击后可能有"确定"弹窗
    bot._log('确定识别点击...')
    pos = wait_for_image(bot, '确定.png', timeout=5)
    if pos is not None:
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
    else:
        bot._log('未检测到确定按钮，跳过')

    time.sleep(3)
    bot._log('等待战斗结束（虚烬异常排除 / 系统陷落）...')
    timeout_val = timeout or 1200
    deadline = time.time() + timeout_val
    while time.time() < deadline:
        if not bot.is_running:
            return False
        # 交替快速扫描两个模板，找到任意一个就结束
        if ((bot.find_image(_stpl('虚烬异常排除.png'), multi_scale=False) is not None) or
            (bot.find_image(_stpl('虚烬系统陷落.png'), multi_scale=False) is not None)):
            bot._log('检测到战斗结束标志，战斗结束')
            return True
        time.sleep(10)
    bot._log('[WARN] 等待虚烬异常排除超时，仍返回 True')
    return True


def run_xujin_battle(bot, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
    """
    虚烬探索流程。

    1. 回主界面
    2. 开侧边栏 → 点挑战
    3. 点试炼挑战
    4. 点虚烬探索入口
    [后续步骤待补全]
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log(f'虚烬探索开始 → {difficulty} ×{streak}')
        bot._log('=' * 40)

        # === 1. 回到主界面 ===
        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)

        # === 2. 开侧边栏 → 点挑战 ===
        if not open_sidebar(bot):
            return False
        bot._log('点击挑战...')
        pos = wait_for_image(bot, '挑战.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # === 3. 点试炼挑战 ===
        bot._log('点击试炼挑战...')
        pos = wait_for_image(bot, '试炼挑战.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # === 4. 点虚烬探索入口 ===
        bot._log('点击虚烬探索入口...')
        pos = wait_for_image(bot, _stpl('虚烬探索入口.png'))
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # === 4.5-10 循环：直到 43 层 + 虚烬已获得 ===
        _current_layer = 0
        while bot.is_running:
            bot._log(f'====== 虚烬探索循环 (当前最高层={_current_layer}) ======')
            # 每次循环前强制释放所有键盘按键，防止上一轮残留的 W 键与 post_click 冲突导致滚轮下滑
            import pyautogui as _pg
            try:
                _pg.keyUp('w')
            except Exception:
                pass

            # === 4.5. 点虚烬普通难度 → 检测虚烬危机选择（通关则切难度） ===
            bot._log('点击虚烬普通难度...')
            pos = wait_for_image(bot, _stpl('虚烬普通难度.png'), timeout=5)
            if pos is not None:
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)
                bot._log('检测虚烬危机选择...')
                pos = wait_for_image(bot, _stpl('虚烬危机选择.png'), timeout=5)
                if pos is not None:
                    bot._log('检测到虚烬危机选择 → 普通难度已通关，切换难度')
                    post_click(hwnd, pos[0], pos[1])
                    time.sleep(2)
                else:
                    bot._log('未检测到虚烬危机选择，保持普通难度')
            else:
                bot._log('未检测到虚烬普通难度，跳过')

            # === 5. 点击自动挑战（没找到则跳过 6-7 直接到步骤 8） ===
            bot._log('点击自动挑战...')
            pos = wait_for_image(bot, _stpl('自动挑战.png'), timeout=5)
            skip_to_step8 = (pos is None)
            if skip_to_step8:
                bot._log('未检测到自动挑战，跳过步骤 6-7 直接进入步骤 8')
            else:
                # DEBUG: 保存截图看点击位置
                import cv2 as _cvdbg
                _dd2 = os.path.join(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__)))), 'debug_screenshots')
                os.makedirs(_dd2, exist_ok=True)
                dbg_img = bot.capture()
                if dbg_img is not None:
                    arr2 = _cvdbg.cvtColor(
                        np.array(dbg_img), _cvdbg.COLOR_RGB2BGR)
                    _cvdbg.circle(
                        arr2, (pos[0] - bot.game_window.left, pos[1] - bot.game_window.top), 8, (0, 0, 255), -1)
                    _cvdbg.putText(arr2, f'click({pos[0]},{pos[1]})', (pos[0] - bot.game_window.left + 12, pos[1] - bot.game_window.top + 4),
                                   _cvdbg.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    _cvdbg.imwrite(os.path.join(
                        _dd2, 'xujin_autochallenge_click.png'), arr2)
                    bot._log(
                        f'Debug: 自动挑战点击标注 → debug_screenshots/xujin_autochallenge_click.png')
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)

                # === 6. 确定识别点击 ===
                bot._log('确定识别点击...')
                pos = wait_for_image(bot, '确定.png', timeout=5)
                if pos is not None:
                    post_click(hwnd, pos[0], pos[1])
                    time.sleep(2)
                else:
                    bot._log('未检测到确定按钮，跳过')

                # === 7. 每5s识别一次获得物品，60s没识别到就退出 ===
                bot._log('等待获得物品（最多60s）...')
                deadline = time.time() + 60
                while bot.is_running and time.time() < deadline:
                    pos = wait_for_image(bot, _stpl('获得物品.png'))
                    if pos is not None:
                        bot._log('检测到获得物品，退出...')
                        exit_battle(bot, 30, 30, single_click=True)
                        break
                    time.sleep(5)
                else:
                    bot._log('60s 未获得物品，退出继续...')
                    exit_battle(bot, 30, 30, single_click=True)

            # === 8. 色号定位红色竖条(仅右上角) → OCR 右边数字 + 虚烬首通 → 虚烬前往挑战 ===
            import cv2
            img = bot.capture()
            if img is not None:
                hw = img.width // 2
                hh = img.height // 2
                # 右上角区域
                corner = img.crop((hw, 0, img.width, hh))

                # 在右上角区域内找红色竖条 RGB(220,26,84)
                # inRange 是 BGR 顺序：B=84, G=26, R=220
                arr = cv2.cvtColor(np.array(corner), cv2.COLOR_RGB2BGR)
                B, G, R = 84, 26, 220
                lower = np.clip(np.array([B - 20, G - 20, R - 20], dtype=np.int16),
                                0, 255).astype(np.uint8)
                upper = np.clip(np.array([B + 20, G + 20, R + 20], dtype=np.int16),
                                0, 255).astype(np.uint8)
                mask = cv2.inRange(arr, lower, upper)
                ys, xs = np.where(mask > 0)
                if len(xs) > 0:
                    # 相对于右上角的坐标
                    red_x = int(np.mean(xs))
                    red_y = int(np.mean(ys))
                    bot._log(f'红色竖条 右上角内({red_x},{red_y})')

                    # 红点右侧，只取红条高度的窄条（排除上方干扰数字）
                    rx = hw + red_x
                    rw = img.width - rx
                    ry = red_y - 5
                    rh = 36
                    rx = max(0, rx)
                    ry = max(0, ry)
                    rw = min(rw, img.width - rx)
                    rh = min(rh, img.height - ry)
                    if rw > 0 and rh > 0:
                        roi = img.crop((rx, ry, rx + rw, ry + rh))

                        # 先找 "-" 号位置 → 数字在 "-" 左边
                        reader = _get_ocr()
                        dash_x = None
                        for det in reader.readtext(np.array(roi), allowlist='-—'):
                            txt = det[1]
                            box = det[0]
                            dash_x = int(sum(p[0] for p in box) / 4)
                            break

                        # 用 "-" 左边区域精确 OCR 数字
                        if dash_x is not None:
                            safe_x = max(1, dash_x - 30)
                            num_roi = roi.crop((0, 0, safe_x, roi.height))
                        else:
                            num_roi = roi

                        # CLAHE + 2x 放大
                        import cv2 as _cv2
                        gray = _cv2.cvtColor(
                            np.array(num_roi), _cv2.COLOR_RGB2GRAY)
                        clahe = _cv2.createCLAHE(
                            clipLimit=2.0, tileGridSize=(8, 8))
                        enhanced = clahe.apply(gray)
                        scaled = _cv2.resize(np.array(num_roi), None, fx=2, fy=2,
                                             interpolation=_cv2.INTER_CUBIC)

                        for det in reader.readtext(scaled, allowlist='0123456789'):
                            txt = det[1]
                            if txt.isdigit():
                                _current_layer = int(txt)
                                bot._log(f'🔥 当前探索层数: {_current_layer} 层')
                                break
                        else:
                            for det in reader.readtext(enhanced, allowlist='0123456789'):
                                txt = det[1]
                                if txt.isdigit():
                                    _current_layer = int(txt)
                                    bot._log(f'🔥 当前探索层数: {_current_layer} 层')
                                    break
                            else:
                                bot._log('[WARN] 未识别到当前探索层数')
                    else:
                        bot._log('[WARN] 红点右侧裁剪区域无效')
                else:
                    bot._log('[WARN] 右上角未找到红色竖条')
            else:
                bot._log('[WARN] 截图失败')

            # 检查循环结束条件：层数 >= 43 且 虚烬已获得（在进入战斗前检查）
            bot._log(f"检查循环结束条件：层数={_current_layer}")
            if _current_layer >= 43:
                pos = wait_for_image(bot, _stpl("虚烬已获得.png"), timeout=5)
                if pos is not None:
                    bot._log("虚烬已获得 + 达到43层，循环结束！")
                    break
            bot._log("未满足结束条件，继续下一轮...")

            bot._log('检测虚烬首通...')
            pos = wait_for_image(bot, _stpl('虚烬首通.png'))
            if pos is not None:
                bot._log('检测到虚烬首通，未通关 → 点击虚烬前往挑战...')
                pos = wait_for_image(bot, _stpl('虚烬前往挑战.png'))
                if pos is None:
                    bot._log('[FAIL] 未检测到虚烬前往挑战')
                    return False
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)

                # === 9. Boss 房间：先锁定 → 等房间 → 按住 W → 卡牌 → 进战斗 ===
                # 先抢焦点 + 移鼠标 + 锁输入，再等待房间加载（用户可能在这期间操作电脑）
                from core._base.window import focus_window
                focus_window(hwnd)
                time.sleep(0.1)

                import ctypes
                gw = bot.game_window
                ctypes.windll.user32.SetCursorPos(
                    gw.left + gw.width // 2, gw.top + gw.height // 2)
                time.sleep(0.3)

                with lock_input(hwnd):
                    bot._log('等待进入 Boss 房间（虚烬房间判断）...')
                    while bot.is_running:
                        pos = wait_for_image(bot, _stpl('虚烬房间判断.png'))
                        if pos is not None:
                            break
                        time.sleep(3)

                    bot._log('按住 W 键前进...')
                    import pyautogui
                    pyautogui.keyDown('w')
                    time.sleep(0.5)

                    bot._log('寻找虚烬卡牌（需要4张）...')
                    import cv2 as _cv3
                    from core._base.template_match import _imread as _read_tpl
                    tpl_card = _read_tpl(_stpl('虚烬卡牌.png'))
                    tw = th = 0
                    if tpl_card is not None:
                        th, tw = tpl_card.shape[:2]

                    card_positions = []
                    for _retry in range(3):  # 最多重新扫 3 次
                        scan_deadline = time.time() + 30
                        while bot.is_running and time.time() < scan_deadline:
                            img = bot.capture()
                            if img is not None and tpl_card is not None:
                                scr = _cv3.cvtColor(
                                    np.array(img), _cv3.COLOR_RGB2BGR)
                                result = _cv3.matchTemplate(
                                    scr, tpl_card, _cv3.TM_CCOEFF_NORMED)
                                loc = np.where(
                                    result >= GAME_CONFIG.template_threshold)
                                tmp = []
                                for pt in zip(*loc[::-1]):
                                    if not any(abs(pt[0]-p[0]) < 20 for p in tmp):
                                        tmp.append(pt)
                                if len(tmp) >= 4:
                                    card_positions = sorted(
                                        tmp, key=lambda p: p[0])
                                    bot._log(f'找到 {len(card_positions)} 张卡牌')
                                    break
                            time.sleep(3)
                        if len(card_positions) >= 4:
                            break
                        bot._log(f'只找到 {len(card_positions)} 张，重新扫描...')
                        time.sleep(2)

                    pyautogui.keyUp('w')
                    time.sleep(1)

                # 点击所有卡牌（从左到右）
                if card_positions and tw > 0:
                    gw = bot.game_window
                    for i, (cx_win, cy_win) in enumerate(card_positions):
                        screen_x = gw.left + cx_win + tw // 2
                        screen_y = gw.top + cy_win + th // 2
                        bot._log(f'点击卡牌 #{i+1} ({screen_x}, {screen_y})')
                        post_click(hwnd, screen_x, screen_y)
                        time.sleep(1)
                else:
                    bot._log('[WARN] 未检测到虚烬卡牌，跳过点击')

                bot._log('查找虚烬进入战斗...')
                pos = wait_for_image(bot, _stpl('虚烬进入战斗.png'))
                if pos is None:
                    bot._log('[FAIL] 未检测到虚烬进入战斗')
                    return False
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)

                bot._log('等待战斗加载（10s）...')
                time.sleep(5)

                # 战斗等待不锁（纯截图+PostMessage，不操作键盘鼠标）
                if not _xujin_wait_battle(bot):
                    return False
                exit_battle(bot, 30, 30, single_click=True)

                # === 10. 按住W找宝箱 → 点击 → Tab → F  ===
                from core._base.window import focus_window
                focus_window(hwnd)
                time.sleep(0.1)

                import ctypes
                gw = bot.game_window
                ctypes.windll.user32.SetCursorPos(
                    gw.left + gw.width // 2, gw.top + gw.height // 2)
                time.sleep(0.3)

                with lock_input(hwnd):
                    bot._log('按住 W 寻找虚烬宝箱图标（最快0.2s一帧，最多30s）...')
                    import pyautogui
                    pyautogui.keyDown('w')
                    time.sleep(0.5)
                    deadline = time.time() + 30
                    while bot.is_running and time.time() < deadline:
                        # 高频检测：每 0.2s 截一帧，避免走过宝箱
                        frame_img = bot.capture()
                        found = False
                        if frame_img is not None:
                            match_result = bot.find_image(
                                _stpl('虚烬宝箱图标.png'), multi_scale=False)
                            if match_result is not None:
                                found = True
                        if found:
                            pyautogui.keyUp('w')
                            time.sleep(0.3)
                            pos = wait_for_image(bot, _stpl('虚烬宝箱图标.png'))
                            if pos is not None:
                                post_click(hwnd, pos[0], pos[1])
                                bot._log('点击虚烬宝箱图标')
                                time.sleep(1)
                                exit_battle(bot, 30, 30, single_click=True)
                            break
                        time.sleep(0.2)
                    else:
                        pyautogui.keyUp('w')
                        bot._log('[WARN] 30s 未找到虚烬宝箱图标，超时继续')

                    bot._log('按下 Tab 键...')
                    pyautogui.press('tab')
                    time.sleep(1)
                    bot._log('按下 F 键...')
                    pyautogui.press('f')

                # 彻底清理键盘/鼠标状态：防止 SendInput 残留导致下一轮 post_click 变滚轮
                # 关键风险：lock_input 释放后鼠标突然出现在游戏中心，
                # 如果这时有任何鼠标按键残留，Unity Raw Input 会解释为拖拽/滚轮。
                try:
                    pyautogui.keyUp('w')
                    pyautogui.keyUp('a')
                    pyautogui.keyUp('s')
                    pyautogui.keyUp('d')
                    pyautogui.mouseUp(button='left')
                    pyautogui.mouseUp(button='middle')
                    pyautogui.mouseUp(button='right')
                    # 把鼠标移出游戏窗口区域（右上角），防止光标瞬跳被 Unity 误判
                    ctypes.windll.user32.SetCursorPos(
                        gw.left + gw.width + 50, gw.top - 50)
                except Exception:
                    pass
                time.sleep(0.5)  # 等 OS 输入队列完全排空

            # while 循环回到开头，下一轮
        bot._log('[OK] 虚烬探索完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
