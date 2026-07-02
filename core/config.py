"""
游戏配置和副本数据
所有可调参数在此集中管理，通过 .env 文件覆盖默认值。
"""
import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class DungeonConfig:
    name: str
    entry_button: str = "凶影追击"
    dungeon_button: str = ""
    start_button: str = "开始挑战"
    auto_button: str = "自动战斗"
    wait_time: float = 30.0


DUNGEONS: Dict[str, DungeonConfig] = {
    "nikenana": DungeonConfig(name="尼可娜娜", dungeon_button="尼可娜娜"),
    "shalun": DungeonConfig(name="莎朗", dungeon_button="莎朗"),
    "heyan": DungeonConfig(name="猎焰者·赫研", dungeon_button="赫研"),
    "lianyujin": DungeonConfig(name="炼狱津", dungeon_button="炼狱津"),
    "keluoluo": DungeonConfig(name="诡饲鸦主·柯洛罗", dungeon_button="柯洛罗"),
    "heerjide": DungeonConfig(name="刺血大公·赫尔基德", dungeon_button="赫尔基德"),
}


# ============================================================
# 全局可调参数
# ============================================================
@dataclass
class GameConfig:
    # ---- 窗口 ----
    window_title_keyword: str = "伊瑟"
    process_name: str = "yise.exe"

    # ---- 模板匹配 ----
    template_threshold: float = 0.75
    multi_scale_default: bool = True

    # ---- 等待/超时 ----
    image_wait_timeout: float = 10       # wait_for_image 默认超时
    image_wait_interval: float = 0.5     # wait_for_image 轮询间隔
    image_gone_timeout: float = 8        # wait_for_image_gone 超时
    image_gone_interval: float = 0.3
    battle_end_timeout: float = 1200      # wait_battle_end 最长等待
    battle_end_interval: float = 2
    preset_load_timeout: float = 15      # setup_preset 等待预设按钮加载
    exit_battle_wait: float = 3          # exit_battle 退出后等待页面切换
    exit_offset_x: int = 30              # 退出按钮 X 偏移
    exit_offset_y: int = 30              # 退出按钮 Y 偏移

    # ---- OCR ----
    ocr_engine: str = "paddle"           # "paddle" | "easyocr"
    blue_dot_rgb: tuple = (0, 255, 246)  # 蓝点检测颜色
    blue_dot_tolerance: int = 10

    # ---- 拖动参数 ----
    drag_px: int = -130
    drag_steps: int = 10
    drag_delay: float = 0.015
    drag_inertia_wait: float = 0.3
    drag_max_rounds: int = 30

    # ---- 点击 ----
    post_click_down_delay: float = 0.06  # post_click 按下等待
    post_click_up_delay: float = 0.03    # post_click 松开等待

    # ---- 窗口缩放 ----
    resize_width: int = 960
    resize_height: int = 540


GAME_CONFIG = GameConfig()


# ============================================================
# .env 加载（覆盖上面的默认值）
# ============================================================
def load_env():
    """从 .env 文件加载配置，覆盖默认值。"""
    try:
        from dotenv import load_dotenv
        load_dotenv()

        # 窗口
        GAME_CONFIG.window_title_keyword = os.getenv(
            "GAME_WINDOW_TITLE", GAME_CONFIG.window_title_keyword)
        GAME_CONFIG.process_name = os.getenv(
            "GAME_PROCESS_NAME", GAME_CONFIG.process_name)

        # 模板匹配
        GAME_CONFIG.template_threshold = float(
            os.getenv("TEMPLATE_THRESHOLD", GAME_CONFIG.template_threshold))

        # 等待
        GAME_CONFIG.battle_end_timeout = int(
            os.getenv("BATTLE_END_TIMEOUT", GAME_CONFIG.battle_end_timeout))
        GAME_CONFIG.exit_battle_wait = float(
            os.getenv("EXIT_BATTLE_WAIT", GAME_CONFIG.exit_battle_wait))

        # OCR
        GAME_CONFIG.ocr_engine = os.getenv(
            "OCR_ENGINE", GAME_CONFIG.ocr_engine)
    except ImportError:
        pass


def get_dungeon_list() -> list:
    return [{"id": did, "name": d.name} for did, d in DUNGEONS.items()]
