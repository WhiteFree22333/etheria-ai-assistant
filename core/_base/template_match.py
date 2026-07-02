"""
图像模板匹配 - 在游戏画面中查找图标/按钮
"""
from dataclasses import dataclass
from typing import Optional, List

import cv2
import numpy as np
from PIL import Image


def _imread(path: str) -> np.ndarray:
    """
    读取图片文件（支持中文/Unicode 路径）。
    cv2.imread 在 Windows 下不支持中文路径，改用 imdecode。
    """
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


@dataclass
class TemplateMatch:
    """模板匹配结果"""
    x: int          # 匹配中心点 X（相对于截图左上角）
    y: int          # 匹配中心点 Y
    confidence: float  # 匹配置信度 0-1
    width: int      # 模板宽度
    height: int     # 模板高度

    @property
    def center(self) -> tuple:
        return (self.x, self.y)


def match_template(
    screenshot: Image.Image,
    template_path: str,
    threshold: float = 0.8
) -> Optional[TemplateMatch]:
    """
    在截图中查找模板图像

    Args:
        screenshot: PIL Image 截图
        template_path: 模板图片文件路径
        threshold: 匹配阈值 (0-1)，越高越严格

    Returns:
        TemplateMatch 或 None
    """
    template = _imread(template_path)
    if template is None:
        return None

    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    # 如果模板比截图大，无法匹配
    th, tw = template.shape[:2]
    sh, sw = screenshot_cv.shape[:2]
    if th > sh or tw > sw:
        return None

    result = cv2.matchTemplate(screenshot_cv, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        x = max_loc[0] + tw // 2
        y = max_loc[1] + th // 2
        return TemplateMatch(
            x=x, y=y,
            confidence=float(max_val),
            width=tw, height=th,
        )
    return None


def match_template_multi_scale(
    screenshot: Image.Image,
    template_path: str,
    scales: List[float] = None,
    threshold: float = 0.8
) -> Optional[TemplateMatch]:
    """
    多尺度模板匹配（适应不同分辨率）

    Args:
        screenshot: 截图
        template_path: 模板路径
        scales: 缩放比例列表，默认 [0.8, 0.9, 1.0, 1.1, 1.2]
        threshold: 匹配阈值

    Returns:
        最佳匹配结果或 None
    """
    if scales is None:
        scales = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.15, 1.3, 1.42, 1.5, 1.67, 1.7, 2.0, 2.3, 2.67]

    template = _imread(template_path)
    if template is None:
        return None

    screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    th, tw = template.shape[:2]

    best_match = None
    best_confidence = 0.0

    for scale in scales:
        new_w = int(tw * scale)
        new_h = int(th * scale)
        if new_w < 10 or new_h < 10:
            continue

        scaled_template = cv2.resize(template, (new_w, new_h))
        sh, sw = screenshot_cv.shape[:2]
        if new_h > sh or new_w > sw:
            continue

        result = cv2.matchTemplate(
            screenshot_cv, scaled_template, cv2.TM_CCOEFF_NORMED
        )
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_confidence:
            best_confidence = max_val
            best_match = TemplateMatch(
                x=max_loc[0] + new_w // 2,
                y=max_loc[1] + new_h // 2,
                confidence=float(max_val),
                width=new_w,
                height=new_h,
            )

    if best_match and best_match.confidence >= threshold:
        return best_match
    return None


def find_best_match(
    screenshot: Image.Image,
    template_paths: List[str],
    threshold: float = 0.8
) -> Optional[TemplateMatch]:
    """
    从多个模板中找最佳匹配

    Args:
        screenshot: 截图
        template_paths: 多个模板路径（同一图标的不同外观）
        threshold: 匹配阈值

    Returns:
        最佳匹配或 None
    """
    best = None
    best_conf = 0.0

    for path in template_paths:
        match = match_template(screenshot, path, threshold)
        if match and match.confidence > best_conf:
            best = match
            best_conf = match.confidence

    return best
