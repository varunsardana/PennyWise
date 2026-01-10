import numpy as np
import cv2
import easyocr
from receipt_story.models.schemas import ReceiptExtraction

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader

def _bytes_to_cv2(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes")
    return img

def _preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10)
    return th

def _heuristic_parse(raw_text: str) -> ReceiptExtraction:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    merchant = lines[0][:80] if lines else "UNKNOWN"

    import re
    money = []
    for ln in lines:
        nums = re.findall(r"\b\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{2})\b", ln)
        for n in nums:
            v = n.replace(",", "")
            try:
                money.append(float(v))
            except:
                pass

    total = max(money, default=0.0)

    date = None
    try:
        import dateparser
        for ln in lines[:12]:
            dt = dateparser.parse(ln, settings={"PREFER_DATES_FROM": "past"})
            if dt:
                date = dt.date().isoformat()
                break
    except:
        date = None

    return ReceiptExtraction(
        merchant=merchant,
        date=date,
        total=total,
        items=[],
        raw_text=raw_text[:8000],
    )

class EasyOCRExtractor:
    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        img = _bytes_to_cv2(image_bytes)
        proc = _preprocess(img)
        reader = get_reader()
        results = reader.readtext(proc)
        texts = [t[1] for t in results if t[1].strip()]
        raw_text = "\n".join(texts)
        return _heuristic_parse(raw_text)
