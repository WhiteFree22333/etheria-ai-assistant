"""
战斗公共模块 — 所有副本战斗通用的基础能力

供 zhike_battle / yuanqi_battle 等模块导入使用。
"""
import os
import time

import numpy as np
from PIL import Image

from core._base.input import post_click
from core._base.window import focus_window, get_client_rect
from core.config import GAME_CONFIG

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMPLATES_DIR = os.path.join(_BASE_DIR, 'templates', 'richang')


def tpl(name: str) -> str:
    """快捷拼接模板完整路径"""
    return os.path.join(_TEMPLATES_DIR, name)


# ============================================================
# 等待/判断工具
# ============================================================

def wait_for_image(bot, template_name: str, timeout: float = None, interval: float = None):
    """循环截图等到图标出现，返回屏幕绝对坐标 (x, y) 或 None。二次确认防误判。

    超时后用 MSS 前台截图做最后一次兜底匹配——绕过 DXGI 缓存/脏帧问题。
    """
    # 如果已经是完整路径就不拼 richang/ 前缀
    template_path = template_name if os.path.isabs(template_name) or '/' in template_name or '\\' in template_name else tpl(template_name)
    timeout = timeout or GAME_CONFIG.image_wait_timeout
    interval = interval or GAME_CONFIG.image_wait_interval
    deadline = time.time() + timeout

    while time.time() < deadline:
        if not bot.is_running:
            return None

        match = bot.find_image(template_path)
        if match:
            time.sleep(0.15)
            match2 = bot.find_image(template_path)
            if match2 is None:
                bot._log(f"检测到 {template_name} 但二次确认丢失，继续...")
                time.sleep(interval)
                continue
            abs_x = bot.game_window.left + match2.x
            abs_y = bot.game_window.top + match2.y
            bot._log(f"检测到: {template_name} ({abs_x}, {abs_y})")
            return (abs_x, abs_y)

        time.sleep(interval)

    # 超时兜底：用 MSS 新建实例做一次强制前台截图（绕过 DXGI 缓存/脏帧）
    bot._log(f"超时：{timeout}s 内未检测到 {template_name}，尝试 MSS 前台截图兜底...")
    from core._base.capture import capture_mss
    gw = bot.game_window
    if not bot.is_running:
        return None
    fresh = capture_mss(gw)
    if fresh is not None:
        import numpy as np
        import cv2
        # cv2.imread 不支持中文路径，用 open+imdecode 绕过
        with open(template_path, 'rb') as _f:
            _data = np.frombuffer(_f.read(), dtype=np.uint8)
        template = cv2.imdecode(_data, cv2.IMREAD_COLOR)
        if template is not None:
            screen_cv = cv2.cvtColor(np.array(fresh), cv2.COLOR_RGB2BGR)
            result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= GAME_CONFIG.template_threshold:
                th, tw = template.shape[:2]
                cx, cy = max_loc[0] + tw // 2, max_loc[1] + th // 2
                abs_x, abs_y = gw.left + cx, gw.top + cy
                bot._log(f"MSS 兜底检测到: {template_name} ({abs_x}, {abs_y}) 置信度 {max_val:.2%}")
                return (abs_x, abs_y)
            bot._log(f"MSS 兜底未通过阈值: {template_name} (置信度 {max_val:.2%} < {GAME_CONFIG.template_threshold})")
    bot._log(f"最终失败: {template_name}")
    return None


def wait_for_image_gone(bot, template_name: str, timeout: float = None, confirm_times: int = 2, interval: float = None):
    """等待图标连续消失 N 次，确认页面已切走。

    如果连续超时仍无法确认 → 放宽条件：只要曾消失过 1 次，就当它已经切走了。
    防止 Unity 偶尔不吃 PostMessage 点击导致永远等不到消失。
    """
    # 如果已经是完整路径就不拼 richang/ 前缀
    template_path = template_name if os.path.isabs(template_name) or '/' in template_name or '\\' in template_name else tpl(template_name)
    timeout = timeout or GAME_CONFIG.image_gone_timeout
    interval = interval or GAME_CONFIG.image_gone_interval
    deadline = time.time() + timeout
    gone_streak = 0
    ever_gone = False

    while time.time() < deadline:
        if not bot.is_running:
            return False
        if bot.find_image(template_path) is None:
            gone_streak += 1
            ever_gone = True
            if gone_streak >= confirm_times:
                bot._log(f"页面已切换: {template_name} 连续 {confirm_times} 次消失")
                return True
        else:
            gone_streak = 0
        time.sleep(interval)

    # 超时兜底：如果曾消失过，放宽为只要当前不存在就算
    if ever_gone:
        bot._log(f"页面切换（放宽）: {template_name} 曾消失后当前不存在 → 视为已切走")
        return True
    bot._log(f"警告：{timeout}s 后 {template_name} 仍未消失，强行继续")
    return True


def wait_battle_end(bot, timeout: float = None, interval: float = None) -> bool:
    """等待连续战斗完成（或不在战斗中秒过）。先等 6 秒让战斗画面加载。"""
    timeout = timeout or GAME_CONFIG.battle_end_timeout
    interval = interval or GAME_CONFIG.battle_end_interval
    # 先回主界面——在子页面里看不到连续战斗图标
    bot.go_back_to_main(tpl("返回.png"))
    time.sleep(0.5)
    for attempt in range(4):
        time.sleep(1.5)
        match = bot.find_image(tpl('连续战斗中.png'), multi_scale=False)
        if match is not None:
            bot._log(f'检测到连续战斗中 (置信度: {match.confidence:.2%})，等待完成...')
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not bot.is_running:
                    return False
                if bot.find_image(tpl('连续战斗完成.png'), multi_scale=False):
                    bot._log('连续战斗完成！')
                    return True
                bot._log('仍在战斗中...')
                time.sleep(interval)
            bot._log(f'超时：{timeout}s 内战斗未完成')
            return False

    bot._log('不在战斗中，跳过等待')
    return True


# ============================================================
# 进入副本第 0-4 步（智壳 / 源器等通用）
# ============================================================

def enter_dungeon(bot, entry_template: str) -> bool:
    hwnd = bot.game_window.hwnd

    if not wait_battle_end(bot):
        bot._log('[FAIL] 上次战斗未完成，停止')
        return False

    bot._log('回到主界面...')
    bot.go_back_to_main(tpl('返回.png'))
    time.sleep(0.5)

    bot._log('查找 tab页...')
    tab_match = bot.find_image(tpl('tab页.png'))
    if tab_match is None:
        tab_match = bot.find_image(tpl('tab页蓝点版.png'))
    if tab_match:
        tab_pos = bot.game_window.left + tab_match.x, bot.game_window.top + tab_match.y
        post_click(hwnd, tab_pos[0], tab_pos[1])
        time.sleep(0.5)
        if wait_for_image(bot, '挑战.png') is None:
            bot._log('[FAIL] 失败：点击 tab页 后侧边栏未弹出')
            return False
        bot._log('侧边栏已弹出')
    else:
        bot._log('侧边栏已打开，跳过点击')

    pos = wait_for_image(bot, '挑战.png')
    if pos is None:
        bot._log('[FAIL] 失败：未检测到挑战按钮')
        return False
    bot._log(f'点击挑战 ({pos[0]}, {pos[1]})...')
    post_click(hwnd, pos[0], pos[1])
    wait_for_image_gone(bot, '挑战.png')
    time.sleep(0.5)

    bot._log(f'查找入口: {entry_template}...')
    pos = wait_for_image(bot, entry_template)
    if pos is None:
        bot._log(f'[FAIL] 失败：未检测到 {entry_template}')
        return False
    bot._log(f'点击 {entry_template} ({pos[0]}, {pos[1]})...')
    _click_and_wait_gone(bot, hwnd, pos[0], pos[1], entry_template)
    time.sleep(0.5)

    bot._log('已进入挑战列表页')
    return True


# ============================================================
# 打开侧边栏（通用入口）
# ============================================================

def _click_and_wait_gone(bot, hwnd, x, y, template_name):
    """点击 + 等图标消失。post_click 自身已双发，这里只需等结果。"""
    post_click(hwnd, x, y)
    time.sleep(0.3)
    wait_for_image_gone(bot, template_name, timeout=timeout, confirm_times=2, interval=1)
    return True


def open_sidebar(bot) -> bool:
    hwnd = bot.game_window.hwnd
    bot._log('检查侧边栏...')
    tab_match = bot.find_image(tpl('tab页.png'))
    if tab_match is None:
        tab_match = bot.find_image(tpl('tab页蓝点版.png'))
    if tab_match:
        tab_pos = bot.game_window.left + tab_match.x, bot.game_window.top + tab_match.y
        post_click(hwnd, tab_pos[0], tab_pos[1])
        time.sleep(0.5)
        bot._log('侧边栏已打开')
    else:
        bot._log('侧边栏已打开，跳过点击')
    return True


# ============================================================
# 超出上限弹窗处理（源器通用）
# ============================================================

def handle_over_limit(bot) -> bool:
    hwnd = bot.game_window.hwnd
    over = wait_for_image(bot, '源器超出上限.png')
    if over is None:
        over = wait_for_image(bot, '源器超出上限2.png', timeout=3)
    if over is not None:
        bot._log('检测到源器超出上限弹窗！')
        close = wait_for_image(bot, '知道了.png')
        if close is None:
            bot._log('[FAIL] 失败：未检测到知道了按钮')
            return False
        post_click(hwnd, close[0], close[1])
        time.sleep(0.5)
        bot._log('已关闭超出上限弹窗')
    return True


# ============================================================
# 战斗入场：选预设阵容 + 使用预设（通用）
# ============================================================

def setup_preset(bot) -> bool:
    hwnd = bot.game_window.hwnd

    bot._log('点击预设按钮...')
    pos = wait_for_image(bot, '预设.png', timeout=GAME_CONFIG.preset_load_timeout)
    if pos is None:
        bot._log('[FAIL] 失败：未找到预设按钮')
        return False
    post_click(hwnd, pos[0], pos[1])
    time.sleep(0.5)

    if bot.find_image(tpl('使用预设.png')) is None:
        bot._log('侧边栏未弹出，再点一次预设...')
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.5)

    use_pos = wait_for_image(bot, '使用预设.png', timeout=GAME_CONFIG.preset_load_timeout)
    if use_pos is None:
        bot._log('[FAIL] 未找到「使用预设」按钮')
        bot._log('[WARN] PRESET_MISSING: 亲，您没有设置预设阵容哦，请设置后回到主页重新开始。')
        return False

    bot._log('点击使用预设...')
    post_click(hwnd, use_pos[0], use_pos[1])
    time.sleep(0.5)

    equipment_pos = wait_for_image(bot, '预设装备占用.png', timeout=3)
    if equipment_pos is not None:
        bot._log('检测到装备占用弹窗，点击确定...')
        confirm_pos = wait_for_image(bot, '确定.png', timeout=GAME_CONFIG.preset_load_timeout)
        if confirm_pos is None:
            bot._log('[FAIL] 失败：未找到确定按钮')
            return False
        post_click(hwnd, confirm_pos[0], confirm_pos[1])
        time.sleep(0.5)

    bot._log('[OK] 预设阵容设置完成')
    return True


# ============================================================
# 进入公会界面（通用）
# ============================================================

def enter_guild_home(bot) -> bool:
    hwnd = bot.game_window.hwnd
    bot._log('回到主界面...')
    bot.go_back_to_main(tpl('返回.png'))
    time.sleep(0.5)
    if not open_sidebar(bot):
        bot._log('[FAIL] 失败：侧边栏未能打开')
        return False
    bot._log('点击超链协会...')
    pos = wait_for_image(bot, '超链协会.png')
    if pos is None:
        bot._log('[FAIL] 失败：未检测到超链协会')
        return False
    post_click(hwnd, pos[0], pos[1])
    time.sleep(2.5)
    return True


# ============================================================
# 手动按钮查找
# ============================================================

_ocr_manual = None

def _find_manual_button(bot, attempt=0):
    time.sleep(1.5)
    img = bot.capture()
    if img is None:
        return None
    gw = bot.game_window

    match = bot.find_image(tpl('手动.png'), multi_scale=False)
    if match is not None:
        abs_x = gw.left + match.x
        abs_y = gw.top + match.y
        bot._log(f'[尝试{attempt}] 模板匹配 手动: ({abs_x}, {abs_y})')
        return (abs_x, abs_y)
    bot._log(f'[尝试{attempt}] 模板失败，开始 OCR 识别 "手动"...')
    global _ocr_manual
    try:
        # PyInstaller bundle: torch DLLs need explicit search path
        import sys
        if getattr(sys, 'frozen', False):
            meipass = sys._MEIPASS
            torch_lib = os.path.join(meipass, 'torch', 'lib')
            if os.path.isdir(torch_lib):
                os.add_dll_directory(torch_lib)
        import easyocr
        if _ocr_manual is None:
            bot._log(f'[尝试{attempt}] 首次加载 EasyOCR 模型（可能需要几秒）...')
            _ocr_manual = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            bot._log(f'[尝试{attempt}] EasyOCR 模型加载完成')
        hw, hh = img.width // 2, img.height // 2

        # 缩小扫描区域：只取右上角大约 1/8 的区域（"手动"按钮常驻位置）
        # x: 右半 + 1/3 开始 → 更靠右，y: 顶部 1/3
        rx = hw + hw // 3
        rw = hw - hw // 3   # 右半再靠右 1/3
        rh = hh // 3
        roi = img.crop((rx, 0, rx + rw, rh))

        import cv2

        # 方案A：CLAHE 增强对比度（比二值化温和，不破坏文字边缘）
        gray = cv2.cvtColor(np.array(roi), cv2.COLOR_RGB2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 方案B：原图 + 放大（EasyOCR 对小文字需要放大）
        scaled = cv2.resize(np.array(roi), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        all_dets = []

        # 多轮识别：原图放大 + CLAHE增强图 + 原图 + 放宽阈值
        for label, img_input in [
            ('2x放大', scaled),
            ('CLAHE', enhanced),
            ('原图', np.array(roi)),
        ]:
            for det in _ocr_manual.readtext(
                img_input,
                text_threshold=0.4,
                low_text=0.2,
                link_threshold=0.2,
                canvas_size=1280,
                mag_ratio=2,
            ):
                txt = det[1]
                conf = det[2]
                all_dets.append((txt, conf, det[0], label))
                # 只匹配"手动"或"手"（不能单独匹配"动"，"自动"里也有"动"）
                if '手动' in txt or '手' in txt:
                    box = det[0]
                    if label == '2x放大':
                        sx, sy = 0.5, 0.5
                    else:
                        sx, sy = 1.0, 1.0
                    cx = rx + int(sum(p[0] * sx for p in box) / 4)
                    cy = int(sum(p[1] * sy for p in box) / 4)
                    bot._log(f'[尝试{attempt}] OCR({label}) 找到 "{txt}": ({cx}, {cy}) {conf:.0%}')
                    return (gw.left + cx, gw.top + cy)

        # 兜底：把所有识别结果按 x 坐标排序拼起来，搜索 "手动"
        all_dets.sort(key=lambda d: d[2][0][0])  # 按 x 坐标排序
        joined = ''.join(d[0] for d in all_dets)
        bot._log(f'[尝试{attempt}] 拼接文本: "{joined}"')
        if '手动' in joined:
            idx = joined.index('手动')
            # 找到对应字符的 box
            char_idx = 0
            for txt, conf, box, label in all_dets:
                if char_idx <= idx < char_idx + len(txt):
                    cx = rx + int(sum(p[0] for p in box) / 4)
                    cy = int(sum(p[1] for p in box) / 4)
                    bot._log(f'[尝试{attempt}] 拼接匹配 "手动" @ ({cx}, {cy})')
                    return (gw.left + cx, gw.top + cy)
                char_idx += len(txt)

        unique = list(dict.fromkeys(d[0] for d in all_dets))
        bot._log(f'[尝试{attempt}] OCR 识别到 {len(unique)} 个文字: {unique[:8]}')
    except Exception as e:
        bot._log(f'[尝试{attempt}] OCR 异常: {e}')
    return None


# ============================================================
# 手动检测 + 预设阵容 + F战斗 + 等战斗结束（通用）
# ============================================================

def enter_and_wait_battle(bot, battle_end_template='Buff.png', timeout=None):
    time.sleep(1.5)
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
        bot._log('未检测到手动按钮，直接进入预设')
    if not setup_preset(bot):
        return False
    bot._log('点击 F战斗...')
    pos = wait_for_image(bot, 'F战斗.png')
    if pos is None:
        bot._log('[FAIL] 失败：未检测到 F战斗')
        return False
    post_click(hwnd, pos[0], pos[1])
    time.sleep(5)
    bot._log(f'等待战斗结束（{battle_end_template} 消失）...')
    timeout = timeout or GAME_CONFIG.battle_end_timeout
    wait_for_image_gone(bot, battle_end_template, timeout=timeout, confirm_times=2, interval=1)
    return True


# ============================================================
# 左下角退出（通用）
# ============================================================

def exit_battle(bot, offset_x=None, offset_y=None, exit_wait=GAME_CONFIG.exit_battle_wait):
    """双击游戏窗口左下角退出（防段位升级弹窗），等 exit_wait 秒让页面切完。"""
    offset_x = offset_x if offset_x is not None else GAME_CONFIG.exit_offset_x
    offset_y = offset_y if offset_y is not None else GAME_CONFIG.exit_offset_y
    time.sleep(exit_wait)
    hwnd = bot.game_window.hwnd
    # 用客户区坐标算退出点 — GetWindowRect 包含标题栏/边框，ScreenToClient 可能溢出
    cl = get_client_rect(hwnd)
    client_left, client_top, client_right, client_bottom = cl
    exit_x = client_left + offset_x
    exit_y = client_bottom - offset_y
    bot._log(f'点击左下角退出 ({exit_x}, {exit_y}) 客户区({client_left},{client_top})-({client_right},{client_bottom})')
    post_click(hwnd, exit_x, exit_y)
    time.sleep(0.5)
    post_click(hwnd, exit_x, exit_y)
    time.sleep(exit_wait)


# ============================================================
# 颜色查找 → 返回所有匹配像素的中心坐标（通用蓝点检测等）
# ============================================================

def find_all_by_color(bot, target_rgb=None, tolerance=None):
    target_rgb = target_rgb or GAME_CONFIG.blue_dot_rgb
    tolerance = tolerance if tolerance is not None else GAME_CONFIG.blue_dot_tolerance
    import cv2
    img = bot.capture()
    if img is None:
        bot._log('[FAIL] find_all_by_color: 截图失败')
        return []
    arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    r, g, b = target_rgb
    lower = np.clip(np.array([b - tolerance, g - tolerance, r - tolerance], dtype=np.int16), 0, 255).astype(np.uint8)
    upper = np.clip(np.array([b + tolerance, g + tolerance, r + tolerance], dtype=np.int16), 0, 255).astype(np.uint8)
    mask = cv2.inRange(arr, lower, upper)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    points = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 3: continue
        x, y, w, h = cv2.boundingRect(cnt)
        points.append((x + w // 2, y + h // 2))
    deduped = []
    for p in points:
        if not any(abs(p[0]-dp[0]) < 10 and abs(p[1]-dp[1]) < 10 for dp in deduped):
            deduped.append(p)
    result = [(bot.game_window.left + p[0], bot.game_window.top + p[1]) for p in deduped]
    result.sort(key=lambda p: p[1])
    gw = bot.game_window
    bot._log(f'窗口: left={gw.left} top={gw.top} {gw.width}x{gw.height}')
    bot._log(f'颜色查找 rgb{target_rgb}±{tolerance}: 找到 {len(result)} 个匹配点')
    for i, (sx, sy) in enumerate(result):
        bot._log(f'  点{i+1}: ({sx}, {sy})')
    return result


# ============================================================
# 通用弹窗处理 — 识别到「前往清理.png」→ 点「知道了.png」
# ============================================================

def handle_cleanup_popup(bot):
    """轮询检测前往清理弹窗（最多3秒），出现即处理。"""
    import cv2, numpy as np
    from core._base.template_match import _imread
    tpl_img = _imread(tpl('前往清理.png'))
    if tpl_img is None:
        return False
    gw = bot.game_window
    for _ in range(12):  # 每 0.25s 扫一次，最多 3s
        time.sleep(0.25)
        img = bot.capture()
        if img is None: continue
        scr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        _, max_val, _, _ = cv2.minMaxLoc(cv2.matchTemplate(scr, tpl_img, cv2.TM_CCOEFF_NORMED))
        if max_val >= GAME_CONFIG.template_threshold:
            bot._log('检测到前往清理弹窗')
            ok = wait_for_image(bot, '知道了.png')
            if ok is not None:
                post_click(gw.hwnd, ok[0], ok[1])
                bot._log('已点击知道了')
                time.sleep(0.5)
            return True
    return False
