from __future__ import annotations
from typing import Any, Dict

from receipt_story.models.schemas import ReceiptExtraction
from receipt_story.services.extraction.fallback_decider import decide_fallback
from receipt_story.services.extraction.vision_fallback import VisionFallbackExtractor


class ReceiptParser:
    def __init__(self, ocr_extractor: Any, vision_extractor: VisionFallbackExtractor | None = None):
        self.ocr_extractor = ocr_extractor
        self.vision_extractor = vision_extractor or VisionFallbackExtractor()

    def parse(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Returns:
          {
            "extraction": ReceiptExtraction,
            "meta": { used_fallback, fallback_reasons, fallback_score, ... }
          }
        """
        ocr_out = self.ocr_extractor.extract(image_bytes)

        extraction: ReceiptExtraction = ocr_out["extraction"]
        metrics: Dict[str, Any] = ocr_out.get("metrics", {})
        raw_text: str = ocr_out.get("raw_text", "")

        decision = decide_fallback(
            extraction,
            {
                **metrics,
                "raw_text_len": len(raw_text),
            },
        )

        response: Dict[str, Any] = {
            "extraction": extraction,
            "meta": {
                "used_fallback": False,
                "fallback_reasons": decision.reasons,
                "fallback_score": decision.score,
                "avg_conf": metrics.get("avg_conf"),
            },
        }

        if not decision.should_fallback:
            return response

        # Try vision fallback
        try:
            vlm_extraction = self.vision_extractor.extract(image_bytes, hint_text=raw_text)
            response["extraction"] = vlm_extraction
            response["meta"]["used_fallback"] = True
        except Exception as e:
            # Fail-safe: return OCR result but keep debug info
            response["meta"]["fallback_error"] = str(e)

        return response
