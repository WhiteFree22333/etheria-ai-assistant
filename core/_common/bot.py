"""
游戏机器人 - 高层任务编排
组合所有 core 模块，提供统一的操作接口
"""
import time
import threading
from typing import Optional, Callable

from PIL import Image

from core._base.window import GameWindow, find_game_window
from core._base.capture import capture_game_screen, save_screenshot, save_template
from core._base.ocr import create_ocr_engine, find_text, PaddleOCREngine, EasyOCREngine
from core._base.template_match import match_template, match_template_multi_scale, TemplateMatch
from core._base.input import click_at, click_window, press_key, move_to, post_click
from core._common.battle_common import tpl
from core.config import DungeonConfig, GAME_CONFIG


class GameBot:
    """游戏自动化机器人"""

    def __init__(self, window_keyword: str = None, ocr_engine: str = None):
        """
        Args:
            window_keyword: 游戏窗口标题关键词
            ocr_engine: OCR 引擎类型 "paddle" 或 "easyocr"
        """
        self.window_keyword = window_keyword or GAME_CONFIG.window_title_keyword
        self._game_window: Optional[GameWindow] = None
        self._ocr_engine = None
        self._ocr_type = ocr_engine or GAME_CONFIG.ocr_engine
        self._running = False
        self._log_callbacks: list[Callable[[str], None]] = []

    # ==================== 生命周期 ====================

    def init(self) -> bool:
        """
        初始化：查找游戏窗口

        Returns:
            是否成功找到游戏窗口
        """
        self._game_window = find_game_window(self.window_keyword)
        if self._game_window:
            self._log(f"找到游戏窗口: {self._game_window.title}")
            return True
        self._log(f"未找到包含 '{self.window_keyword}' 的窗口")
        return False

    @property
    def game_window(self) -> Optional[GameWindow]:
        return self._game_window

    @property
    def is_running(self) -> bool:
        return self._running

    # ==================== 截图 ====================

    def capture(self) -> Optional[Image.Image]:
        """截取游戏画面"""
        if not self._game_window:
            return None
        return capture_game_screen(self._game_window)

    def save_screenshot(self) -> Optional[str]:
        """截取并保存游戏画面，返回文件路径"""
        img = self.capture()
        if img:
            return save_screenshot(img)
        return None

    # ==================== 图标识别与点击 ====================

    def find_image(
        self,
        template_path: str,
        threshold: float = None,
        multi_scale: bool = True,
    ) -> Optional[TemplateMatch]:
        """
        在当前游戏画面中查找图标

        Args:
            template_path: 模板图片路径
            threshold: 匹配置信度阈值
            multi_scale: 是否使用多尺度匹配（默认开启，适应窗口大小变化）

        Returns:
            TemplateMatch 或 None
        """
        threshold = threshold or GAME_CONFIG.template_threshold
        screenshot = self.capture()
        if screenshot is None:
            self._log("截图失败，无法进行模板匹配")
            return None

        if multi_scale:
            result = match_template_multi_scale(screenshot, template_path, threshold=threshold)
        else:
            result = match_template(screenshot, template_path, threshold=threshold)

        if result:
            self._log(f"找到图标 (置信度: {result.confidence:.2%}, 位置: {result.x}, {result.y})")
        else:
            self._log("未找到匹配图标")
        return result

    def click_image(
        self,
        template_path: str,
        threshold: float = None,
        multi_scale: bool = True,
    ) -> bool:
        """
        查找图标并点击

        Args:
            template_path: 模板图片路径
            threshold: 匹配置信度阈值
            multi_scale: 是否使用多尺度匹配（默认开启，适应窗口大小变化）

        Returns:
            是否成功找到并点击
        """
        match = self.find_image(template_path, threshold, multi_scale)
        if match is None:
            return False

        # 转换为屏幕绝对坐标
        abs_x = self._game_window.left + match.x
        abs_y = self._game_window.top + match.y

        self._log(f"点击图标位置: ({abs_x}, {abs_y})")
        # 使用 PostMessage 直接向游戏窗口发送点击，鼠标不移动
        post_click(self._game_window.hwnd, abs_x, abs_y)
        return True

    def find_image_position(
        self,
        template_path: str,
        threshold: float = None,
    ) -> Optional[tuple]:
        """
        查找图标位置（不点击），返回屏幕绝对坐标

        Returns:
            (screen_x, screen_y) 或 None
        """
        match = self.find_image(template_path, threshold)
        if match is None:
            return None

        abs_x = self._game_window.left + match.x
        abs_y = self._game_window.top + match.y
        return (abs_x, abs_y)

    # ==================== 文字识别与点击 ====================

    def _get_ocr(self):
        """懒加载 OCR 引擎"""
        if self._ocr_engine is None:
            self._log(f"初始化 OCR 引擎 ({self._ocr_type})...")
            self._ocr_engine = create_ocr_engine(self._ocr_type)
        return self._ocr_engine

    def click_text(self, text: str) -> bool:
        """
        OCR 识别文字并点击

        Args:
            text: 要查找并点击的文字

        Returns:
            是否成功找到并点击
        """
        screenshot = self.capture()
        if screenshot is None:
            self._log("截图失败")
            return False

        engine = self._get_ocr()
        position = find_text(engine, screenshot, text)
        if position is None:
            self._log(f"未找到文字: '{text}'")
            return False

        abs_x = self._game_window.left + position[0]
        abs_y = self._game_window.top + position[1]

        self._log(f"点击文字 '{text}' 位置: ({abs_x}, {abs_y})")
        click_at(abs_x, abs_y)
        return True

    # ==================== 返回主界面 ====================

    def go_back_to_main(
        self,
        back_template: str = "返回.png",
        max_retries: int = 10,
        threshold: float = None,
    ) -> bool:
        """
        如果画面中有「返回」按钮，点击它返回主界面。
        先识别「返回.png」，没找到则识别「返回2.png」，
        两个都找不到说明已回到主界面。
        多尺度匹配关闭：返回按钮尺寸在游戏中固定不变，单尺度更精准防误匹配。
        """
        back_templates = [back_template, tpl("返回2.png")]
        thr = threshold or 0.82  # 返回按钮特征明显，阈值提到 0.82 防误判
        clicked = False
        for i in range(max_retries):
            match = None
            for tpl_name in back_templates:
                match = self.find_image(tpl_name, thr, multi_scale=False)
                if match is not None:
                    break

            if match is None:
                if i == 0:
                    self._log("已在主界面，无需返回")
                else:
                    self._log(f"已回到主界面（点击了 {i} 次返回）")
                return clicked

            abs_x = self._game_window.left + match.x
            abs_y = self._game_window.top + match.y
            self._log(f"点击返回按钮 ({i+1}/{max_retries}) 位置: ({abs_x}, {abs_y})")
            post_click(self._game_window.hwnd, abs_x, abs_y)
            clicked = True
            time.sleep(0.8)

        self._log(f"警告：点击 {max_retries} 次返回后仍未回到主界面")
        return clicked

    # ==================== 按键 ====================

    def press(self, key: str):
        """按键盘按键"""
        self._log(f"按下按键: {key}")
        press_key(key)

    # ==================== 副本任务 ====================

    def run_dungeon(
        self,
        dungeon_id: str,
        count: int = 1,
        auto_fight: bool = True,
    ):
        """
        执行副本刷图任务（在后台线程中调用）

        Args:
            dungeon_id: 副本 ID
            count: 执行次数
            auto_fight: 是否开启自动战斗
        """
        from core.config import DUNGEONS

        config = DUNGEONS.get(dungeon_id)
        if config is None:
            self._log(f"无效的副本 ID: {dungeon_id}")
            return

        self._running = True
        self._log(f"开始副本: {config.name} (共 {count} 次)")

        try:
            for i in range(count):
                if not self._running:
                    self._log("任务已停止")
                    break

                self._log(f"--- 第 {i+1}/{count} 次 ---")

                # 1. 进入副本入口
                if config.entry_button:
                    self._log(f"点击入口: {config.entry_button}")
                    self.click_text(config.entry_button)
                    time.sleep(2)

                # 2. 选择副本
                if config.dungeon_button:
                    self._log(f"选择副本: {config.dungeon_button}")
                    self.click_text(config.dungeon_button)
                    time.sleep(1.5)

                # 3. 开始挑战
                if config.start_button:
                    self._log(f"开始挑战: {config.start_button}")
                    self.click_text(config.start_button)
                    time.sleep(2)

                # 4. 自动战斗
                if auto_fight and config.auto_button:
                    self._log(f"切换自动战斗: {config.auto_button}")
                    self.click_text(config.auto_button)
                    time.sleep(1)

                # 5. 等待战斗结束
                self._log(f"等待战斗结束 ({config.wait_time}秒)...")
                for _ in range(int(config.wait_time)):
                    if not self._running:
                        break
                    time.sleep(1)

                if not self._running:
                    break

                # 6. 领取奖励
                self._log("领取奖励...")
                self.click_text("确认")
                time.sleep(1)
                self.click_text("领取")
                time.sleep(1)

                # 7. 返回
                self.press("esc")
                time.sleep(1)

            self._log(f"副本 {config.name} 完成")
        except Exception as e:
            self._log(f"执行出错: {e}")
        finally:
            self._running = False

    def stop(self):
        """停止当前任务"""
        self._running = False

    # ==================== 工具方法 ====================

    def on_log(self, callback: Callable[[str], None]):
        """注册日志回调"""
        self._log_callbacks.append(callback)

    def _log(self, message: str):
        try:
            print(f"[Bot] {message}")
        except UnicodeEncodeError:
            print(f"[Bot] {repr(message)}")
        for cb in self._log_callbacks:
            try:
                cb(message)
            except Exception:
                pass
