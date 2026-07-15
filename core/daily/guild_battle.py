"""
公会/竞技场模块 — 自动完成公会相关日常

全 PostMessage 后台点击，零键盘依赖。
"""
from core.config import GAME_CONFIG
from core._common.battle_common import tpl, wait_for_image, open_sidebar, setup_preset, enter_and_wait_battle, exit_battle, enter_guild_home
from core._base.input import post_click
from PIL import Image
import numpy as np
import os
import re
import time

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'


_ocr_reader = None


def _get_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import sys
        import os
        if getattr(sys, 'frozen', False):
            torch_lib = os.path.join(sys._MEIPASS, 'torch', 'lib')
            if os.path.isdir(torch_lib):
                os.add_dll_directory(torch_lib)
        import easyocr
        _ocr_reader = easyocr.Reader(['en'], gpu=False)
    return _ocr_reader


def _ocr_number_in_region(bot, img, x, y, w, h):
    x, y = max(0, x), max(0, y)
    x2, y2 = min(img.width, x + w), min(img.height, y + h)
    if x2 <= x or y2 <= y:
        return 0
    cropped = img.crop((x, y, x2, y2)).resize(
        ((x2-x)*2, (y2-y)*2), Image.LANCZOS)
    arr = np.array(cropped)
    bot._log(f'OCR 字区域: ({x},{y}) {x2-x}×(y2-y) (×2)')
    for det in _get_reader().readtext(arr, allowlist='0123456789'):
        text, conf = det[1], det[2]
        bot._log(f'OCR: "{text}" ({conf:.0%})')
        m = re.search(r'\d+', text)
        if m:
            return int(m.group())
    bot._log('OCR 未找到字')
    return 0


def run_guild_arena(bot) -> bool:
    """竞技场自动流程。"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('竞技场自动开始')
        bot._log('=' * 40)
        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot):
            return False
        pos = wait_for_image(bot, '竞技场图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.8)
        pos = wait_for_image(bot, '竞技场入口.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        exit_battle(bot, 30, 30)
        exit_battle(bot, 30, 30)
        pos = wait_for_image(bot, '竞技场挑战.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.8)
        battle_num = 0
        while bot.is_running:
            pos = bot.find_image(tpl('竞技场积分.png'))
            if pos is None:
                return False
            sx = bot.game_window.left + pos.x
            sy = bot.game_window.top + bot.game_window.height // 2
            post_click(hwnd, sx, sy)
            time.sleep(0.1)
            post_click(hwnd, sx, sy)
            time.sleep(0.8)
            if bot.find_image(tpl('灰色竞技场挑战.png')) is not None:
                bot._log('票为 0，竞技场结束')
                break
            battle_num += 1
            bot._log(f'=== 第 {battle_num} 场 ===')
            pos = wait_for_image(bot, '挑战竞技场进入图标.png')
            if pos is None:
                if bot.find_image(tpl('灰色竞技场挑战.png')) is not None:
                    bot._log('票为 0（灰色挑战），竞技场结束')
                    break
                bot._log('[FAIL] 失败：未检测到挑战进入图标')
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(0.1)
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2.5)
            if not enter_and_wait_battle(bot, 'Buff.png'):
                return False
            exit_battle(bot, 30, 30)
        bot._log(f'[OK] 竞技场完成（共 {battle_num} 场）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_signin(bot) -> bool:
    """公会签到流程。"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('公会签到开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        sign_pos = bot.find_image(tpl('公会签到蓝点.png'))
        if sign_pos is not None:
            ax = bot.game_window.left + sign_pos.x
            ay = bot.game_window.top + sign_pos.y
            bot._log(f'蓝点签到 ({ax}, {ay})...')
            post_click(hwnd, ax, ay)
            time.sleep(0.5)
        else:
            bot._log('已签到（无蓝点），跳过')
        exit_battle(bot, 30, 30)
        bot._log('[OK] 公会签到完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_anchor(bot) -> bool:
    """锚点勘测流程。"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('锚点勘测开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        pos = wait_for_image(bot, '锚点勘测.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        pos = wait_for_image(bot, '锚点勘测前往战斗.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        if not enter_and_wait_battle(bot, 'Buff.png'):
            return False
        time.sleep(4)
        exit_battle(bot, 30, 30)
        bot._log('[OK] 锚点勘测完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_theater(bot) -> bool:
    """
    幻音剧场流程。
    1. 回主界面 + 开侧边栏
    2. 点挑战 → 等加载
    3. 点试炼挑战 → 等加载
    4. 点幻音剧场入口
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('幻音剧场开始')
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
        bot._log('点击试炼挑战...')
        pos = wait_for_image(bot, '试炼挑战.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        bot._log('点击幻音剧场入口...')
        pos = wait_for_image(bot, '幻音剧场入口.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # ---- 5-11 循环区：创建房间 → 联合 → 布阵 → 上阵 → 确认 → 匹配 → 循环开始 ----
        # 中途队友退出会回退到"创建房间"画面，需要重新走一遍
        while bot.is_running:
            bot._log('创建房间...')
            pos = wait_for_image(bot, '幻音创建房间.png')
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            bot._log('联合...')
            pos = wait_for_image(bot, '幻音联合.png')
            if pos is None:
                pos = wait_for_image(bot, '幻音联合2.png')
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            bot._log('布阵...')
            pos = wait_for_image(bot, '幻音布阵.png')
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            bot._log('上阵区域...')
            pos = wait_for_image(bot, '幻音上阵区域.png')
            if pos is None:
                return False
            r = bot.find_image(tpl('幻音上阵区域.png'))
            if r is None:
                return False
            right_edge = r.x + r.width // 2
            step = r.width // 2 - 20
            cy = bot.game_window.top + r.y
            for i in range(4):
                cx = bot.game_window.left + right_edge + (i + 1) * step
                post_click(hwnd, cx, cy)
                time.sleep(0.5)

            bot._log('确认...')
            pos = wait_for_image(bot, '幻音确认.png')
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)

            bot._log('匹配...')
            pos = wait_for_image(bot, '幻音剧场匹配.png')
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])

            if wait_for_image(bot, '幻音开始.png', timeout=90) is None:
                bot._log('[FAIL] 超时：未检测到幻音开始')
                return False

            bot._log('循环点击幻音开始，等待匹配...')
            while bot.is_running:
                sp = bot.find_image(tpl('幻音开始.png'))
                if sp is None:
                    break
                post_click(hwnd, bot.game_window.left +
                           sp.x, bot.game_window.top + sp.y)
                time.sleep(1)

            # 幻音开始消失了 → 检测是进入战斗还是队友退出了
            bot._log('幻音开始消失，检测状态...')
            rolled_back = False
            for check in range(2):
                time.sleep(2)
                rb = bot.find_image(tpl('幻音创建房间.png'))
                if rb is not None:
                    bot._log(f'第{check+1}次检测到创建房间 → 队友退出，重新建房')
                    rolled_back = True
                    break
                bot._log(f'第{check+1}次未检测到创建房间')
            if rolled_back:
                continue  # 回到外层 while，从创建房间重新开始
            # 两次都没检测到 → 进入战斗了
            break

        bot._log('匹配成功，进入战斗')

        bot._log('等待战斗结束...')
        if wait_for_image(bot, '幻音结束标志.png', timeout=300) is None:
            bot._log('[FAIL] 超时：未检测到幻音结束标志')
            return False
        pos = wait_for_image(bot, '是结算评级.png', timeout=10)
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        exit_battle(bot, 30, 30)
        bot._log('[OK] 幻音剧场完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_remind(bot) -> bool:
    """提醒成员签到：进入公会 → 点成员图标 → OCR 扫描成员列表"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('提醒成员签到开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        bot._log('点击公会成员图标...')
        pos = wait_for_image(bot, '公会成员图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2.5)
        bot._log('等待成员列表加载...')
        time.sleep(2)
        img = bot.capture()
        if img is None:
            return False

        import easyocr
        import numpy as np
        import re
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        # 先全屏扫，找「协会成员」标题的位置
        bot._log('EasyOCR 全屏扫描，定位「协会成员」...')
        all_results = reader.readtext(np.array(img))

        title_y = img.height  # 默认从底部开始（找不到标题就全屏）
        for det in all_results:
            if '协会成员' in det[1]:
                box = det[0]
                title_y = int(max(p[1] for p in box))  # 标题底部 Y
                bot._log(f'找到「协会成员」标题，底部 Y={title_y}')
                break

        # 从标题下方 +10px 开始裁剪
        list_top = title_y + 10
        list_top = max(0, min(list_top, img.height - 50))
        list_img = img.crop((0, list_top, img.width, img.height))
        bot._log(f'EasyOCR 扫描成员列表 ({list_img.width}x{list_img.height})...')

        results = reader.readtext(np.array(list_img))
        if not results:
            bot._log('OCR 未识别到任何文字')
            return False
        bot._log(f'共 {len(results)} 个文本框')

        # 提取带 # 的文本 + 修复 OCR 拆字
        def _scan_round(dets, list_offset_y=0):
            """扫描一轮 OCR 结果, 修复单字符被拆的问题, 返回名字列表"""
            # 先按 Y 排序, 同一行排序
            dets = sorted(dets, key=lambda d: (
                int(sum(p[1] for p in d[0]) / 4), int(sum(p[0] for p in d[0]) / 4)))
            names = []
            i = 0
            while i < len(dets):
                d = dets[i]
                text = d[1]
                cy = list_offset_y + int(sum(p[1] for p in d[0]) / 4)
                # 检查是否包含 #数字
                m = re.search(r'#\d+', text)
                if m:
                    prefix = text[:m.start()].strip()
                    # 如果前缀太短 (1个字符甚至空), 看前面一个检测框是不是名词的一部分
                    if len(prefix) <= 1 and i > 0:
                        prev = dets[i-1]
                        prev_text = prev[1]
                        prev_cy = list_offset_y + \
                            int(sum(p[1] for p in prev[0]) / 4)
                        # 前一个框在 30px 以内且不包含 #
                        if abs(cy - prev_cy) < 30 and '#' not in prev_text:
                            # 拼在一起作为名字
                            combined = (prev_text + prefix).strip()
                            if combined:
                                names.append(combined)
                            i += 1
                            break
                    if prefix:
                        names.append(prefix)
                i += 1
            return names

        all_names = set()
        for nm in _scan_round(results, list_top):
            all_names.add(nm)
            bot._log(f'  成员: {nm}')

        # 找第一个 # 位置定光标
        first = None
        for d in results:
            if re.search(r'#\d+', d[1]):
                box = d[0]
                cx = int(sum(p[0] for p in box) / 4)
                cy = list_top + int(sum(p[1] for p in box) / 4)
                first = (bot.game_window.left + cx +
                         30, bot.game_window.top + cy)
                break

        if first is None:
            bot._log('[WARN] 未找到 # 位置')
        else:
            import ctypes
            from core._base.input import scroll
            bot._log(f'滚动扫描成员列表...')
            ctypes.windll.user32.SetCursorPos(first[0], first[1])
            time.sleep(0.1)
            dry = 0
            for rnd in range(60):
                if not bot.is_running:
                    break
                scroll(-5, hwnd)
                time.sleep(0.3)
                img2 = bot.capture()
                if img2 is None:
                    break
                li2 = img2.crop((0, list_top, img2.width, img2.height))
                r2 = reader.readtext(np.array(li2))
                added = 0
                for nm in _scan_round(r2, list_top):
                    if nm not in all_names:
                        all_names.add(nm)
                        added += 1
                        bot._log(f'  新成员: {nm}')
                if added == 0:
                    dry += 1
                    if dry >= 2:
                        bot._log(f'连续 {dry} 轮无新成员，扫描结束')
                        break
                else:
                    dry = 0
                bot._log(f'第{rnd+1}轮 +{added}人，共{len(all_names)}人')

        bot._log(f'成员名单({len(all_names)}人): {", ".join(sorted(all_names))}')
        exit_battle(bot, 30, 30)
        bot._log('[OK] 提醒成员签到完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_claim_all(bot) -> bool:
    """一键领取：回主界面 → 开侧边栏 → 点任务 → 点全部领取 → 退出"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('一键领取开始')
        bot._log('=' * 40)
        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot):
            return False
        bot._log('点击任务...')
        pos = wait_for_image(bot, '任务.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        # 先找全部领取，找不到就找单个领取
        bot._log('查找领取按钮...')
        pos = bot.find_image(tpl('全部领取.png'))
        if pos is not None:
            bot._log('点击全部领取...')
            post_click(hwnd, bot.game_window.left +
                       pos.x, bot.game_window.top + pos.y)
            time.sleep(2)
        else:
            # 没有全部领取，直接进入逐项领取循环
            bot._log('未找到全部领取，尝试逐项领取...')

        # 逐项领取循环：找领取 → 点 → 退出 → 继续找领取
        num = 0
        while bot.is_running:
            cp = bot.find_image(tpl('领取.png'))
            if cp is None:
                if num == 0:
                    bot._log('[FAIL] 失败：找不到任何领取按钮')
                    return False
                bot._log('没有更多可领取项')
                break
            num += 1
            ax = bot.game_window.left + cp.x
            ay = bot.game_window.top + cp.y
            bot._log(f'领取 #{num} ({ax}, {ay})...')
            post_click(hwnd, ax, ay)
            time.sleep(1)
            # 退出领奖弹窗，仍在任务页，继续找下一个领取
            exit_battle(bot, 30, 30)

        bot._log(f'[OK] 一键领取完成（共 {num} 项）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_anchor_claim(bot) -> bool:
    """锚点勘测一键领取"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    from core._common.battle_common import find_all_by_color
    try:
        bot._log('=' * 40)
        bot._log('锚点勘测一键领取开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        bot._log('点击锚点勘测...')
        pos = wait_for_image(bot, '锚点勘测.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(3)
        gw = bot.game_window
        mid_x = gw.left + gw.width // 2
        half_y = gw.top + gw.height // 2
        blue_rgb = (0, 255, 246)
        round_num = 0
        while bot.is_running:
            round_num += 1
            bot._log(f'--- 第{round_num}轮 ---')
            # 找左半部分蓝点
            left_dots = [p for p in find_all_by_color(
                bot, blue_rgb) if p[0] < mid_x]
            if not left_dots:
                bot._log('左半部分无蓝点，领取完成')
                break
            # 点第一个
            bot._log(f'点击左侧蓝点 ({left_dots[0][0]}, {left_dots[0][1]})...')
            post_click(hwnd, left_dots[0][0], left_dots[0][1])
            time.sleep(1.5)
            # 找右下 1/4 区域蓝点，依次点击
            right_dots = [p for p in find_all_by_color(bot, blue_rgb)
                          if p[0] >= mid_x and p[1] >= half_y]
            bot._log(f'右侧 {len(right_dots)} 个蓝点')
            for rx, ry in right_dots:
                if not bot.is_running:
                    break
                cx, cy = rx - 15, ry + 10
                bot._log(f'点击右侧蓝点 原始({rx},{ry}) → 偏移({cx},{cy})...')
                post_click(hwnd, cx, cy)
                time.sleep(0.8)
                exit_battle(bot, 30, 30)
        bot._log(f'[OK] 锚点勘测一键领取完成（共{round_num-1}轮）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_test_stamina_check(bot) -> bool:
    """测试: 回主页 → 点体力图标 → 识别体力库存右边数字"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    import easyocr
    import numpy as np
    import re
    try:
        bot._log('=' * 40)
        bot._log('测试：体力库存识别')
        bot._log('=' * 40)
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        bot._log('点击体力图标...')
        pos = wait_for_image(bot, '体力图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        bot._log('识别体力库存...')
        stock = bot.find_image(tpl('体力库存.png'))
        if stock is None:
            bot._log('[FAIL] 失败：未检测到体力库存')
            return False
        ax = bot.game_window.left + stock.x
        ay = bot.game_window.top + stock.y
        bot._log(
            f'体力库存位置 窗口内({stock.x},{stock.y}) 屏幕({ax},{ay}) 宽{stock.width}高{stock.height}')
        img = bot.capture()
        if img is None:
            return False
        # 体力数字在右方较远处（宽约 120px）
        nx = stock.width + 2
        ny = stock.y - 7
        nw = 60
        nh = stock.height + 2
        # 防越界
        nx, ny = max(0, nx), max(0, ny)
        nw = min(nw, img.width - nx)
        nh = min(nh, img.height - ny)
        if nw <= 0 or nh <= 0:
            bot._log('[FAIL] 裁剪区域无效')
            return False
        region = img.crop((nx, ny, nx + nw, ny + nh))
        # 放大2倍提高 OCR 准确率
        region = region.resize((nw * 2, nh * 2), Image.LANCZOS)
        arr = np.array(region)
        bot._log(f'数字区域 窗口内({nx},{ny}) {nw}×{nh} (×2放大) → OCR中...')
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(arr, allowlist='0123456789')
        if not results:
            bot._log('OCR 未识别到任何数字')
            return False
        num = None
        for det in results:
            text, conf = det[1], det[2]
            bot._log(f'OCR: "{text}" ({conf:.0%})')
            m = re.search(r'\d+', text)
            if m:
                num = int(m.group())
                break
        if num is None:
            bot._log('未提取到数字')
            return False
        bot._log(f'体力库存数量: {num}')
        exit_battle(bot, 30, 30)
        bot._log(f'[OK] 测试完成（体力={num}）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_assist(bot) -> bool:
    """协会共助: enter_guild_home → 协会共助 → 协会共助一键"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('协会共助开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        bot._log('点击协会共助...')
        pos = wait_for_image(bot, '协会共助.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        bot._log('点击协会共助一键...')
        pos = wait_for_image(bot, '协会共助一键.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        pos = wait_for_image(bot, '确定.png', timeout=3)
        if pos is not None:
            bot._log('检测到确定弹窗，点击确定...')
            post_click(hwnd, pos[0], pos[1])
            time.sleep(1)
        else:
            bot._log('未检测到确定弹窗')

        exit_battle(bot, 30, 30)
        bot._log('[OK] 协会共助完成')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False

    # ==== 以下旧逻辑已注释（游戏更新后不再需要逐系助力） ====
    # import cv2
    # import numpy as np
    # from core._base.template_match import _imread as _read_tpl
    # for icon_png, icon_label in [
    #     ('协会理图标.png', '理'),
    #     ('协会异图标.png', '异'),
    #     ('协会虚图标.png', '虚'),
    # ]:
    #     if not bot.is_running: break
    #     bot._log(f'=== {icon_label}系助力 ===')
    #     pos = wait_for_image(bot, icon_png)
    #     if pos is None: bot._log(f'[WARN] 未检测到{icon_label}图标，跳过'); continue
    #     post_click(hwnd, pos[0], pos[1]); time.sleep(2)
    #     round_num = 0
    #     while bot.is_running:
    #         round_num += 1
    #         cards = _find_all_cards(bot, '协会助力卡片.png')
    #         if not cards: bot._log(f'{icon_label}系没有更多卡片'); break
    #         cards.sort(key=lambda p: (p[1], p[0]))
    #         cx, cy = cards[0][0], cards[0][1]
    #         bot._log(f'{icon_label}助力 #{round_num} ({cx}, {cy})...')
    #         post_click(hwnd, cx, cy)
    #         # ... 模因不足/已助力/确定按钮循环 ...


def _find_all_cards(bot, template_name):
    """模板匹配返回所有命中位置的屏幕坐标列表。需坐标去重。"""
    import cv2
    import numpy as np
    from core._base.template_match import _imread
    template = _imread(tpl(template_name))
    if template is None:
        return []
    img = bot.capture()
    if img is None:
        return []
    scr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    th, tw = template.shape[:2]
    result = cv2.matchTemplate(scr, template, cv2.TM_CCOEFF_NORMED)
    threshold = GAME_CONFIG.template_threshold
    loc = np.where(result >= threshold)
    points = []
    gw = bot.game_window
    for y, x in zip(loc[0], loc[1]):
        points.append((gw.left + x + tw // 2, gw.top + y + th // 2))
    # 去重: 15px 内的点合并
    deduped = []
    for p in points:
        if not any(abs(p[0] - dp[0]) < 15 and abs(p[1] - dp[1]) < 15 for dp in deduped):
            deduped.append(p)
    bot._log(f'find_all_cards: {len(deduped)} 个去重后')
    return deduped


def run_guild_weekly(bot) -> bool:
    """公会每周任务领取: enter_guild_home → 公会每周任务图标 → 循环领取"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('公会每周任务领取开始')
        bot._log('=' * 40)
        if not enter_guild_home(bot):
            return False
        bot._log('点击公会每周任务图标...')
        pos = wait_for_image(bot, '公会每周任务图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        num = 0
        while bot.is_running:
            claim = bot.find_image(tpl('公会每周领取按钮.png'))
            if claim is None:
                time.sleep(1.5)
                claim = bot.find_image(tpl('公会每周领取按钮.png'))
            if claim is None:
                bot._log('没有更多可领取项')
                break
            num += 1
            ax = bot.game_window.left + claim.x
            ay = bot.game_window.top + claim.y
            bot._log(f'领取 #{num} ({ax}, {ay})...')
            post_click(hwnd, ax, ay)
            time.sleep(0.5)
            exit_battle(bot, 30, 30)
        bot._log(f'[OK] 公会每周任务领取完成（共{num}项）')

        # 依次领取协力点数 500→5000，点击位置在图标上方 3 倍身位
        for pts in [500, 1000, 1500, 2000, 2500, 3000, 4000, 5000]:
            if not bot.is_running:
                break
            match = bot.find_image(tpl(f'公会协力点数{pts}.png'))
            if match is None:
                bot._log(f'协力{pts}未找到，跳过')
                continue
            cx = bot.game_window.left + match.x
            cy = bot.game_window.top + match.y - match.height * 3
            bot._log(
                f'协力{pts}: ({match.x},{match.y}) 上移{3*match.height}px → ({cx},{cy})')
            post_click(hwnd, cx, cy)
            time.sleep(0.8)
            exit_battle(bot, 30, 30)

        exit_battle(bot, 30, 30)
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


def run_guild_arena_claim(bot) -> bool:
    """竞技场一键领取: 回主页→开侧边→竞技场图标→入口→奖励→循环领取→关闭"""
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('竞技场一键领取开始')
        bot._log('=' * 40)
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot):
            return False
        pos = wait_for_image(bot, '竞技场图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.8)
        pos = wait_for_image(bot, '竞技场入口.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(0.8)
        pos = wait_for_image(bot, '竞技场奖励图标.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        num = 0
        while bot.is_running:
            btn = bot.find_image(tpl('竞技场奖励领取按钮.png'))
            if btn is None:
                bot._log('没有更多奖励可领取')
                break
            num += 1
            ax = bot.game_window.left + btn.x
            ay = bot.game_window.top + btn.y
            bot._log(f'领取 #{num} ({ax}, {ay})...')
            post_click(hwnd, ax, ay)
            exit_battle(bot, 30, 30)
        pos = wait_for_image(bot, '咔嚓.png')
        if pos is not None:
            post_click(hwnd, pos[0], pos[1])
            time.sleep(0.5)
        bot._log(f'[OK] 竞技场一键领取完成（共{num}项）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False


# ============================================================
# 超链终端一键领取
# ============================================================

def run_guild_hyperchain(bot) -> bool:
    """
    超链终端一键领取。
    1. 回主页 + 开侧边栏
    2. 超链终端入口 → 一键领取 → exit
    3. 补给中心 → 开启补给 → exit
    4. 返回 → 事务所
    5. 派遣完成 × 多轮点击 → exit → 直到没有
    """
    import cv2 as _cv2
    from core._base.template_match import _imread as _read_tpl
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log('超链终端一键领取开始')
        bot._log('=' * 40)

        # ---- 1. 导航到首页 ----
        bot._log('回到主界面...')
        bot.go_back_to_main(tpl('返回.png'))
        time.sleep(0.5)
        if not open_sidebar(bot):
            return False

        # ---- 2. 超链终端入口 ----
        bot._log('点击超链终端入口...')
        pos = wait_for_image(bot, '超链终端入口.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # ---- 3. 一键领取 ----
        bot._log('点击超链终端一键领取...')
        pos = wait_for_image(bot, '超链终端一键领取.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)
        exit_battle(bot, 30, 30)

        # ---- 4. 补给中心 ----
        bot._log('点击超链补给中心...')
        pos = wait_for_image(bot, '超链补给中心.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # ---- 5. 开启补给 ----
        bot._log('点击超链开启补给...')
        pos = wait_for_image(bot, '超链开启补给.png')
        if pos is not None:
            post_click(hwnd, pos[0], pos[1])
            time.sleep(2)
        else:
            bot._log('未检测到超链开启补给，跳过')
        exit_battle(bot, 30, 30)

        # ---- 6. 返回 → 事务所 ----
        # bot._log('点击返回...')
        # pos = wait_for_image(bot, '返回.png')
        # if pos is None:
        #     return False
        # post_click(hwnd, pos[0], pos[1])
        # time.sleep(1)

        bot._log('点击超链事务所...')
        pos = wait_for_image(bot, '超链事务所.png')
        if pos is None:
            return False
        post_click(hwnd, pos[0], pos[1])
        time.sleep(2)

        # ---- 7. 派遣完成 × 多轮 ----
        tpl_dispatch = _read_tpl(tpl('超链派遣完成.png'))
        dispatch_found = 0
        while bot.is_running:
            img = bot.capture()
            if img is None or tpl_dispatch is None:
                break
            gw = bot.game_window
            scr = _cv2.cvtColor(np.array(img), _cv2.COLOR_RGB2BGR)
            result = _cv2.matchTemplate(
                scr, tpl_dispatch, _cv2.TM_CCOEFF_NORMED)
            th_d, tw_d = tpl_dispatch.shape[:2]
            loc = np.where(result >= GAME_CONFIG.template_threshold)
            pts = []
            for pt in zip(*loc[::-1]):
                if not any(abs(pt[0]-p[0]) < 20 and abs(pt[1]-p[1]) < 20 for p in pts):
                    pts.append(pt)
            if not pts:
                bot._log('没有更多派遣完成')
                break
            # 只点第一个（最上方），点完 exit，下一轮重新扫描
            pts.sort(key=lambda p: p[1])
            cx_w, cy_w = pts[0]
            sx = gw.left + cx_w + tw_d // 2
            sy = gw.top + cy_w + th_d // 2
            bot._log(f'派遣 ({sx}, {sy})')
            post_click(hwnd, sx, sy)
            time.sleep(0.5)
            exit_battle(bot, 30, 30, single_click=True)
            dispatch_found += 1

        bot._log(f'[OK] 超链终端完成（共{dispatch_found}项派遣）')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
