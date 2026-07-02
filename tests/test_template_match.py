"""
测试模板匹配功能（第一个功能的核心）

TM_CCOEFF_NORMED 要求模板有纹理变化（不能是纯色），
所以测试图标使用渐变色。
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from PIL import Image

from core._base.template_match import match_template, match_template_multi_scale, TemplateMatch


def _make_gradient_icon(h, w):
    """创建一个有渐变的图标（水平红色渐变），确保有足够的纹理用于模板匹配"""
    icon = np.zeros((h, w, 3), dtype=np.uint8)
    for col in range(w):
        intensity = int(100 + 155 * col / w)  # 100-255
        icon[:, col] = (0, 0, intensity)  # BGR: 蓝色渐变红色
    return icon


def test_match_template_found():
    """测试：模板能在截图中被找到"""
    bg = np.zeros((200, 200, 3), dtype=np.uint8)
    bg[:] = (50, 50, 50)

    # 创建一个有渐变的图标（非纯色）
    th, tw = 30, 40
    icon = _make_gradient_icon(th, tw)
    bg[60:90, 80:120] = icon

    screenshot = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        template_path = f.name
        cv2.imwrite(template_path, icon)

    try:
        result = match_template(screenshot, template_path, threshold=0.9)
        assert result is not None, "Should find the icon"
        # 中心: x = 80 + 40/2 = 100, y = 60 + 30/2 = 75
        assert abs(result.x - 100) <= 2, f"X should be ~100, got: {result.x}"
        assert abs(result.y - 75) <= 2, f"Y should be ~75, got: {result.y}"
        assert result.confidence > 0.95, f"Confidence should be > 0.95, got: {result.confidence}"
        print(f"PASS test_match_template_found: pos=({result.x}, {result.y}), conf={result.confidence:.4f}")
    finally:
        os.unlink(template_path)


def test_match_template_not_found():
    """测试：不存在的图标不应该被找到"""
    bg = np.zeros((200, 200, 3), dtype=np.uint8)
    bg[:] = (50, 50, 50)
    screenshot = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))

    # 不在背景中的图标（白色渐变）
    icon = _make_gradient_icon(30, 30)

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        template_path = f.name
        cv2.imwrite(template_path, icon)

    try:
        result = match_template(screenshot, template_path, threshold=0.9)
        assert result is None, "Should not find non-existent icon"
        print("PASS test_match_template_not_found: returned None")
    finally:
        os.unlink(template_path)


def test_multi_scale_found():
    """测试：多尺度匹配能找到缩放的图标"""
    bg = np.zeros((300, 300, 3), dtype=np.uint8)
    bg[:] = (50, 50, 50)

    icon = _make_gradient_icon(20, 20)
    bg[100:120, 150:170] = icon

    screenshot = Image.fromarray(cv2.cvtColor(bg, cv2.COLOR_BGR2RGB))

    # 模板是 24x24（放大了 1.2 倍）
    icon_large = cv2.resize(icon, (24, 24))

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        template_path = f.name
        cv2.imwrite(template_path, icon_large)

    try:
        result_multi = match_template_multi_scale(
            screenshot, template_path,
            scales=[0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
            threshold=0.8
        )
        assert result_multi is not None, "Multi-scale should find scaled icon"
        assert result_multi.confidence > 0.8
        print(f"PASS test_multi_scale_found: pos=({result_multi.x}, {result_multi.y}), conf={result_multi.confidence:.4f}")
    finally:
        os.unlink(template_path)


if __name__ == '__main__':
    print("=" * 50)
    print("Testing core/template_match.py - icon recognition")
    print("=" * 50)
    test_match_template_found()
    test_match_template_not_found()
    test_multi_scale_found()
    print("\nAll tests passed!")
