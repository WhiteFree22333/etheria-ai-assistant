"""
开发启动脚本
Usage:
    python scripts/run.py              # 启动桌面 GUI
    python scripts/run.py --cli         # CLI 模式
    python scripts/run.py --capture     # 截图并保存
    python scripts/run.py --find ICON   # 查找图标
    python scripts/run.py --click ICON  # 查找并点击图标
"""
import sys
import os

# 修复 Windows DPI 缩放导致的坐标偏移（必须在所有 import 之前）
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def main():
    args = sys.argv[1:]

    if '--cli' in args:
        run_cli()
    elif '--capture' in args:
        run_capture()
    elif '--find' in args:
        idx = args.index('--find')
        template_name = args[idx + 1] if idx + 1 < len(args) else None
        run_find(template_name)
    elif '--click' in args:
        idx = args.index('--click')
        template_name = args[idx + 1] if idx + 1 < len(args) else None
        run_click(template_name)
    else:
        run_gui()


def run_gui():
    """启动桌面 GUI"""
    from ui.app import run
    run()


def run_cli():
    """命令行交互模式"""
    from core._common.bot import GameBot
    from core._base.window import get_all_windows

    print("=" * 50)
    print("🎮 游戏 AI 助手 - CLI 模式")
    print("=" * 50)

    bot = GameBot()

    # 列出所有窗口
    print("\n当前可见窗口:")
    for i, (hwnd, title) in enumerate(get_all_windows()[:15], 1):
        print(f"  {i}. {title}")

    # 查找游戏窗口
    if not bot.init():
        kw = input("\n输入窗口标题关键词（留空退出）: ").strip()
        if kw:
            bot = GameBot(window_keyword=kw)
            if not bot.init():
                print("仍未找到游戏窗口")
                return
        else:
            return

    print("\n命令:")
    print("  screenshot  - 截取并保存游戏画面")
    print("  find <文字> - OCR 查找文字位置")
    print("  click <文字> - 点击文字")
    print("  template <名称> - 查找图标模板位置")
    print("  tclick <名称> - 查找图标并点击")
    print("  quit        - 退出")

    while True:
        try:
            cmd = input("\n> ").strip()
            if not cmd:
                continue

            parts = cmd.split(maxsplit=1)
            action = parts[0].lower()

            if action == 'quit':
                break
            elif action == 'screenshot':
                path = bot.save_screenshot()
                if path:
                    print(f"截图已保存: {path}")
            elif action == 'find':
                if len(parts) > 1:
                    pos = bot.click_text(parts[1])  # 只查找不实际点击... 实际上会点击
                    # 更好的体验: 用 OCR 查找
                    from core._base.ocr import create_ocr_engine, find_text
                    screenshot = bot.capture()
                    if screenshot:
                        engine = create_ocr_engine()
                        pos = find_text(engine, screenshot, parts[1])
                        if pos:
                            abs_x = bot.game_window.left + pos[0]
                            abs_y = bot.game_window.top + pos[1]
                            print(f"找到文字 '{parts[1]}' 位置: ({abs_x}, {abs_y})")
                        else:
                            print(f"未找到文字: '{parts[1]}'")
            elif action == 'click':
                if len(parts) > 1:
                    bot.click_text(parts[1])
            elif action == 'template':
                if len(parts) > 1:
                    tpl = parts[1]
                    if not tpl.endswith('.png'):
                        tpl += '.png'
                    template_path = os.path.join(BASE_DIR, 'templates', tpl)
                    pos = bot.find_image_position(template_path)
                    if pos:
                        print(f"找到图标 '{tpl}' 位置: ({pos[0]}, {pos[1]})")
                    else:
                        print(f"未找到图标: '{tpl}'")
            elif action == 'tclick':
                if len(parts) > 1:
                    tpl = parts[1]
                    if not tpl.endswith('.png'):
                        tpl += '.png'
                    template_path = os.path.join(BASE_DIR, 'templates', tpl)
                    ok = bot.click_image(template_path)
                    print("已点击" if ok else "未找到图标")
            else:
                print(f"未知命令: {action}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"错误: {e}")


def run_capture():
    """快速截图"""
    from core._common.bot import GameBot
    bot = GameBot()
    if bot.init():
        path = bot.save_screenshot()
        if path:
            print(f"截图已保存: {path}")
    else:
        print("未找到游戏窗口")


def run_find(template_name: str = None):
    """查找图标"""
    if template_name is None:
        template_name = input("模板文件名: ").strip()

    if not template_name.endswith('.png'):
        template_name += '.png'

    from core._common.bot import GameBot
    bot = GameBot()
    if not bot.init():
        print("未找到游戏窗口")
        return

    template_path = os.path.join(BASE_DIR, 'templates', template_name)
    if not os.path.exists(template_path):
        print(f"模板不存在: {template_path}")
        return

    pos = bot.find_image_position(template_path)
    if pos:
        print(f"找到图标，屏幕坐标: ({pos[0]}, {pos[1]})")
    else:
        print("未找到匹配图标")


def run_click(template_name: str = None):
    """查找并点击图标"""
    if template_name is None:
        template_name = input("模板文件名: ").strip()

    if not template_name.endswith('.png'):
        template_name += '.png'

    from core._common.bot import GameBot
    bot = GameBot()
    if not bot.init():
        print("未找到游戏窗口")
        return

    template_path = os.path.join(BASE_DIR, 'templates', template_name)
    if not os.path.exists(template_path):
        print(f"模板不存在: {template_path}")
        return

    ok = bot.click_image(template_path)
    print("已点击" if ok else "未找到匹配图标")


if __name__ == '__main__':
    main()
