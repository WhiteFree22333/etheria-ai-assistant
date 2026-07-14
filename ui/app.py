"""
游戏 AI 助手 - pywebview 桌面应用
提供原生窗口 + Vue 3 界面
"""
import sys
import os

if getattr(sys, 'frozen', False):
    torch_lib = os.path.join(sys._MEIPASS, 'torch', 'lib')
    if os.path.isdir(torch_lib):
        import ctypes as _ct
        LL = _ct.windll.kernel32.LoadLibraryExW
        print(f'[Preload] torch_lib={torch_lib}')
        ok = 0
        total = 0

        # Step 1: Preload MSVC runtime DLLs from _internal root FIRST.
        # c10.dll, torch_cpu.dll, shm.dll all depend on these, but they
        # live in _internal/ (not torch/lib/), so LOAD_WITH_ALTERED_SEARCH_PATH
        # (0x8) won't find them when loading c10.dll later.
        for dll in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
            fp = os.path.join(sys._MEIPASS, dll)
            if not os.path.isfile(fp):
                continue
            total += 1
            try:
                LL(fp, 0, 0x8)
                ok += 1
                print(f'[Preload] OK {dll}')
            except Exception as e:
                print(f'[Preload] FAIL {dll}: {e}')

        # Step 2: Preload torch DLLs in strict dependency order.
        # deps: libiomp → uv → c10 → torch → torch_global_deps → torch_cpu → shm → torch_python
        torch_order = [
            'libiomp5md.dll', 'libiompstubs5md.dll', 'uv.dll',
            'c10.dll',
            'torch.dll', 'torch_global_deps.dll',
            'torch_cpu.dll',
            'shm.dll',
            'torch_python.dll',
        ]
        for f in torch_order:
            fp = os.path.join(torch_lib, f)
            if not os.path.isfile(fp):
                continue
            total += 1
            try:
                LL(fp, 0, 0x8)
                ok += 1
                print(f'[Preload] OK {f}')
            except Exception as e:
                print(f'[Preload] FAIL {f}: {e}')

        print(f'[Preload] {ok}/{total} DLLs loaded')

        # Step 3: Disable inspect.getsource — PyInstaller rewrites co_filename
        # to bundle paths, so .py files exist and getfile() succeeds. But the
        # real source often spans hundreds of lines, and torch.jit parses it
        # expecting a single function → "Expected a single top-level function".
        # Worse, the line numbers in co_firstlineno don't match the real file.
        # SOLUTION: always return a minimal per-function stub; never call the
        # original. In a frozen app, no one legitimately needs source at runtime.
        import warnings as _w
        _w.filterwarnings('ignore', message=".*pin_memory.*")
        import inspect as _inspect
        _inspect_getfile_orig = _inspect.getfile
        def _patched_getfile(obj):
            try:
                return _inspect_getfile_orig(obj)
            except Exception:
                return '<frozen>'
        def _patched_getsource(obj):
            n = getattr(obj, '__name__', 'unknown')
            return f'def {n}():\n    pass\n'
        def _patched_getsourcelines(obj):
            n = getattr(obj, '__name__', 'unknown')
            return [f'def {n}():\n', '    pass\n'], 1
        def _patched_findsource(obj):
            n = getattr(obj, '__name__', 'unknown')
            return [f'def {n}():\n', '    pass\n'], 1
        _inspect.getsource = _patched_getsource
        _inspect.getfile = _patched_getfile
        _inspect.getsourcelines = _patched_getsourcelines
        _inspect.findsource = _patched_findsource
        print('[Preload] inspect disabled (always stub), warnings filtered')

# 修复 Windows DPI 缩放导致的坐标偏移（必须在所有 GUI 导入之前）
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import json
import base64
import io
import time
import threading
import traceback

# 禁用 PaddlePaddle 的 MKL-DNN 优化
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from PIL import Image
import webview

# 确保 core 模块可导入
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from core._common.bot import GameBot
from core.config import get_dungeon_list, load_env, GAME_CONFIG
from core._base.capture import save_template, capture_mss
from core._base.selector import select_region_from_fullscreen
from core._base.window import GameWindow

# 日志队列 — 后台线程刷新到前端，避免长 API 调用阻塞 evaluate_js 渲染
import queue
_log_queue = queue.Queue()
_log_window_ref = [None]  # 列表包装，线程安全地引用 window 对象

def _log_flusher(window_ref):
    """后台线程：从日志队列取消息，推送到 pywebview 前端。"""
    while True:
        msg = _log_queue.get()
        if msg is None:
            break  # 停止信号
        try:
            window = window_ref[0] if window_ref[0] else None
            if window is not None:
                window.evaluate_js(
                    f'if(window.__vueApp){{window.__vueApp.addLog({json.dumps(msg)});}}'
                    f'else{{console.log("_push_log:",{json.dumps(msg)});}}'
                )
        except Exception:
            pass


class Api:
    """
    Python API 桥接类
    所有公开方法自动暴露给 JavaScript：window.pywebview.api.xxx()
    """

    def __init__(self):
        self.bot: GameBot = None
        self._task_thread = None
        self._window = None

    def set_window(self, window):
        self._window = window
        # 把窗口引用注入 _log_flusher 后台线程
        if _log_window_ref[0] is None:
            _log_window_ref[0] = window
            threading.Thread(target=_log_flusher, args=(_log_window_ref,), daemon=True).start()


    def _push_log(self, message: str):
        """推送日志到 JS 前端（通过后台队列避免阻塞）+ 打印到控制台"""
        try:
            print(f"[Api] {message}")
        except UnicodeEncodeError:
            print(f"[Api] {message.encode('gbk', errors='replace').decode('gbk')}")

        # 推入队列，后台线程异步刷新到前端（不阻塞 API 线程）
        _log_queue.put(message)

        # 错误标记直接弹 alert（需要立即响应，不排队）
        if 'PRESET_MISSING' in message:
            if self._window:
                self._window.evaluate_js(
                    'alert("亲，您没有设置预设阵容哦，请设置后回到主页重新开始。")'
                )
        elif 'STAMINA_MISSING' in message:
            if self._window:
                self._window.evaluate_js(
                    'alert("亲，您的体力不足请先使用体力后再开始哦！")'
                )

    # ==================== 生命周期 ====================

    def check_update(self) -> dict:
        """检查 GitHub Releases 是否有新版本。返回 {has_update, version, url}"""
        from core import __version__
        try:
            import urllib.request, json
            req = urllib.request.Request(
                'https://api.github.com/repos/WhiteFree22333/etheria-ai-assistant/releases/latest',
                headers={'User-Agent': 'remary-assistant'}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
                latest = data.get('tag_name', 'v0.0.0').lstrip('v')
                current = __version__
                has_update = _version_newer(latest, current)
                return {
                    'has_update': has_update,
                    'current': f'v{current}',
                    'latest': data.get('tag_name', ''),
                    'url': data.get('html_url', ''),
                }
        except Exception as e:
            return {'has_update': False, 'error': str(e)}

    def set_server(self, server_key: str) -> dict:
        """
        设置区服，更新游戏窗口搜索关键词。
        server_key: 'cn'(国服) / 'global'(国际服) / 'asia'(东亚服)
        """
        servers = {
            'cn':    {'label': '国服',   'keyword': '伊瑟'},
            'global': {'label': '国际服', 'keyword': 'Etheria'},
            'asia':  {'label': '东亚服', 'keyword': '伊瑟'},
        }
        if server_key not in servers:
            return {"success": False, "message": f"未知区服: {server_key}"}
        info = servers[server_key]
        GAME_CONFIG.window_title_keyword = info['keyword']
        # 初始化 bot 并尝试找到游戏窗口
        if self.bot is None:
            self.bot = GameBot()
            self.bot.on_log(self._push_log)
        self.bot.window_keyword = info['keyword']
        ok = self.bot.init()
        if ok:
            self._push_log(f"已切换区服: {info['label']} ({info['keyword']}) — 找到游戏窗口")
            return {"success": True, "message": f"已选择 {info['label']}"}
        else:
            self._push_log(f"已切换区服: {info['label']}，但未找到窗口 '{info['keyword']}'")
            return {"success": False, "message": f"未找到 '{info['keyword']}' 窗口，请确认游戏中已打开或选择其他区服"}

    def init_assistant(self) -> dict:
        """初始化助手，查找游戏窗口"""
        if self.bot is None:
            load_env()
            self.bot = GameBot()
            self.bot.on_log(self._push_log)

        ok = self.bot.init()
        return {"success": ok, "message": "找到游戏窗口" if ok else "未找到游戏窗口"}

    # ==================== 副本任务 ====================

    def get_dungeons(self) -> list:
        """获取副本列表"""
        dungeons = get_dungeon_list()
        return [
            {"id": d["id"], "name": d["name"], "count": 1, "auto": True}
            for d in dungeons
        ]

    def start_dungeon(self, dungeon_id: str, count: int = 1, auto_fight: bool = True) -> dict:
        """开始副本任务（后台线程执行）"""
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return {"success": False, "message": "未找到游戏窗口"}

        if self.bot.is_running:
            return {"success": False, "message": "任务已在运行中"}

        def task():
            self.bot.run_dungeon(dungeon_id, count, auto_fight)

        self._task_thread = threading.Thread(target=task, daemon=True)
        self._task_thread.start()
        return {"success": True, "message": "任务已开始"}

    def stop_task(self) -> dict:
        """停止当前任务"""
        if self.bot:
            self.bot.stop()
        return {"success": True, "message": "已请求停止"}

    def get_status(self) -> dict:
        """获取运行状态"""
        if self.bot is None:
            return {"running": False, "busy": False}
        return {
            "running": self.bot.is_running,
            "busy": self.bot.is_running,
        }

    # ==================== 图标识别 ====================

    def capture_preview(self) -> str:
        """
        截取游戏画面，返回 base64 编码的 PNG
        """
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return ""

        img = self.bot.capture()
        if img is None:
            return ""

        # 缩小预览图（超过 1200px 宽度时等比缩放）
        if img.width > 1200:
            ratio = 1200 / img.width
            new_size = (1200, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def save_template(
        self, name: str, x: int, y: int, w: int, h: int
    ) -> bool:
        """
        从预览截图中裁剪区域保存为模板

        Args:
            name: 模板名称（不含扩展名）
            x, y, w, h: 裁剪区域（相对于预览图坐标）
        """
        if self.bot is None or self.bot.game_window is None:
            return False

        img = self.bot.capture()
        if img is None:
            return False

        # 如果预览图被缩放过，需要还原坐标
        if img.width > 1200:
            ratio = img.width / 1200
            x = int(x * ratio)
            y = int(y * ratio)
            w = int(w * ratio)
            h = int(h * ratio)

        cropped = img.crop((x, y, x + w, y + h))
        templates_dir = os.path.join(BASE_DIR, 'templates', 'richang')
        filepath = save_template(cropped, name, templates_dir)
        return filepath is not None

    def list_templates(self, subdir: str = '') -> list:
        """列出所有已保存的模板"""
        templates_dir = os.path.join(BASE_DIR, 'templates', subdir) if subdir else os.path.join(BASE_DIR, 'templates', 'richang')
        if not os.path.isdir(templates_dir):
            return []
        return sorted([
            f for f in os.listdir(templates_dir)
            if f.endswith('.png')
        ])

    def select_and_save_template(self, name: str, subdir: str = '') -> dict:
        """
        一键选取图标：全屏截图 → 1:1全屏框选 → 转为游戏窗口坐标 → 保存模板

        Args:
            name: 模板名称（不含扩展名）
            subdir: 子目录，如 'shilian'，留空则存到 templates/

        Returns:
            {"success": bool, "message": str, "filename": str}
        """
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return {"success": False, "message": "未找到游戏窗口"}

        gw = self.bot.game_window

        # 截取整个屏幕（mss monitors[1] = 主显示器）
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]
            full_screenshot = sct.grab(monitor)
            full_img = Image.frombytes(
                "RGB", full_screenshot.size, full_screenshot.bgra, "raw", "BGRX"
            )

        # 全屏框选 → 得到屏幕绝对坐标
        region = select_region_from_fullscreen(full_img)
        if region is None:
            return {"success": False, "message": "已取消选取"}

        screen_x, screen_y, rw, rh = region

        # 转为游戏窗口内相对坐标
        game_x = screen_x - gw.left
        game_y = screen_y - gw.top

        # 从游戏窗口截图中裁剪
        game_img = self.bot.capture()
        if game_img is None:
            return {"success": False, "message": "裁剪截图失败"}

        # 边界检查
        game_x = max(0, game_x)
        game_y = max(0, game_y)
        rw = min(rw, game_img.width - game_x)
        rh = min(rh, game_img.height - game_y)

        if rw <= 0 or rh <= 0:
            return {"success": False, "message": "选取区域不在游戏窗口内"}

        cropped = game_img.crop((game_x, game_y, game_x + rw, game_y + rh))
        templates_dir = os.path.join(BASE_DIR, 'templates', subdir) if subdir else os.path.join(BASE_DIR, 'templates', 'richang')
        os.makedirs(templates_dir, exist_ok=True)
        filepath = save_template(cropped, name, templates_dir)

        return {
            "success": True,
            "message": f"模板已保存: {name}.png ({rw}×{rh})",
            "filename": f"{name}.png",
            "region": [game_x, game_y, rw, rh],
        }

    def find_image(self, template_name: str) -> list:
        """
        查找图标位置

        Returns:
            [x, y] 屏幕坐标，或 None
        """
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return None

        template_path = os.path.join(BASE_DIR, 'templates', 'richang', template_name)
        if not os.path.exists(template_path):
            return None

        pos = self.bot.find_image_position(template_path)
        return [pos[0], pos[1]] if pos else None

    def click_image(self, template_name: str) -> bool:
        """查找图标并点击"""
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return False

        template_path = os.path.join(BASE_DIR, 'templates', 'richang', template_name)
        if not os.path.exists(template_path):
            return False

        return self.bot.click_image(template_path)

    def go_back_to_main(self, back_template: str = "返回.png", max_retries: int = 5) -> bool:
        """
        如果画面中有返回按钮，点击它直到回到主界面。

        Args:
            back_template: 返回按钮模板文件名
            max_retries: 最多点击几次

        Returns:
            True 表示至少点击了一次，False 表示本来就在主界面
        """
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return False

        template_path = os.path.join(BASE_DIR, 'templates', 'richang', back_template)
        if not os.path.exists(template_path):
            print(f"[Api] 模板不存在: {template_path}")
            return False
        return self.bot.go_back_to_main(template_path, max_retries)

    def run_zhike_battle(self, character_name: str, difficulty: str = '炼狱', streak: int = 1) -> bool:
        """
        执行智壳战斗流程。

        调用 core/zhike_battle.py 中的完整流程：
        主页 → Tab侧边栏 → 挑战 → 智壳掉落 → 滚轮翻角色 → 选难度 → 设次数 → 确认
        """
        print(f"[Api] run_zhike_battle 被调用，角色: {character_name}, 难度: {difficulty}, 场次: {streak}")
        print(f"[Api] self.bot = {self.bot}")

        if self.bot is None:
            print("[Api] bot 为空，正在初始化...")
            result = self.init_assistant()
            print(f"[Api] init_assistant 结果: {result}")
            if not result["success"]:
                print(f"[Api] 初始化失败: {result.get('message')}")
                self._push_log(f"初始化失败: {result.get('message')}")
                return False
            print("[Api] 初始化成功")

        print("[Api] 正在导入 zhike_battle 模块...")
        try:
            from core.daily.zhike_battle import run_zhike_battle
        except Exception as e:
            print(f"[Api] 导入失败: {e}")
            import traceback
            traceback.print_exc()
            self._push_log(f"模块导入失败: {e}")
            return False

        print(f"[Api] 开始执行战斗流程...")
        try:
            ok = run_zhike_battle(self.bot, character_name, difficulty, streak)
            print(f"[Api] 战斗流程返回: {ok}")
            return ok
        except Exception as e:
            print(f"[Api] 战斗流程异常: {e}")
            import traceback
            traceback.print_exc()
            self._push_log(f"战斗流程异常: {e}")
            return False

    def run_yuanqi_battle(self, character_name: str, difficulty: str = '地狱四', streak: int = 1, double_stamina: bool = False) -> bool:
        """执行源器战斗流程。"""
        print(f"[Api] run_yuanqi_battle 被调用，角色: {character_name}, 双倍: {double_stamina}")
        if self.bot is None:
            result = self.init_assistant()
            if not result["success"]:
                return False
        from core.daily.yuanqi_battle import run_yuanqi_battle
        return run_yuanqi_battle(self.bot, character_name, difficulty, streak, double_stamina)

    # ======== 潜能/经验 ========
    def run_qianneng_battle(self, character_name: str = "", difficulty: str = "", streak: int = 1, double_stamina: bool = False) -> bool:
        """潜能/经验"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.qianneng_battle import run_qianneng_battle
        return run_qianneng_battle(self.bot, character_name, difficulty, streak, double_stamina)

    # ======== 公会/竞技场 ========
    def run_guild_arena(self) -> bool:
        """竞技场自动"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_arena
        return run_guild_arena(self.bot)

    def run_guild_signin(self) -> bool:
        """公会签到"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_signin
        return run_guild_signin(self.bot)

    def run_guild_anchor(self) -> bool:
        """锚点勘测"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_anchor
        return run_guild_anchor(self.bot)

    def run_guild_weekly(self) -> bool:
        """公会每周任务领取"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_weekly
        return run_guild_weekly(self.bot)

    def run_guild_assist(self) -> bool:
        """协会共助"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_assist
        return run_guild_assist(self.bot)

    # ======== 活动 ========
    def run_anlong_battle(self, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
        """暗笼激斗"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.events.anlong_battle import run_anlong_battle
        return run_anlong_battle(self.bot, character_name, difficulty, streak)

    def run_chaoneng_battle(self, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
        """超能二十一"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.events.chaoneng_battle import run_chaoneng_battle
        return run_chaoneng_battle(self.bot, character_name, difficulty, streak)

    def run_yuanwang_battle(self, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
        """源网征令"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.events.yuanwang_battle import run_yuanwang_battle
        return run_yuanwang_battle(self.bot, character_name, difficulty, streak)

    def run_xujin_battle(self, character_name: str = '', difficulty: str = '普通', streak: int = 1) -> bool:
        """虚烬探索"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.events.xujin_battle import run_xujin_battle
        return run_xujin_battle(self.bot, character_name, difficulty, streak)

    def run_guild_remind(self) -> bool:
        """提醒成员签到"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_remind
        return run_guild_remind(self.bot)

    def resize_game_window(self, width: int = 960, height: int = 540) -> dict:
        """调整游戏窗口到指定尺寸，放置到屏幕左上角。"""
        print("[Api] resize_game_window called", width, height)
        if self.bot is None:
            if not self.init_assistant().get('success'):
                print("[Api] init_assistant failed")
                return {"success": False, "message": "未找到游戏窗口"}
        # 重新搜索游戏窗口——游戏重启后旧句柄会失效
        self.bot.init()
        if self.bot.game_window is None:
            print("[Api] game_window is None")
            return {"success": False, "message": "游戏窗口未找到"}
        import win32gui, win32con
        hwnd = self.bot.game_window.hwnd
        print(f"[Api] hwnd={hwnd}")
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetWindowPos(hwnd, 0, 0, 0, width, height,
                              win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW)
        # 缩放后再次刷新缓存坐标
        self.bot.init()
        print(f"[Api] SetWindowPos done, window cache refreshed")
        self._push_log(f'游戏窗口已缩放至 {width}×{height}，左上角')
        return {"success": True, "message": f"缩放至 {width}x{height}"}

    def test_stamina_check(self) -> bool:
        """测试：体力库存识别"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_test_stamina_check
        return run_test_stamina_check(self.bot)

    def run_guild_arena_claim(self) -> bool:
        """竞技场一键领取"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_arena_claim
        return run_guild_arena_claim(self.bot)

    def run_guild_anchor_claim(self) -> bool:
        """锚点勘测一键领取"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_anchor_claim
        return run_guild_anchor_claim(self.bot)

    def run_guild_claim_all(self) -> bool:
        """一键领取"""
        if self.bot is None:
            if not self.init_assistant().get('success'): return False
        from core.daily.guild_battle import run_guild_claim_all
        return run_guild_claim_all(self.bot)

    def run_guild_theater(self) -> bool:
        """幻音剧场"""
        if self.bot is None:
            if not self.init_assistant().get("success"): return False
        from core.daily.guild_battle import run_guild_theater
        return run_guild_theater(self.bot)

    def debug_exit_point(self, offset_x: int = 60, offset_y: int = 60) -> str:
        """[开发用] 截图标注退出点击位置，调试坐标时使用"""
        import base64, io, cv2, numpy as np
        if self.bot is None:
            r = self.init_assistant()
            if not r['success']:
                return ''
        img = self.bot.capture()
        if img is None:
            return ''
        gw = self.bot.game_window
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        x, y = offset_x, gw.height - offset_y
        cv2.circle(arr, (x, y), 12, (0, 0, 255), 2)
        cv2.circle(arr, (x, y), 4, (0, 0, 255), -1)
        cv2.putText(arr, f'({x},{y})', (x + 18, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1)
        import os as _os
        dd = _os.path.join(BASE_DIR, 'debug_screenshots')
        _os.makedirs(dd, exist_ok=True)
        cv2.imwrite(_os.path.join(dd, f'exit_({x},{y}).png'), arr)
        buf = io.BytesIO()
        cv2.imencode('.png', arr)[1].tofile(buf)
        return base64.b64encode(buf.getvalue()).decode('utf-8')

    def test_background_capture(self) -> str:
        """
        [调试] 用 DXCam / PrintWindow / BitBlt / MSS 四路分别截图，
        保存到 debug_screenshots/，用于验证"游戏窗口被遮挡时还能不能截到"。
        返回四张图的 base64 列表（前端可预览）。
        """
        if self.bot is None:
            r = self.init_assistant()
            if not r['success']:
                self._push_log('[FAIL] 未找到游戏窗口')
                return ''
        import base64 as _b64, io, cv2 as _cv2, numpy as _np, os as _os
        gw = self.bot.game_window
        _dd = _os.path.join(BASE_DIR, 'debug_screenshots')
        _os.makedirs(_dd, exist_ok=True)

        results = {}
        # 1) DXCam
        try:
            from core._base.capture import capture_dxcam
            img = capture_dxcam(gw)
            if img is not None:
                _cv2.imwrite(_os.path.join(_dd, 'bg_test_1_dxcam.png'), _cv2.cvtColor(_np.array(img), _cv2.COLOR_RGB2BGR))
                results['1_dxcam'] = 'OK'
            else:
                results['1_dxcam'] = 'FAIL(None)'
        except Exception as e:
            results['1_dxcam'] = f'FAIL({e})'

        # 2) PrintWindow (PW_RENDERFULLCONTENT)
        try:
            from core._base.capture import capture_printwindow_pca
            img = capture_printwindow_pca(gw.hwnd, gw)
            if img is not None:
                _cv2.imwrite(_os.path.join(_dd, 'bg_test_2_printwindow.png'), _cv2.cvtColor(_np.array(img), _cv2.COLOR_RGB2BGR))
                results['2_printwindow'] = 'OK'
            else:
                results['2_printwindow'] = 'FAIL(None)'
        except Exception as e:
            results['2_printwindow'] = f'FAIL({e})'

        # 3) BitBlt
        try:
            from core._base.capture import capture_bitblt
            img = capture_bitblt(gw.hwnd, gw)
            if img is not None:
                _cv2.imwrite(_os.path.join(_dd, 'bg_test_3_bitblt.png'), _cv2.cvtColor(_np.array(img), _cv2.COLOR_RGB2BGR))
                results['3_bitblt'] = 'OK'
            else:
                results['3_bitblt'] = 'FAIL(None)'
        except Exception as e:
            results['3_bitblt'] = f'FAIL({e})'

        # 4) MSS（前台，会强行 focus 游戏窗口）
        try:
            from core._base.capture import capture_mss
            img = capture_mss(gw)
            if img is not None:
                _cv2.imwrite(_os.path.join(_dd, 'bg_test_4_mss.png'), _cv2.cvtColor(_np.array(img), _cv2.COLOR_RGB2BGR))
                results['4_mss'] = 'OK'
            else:
                results['4_mss'] = 'FAIL(None)'
        except Exception as e:
            results['4_mss'] = f'FAIL({e})'

        self._push_log(f'背景截图测试: {results}')
        self._push_log(f'截图已保存 debug_screenshots/bg_test_*.png — 请在被遮挡+不被遮挡两种情况下各测一次，对比四张图')
        return ''

    def delete_template(self, template_name: str) -> bool:
        """删除模板文件"""
        template_path = os.path.join(BASE_DIR, 'templates', 'richang', template_name)
        if os.path.exists(template_path):
            os.remove(template_path)
            return True
        return False


def on_loaded(*_args):
    """页面加载完成后，注入 Vue 实例引用 + 设置窗口图标"""
    js = """
    setTimeout(() => {
        const app = document.querySelector('#app').__vue_app__;
        if (app) {
            const vm = app._instance.proxy;
            window.__vueApp = vm;
        }
    }, 100);
    """
    try:
        w = webview.windows[0]
        w.evaluate_js(js)
    except Exception:
        pass

    # 设置窗口图标
    import win32gui, win32con
    ico_path = os.path.join(BASE_DIR, 'app.ico')
    if os.path.exists(ico_path):
        try:
            hwnd = win32gui.FindWindow(None, '瑞玛丽小助手V1.0')
            if hwnd:
                big = win32gui.LoadImage(None, ico_path, win32con.IMAGE_ICON, 0, 0,
                    win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
                small = win32gui.LoadImage(None, ico_path, win32con.IMAGE_ICON, 16, 16,
                    win32con.LR_LOADFROMFILE)
                if big: win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, big)
                if small: win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, small)
                print('[App] 窗口图标已设置')
        except Exception as e:
            print(f'[App] 图标设置失败: {e}')
    else:
        print('[App] 未找到 app.ico，使用默认图标')


def _start_hot_reload(window, static_dir: str):
    """
    启动热更新监控线程。

    每隔 1 秒检查 static/ 目录下的文件有没有变动。
    如果发现 HTML/CSS/JS 文件被修改，立刻刷新页面。

    就像保安巡逻一样，检查文件是不是被改过了。
    """
    # 第一次扫描：记录每个文件当前的修改时间
    last_mtimes = {}
    for root, dirs, files in os.walk(static_dir):
        for f in files:
            filepath = os.path.join(root, f)
            last_mtimes[filepath] = os.path.getmtime(filepath)

    def watch():
        nonlocal last_mtimes
        while True:
            time.sleep(1)  # 每 1 秒巡逻一次
            try:
                # 重新扫描所有文件
                for root, dirs, files in os.walk(static_dir):
                    for f in files:
                        filepath = os.path.join(root, f)
                        old_time = last_mtimes.get(filepath, 0)
                        new_time = os.path.getmtime(filepath)

                        # 修改时间变了 → 文件被改动过！
                        if new_time > old_time:
                            print(f"[热更新] 检测到文件变化: {f}，刷新页面...")
                            last_mtimes[filepath] = new_time
                            # 告诉浏览器：刷新！
                            window.evaluate_js('location.reload()')
                            break  # 一次只刷一次，不用重复刷
            except Exception:
                pass  # 巡逻出错不崩溃，继续检查

    t = threading.Thread(target=watch, daemon=True)
    t.start()


def _is_vite_running() -> bool:
    """检测 Vite 开发服务器是否在运行"""
    import urllib.request
    try:
        urllib.request.urlopen('http://localhost:5173', timeout=1)
        return True
    except Exception:
        return False




def _version_newer(a, b):
    """比较 a >= b，例: _version_newer('1.1.0', '1.0.0') → True"""
    try:
        return tuple(int(x) for x in a.split('.')) >= tuple(int(x) for x in b.split('.'))
    except Exception:
        return False


def run():
    """启动桌面应用"""
    # 告诉 Windows：这不是普通 Python 进程，是独立应用（影响任务栏图标）
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('remary.assistant.v1')

    api = Api()

    # 优先使用 Vite 开发服务器（保存即刷新 HMR），否则用构建好的文件
    if _is_vite_running():
        url = 'http://localhost:5173'
        print('[App] 检测到 Vite 开发服务器，使用 HMR 模式')
    else:
        # PyInstaller 打包后文件在 sys._MEIPASS 里，开发时在 BASE_DIR/ui/static/
        if getattr(sys, 'frozen', False):
            static_dir = os.path.join(sys._MEIPASS, 'ui', 'static')
        else:
            static_dir = os.path.join(BASE_DIR, 'ui', 'static')
        index_path = os.path.join(static_dir, 'index.html')
        _errors = []
        url = ''

        if not os.path.isfile(index_path):
            _errors.append(f'静态文件不存在: {index_path}')
        else:
            # 尝试启动本地 HTTP 服务器避免 file:// 中文路径编码问题
            try:
                import http.server, socket, threading
                _port = None
                for _p in range(49152, 49216):
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.bind(('127.0.0.1', _p))
                            _port = _p
                            break
                    except OSError:
                        continue
                if _port is not None:
                    class _StaticHandler(http.server.SimpleHTTPRequestHandler):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, directory=static_dir, **kwargs)
                    _httpd = http.server.HTTPServer(('127.0.0.1', _port), _StaticHandler)
                    threading.Thread(target=_httpd.serve_forever, daemon=True).start()
                    url = f'http://127.0.0.1:{_port}/index.html'
                else:
                    _errors.append('无法绑定 HTTP 端口')
            except Exception as e:
                _errors.append(f'HTTP 服务器启动失败: {e}')

            # 兜底用 file://
            if not url:
                url = index_path

        # 如果有错误但 file:// 可能能用 → 尝试加载，并注入错误提示
        if _errors:
            _err_html = '<br>'.join(_errors)
            print('[App] 启动警告:', _err_html)
        if not url:
            url = f'data:text/html,<html><body style="background:#1a1a2e;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif"><div style="text-align:center"><h2>⚠️ 加载失败</h2><p>{"<br>".join(_errors)}</p></div></body></html>'

    window = webview.create_window(
        title='瑞玛丽小助手V1.0',
        url=url,
        js_api=api,
        width=980,
        height=780,
        min_size=(800, 600),
        text_select=False,
        confirm_close=True,
    )

    api.set_window(window)

    webview.start(on_loaded, window, debug=('--debug' in sys.argv), gui='edgechromium')


if __name__ == '__main__':
    run()
