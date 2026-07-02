"""
区域选取器 - 全屏截图 + 1:1 像素显示，零坐标偏差
"""
import ctypes
import tkinter as tk
from PIL import Image, ImageTk
from typing import Optional

# 修复 Windows DPI 缩放（必须在创建任何窗口之前）
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def select_region_from_fullscreen(screenshot: Image.Image) -> Optional[tuple]:
    """
    全屏截图方案：截取整个屏幕，1:1 显示，鼠标坐标即屏幕坐标。
    返回 (screen_x, screen_y, w, h) — 屏幕绝对坐标。
    """
    root = tk.Tk()
    root.attributes('-fullscreen', True)
    root.attributes('-topmost', True)
    root.config(cursor='crosshair')

    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()

    # 如果截图尺寸和屏幕不一致，缩放到正好铺满屏幕
    img_w, img_h = screenshot.size
    if img_w != sw or img_h != sh:
        display_img = screenshot.resize((sw, sh), Image.LANCZOS)
        scale_x = img_w / sw
        scale_y = img_h / sh
    else:
        display_img = screenshot
        scale_x = 1.0
        scale_y = 1.0

    photo = ImageTk.PhotoImage(display_img)

    canvas = tk.Canvas(root, width=sw, height=sh, highlightthickness=0, bg='black')
    canvas.pack()
    canvas.create_image(0, 0, anchor='nw', image=photo)

    state = {'start_x': 0, 'start_y': 0, 'rect_id': None, 'result': None}

    def on_down(event):
        state['start_x'] = event.x
        state['start_y'] = event.y
        if state['rect_id']:
            canvas.delete(state['rect_id'])
        state['rect_id'] = canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline='#ff00ff', width=2,
        )

    def on_move(event):
        if state['rect_id']:
            canvas.coords(
                state['rect_id'],
                state['start_x'], state['start_y'],
                event.x, event.y,
            )

    def on_up(event):
        x1, y1 = state['start_x'], state['start_y']
        x2, y2 = event.x, event.y
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        w = right - left
        h = bottom - top
        if w >= 10 and h >= 10:
            # 映射回原始截图坐标
            orig_x = int(left * scale_x)
            orig_y = int(top * scale_y)
            orig_w = int(w * scale_x)
            orig_h = int(h * scale_y)
            state['result'] = (orig_x, orig_y, orig_w, orig_h)
            root.quit()

    def on_key(event):
        if event.keysym == 'Escape':
            root.quit()

    canvas.bind('<ButtonPress-1>', on_down)
    canvas.bind('<B1-Motion>', on_move)
    canvas.bind('<ButtonRelease-1>', on_up)
    root.bind('<Escape>', on_key)

    tip = canvas.create_text(
        sw // 2, sh - 24,
        text='拖动鼠标框选图标区域 | ENTER 确认 | ESC 取消',
        fill='#aaaaaa', font=('Microsoft YaHei', 11),
    )

    root.mainloop()
    root.destroy()
    return state['result']
