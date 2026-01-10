import os
import re
from typing import Optional, List, Tuple, Dict, Any

import numpy as np
import cv2
import easyocr
import dateparser
from rapidfuzz import process, fuzz

from receipt_story.models.schemas import ReceiptExtraction

# NOTE: EasyOCR model load is expensive; keep a singleton reader.
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


def _resize(img, scale: float):
    if scale == 1.0:
        return img
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)


def _sharpen(gray):
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]], dtype=np.float32)
    return cv2.filter2D(gray, -1, kernel)


def _preprocess_variants(img_bgr) -> List[Tuple[str, np.ndarray]]:
    """
    Return multiple preprocessed images; receipts vary a lot.
    We try a few variants and later pick the best based on extraction score.
    """
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray_dn = cv2.bilateralFilter(gray, 9, 75, 75)

    variants = []

    th_adapt = cv2.adaptiveThreshold(
        gray_dn, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 31, 10
    )
    variants.append(("adaptive", th_adapt))
    variants.append(("adaptive_x2", _resize(th_adapt, 2.0)))

    _, th_otsu = cv2.threshold(gray_dn, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", th_otsu))

    th_otsu_x2 = _resize(th_otsu, 2.0)
    variants.append(("otsu_x2_sharp", _sharpen(th_otsu_x2)))

    gray_x2 = _resize(gray_dn, 2.0)
    variants.append(("gray_x2_sharp", _sharpen(gray_x2)))

    return variants


def _ocr_read(reader, img) -> Tuple[str, float]:
    """
    Returns: (raw_text, avg_confidence)
    Sort by y-position so lines come out top-to-bottom.
    """
    allow = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$€£.,:/-#()@% "
    results = reader.readtext(img, detail=1, paragraph=False, allowlist=allow)

    cleaned = []
    confs = []

    for bbox, text, conf in results:
        t = (text or "").strip()
        if not t:
            continue
        ys = [pt[1] for pt in bbox]
        y = float(min(ys)) if ys else 0.0
        cleaned.append((y, t))
        try:
            confs.append(float(conf))
        except Exception:
            pass

    cleaned.sort(key=lambda x: x[0])
    raw_text = "\n".join([t for _, t in cleaned])
    avg_conf = sum(confs) / len(confs) if confs else 0.0
    return raw_text, avg_conf


def _normalize_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _normalize_merchant_text(s: str) -> str:
    s = (s or "").upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)
    s = _normalize_spaces(s)
    return s


def _detect_currency(lines: List[str]) -> str:
    """
    Very small heuristic: default USD, detect CAD/EUR/GBP if explicitly present.
    """
    blob = " ".join(lines).upper()

    if " CAD" in blob or "CANADIAN DOLLAR" in blob or "(CAD)" in blob:
        return "CAD"
    if " USD" in blob or "(USD)" in blob:
        return "USD"
    if " EUR" in blob or "€" in blob:
        return "EUR"
    if " GBP" in blob or "£" in blob:
        return "GBP"

    if " HST" in blob or " GST" in blob or " PST" in blob:
        return "CAD"

    return "USD"


# ---------- MONEY PARSING ----------

_MONEY_TOKEN_RE = re.compile(
    r"""
    (?<!\d)
    (?:[$€£]\s*)?
    (
        \d{1,3}(?:,\d{3})+(?:\.\d{2})
        |
        \d+(?:\.\d{2})
        |
        \d{1,3}(?:\.\d{3})+(?:,\d{2})
        |
        \d+(?:,\d{2})
    )
    (?!\d)
    """,
    re.VERBOSE
)

_MONEY_AT_END_RE = re.compile(
    r"""
    (?:[$€£]\s*)?
    (
        \d{1,3}(?:,\d{3})+(?:\.\d{2})
        |
        \d+(?:\.\d{2})
        |
        \d{1,3}(?:\.\d{3})+(?:,\d{2})
        |
        \d+(?:,\d{2})
    )
    \s*$
    """,
    re.VERBOSE
)


def _money_to_float(token: str) -> Optional[float]:
    t = (token or "").strip()

    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t and "." not in t:
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")

    try:
        return float(t)
    except Exception:
        return None


def _parse_money_candidates(line: str) -> List[float]:
    s = (line or "").strip()
    s = re.sub(r"(?<=\d)[Oo](?=\d)", "0", s)

    vals: List[float] = []
    for m in _MONEY_TOKEN_RE.findall(s):
        v = _money_to_float(m)
        if v is not None:
            vals.append(v)
    return vals


def _parse_money_at_end(line: str) -> Optional[float]:
    s = (line or "").strip()
    s = re.sub(r"(?<=\d)[Oo](?=\d)", "0", s)

    m = _MONEY_AT_END_RE.search(s)
    if not m:
        return None
    return _money_to_float(m.group(1))


def _infer_total_from_max_money(lines: List[str]) -> Tuple[Optional[float], Optional[str]]:
    """
    If label-based TOTAL search fails, infer total as the max money amount
    near the bottom of the receipt (last ~25 lines).
    This avoids grabbing phone numbers because we only parse money-shaped tokens.
    """
    best_v = None
    best_ln = None
    for ln in lines[-25:]:
        v = _parse_money_at_end(ln)
        if v is None:
            vals = _parse_money_candidates(ln)
            v = vals[-1] if vals else None
        if v is not None:
            if best_v is None or v > best_v:
                best_v = v
                best_ln = ln
    return best_v, best_ln


# ---------- KEYWORD SEARCH ----------

def _compile_label_patterns(labels: List[str]) -> List[re.Pattern]:
    pats = []
    for lab in labels:
        lab = lab.strip().lower()
        parts = [re.escape(p) for p in lab.split()]
        regex = r"\b" + r"\s+".join(parts) + r"\b"
        pats.append(re.compile(regex, re.IGNORECASE))
    return pats


def _find_value_by_labels(
    lines: List[str],
    labels: List[str],
    lookahead: int = 2,
    forbid_labels: Optional[List[str]] = None,
) -> Tuple[Optional[float], Optional[str]]:
    forbid_labels = forbid_labels or []
    label_pats = _compile_label_patterns(labels)
    forbid_pats = _compile_label_patterns(forbid_labels) if forbid_labels else []

    def forbidden(ln: str) -> bool:
        return any(p.search(ln) for p in forbid_pats)

    for i, ln in enumerate(lines):
        if forbidden(ln):
            continue

        if any(p.search(ln) for p in label_pats):
            v_end = _parse_money_at_end(ln)
            if v_end is not None:
                return v_end, ln

            vals = _parse_money_candidates(ln)
            if vals:
                return vals[-1], ln

            for j in range(1, lookahead + 1):
                if i + j < len(lines):
                    ln2 = lines[i + j]
                    v2_end = _parse_money_at_end(ln2)
                    if v2_end is not None:
                        return v2_end, ln2
                    vals2 = _parse_money_candidates(ln2)
                    if vals2:
                        return vals2[-1], ln2

    return None, None


def _parse_date(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
    patterns = [
        re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        re.compile(r"(\d{4}[/-]\d{1,2}[/-]\d{1,2})"),
    ]

    def to_iso(tok: str) -> Optional[str]:
        dt = dateparser.parse(tok, settings={"PREFER_DATES_FROM": "past"})
        if not dt:
            return None
        if dt.year < 2000 or dt.year > 2100:
            return None
        return dt.date().isoformat()

    for i, ln in enumerate(lines):
        lo = ln.lower()
        if "date" in lo or "time" in lo or "issued" in lo:
            for pat in patterns:
                m = pat.search(ln)
                if m:
                    iso = to_iso(m.group(1))
                    if iso:
                        return iso, ln
            if i + 1 < len(lines):
                ln2 = lines[i + 1]
                for pat in patterns:
                    m2 = pat.search(ln2)
                    if m2:
                        iso = to_iso(m2.group(1))
                        if iso:
                            return iso, ln2

    found = []
    for ln in lines:
        for pat in patterns:
            m = pat.search(ln)
            if m:
                iso = to_iso(m.group(1))
                if iso:
                    found.append((iso, ln))
    if found:
        found.sort(key=lambda x: x[0])
        return found[-1][0], found[-1][1]

    return None, None


def _load_known_merchants() -> List[str]:
    base = [
        "UBER",
        "COSTCO WHOLESALE", "COSTCO",
        "WHOLE FOODS", "TRADER JOE", "SAFEWAY", "WALMART", "TARGET",
        "STARBUCKS", "PEETS", "CVS", "WALGREENS",
        "SHELL", "CHEVRON",
    ]

    path = os.getenv("RECEIPT_STORY_MERCHANTS_PATH")
    if not path:
        return base

    try:
        if os.path.exists(path):
            extra = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    t = line.strip()
                    if t and not t.startswith("#"):
                        extra.append(t.upper())
            merged = []
            seen = set()
            for m in base + extra:
                if m not in seen:
                    merged.append(m)
                    seen.add(m)
            return merged
    except Exception:
        pass

    return base


def _extract_merchant(lines: List[str]) -> Tuple[str, float, Optional[str]]:
    known = _load_known_merchants()
    header = " ".join(lines[:12]) if lines else ""
    header_n = _normalize_merchant_text(header)

    for m in known:
        m_n = _normalize_merchant_text(m)
        if m_n and m_n in header_n:
            return m, 100.0, header

    match = process.extractOne(header_n, known, scorer=fuzz.WRatio)
    if match and match[1] >= 82:
        return match[0], float(match[1]), header

    for ln in lines[:8]:
        ln_n = _normalize_merchant_text(ln)
        if len(ln_n) >= 3 and not any(w in ln_n for w in ["RECEIPT", "INVOICE", "THANK YOU"]):
            return ln.strip()[:80], 0.0, ln

    merchant = lines[0][:80] if lines else "UNKNOWN"
    return merchant, 0.0, lines[0] if lines else None


def _sane_money(x: Optional[float]) -> Optional[float]:
    if x is None:
        return None
    if x < 0 or x > 1_000_000:
        return None
    return float(x)


def _heuristic_parse(raw_text: str, avg_conf: float, variant_name: str) -> Tuple[ReceiptExtraction, float, Dict[str, Any]]:
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    currency = _detect_currency(lines)

    merchant, mscore, merchant_ev = _extract_merchant(lines)

    # TOTAL: prioritize explicit invoice-style totals
    total, total_ev = _find_value_by_labels(
        lines,
        labels=["overall total", "grand total", "amount due", "total due", "balance due"],
        lookahead=2,
    )
    if total is None:
        total, total_ev = _find_value_by_labels(
            lines,
            labels=["total"],
            lookahead=2,
            forbid_labels=["subtotal", "total number of items", "total items", "total tax"],
        )

    # If still missing, infer from max amount near bottom
    total_inferred = False
    if total is None:
        inferred_total, inferred_ln = _infer_total_from_max_money(lines)
        if inferred_total is not None:
            total = inferred_total
            total_ev = inferred_ln
            total_inferred = True

    # SUBTOTAL
    subtotal, subtotal_ev = _find_value_by_labels(lines, labels=["subtotal", "sub total"], lookahead=2)

    # TAX
    tax, tax_ev = _find_value_by_labels(
        lines,
        labels=["tax", "sales tax", "hst", "gst", "pst", "vat", "total tax"],
        lookahead=2,
        forbid_labels=["total", "subtotal"],
    )

    # DATE
    date_iso, date_ev = _parse_date(lines)

    # Gas receipt heuristic
    looks_like_gas = any("price/gal" in ln.lower() or "pump" in ln.lower() for ln in lines)
    if looks_like_gas and subtotal is None and total is not None:
        subtotal = float(total)
        subtotal_ev = total_ev

    total = _sane_money(total)
    subtotal = _sane_money(subtotal)
    tax = _sane_money(tax)

    # Grounding: total should not be < subtotal
    if total is not None and subtotal is not None and total + 0.01 < subtotal:
        subtotal = None
        subtotal_ev = None

    evidence_lines = []
    if merchant_ev:
        evidence_lines.append("merchant_evidence: " + merchant_ev[:140])
    if total_ev:
        evidence_lines.append("total_evidence: " + total_ev[:140])
    if total_inferred:
        evidence_lines.append("total_inferred: True")
    if subtotal_ev:
        evidence_lines.append("subtotal_evidence: " + subtotal_ev[:140])
    if tax_ev:
        evidence_lines.append("tax_evidence: " + tax_ev[:140])
    if date_ev:
        evidence_lines.append("date_evidence: " + date_ev[:140])

    debug_prefix = f"[ocr_variant={variant_name} avg_conf={avg_conf:.2f} merchant_score={mscore:.0f} currency={currency}]\n"
    debug_prefix += "\n".join(evidence_lines) + "\n\n" if evidence_lines else "\n\n"

    extraction = ReceiptExtraction(
        merchant=merchant,
        date=date_iso,
        currency=currency,
        subtotal=subtotal,
        tax=tax,
        tip=None,
        total=float(total) if total is not None else 0.0,
        items=[],
        raw_text=(debug_prefix + raw_text)[:8000],
        category="Other",
    )

    score = 0.0
    score += avg_conf * 10.0
    score += (1.0 if total is not None else 0.0) * 10.0
    score += (1.0 if subtotal is not None else 0.0) * 3.0
    score += (1.0 if tax is not None else 0.0) * 2.0
    score += (1.0 if date_iso is not None else 0.0) * 3.0
    score += (mscore / 100.0) * 4.0

    meta: Dict[str, Any] = {
        "avg_conf": float(avg_conf),
        "raw_text": raw_text,
        "raw_text_len": len(raw_text),
        "variant_name": variant_name,
        "merchant_score": float(mscore),
        "currency": currency,
        "parse_score": float(score),
        "merchant_evidence": merchant_ev,
        "total_evidence": total_ev,
        "total_inferred": bool(total_inferred),
        "subtotal_evidence": subtotal_ev,
        "tax_evidence": tax_ev,
        "date_evidence": date_ev,
    }

    return extraction, score, meta


class EasyOCRExtractor:
    def extract_with_meta(self, image_bytes: bytes, mime_type: str) -> Tuple[ReceiptExtraction, Dict[str, Any]]:
        img = _bytes_to_cv2(image_bytes)
        reader = get_reader()

        variants = _preprocess_variants(img)

        best_extraction: Optional[ReceiptExtraction] = None
        best_score = -1e9
        best_meta: Dict[str, Any] = {}

        for name, proc in variants:
            raw_text, avg_conf = _ocr_read(reader, proc)
            if not raw_text.strip():
                continue

            extraction, score, meta = _heuristic_parse(raw_text, avg_conf, name)

            if score > best_score:
                best_score = score
                best_extraction = extraction
                best_meta = meta

        if best_extraction is None:
            failed = ReceiptExtraction(
                merchant="UNKNOWN",
                date=None,
                currency="USD",
                subtotal=None,
                tax=None,
                tip=None,
                total=0.0,
                items=[],
                raw_text="[ocr_failed] no text extracted",
                category="Other",
            )
            meta = {
                "ocr_failed": True,
                "avg_conf": 0.0,
                "raw_text": "",
                "raw_text_len": 0,
                "variant_name": None,
                "merchant_score": 0.0,
                "currency": "USD",
                "parse_score": 0.0,
            }
            return failed, meta

        best_meta = dict(best_meta)
        best_meta["ocr_failed"] = False
        best_meta["best_score"] = float(best_score)

        return best_extraction, best_meta

    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        extraction, _meta = self.extract_with_meta(image_bytes, mime_type=mime_type)
        return extraction