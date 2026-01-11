from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any

from receipt_story.models.schemas import ReceiptExtraction


@dataclass
class FallbackDecision:
    should_fallback: bool
    reasons: List[str]
    score: float


def decide_fallback(extraction: ReceiptExtraction, meta: Dict[str, Any]) -> FallbackDecision:
    """
    Decide when OCR result is unreliable enough to trigger Vision fallback.

    Key idea:
    - OCR can be "confident" but still wrong on numbers (missing digits, label confusion).
    - So we add numeric sanity checks, not just avg_conf/text_len.
    """
    reasons: List[str] = []
    score = 0.0

    avg_conf = float(meta.get("avg_conf") or 0.0)
    raw_text_len = int(meta.get("raw_text_len") or 0)
    merchant_score = float(meta.get("merchant_score") or 0.0)

    subtotal = extraction.subtotal
    tax = extraction.tax
    tip = getattr(extraction, "tip", None)
    total = extraction.total

    # ---- OCR quality gates ----
    if avg_conf < 0.45:
        reasons.append(f"low_ocr_conf:{avg_conf:.2f}")
        score += 2.0

    if raw_text_len < 80:
        reasons.append(f"low_text_len:{raw_text_len}")
        score += 1.5

    if merchant_score and merchant_score < 60:
        reasons.append(f"low_merchant_score:{merchant_score:.1f}")
        score += 2.0

    if not extraction.merchant or len(extraction.merchant.strip()) < 2:
        reasons.append("missing_merchant")
        score += 2.0

    if not extraction.date:
        reasons.append("missing_date")
        score += 1.0

    # IMPORTANT:
    # Your OCR extractor sets total=0.0 when not found.
    # So "is None" is not enough; treat 0.0 as missing unless evidence says otherwise.
    total_evidence = meta.get("total_evidence")
    if (total is None) or (float(total) == 0.0 and not total_evidence):
        reasons.append("missing_total")
        score += 3.0

    # ---- Numeric sanity checks (wrong-but-present) ----
    # 1) Total < Subtotal is basically impossible
    if subtotal is not None and total is not None and total > 0:
        if total + 0.01 < subtotal:
            reasons.append("total_lt_subtotal")
            score += 3.0

    # 2) If tax >= total*0.50, that’s almost certainly wrong for normal receipts
    if tax is not None and total is not None and total > 0:
        if tax >= total * 0.50:
            reasons.append("tax_too_high_vs_total")
            score += 3.0

    # 3) If tax > subtotal (common OCR swap symptom) and subtotal exists
    if tax is not None and subtotal is not None and subtotal > 0:
        if tax > subtotal * 0.60:
            reasons.append("tax_too_high_vs_subtotal")
            score += 2.5

    # 4) If subtotal is tiny compared to total, likely missing a digit (2.30 vs 23.16)
    if subtotal is not None and total is not None and total > 0:
        ratio = subtotal / total if total else 0
        if ratio < 0.35:
            reasons.append(f"subtotal_too_small_ratio:{ratio:.2f}")
            score += 2.0

    # 5) If subtotal+tax(+tip) wildly mismatches total
    if subtotal is not None and total is not None and total > 0:
        approx = subtotal + (tax or 0.0) + (tip or 0.0)
        if approx > 0 and abs(total - approx) / approx > 0.20:
            reasons.append("total_mismatch_subtotal_tax")
            score += 2.0

    should_fallback = score >= 3.0
    return FallbackDecision(should_fallback=should_fallback, reasons=reasons, score=score)
