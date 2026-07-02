"""
源网征令活动模块

全 PostMessage 后台点击，零键盘依赖。
"""
import os
import time

import numpy as np
from PIL import Image

from core._base.input import post_click
from core._base.window import get_client_rect
from core._common.battle_common import tpl, wait_for_image, open_sidebar, exit_battle, find_all_by_color, _find_manual_button, wait_for_image_gone
from core.config import GAME_CONFIG

# 选牌 OCR 引擎（懒加载）
_ocr_reader_yuanwang = None
# 三张选牌的点击位置（客户区坐标）
_CARD_CLICKS = [
    (453, 350),
    (531, 345),
    (605, 347),
]
# 选牌后读取详情的 OCR 区域（客户区坐标）
_CARD_DETAIL_REGION = (197, 374, 307, 398)
# 选牌优先级：（关键词, [单字备选]）
_CARD_KEYWORDS = [
    ('晶格', ['晶']),
    ('强化', ['强']),
    ('全量', ['全', '量']),
    ('质补', ['质', '补']),
    ('晋升', ['晋', '升']),
    ('突破', ['突']),
]

_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_SHILIAN_TPL = os.path.join(_BASE_DIR, 'templates', 'shilian')


def _stpl(name: str) -> str:
    """试炼模板路径 — templates/shilian/"""
    return os.path.join(_SHILIAN_TPL, name)


# ============================================================
# 区域检测（公共方法 — 识别用户当前处于哪个区域）
# ============================================================

# 区域模板列表：（内部标识, 文件名）
_REGION_TEMPLATES = [
    ('蜃都', '当前区域蜃都区域.png'),
    ('坎特', '当前区域坎特区域.png'),
    ('洛莱', '当前区域洛莱区域.png'),
]


def _get_ocr():
    """懒加载 EasyOCR 引擎"""
    global _ocr_reader_yuanwang
    if _ocr_reader_yuanwang is None:
        import sys as _sys
        if getattr(_sys, 'frozen', False):
            _tl = os.path.join(_sys._MEIPASS, 'torch', 'lib')
            if os.path.isdir(_tl):
                os.add_dll_directory(_tl)
        import easyocr
        _ocr_reader_yuanwang = easyocr.Reader(['ch_sim', 'en'], gpu=False)
    return _ocr_reader_yuanwang


def _select_card_by_ocr(bot) -> bool:
    """
    先依次点击三张选牌、每次识别详情区域文字，收集所有匹配结果。
    然后按优先级（晶格 > 全量 > 质补）选最优的那张，点击它。
    都没匹配到 → 返回 False。
    """
    hwnd = bot.game_window.hwnd
    cl = get_client_rect(hwnd)

    import os as _os
    import cv2
    _dd = _os.path.join(_os.path.dirname(_os.path.dirname(
        _os.path.dirname(_os.path.abspath(__file__)))), 'debug_screenshots')
    _os.makedirs(_dd, exist_ok=True)

    reader = _get_ocr()
    # 收集每张牌的匹配关键词
    card_matches: list[tuple[int, str]] = []  # (牌索引, 关键词)

    for i, (cx, cy) in enumerate(_CARD_CLICKS):
        screen_x = cl[0] + cx
        screen_y = cl[1] + cy
        bot._log(f'选牌 #{i+1} 点击 ({screen_x}, {screen_y})')
        post_click(hwnd, screen_x, screen_y)
        time.sleep(1.5)

        img = bot.capture()
        if img is None:
            continue
        rx1, ry1, rx2, ry2 = _CARD_DETAIL_REGION
        roi = img.crop((rx1, ry1, rx2, ry2))

        roi.save(_os.path.join(_dd, f'card_ocr_detail_{i+1}.png'))
        bot._log(
            f'Debug: 选牌详情#{i+1} → debug_screenshots/card_ocr_detail_{i+1}.png ({roi.width}x{roi.height})')

        gray = cv2.cvtColor(np.array(roi), cv2.COLOR_RGB2GRAY)
        clahe_model = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe_model.apply(gray)
        scaled = cv2.resize(np.array(roi), None, fx=2, fy=2,
                            interpolation=cv2.INTER_CUBIC)

        all_dets = []
        for label, img_input in [
            ('2x放大', scaled),
            ('CLAHE', enhanced),
            ('原图', np.array(roi)),
        ]:
            for det in reader.readtext(
                img_input,
                text_threshold=0.4,
                low_text=0.2,
                link_threshold=0.2,
                canvas_size=1280,
                mag_ratio=2,
            ):
                all_dets.append((det[1], det[2]))

        unique = list(dict.fromkeys(t[0] for t in all_dets))
        bot._log(f'选牌 #{i+1} OCR 识别到: {unique}')

        for keyword, singles in _CARD_KEYWORDS:
            for txt, _ in all_dets:
                if keyword in txt or any(s in txt for s in singles):
                    bot._log(f'选牌 #{i+1} 匹配 "{keyword}"（识别 "{txt}"）')
                    card_matches.append((i, keyword))
                    break  # 每张牌只记第一个命中的关键词
            else:
                continue
            break  # 外层也 break，一张牌只记一次

    if not card_matches:
        bot._log('三张选牌均未匹配到晶格/全量/质补')
        return False

    # 按关键词优先级排序，取最优
    keyword_rank = {kw: idx for idx, (kw, _) in enumerate(_CARD_KEYWORDS)}
    card_matches.sort(key=lambda m: keyword_rank.get(m[1], 99))
    best_i, best_kw = card_matches[0]
    bot._log(f'最优选牌: #{best_i+1} "{best_kw}"')

    # 如果最优牌不是最后一张（当前已点击的那张），重新点击最优牌
    last_clicked = len(_CARD_CLICKS) - 1
    if best_i != last_clicked:
        cx, cy = _CARD_CLICKS[best_i]
        screen_x = cl[0] + cx
        screen_y = cl[1] + cy
        bot._log(f'重新点击最优牌 #{best_i+1} ({screen_x}, {screen_y})')
        post_click(hwnd, screen_x, screen_y)
        time.sleep(1)

    return True


def detect_region(bot) -> str | None:
    """
    检测当前处于哪个区域。
    先模板匹配找到区域标签，再检测文字颜色：黑色=活跃区域，白色=非活跃。
    每个区域模板识别 2 次（间隔 0.3s），以防页面加载动画导致漏检。

    Returns:
        '蜃都' / '坎特' / '洛莱' / None
    """
    img = bot.capture()
    if img is None:
        return None
    arr = np.array(img)  # RGB
    bot._log('检测当前区域...')
    DARK_MAX = 60  # 各通道 < 60 视为黑色
    candidates = []  # (conf, region_id)
    for region_id, template_name in _REGION_TEMPLATES:
        for attempt in range(2):
            time.sleep(0.3)
            match = bot.find_image(_stpl(template_name), multi_scale=False)
            if match is not None:
                mw2, mh2 = match.width // 2, match.height // 2
                y1 = max(0, match.y - mh2)
                y2 = min(arr.shape[0], match.y + mh2)
                x1 = max(0, match.x - mw2)
                x2 = min(arr.shape[1], match.x + mw2)
                region_pixels = arr[y1:y2, x1:x2, :].reshape(-1, 3)
                darkest_idx = np.argmin(region_pixels.max(axis=1))
                r, g, b = region_pixels[darkest_idx]
                r, g, b = int(r), int(g), int(b)
                bot._log(
                    f'{region_id} 置信度{match.confidence:.2%} 最暗RGB({r},{g},{b})')
                if r < DARK_MAX and g < DARK_MAX and b < DARK_MAX:
                    candidates.append((match.confidence, region_id))
    if candidates:
        candidates.sort(reverse=True)
        best_conf, best_region = candidates[0]
        bot._log(
            f'当前区域: {best_region}（置信度{best_conf:.2%}，从{len(candidates)}个候选选最优）')
        return best_region
    bot._log('[WARN] 未检测到任何已知区域')
    return None


# ============================================================
# 源网征令主流程
# ============================================================

def _quick_clean_and_recruit_exit(bot):
    """
    步骤 7+8 公共方法：源网快速清理 + 已成功招募弹窗处理。
    两个步骤独立执行，任意一步找不到都不中断后续流程。
    """
    hwnd = bot.game_window.hwnd
    time.sleep(8)
    # 步骤 7：源网快速清理
    pos = wait_for_image(bot, _stpl('源网快速清理可点击.png'), timeout=5)
    if pos is not None:
        bot._log('点击源网快速清理...')
        post_click(hwnd, pos[0], pos[1])
        time.sleep(8)
        exit_battle(bot, 30, 30)
    else:
        bot._log('未找到源网快速清理，跳过')

    # 步骤 8：已成功招募弹窗
    pos = wait_for_image(bot, _stpl('已成功招募.png'), timeout=5)
    if pos is not None:
        bot._log('检测到已成功招募弹窗，二次退出...')
        exit_battle(bot, 30, 30)
    else:
        bot._log('未出现已成功招募弹窗，无需二次退出')


def _yuanwang_wait_battle(bot, timeout=None):
    """
    源网专用战斗等待 — 和 enter_and_wait_battle 不同：
    不需要 setup_preset、不需要点 F战斗。
    只检查手动 → 等 Buff.png 消失。
    超时默认 300s（普通战斗最长 5 分钟），失败返回 False。
    """
    hwnd = bot.game_window.hwnd
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
        bot._log('未检测到手动按钮')

    timeout = timeout or 300  # 最多等 5 分钟
    bot._log(f'等待战斗结束（Buff.png 消失，最多{timeout}s）...')
    gone = wait_for_image_gone(
        bot, tpl('Buff.png'), timeout=timeout, confirm_times=3, interval=2)
    if gone:
        bot._log('战斗已结束')
        return True
    else:
        bot._log(f'[FAIL] 等待超时：Buff.png {timeout}s 未消失')
        return False


def run_yuanwang_battle(bot, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
    """
    源网征令流程。

    1.  回主界面
    2.  开侧边栏 → 点挑战
    3.  点试炼挑战
    4.  点源网征令入口
    5.  点源网征令前往行动
    6.  检测当前区域（蜃都/坎特/洛莱）
    7.  点源网快速清理 → 退出战斗
    8.  检测"已成功招募"弹窗 → 二次退出
    9.  色号识别六边形红点 → 点源网前往挑战 → 点源网确认 → 进战斗
    [后续步骤待补全]
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log(f'源网征令开始 → {difficulty} ×{streak}')
        bot._log('=' * 40)

        # === 1. 回到主界面 ===
        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)

        # === 2. 开侧边栏 → 点挑战（richang 模板） ===
        if not open_sidebar(bot):
            return False
        bot._log('点击挑战...')
        pos = wait_for_image(bot, '挑战.png', timeout=5)
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # === 3. 点试炼挑战（richang 模板） ===
        bot._log('点击试炼挑战...')
        pos = wait_for_image(bot, '试炼挑战.png', timeout=5)
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # === 4. 点源网征令入口（shilian 模板） ===
        bot._log('点击源网征令入口...')
        pos = wait_for_image(bot, _stpl('源网征令入口.png'), timeout=5)
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # 源网征令入口后可能直接进入选牌画面 → 跳过 5-8 先选牌
        skip_to_card = False
        pos = wait_for_image(bot, _stpl('集成读卡.png'), timeout=3)
        if pos is not None:
            bot._log('检测到集成读卡（入口后直接进入选牌），跳过步骤 5-8')
            skip_to_card = True

        if skip_to_card:
            bot._log('直接进入选牌流程...')
            _select_card_by_ocr(bot)
            pos = wait_for_image(bot, _stpl('集成确认按钮.png'), timeout=5)
            if pos is not None:
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)

                pos = wait_for_image(bot, _stpl('货箱集成器.png'), timeout=5)
                if pos is not None:
                    pos = wait_for_image(bot, _stpl('货箱集成打开.png'), timeout=5)
                    if pos is not None:
                        bot._log('点击货箱集成打开...')
                        post_click(hwnd, pos[0], pos[1])
                        time.sleep(2)
            exit_battle(bot, 30, 30)
        else:
            # === 5. 点源网征令前往行动（shilian 模板） ===
            bot._log('点击源网征令前往行动...')
            pos = wait_for_image(bot, _stpl('源网征令前往行动.png'), timeout=5)
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

        # === 7+8. 源网快速清理 + 已成功招募弹窗（A/B 线共用） ===
        _quick_clean_and_recruit_exit(bot)

        # === 9-10 循环：红点 → 战斗 → 选牌 → 确认，直到无红点（A/B 线共用） ===
        RED_HEXAGON_RGB = (226, 33, 40)
        stale_rounds = 0
        while bot.is_running:
            # --- 找红点 ---
            bot._log(f'色号查找六边形红点 rgb{RED_HEXAGON_RGB}...')
            red_points = find_all_by_color(
                bot, target_rgb=RED_HEXAGON_RGB, tolerance=30)
            if not red_points:
                bot._log('未找到六边形红点，红点循环结束')
                break

            # --- 合并临近红点（一个六边形被识别成多个点）---
            CLUSTER_DIST = 20  # X 或 Y 差 < 20px 视为同一个点
            merged = []
            for rx, ry in sorted(red_points, key=lambda p: p[0]):
                if merged and abs(rx - merged[-1][0]) < CLUSTER_DIST and abs(ry - merged[-1][1]) < CLUSTER_DIST:
                    continue  # 和上一个合并的点太近，跳过
                merged.append((rx, ry))
            red_points = [p for p in merged if p != (733, 537)]
            bot._log(
                f'红点合并: {len(red_points)} 个（原始 {len(sorted(red_points, key=lambda p: p[0]))} 个）')

            # --- 按离圆心距离排序：外围 → 内部 ---
            gw = bot.game_window
            if red_points:
                import math
                # 圆心优先用终极圆心.png，识别不到则用游戏画面中心
                core = bot.find_image(_stpl('终极圆心.png'), multi_scale=False)
                if core is not None:
                    cx, cy = core.x, core.y
                    bot._log(f'圆心: 终极圆心.png ({cx}, {cy})')
                else:
                    cx = gw.width // 2
                    cy = gw.height // 2
                    bot._log(f'圆心: 游戏画面中心 ({cx}, {cy}) 未找到终极圆心.png')
                # 按离圆心距离排序，距离差 <40px 的视为同圈，圈内 Y 小优先（上→下）
                dists = [(math.hypot(p[0] - cx, p[1] - cy), p[1], p)
                         for p in red_points]
                dists.sort(key=lambda d: (-round(d[0], -1), d[1]))
                red_points = [d[2] for d in dists]
            bot._log(
                f'红点排序(外围→{cx},{cy}): points={red_points[:5]}')

            # 依次尝试每个红点，直到切到挑战页面
            challenge_pos = None
            tried_rx = set()
            last_red_points = red_points[:]  # 保存上轮红点快照
            for ri, (rx, ry) in enumerate(red_points):
                rx_key = round(rx, -1)
                if rx_key in tried_rx:
                    continue

                bot._log(f'尝试红点 #{ri+1} ({rx}, {ry})...')
                post_click(hwnd, rx, ry)
                time.sleep(2)

                pos = wait_for_image(bot, _stpl('源网前往挑战.png'), timeout=5)
                if pos is not None:
                    bot._log(f'红点 #{ri+1} 切到挑战页面')
                    challenge_pos = pos
                    break

                bot._log(f'红点 #{ri+1} 未切到挑战页面，返回地图...')
                tried_rx.add(rx_key)
                exit_battle(bot, 30, 30)
                time.sleep(1)

                # 重新扫描红点 → 和上轮对比，判断位置是否大变
                new_points = find_all_by_color(
                    bot, target_rgb=RED_HEXAGON_RGB, tolerance=30)
                merged2 = []
                for rx2, ry2 in sorted(new_points, key=lambda p: p[0]):
                    if merged2 and abs(rx2 - merged2[-1][0]) < CLUSTER_DIST and abs(ry2 - merged2[-1][1]) < CLUSTER_DIST:
                        continue
                    merged2.append((rx2, ry2))
                new_points = [p for p in merged2 if p != (733, 537)]

                # 对比新旧红点区域：如果超过一半的点位置变化 > 30px → 视为位置大变
                MOVED_THRESH = 30
                moved_count = 0
                for op in last_red_points:
                    # 检查 old_point 是否在新列表里有"接近"的对应点
                    close = any(abs(nx - op[0]) < MOVED_THRESH and abs(ny - op[1]) < MOVED_THRESH
                                for nx, ny in new_points)
                    if not close:
                        moved_count += 1
                total = max(len(last_red_points), 1)
                ratio = moved_count / total

                if ratio >= 0.5 or len(new_points) != len(last_red_points):
                    bot._log(
                        f'红点位置变化（{moved_count}/{total}={ratio:.0%}）→ 重新排序')
                    last_red_points = new_points[:]
                    red_points = new_points[:]
                    if red_points:
                        # 重新排序：用同样的圆心逻辑
                        core2 = bot.find_image(
                            _stpl('终极圆心.png'), multi_scale=False)
                        if core2 is not None:
                            cx2, cy2 = core2.x, core2.y
                        else:
                            cx2, cy2 = gw.width // 2, gw.height // 2
                        dists2 = [(math.hypot(p[0] - cx2, p[1] - cy2), p[1], p)
                                  for p in red_points]
                        dists2.sort(key=lambda d: (-round(d[0], -1), d[1]))
                        red_points = [d[2] for d in dists2]
                    break  # 退出 for，外层 while 用新 red_points 重新遍历
                else:
                    bot._log(f'红点位置未变（ratio={ratio:.0%}），保持原顺序继续')

            if challenge_pos is None:
                stale_rounds += 1
                bot._log(f"所有红点均未切到挑战页面 (stale={stale_rounds}/3)")
                if stale_rounds >= 3:
                    bot._log("[WARN] 红点连续 3 轮无进展，放弃循环")
                    break
                exit_battle(bot, 30, 30)
                time.sleep(1)
                continue
            stale_rounds = 0  # 有进展就重置

            # 点击"源网前往挑战"
            post_click(hwnd, challenge_pos[0], challenge_pos[1])
            time.sleep(2)

            bot._log('点击源网确认...')
            pos = wait_for_image(bot, _stpl('源网确认.png'), timeout=5)
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            if not _yuanwang_wait_battle(bot):
                return False
            exit_battle(bot, 30, 30)

            # --- 战斗后：第二场 or 选牌 ---
            time.sleep(2)
            pos = wait_for_image(bot, _stpl('源网确认.png'), timeout=5)
            if pos is not None:
                bot._log('检测到源网确认（第二场）→ 再次进入战斗...')
                post_click(hwnd, pos[0], pos[1])
                time.sleep(2)
                if not _yuanwang_wait_battle(bot):
                    return False
                exit_battle(bot, 30, 30)

            time.sleep(3)
            pos = wait_for_image(bot, _stpl('集成读卡.png'), timeout=5)
            if pos is not None:
                bot._log('检测到集成读卡，开始选牌...')
                _select_card_by_ocr(bot)

                bot._log('点击集成确认按钮...')
                pos = wait_for_image(bot, _stpl('集成确认按钮.png'), timeout=5)
                if pos is not None:
                    post_click(hwnd, pos[0], pos[1])
                    time.sleep(2)
                    exit_battle(bot, 30, 30)

                    # 检测货箱集成器 → 打开
                    pos = wait_for_image(bot, _stpl('货箱集成器.png'), timeout=5)
                    if pos is not None:
                        bot._log('检测到货箱集成器，查找货箱集成打开...')
                        pos = wait_for_image(
                            bot, _stpl('货箱集成打开.png'), timeout=5)
                        if pos is not None:
                            bot._log('点击货箱集成打开...')
                            post_click(hwnd, pos[0], pos[1])
                            time.sleep(2)
                        else:
                            bot._log('[WARN] 未检测到货箱集成打开')
                    else:
                        bot._log('未检测到货箱集成器，跳过')
                else:
                    bot._log('[WARN] 未检测到集成确认按钮')
                time.sleep(3)
                exit_battle(bot, 30, 30)
            else:
                bot._log('未检测到集成读卡')
                exit_battle(bot, 30, 30)
            # 选牌/确认结束后执行快速清理 + 已成功招募
            _quick_clean_and_recruit_exit(bot)
            # 循环回到找红点

        bot._log(f'[OK] 源网征令完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
