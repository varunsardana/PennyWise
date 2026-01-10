from __future__ import annotations

import os
from typing import Optional

from receipt_story.models.schemas import ReceiptExtraction
from receipt_story.services.extraction.base import Extractor
from receipt_story.services.extraction.ocr_extractor import EasyOCRExtractor
from receipt_story.services.extraction.fallback_decider import decide_fallback
from receipt_story.services.extraction.vision_fallback import VisionFallbackExtractor


class HybridExtractor(Extractor):
    """
    OCR-first extractor with Vision LLM fallback when OCR output looks unreliable.

    Debugging principle:
    - Always leave a "breadcrumb" in raw_text so we can prove which path was used.
    """

    def __init__(
        self,
        ocr: Optional[EasyOCRExtractor] = None,
        vision: Optional[VisionFallbackExtractor] = None,
    ):
        self.ocr = ocr or EasyOCRExtractor()
        self.vision = vision or VisionFallbackExtractor()

    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        force = os.getenv("RECEIPT_FORCE_VISION", "").lower() in {"1", "true", "yes"}

        if force:
            try:
                v = self.vision.extract(image_bytes, mime_type=mime_type, hint_text=None)
                v.raw_text = ("[source=vision_forced]\n" + (v.raw_text or ""))[:8000]
                return v
            except Exception as e:
                # Important: include error message (truncated) to debug quickly
                o = self.ocr.extract(image_bytes, mime_type=mime_type)
                o.raw_text = (
                    f"[source=vision_forced_failed:{type(e).__name__}:{str(e)[:200]}]\n"
                    + (o.raw_text or "")
                )[:8000]
                return o

        # 1) OCR + meta
        extraction, meta = self.ocr.extract_with_meta(image_bytes, mime_type=mime_type)

        # 2) Decide fallback
        decision = decide_fallback(extraction, meta)

        if not decision.should_fallback:
            extraction.raw_text = (
                f"[source=ocr accepted score={decision.score:.1f}]\n"
                + (extraction.raw_text or "")
            )[:8000]
            return extraction

        # 3) Try vision fallback, fail-safe to OCR
        try:
            vlm_extraction = self.vision.extract(
                image_bytes,
                mime_type=mime_type,
                hint_text=meta.get("raw_text", ""),
            )
            vlm_extraction.raw_text = (
                f"[source=vision fallback_score={decision.score:.1f} reasons={','.join(decision.reasons)}]\n"
                + (vlm_extraction.raw_text or "")
            )[:8000]
            return vlm_extraction
        except Exception as e:
            extraction.raw_text = (
                f"[source=ocr fallback_failed:{type(e).__name__}:{str(e)[:200]} "
                f"fallback_score={decision.score:.1f} reasons={','.join(decision.reasons)}]\n"
                + (extraction.raw_text or "")
            )[:8000]
            return extraction
