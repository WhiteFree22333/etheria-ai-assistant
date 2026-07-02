"""
OCR 文字识别 - 支持 PaddleOCR 和 EasyOCR
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple

import numpy as np
from PIL import Image


@dataclass
class TextMatch:
    """文字识别结果"""
    text: str
    confidence: float
    center_x: int
    center_y: int
    # 原始包围盒（四个角点）
    box: list = None


class PaddleOCREngine:
    """PaddleOCR 引擎（中文识别效果好）"""

    def __init__(self):
        self._ocr = None

    def _ensure_loaded(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang='ch')

    def recognize(self, image: Image.Image) -> List[TextMatch]:
        """识别图像中的文字"""
        self._ensure_loaded()

        img_array = np.array(image)
        result = self._ocr.ocr(img_array)

        if not result or not result[0]:
            return []

        texts = []
        for line in result[0]:
            box = line[0]
            text = line[1][0]
            confidence = line[1][1]

            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            center_x = int(sum(x_coords) / 4)
            center_y = int(sum(y_coords) / 4)

            texts.append(TextMatch(
                text=text,
                confidence=confidence,
                center_x=center_x,
                center_y=center_y,
                box=box,
            ))

        return texts


class EasyOCREngine:
    """EasyOCR 引擎（更轻量，不需要 PaddlePaddle）"""

    def __init__(self):
        self._reader = None

    def _ensure_loaded(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

    def recognize(self, image: Image.Image) -> List[TextMatch]:
        """识别图像中的文字"""
        self._ensure_loaded()

        img_array = np.array(image)
        result = self._reader.readtext(img_array)

        texts = []
        for detection in result:
            box = detection[0]
            text = detection[1]
            confidence = detection[2]

            x_coords = [p[0] for p in box]
            y_coords = [p[1] for p in box]
            center_x = int(sum(x_coords) / 4)
            center_y = int(sum(y_coords) / 4)

            texts.append(TextMatch(
                text=text,
                confidence=confidence,
                center_x=center_x,
                center_y=center_y,
                box=box,
            ))

        return texts


def create_ocr_engine(engine_type: str = "paddle"):
    """
    创建 OCR 引擎

    Args:
        engine_type: "paddle" 或 "easyocr"
    """
    if engine_type == "easyocr":
        return EasyOCREngine()
    return PaddleOCREngine()


def find_text(
    engine,
    image: Image.Image,
    target_text: str,
) -> Optional[Tuple[int, int]]:
    """
    在图像中查找目标文字，返回中心坐标

    Args:
        engine: PaddleOCREngine 或 EasyOCREngine
        image: PIL Image
        target_text: 要查找的文字

    Returns:
        (center_x, center_y) 或 None
    """
    matches = engine.recognize(image)
    for m in matches:
        if target_text in m.text:
            return (m.center_x, m.center_y)
    return None
