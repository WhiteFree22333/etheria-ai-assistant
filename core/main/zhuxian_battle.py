"""
主线剧情模块

全 PostMessage 后台点击，零键盘依赖。

模板目录：templates/zhuxian/（子目录在 ui/app.py 里用 select_and_save_template 存）
「获得物品.png」复用 templates/shilian/ 里的那张，不重复截。
"""
import os
import time

import win32gui

from core._base.input import post_click
from core._base.template_match import match_template_multi_scale
from core._base.window import get_client_rect
from core.config import GAME_CONFIG
from core._common.battle_common import (
    tpl,
    wait_for_image,
    wait_for_image_gone,
    open_sidebar,
    exit_battle,
    exit_battle_verified,
    _find_manual_button,
)

_BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_ZHUXIAN_TPL = os.path.join(_BASE_DIR, 'templates', 'zhuxian')
_SHILIAN_TPL = os.path.join(_BASE_DIR, 'templates', 'shilian')

# 主线一关最多打几场。「没出获得物品就回主线前往挑战重来」是死循环，设上限兜底。
_MAX_REWARD_ROUNDS = 7

# 主循环最多跑几轮（一轮 = 回主界面 → 开主线 → 选章节）。只是防死循环的兜底。
_MAX_STAGE_ENTRY_ROUNDS = 99

# 一轮里最多连打几关。打完一关不回主界面重选章节，直接从「进关卡」重进，
# 所以需要一个独立的计数上限兜底（正常一章也就几关到十几关）。
_MAX_STAGE_CLEAR_ROUNDS = 30

# 连续多少轮「进关卡后既没跳过剧情也没主线前往挑战」才认定全关打完。
# 单次没出现可能只是卡顿/切屏，要连续命中才敢收工。
_MAX_NO_STAGE_STREAK = 10

# 「前置关卡判断.png」是个弹出来很快就消失的提示，用默认的 0.5s 采样间隔经常整段错过。
# 缩到 0.1s，多抓几次。
_POPUP_POLL_INTERVAL = 0.1

# 困难模式下「没有关卡」命中多少次算到了最后一关。第 1 次命中仍按普通逻辑回主界面
# 重开一轮，所以计数是跨轮累加的（放在关卡循环里会每轮清零、永远到不了这个数）。
_HARD_LAST_STAGE_HITS = 2

# 「结算界面」的标志图。打完一场后用它判断有没有真的退出去 —— 详见
# battle_common.exit_battle_verified。
# 它是通用战斗结算面板，公会那边（锚点勘测）也是同一个界面，所以这张图放在
# templates/richang/ 里共用，tpl() 就能找到，不用 _ztpl()。
_SETTLEMENT_MARK = '战斗统计.png'


def _ztpl(name: str) -> str:
    """主线模板路径 — templates/zhuxian/"""
    return os.path.join(_ZHUXIAN_TPL, name)


def _stpl(name: str) -> str:
    """试炼模板路径 — templates/shilian/（主线和试炼共用「获得物品」那张图）"""
    return os.path.join(_SHILIAN_TPL, name)


def _sync_window_rect(bot, hwnd):
    """把 bot.game_window 的快照矩形对齐到当前的 GetWindowRect。

    bot.game_window 是 bot.init() 时读一次的快照，之后全程没人刷新。但截图
    （PrintWindow / BitBlt）内部是**现读** GetWindowRect 的，截出来的是「现在」的画面；
    wait_for_image / _wait_best_of 却拿「当初」的 left/top 把图内坐标还原成屏幕坐标。
    窗口一移动，两者就差一个位移 —— 横坐标整体偏（纵坐标因为另外现读客户区，反而正常）。

    只改矩形坐标，不重新搜窗口：bot.init() 要枚举全屏所有窗口，每帧调太重。
    句柄失效就原样返回，交给调用方原有的失败分支处理。
    """
    gw = bot.game_window
    if gw is None or hwnd is None or gw.hwnd != hwnd:
        return
    try:
        rect = win32gui.GetWindowRect(hwnd)
    except Exception:
        return
    if (gw.left, gw.top, gw.right, gw.bottom) != rect:
        bot._log(
            f'窗口位置变了 ({gw.left},{gw.top}) → ({rect[0]},{rect[1]})，刷新快照')
        gw.left, gw.top, gw.right, gw.bottom = rect


def _wait_best_of(bot, names, timeout=None, interval=None):
    """在同一帧里同时匹配多个模板，返回置信度最高的 (x, y, name, conf)。

    都不过阈值 → 一直等到超时，返回 None。

    为什么不能「先找 A，A 没找到再找 B」：主线这两个按钮
    「主线前往挑战」和「主线前往挑战无体力」长得几乎一样（就差个体力图标），
    分批找会张冠李戴——找 B 的那一次匹配很可能其实是 A，只是分数掉到阈值下。
    同一帧里把两张图都跑一遍再比分，才是可比的。

    conf 是原始多尺度匹配分（0~1），没有二次确认——调用方只是拿它比大小，
    真的要点之前仍然会走 post_click，点空了下一轮还会重来。
    """
    paths = [(n, _ztpl(n)) for n in names]
    threshold = GAME_CONFIG.template_threshold
    timeout = timeout or GAME_CONFIG.image_wait_timeout
    interval = interval or GAME_CONFIG.image_wait_interval
    deadline = time.time() + timeout

    while time.time() < deadline:
        if not bot.is_running:
            return None

        # 每帧对齐一次：截图是现读窗口矩形截的，坐标还原若用旧快照就会整体偏
        _sync_window_rect(bot, bot.game_window.hwnd)

        shot = bot.capture()
        if shot is None:
            time.sleep(interval)
            continue

        best = None
        scores = []
        for name, path in paths:
            r = match_template_multi_scale(shot, path, threshold=threshold)
            if r is None:
                scores.append(f'{name} 未过阈值')
                continue
            scores.append(f'{name} {r.confidence:.2%}')
            if best is None or r.confidence > best[3]:
                # 截图是窗口矩形，和 wait_for_image 一样加窗口左上角还原成屏幕绝对坐标
                gw = bot.game_window
                best = (gw.left + r.x, gw.top + r.y, name, r.confidence)

        if best is not None:
            bot._log('本帧匹配 — ' + '，'.join(scores))
            return best

        time.sleep(interval)

    bot._log(f'超时：{timeout}s 内 {"、".join(names)} 都没过阈值')
    return None


def _no_stage_left(bot, pos_skip) -> bool:
    """这一关还有没有关卡可打。跳过剧情没出现、两个「主线前往挑战」也都没出现 = 没有。

    「主线前往挑战无体力」必须一起算：体力耗尽时按钮会换成那一张，只判有体力的那张
    会把「没体力」误判成「没关卡」→ 一轮轮回主界面空转，攒够 _MAX_NO_STAGE_STREAK
    次还会假报「全关挑战结束」。

    用 _wait_best_of 同帧比，而不是「先找有体力的，找不到再找没体力的」——这两张图
    长得几乎一样（就差个体力图标），分批找会互相误匹配。

    困难模式最后一关也会命中这里（那一关「主线前往挑战」根本不出现），
    所以调用方拿到 True 之后还得再判一次 hard_mode。
    """
    if pos_skip is not None:
        return False
    return _wait_best_of(bot, ['主线前往挑战.png', '主线前往挑战无体力.png']) is None


def _click_center(bot, hwnd, label: str):
    """点「主线横坐标定位.png」的横坐标 + 游戏窗口客户区纵坐标中心。

    横坐标交给模板：章节卡片的可点区域横向不一定在窗口正中，靠模板定位更稳。
    纵坐标现读客户区中心——不用 bot.game_window.center，那个是 GameWindow 里的快照，
    left/top/right/bottom 在 find_game_window 时读一次就固定了，游戏窗口一旦移动
    （游戏自己重排 / 用户拖动 / DPI 变化 / resize_game_window）就永远打到旧位置。
    也不用 GetWindowRect 的中心——那含标题栏和边框，比客户区中心偏上十几像素。
    """
    bot._log(f'定位中心（{label}）...')
    # wait_for_image 的横坐标是「快照 left + 图内匹配 x」，快照旧了就会偏
    _sync_window_rect(bot, hwnd)
    pos = wait_for_image(bot, _ztpl('主线横坐标定位.png'))
    if pos is None:
        bot._log(f'[WARN] 未找到「主线横坐标定位.png」，{label} 没点')
        return
    cl = get_client_rect(hwnd)
    cy = (cl[1] + cl[3]) // 2
    bot._log(f'点击 ({pos[0]}, {cy}) — 横坐标来自模板，纵坐标取客户区中心')
    post_click(hwnd, pos[0], cy)


def _click_at_ratio(bot, hwnd, x_ratio: float, label: str):
    """按客户区比例点：横坐标 = 客户区左 + 宽 × x_ratio，纵坐标 = 客户区纵向正中。

    困难模式用：识别到「前置关卡判断」后，真正的入口不在「主线横坐标定位」那张图的
    位置上，得按比例挪过去。纵坐标跟 _click_center 一致，都是现读客户区中心。
    """
    cl = get_client_rect(hwnd)
    cx = cl[0] + int((cl[2] - cl[0]) * x_ratio)
    cy = (cl[1] + cl[3]) // 2
    bot._log(f'点击 ({cx}, {cy}) — 客户区横向 {x_ratio:.0%}、纵向正中（{label}）')
    post_click(hwnd, cx, cy)


def _click_f_battle(bot, hwnd) -> bool:
    """等 F战斗 出现 → 点击 → 查手动按钮（出现就点掉）。找不到 F战斗 返回 False。"""
    pos = wait_for_image(bot, 'F战斗.png')
    if pos is None:
        bot._log('[FAIL] 失败：未检测到 F战斗')
        return False
    post_click(hwnd, pos[0], pos[1])

    # 点完 F战斗 再查手动：出现说明这场要手动，点掉它
    manual_pos = _find_manual_button(bot, max_attempts=2)
    if manual_pos is not None:
        post_click(hwnd, manual_pos[0], manual_pos[1])
        time.sleep(0.5)
    else:
        bot._log('未检测到手动按钮')
    return True


def _wait_battle_end(bot, label: str = '') -> bool:
    """等 Buff.png 消失 = 本场战斗结束。超时返回 False。"""
    # 先等战斗画面加载出来。不等的话 Buff.png 还没出现，
    # wait_for_image_gone 会把它当成「连续 3 次消失」直接判战斗结束（假结束）。
    # 与 battle_common.enter_and_wait_battle 里点完 F战斗 的 sleep(5) 同理。
    time.sleep(5)
    bot._log(f'等待战斗结束{label}（Buff.png 消失，最多 300s）...')
    gone = wait_for_image_gone(
        bot, tpl('Buff.png'), timeout=300, confirm_times=3, interval=2)
    if not gone:
        bot._log('[FAIL] 等待超时：Buff.png 300s 未消失')
        return False
    bot._log('战斗已结束')
    return True


def run_zhuxian_battle(bot, character_name: str = '', difficulty: str = '普通', streak: int = 1,
                       double_stamina: bool = False) -> bool:
    """
    主线剧情流程。

    主循环（一轮 = 回主界面 → 开主线 → 选章节）：
    1. 回主界面
    2. 开侧边栏 → 点挑战
    3. 点主线入口
    4. 点窗口中心选章节
    然后进关卡循环（一轮里连打多关，每关都从 4b 开始，不回主界面重选章节）：
    4b. 再点窗口中心进关卡 → 跳过剧情
        识别到「获得物品」说明这关已通关 → 跳过战斗步骤，直接重进关卡打下一关
    5~9. 这一关打到出「获得物品」为止：「主线前往挑战」和「主线前往挑战无体力」
         同帧识别、比置信度点高的那个 → 点 F战斗（顺手点掉手动按钮）
         → 等 Buff.png 消失 → 左下角退出结算
         → 退出结算之后才认「主线跳过」（收尾剧情在结算之后才播），出现就点它，
           再认出「主线章节完成」就是本章最后一场 → 退出，回主界面开下一章
         → 再等「获得物品」：等到就单次退出，重进关卡打下一关；
           没等到说明这关还有下一场，回「主线前往挑战」重来
         点到的是「无体力」那个则先看 F战斗：出来了说明只是图标缓存、人已在关卡里，
         直接开打；没出来才是真·体力不足 → 兑换稳定值 → 确定体力兑换 →
         退出结算，回到本场开头重来（未勾选自动兑换则直接结束任务）

    有三处会回主界面重开一轮：4b 之后「主线跳过」和「主线前往挑战」都没出现、
    打出「主线章节完成」、以及困难模式最后一关打完。其余情况都在关卡循环里打转。
    收工条件：第一处连续 _MAX_NO_STAGE_STREAK 次命中 → 全关挑战结束。
             单次没出现只当卡顿，回主界面重来。

    困难模式：第 3 步点完主线入口后识别「主线困难模式.png」标记 hard_mode。
    每轮重判一次 —— 回主界面重开一轮会进新章节，新章节不一定是困难模式，
    做成粘性会把普通章节也当困难走。

    困难模式最后一关「主线前往挑战」根本不会再出现，上面那个「没有关卡」的判断
    会一直命中 —— 但它不是全关打完。所以 hard_mode 下这个判断累计命中
    _HARD_LAST_STAGE_HITS 次（hard_no_stage，跨轮累加）就改点
    「主线困难最后一关.png」进关，点完回同一个判断重判一次，正常往下走去打。
    第 1 次命中仍按普通逻辑回主界面重开一轮。

    困难最后一关打完实测不播剧情（第 8b 步的「主线跳过」不会出现）、也不出
    「获得物品」，左下角退出结算（第 8 步）就是这一关的终点：直接回主界面重开一轮
    （下一轮进新章节），不像普通关那样回 4b 重进关卡 —— 那样会又认出
    「主线困难最后一关」再打一遍。回去时连续计数清零，按原来的逻辑从头数。

    参数 character_name / difficulty / streak 只为对齐 CharacterList.vue 的调用约定
    （统一传 3 个参数），主线目前一次只打一关，这三个值只用于日志。
    double_stamina：体力不足时是否自动兑换体力（对应 UI 的「是否自动使用体力」勾选框）。
    """
    hwnd = bot.game_window.hwnd
    bot._running = True
    try:
        bot._log('=' * 40)
        bot._log(f'主线开始{(" → " + character_name) if character_name else ""}'
                 f'{(" · 体力不足自动兑换" if double_stamina else " · 体力不足即停止")}')
        bot._log('=' * 40)

        # === 主循环：一轮 = 回主界面 → 开主线 → 选章节 ===
        # 一轮里能连打多关：每关打完（获得物品）只回到「进关卡」重进，不回主界面重选章节。
        # 只有两种情况回主界面重开一轮：
        #   1) 进关卡后「主线跳过」和「主线前往挑战」都没出现 = 这关没有关卡可打
        #   2) 打出「主线章节完成」= 本章通了
        # 结束条件：连续 _MAX_NO_STAGE_STREAK 次命中 (1) → 全关打完。
        # 单次没出现可能只是卡顿/切屏，要连续命中才敢收工。
        all_cleared = False
        no_stage_streak = 0
        # 困难模式下「没有关卡」的累计命中次数。放在函数级、不放进循环里：
        # 第 1 次命中是回主界面重开一轮的，计数必须跨轮累加才到得了 _HARD_LAST_STAGE_HITS。
        # hard_mode 每轮在第 3 步重新判定，所以不用在这儿初始化。
        hard_no_stage = 0
        for cycle_no in range(1, _MAX_STAGE_ENTRY_ROUNDS + 1):
            if not bot.is_running:
                bot._log('收到停止请求，退出主线循环')
                break

            bot._log(f'--- 第 {cycle_no} 轮 ---')

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

            # === 3. 点主线入口 ===
            bot._log('点击主线入口...')
            pos = wait_for_image(bot, _ztpl('主线入口.png'))
            if pos is None:
                return False
            post_click(hwnd, pos[0], pos[1])

            # 进来后先认一下困难模式，这 5s 顺便当原来那个「等章节界面加载」用
            # （wait_for_image 找到了就提前返回，没找到就等到超时，耗时和原来一致）。
            # 每轮重新判、不做成粘性：回主界面重开一轮之后会进新章节，新章节不一定还是
            # 困难模式，粘住会把普通章节也当困难走。
            hard_mode = wait_for_image(
                bot, _ztpl('主线困难模式.png'), timeout=5) is not None
            if hard_mode:
                bot._log('识别到「主线困难模式」，本轮按困难模式走')

            # === 4. 点窗口中心选章节 ===
            _click_center(bot, hwnd, '选章节')
            time.sleep(3)

            # === 关卡循环：这一轮里连打多关，每关都从「进关卡」开始 ===
            # 打完一关只回到这里重进下一关，不回主界面重选章节。
            chapter_done = False
            # 这一场是从「主线困难最后一关」进来的（打完不播剧情，收尾要走回主界面那条路）
            hard_last_stage = False
            # 困难最后一关收尾 = 回主界面重开一轮（和 chapter_done 一样出关卡循环）
            back_to_menu = False
            for stage_no in range(1, _MAX_STAGE_CLEAR_ROUNDS + 1):
                if not bot.is_running:
                    bot._log('收到停止请求，退出主线关卡循环')
                    break

                bot._log(f'--- 第 {cycle_no} 轮 · 第 {stage_no} 关 ---')

                # === 4b. 进关卡 ===
                _click_center(bot, hwnd, '进关卡')

                # 进关卡后出现「前置关卡判断」= 这关是困难模式，
                # 真正的入口不在「主线横坐标定位」的位置上，改点客户区横向 1/5、纵向正中。
                # 这里只影响这一次点击的位置，不去动 hard_mode 那个标记
                # （hard_mode 只由第 3 步的「主线困难模式.png」决定）。
                #
                # 没用 wait_for_image：它命中后要 sleep(0.15) 再确认一次，这个弹窗一闪就没，
                # 二次确认反而会把真的命中判成「丢失」丢掉。_wait_best_of 是单帧匹配、
                # 没有二次确认，再把采样间隔缩到 0.1s，才抓得住。
                if _wait_best_of(bot, ['前置关卡判断.png'],
                                 timeout=5, interval=_POPUP_POLL_INTERVAL) is not None:
                    bot._log('识别到「前置关卡判断」，困难模式，改点横向 1/5 处...')
                    _click_at_ratio(bot, hwnd, 1 / 5, '困难模式进关卡')
                    time.sleep(6)
                else:
                    time.sleep(4)

                # --- 跳过剧情 ---
                pos_skip = wait_for_image(bot, _ztpl('主线跳过.png'), timeout=10)
                if pos_skip is not None:
                    bot._log('跳过剧情...')
                    post_click(hwnd, pos_skip[0], pos_skip[1])
                    time.sleep(6)
                else:
                    bot._log('未出现跳过剧情')

                # --- 跳过剧情和两个「主线前往挑战」都没出现 = 这关没有关卡可打 ---
                # 这个判断必须排在下面「获得物品」之前：已通关的关卡重进不会再播剧情
                # （不出「主线跳过」），所以不能只看跳过；但两个都没出现时连奖励也没有，
                # 此时「获得物品」一定不出现，先判它是安全的，不会把已通关的关误判成全关结束。
                no_stage = _no_stage_left(bot, pos_skip)

                # 困难模式：这个判断累计命中 2 次 = 打到困难模式最后一关了。
                # 那一关「主线前往挑战」不会再出现，得换点「主线困难最后一关」进关。
                # 第 1 次命中按普通逻辑回主界面重开一轮，计数跨轮累加，所以这里用的是
                # 函数级的 hard_no_stage，而不是本轮内会清零的 no_stage_streak。
                if no_stage and hard_mode:
                    hard_no_stage += 1
                    bot._log(f'[WARN] 困难模式没有关卡（累计 {hard_no_stage} 次）')
                    if hard_no_stage >= _HARD_LAST_STAGE_HITS:
                        pos_last = wait_for_image(
                            bot, _ztpl('主线困难最后一关.png'), timeout=10)
                        if pos_last is None:
                            bot._log('[WARN] 没找到「主线困难最后一关.png」，按没关卡兜底')
                        else:
                            bot._log('困难模式最后一关，点击进入...')
                            post_click(hwnd, pos_last[0], pos_last[1])
                            time.sleep(6)
                            # 回到本步重判一次（pos_skip 一定还是 None，上面就是这么进来的）：
                            # 点对了这一场该有的按钮就会重新出现，正常往下走去打。
                            # 还没出来也不死循环 —— 交给下面的「没关卡」兜底。
                            no_stage = _no_stage_left(bot, pos_skip)
                            if not no_stage:
                                bot._log('「主线前往挑战」已出现，继续打这一场')
                                # 记下「这一场是从最后一关进来的」：它打完不会播剧情，
                                # 收尾方式也和普通关不一样（见第 9 步）。
                                hard_last_stage = True

                if no_stage:
                    no_stage_streak += 1
                    bot._log(
                        f'[WARN] 没有关卡（连续 {no_stage_streak}/{_MAX_NO_STAGE_STREAK}）')
                    if no_stage_streak >= _MAX_NO_STAGE_STREAK:
                        bot._log('[OK] 全关挑战结束完成')
                        all_cleared = True
                        break
                    bot._log('回主界面重来...')
                    # 出关卡循环 → 外层下一轮就是「回主界面」
                    break

                # 这关有关卡可打，连续计数清零
                no_stage_streak = 0
                hard_no_stage = 0

                # --- 识别到「获得物品」= 这关已经打完了 → 重进关卡打下一关 ---
                if wait_for_image(bot, _stpl('获得物品.png'), timeout=5) is not None:
                    exit_battle(bot, 30, 30)
                    if hard_last_stage:
                        # 兜底：困难最后一关正常打完是不出「获得物品」的（走不到这儿），
                        # 万一认到残留的奖励图标，也不能当「还有下一关」继续 ——
                        # 那样会又认出「主线困难最后一关」再打一遍。回主界面重开一轮。
                        bot._log('困难模式最后一关已通关，回主界面重开一轮...')
                        back_to_menu = True
                        break
                    bot._log('这关已通关，进下一关...')
                    continue

                # --- 5~9. 这一关一直打到出「获得物品」为止 ---
                # 没等到「获得物品」说明这关还有下一场，回「主线前往挑战」重打一遍。
                for round_no in range(1, _MAX_REWARD_ROUNDS + 1):
                    # --- 5. 点「主线前往挑战」---
                    # 体力够 / 不够是两个长得很像的按钮，同帧识别、比置信度取高的那个。
                    # 不能「先找有体力的，找不到再找没体力的」——那样两边会互相误匹配。
                    bot._log(
                        f'点击主线前往挑战...（第 {cycle_no} 轮 · 第 {stage_no} 关 · 第 {round_no} 场）')
                    found = _wait_best_of(
                        bot, ['主线前往挑战.png', '主线前往挑战无体力.png'])
                    if found is None:
                        bot._log(f'[WARN] 第 {round_no} 场：没找到「主线前往挑战」，重试...')
                        continue
                    fx, fy, fname, fconf = found
                    bot._log(f'点击 {fname}（置信度 {fconf:.2%}）')
                    post_click(hwnd, fx, fy)
                    time.sleep(2)

                    # 点到的是「无体力」那个 —— 但先别急着兑换，这不一定是真没体力：
                    # 用掉体力之后这个按钮的图标有缓存，明明体力够、已经进关卡了，
                    # 它还是显示成「无体力」。所以先看一眼 F战斗：出来了就是已经在打。
                    if fname == '主线前往挑战无体力.png':
                        if wait_for_image(bot, 'F战斗.png', timeout=6) is not None:
                            bot._log('检测到 F战斗：「无体力」只是按钮缓存，已经在关卡里，直接开打')
                        else:
                            # 弹出「兑换稳定值」才说明确实体力不足；没弹出来就当下一次重试。
                            pos_exchange = wait_for_image(
                                bot, _ztpl('兑换稳定值.png'))
                            if pos_exchange is None:
                                bot._log(
                                    f'[WARN] 第 {round_no} 场：没弹出「兑换稳定值」，重试...')
                                continue

                            if not double_stamina:
                                bot._log('[FAIL] 体力不足，且未勾选「是否自动使用体力」，结束主线')
                                return False

                            bot._log('体力不足，自动兑换体力...')
                            post_click(hwnd, pos_exchange[0], pos_exchange[1])
                            time.sleep(1)

                            pos_confirm = wait_for_image(
                                bot, _ztpl('确定体力兑换.png'))
                            if pos_confirm is None:
                                bot._log('[WARN] 没找到「确定体力兑换」，兑换可能没生效')
                            else:
                                post_click(
                                    hwnd, pos_confirm[0], pos_confirm[1])
                                time.sleep(1)

                            exit_battle(bot, 30, 30, single_click=True)
                            # 回到本场开头重来：兑换完体力够了，「主线前往挑战」应该能出来了
                            continue

                    # --- 6. 点 F战斗 开打（点完查手动）---
                    if not _click_f_battle(bot, hwnd):
                        return False

                    # --- 7. 等本场战斗结束 ---
                    if not _wait_battle_end(
                            bot, f'（第 {cycle_no} 轮 · 第 {stage_no} 关 · 第 {round_no} 场）'):
                        return False

                    # --- 8. 左下角退出结算 ---
                    # 战斗刚结束这一下最容易丢点击（跑久了更明显），所以用带校验的版本：
                    # 点完「战斗统计」还在就补点。实现在 battle_common。
                    exit_battle_verified(bot, _SETTLEMENT_MARK, 30, 30)

                    if hard_last_stage:
                        # 困难模式最后一关实测：打完不播剧情（下面 8b 的「主线跳过」不出现），
                        # 也**不出「获得物品」**，左下角退出结算就是这一关的终点。
                        # 所以这里直接回主界面重开一轮（下一轮进新章节），不能像普通关那样
                        # 回 4b 重进关卡 —— 那样会又认出「主线困难最后一关」再打一遍。
                        bot._log('困难模式最后一关打完，回主界面重开一轮...')
                        back_to_menu = True
                        break

                    # --- 8b. 可能是本章最后一场：退出结算后才播收尾剧情，出「主线跳过」---
                    # 顺序是先退出结算、再认「主线跳过」—— 收尾剧情在结算界面之后才播。
                    pos_skip_end = wait_for_image(
                        bot, _ztpl('主线跳过.png'), timeout=8)
                    if pos_skip_end is not None:
                        bot._log('出现跳过剧情，可能是本章最后一场...')
                        post_click(hwnd, pos_skip_end[0], pos_skip_end[1])
                        time.sleep(3)
                        if wait_for_image(bot, _ztpl('主线章节完成.png')) is not None:
                            bot._log('本章完成，退出回主界面...')
                            exit_battle(bot, 30, 30)
                            chapter_done = True
                            break
                        bot._log('没出现章节完成，不是最后一场，继续...')
                    else:
                        bot._log('未出现跳过剧情，不是最后一场')

                    # --- 9. 出「获得物品」→ 单次退出，本关结束，重进关卡打下一关 ---
                    pos = wait_for_image(bot, _stpl('获得物品.png'), timeout=5)
                    if pos is not None:
                        bot._log('检测到获得物品，退出...')
                        exit_battle_verified(
                            bot, _SETTLEMENT_MARK, 30, 30, single_click=True)
                        time.sleep(2)
                        break
                    bot._log(f'第 {round_no} 场：没出「获得物品」，回「主线前往挑战」再打一场...')
                else:
                    bot._log(
                        f'[WARN] 第 {stage_no} 关打了 {_MAX_REWARD_ROUNDS} 场都没出「获得物品」，重进关卡...')

                # 本章通了 / 困难最后一关打完 → 出关卡循环，外层下一轮回主界面开下一章
                if back_to_menu:
                    # 上一章的困难最后一关结束了，连续计数清零，接着按原来的逻辑走：
                    # 下一轮进的是新章节，「没有关卡」从头开始数。
                    no_stage_streak = 0
                    hard_no_stage = 0
                if chapter_done or back_to_menu:
                    break
            else:
                bot._log(
                    f'[WARN] 第 {cycle_no} 轮连打 {_MAX_STAGE_CLEAR_ROUNDS} 关还没通本章，回主界面重来')

            # 全关打完 → 连外层主循环一起停
            if all_cleared:
                break
        else:
            bot._log(f'[WARN] 跑满 {_MAX_STAGE_ENTRY_ROUNDS} 轮都没结束，兜底退出')

        if not all_cleared:
            bot._log('[OK] 主线循环结束')
        bot._log('=' * 40)
        return True
    finally:
        bot._running = False
