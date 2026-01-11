from __future__ import annotations

import base64
import json
import os
from typing import Optional, Any, Dict, List

import dateparser

from receipt_story.models.schemas import ReceiptExtraction


def _extract_json_object(text: str) -> Dict[str, Any]:
    """
    Models sometimes wrap JSON in text. Pull the first {...} block.
    """
    if not text:
        raise ValueError("Empty model response")

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response")

    blob = text[start : end + 1]
    return json.loads(blob)


def _to_float(val: Any) -> Optional[float]:
    """
    Convert model-returned values to float safely.
    Accepts: float/int, "23.16", "$23.16", "23,160.00"
    Returns None if not parseable.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip()
        s = s.replace("$", "").replace("€", "").replace("£", "")
        s = s.replace(",", "")
        # handle parentheses as negative: (12.34)
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        try:
            return float(s)
        except Exception:
            return None
    return None


def _to_iso_date(val: Any) -> Optional[str]:
    """
    Convert model-returned date to YYYY-MM-DD if possible.
    Accepts already-ISO, or common receipt formats like 07/04/2025 2:43 PM.
    """
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        # If it's already YYYY-MM-DD
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            return s[:10]
        dt = dateparser.parse(s)
        return dt.date().isoformat() if dt else None
    return None


def _normalize_currency(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, str):
        s = val.strip().upper()
        if s in {"USD", "CAD", "EUR", "GBP"}:
            return s
        # common symbols
        if "$" in s:
            return "USD"
        return None
    return None


def _normalize_items(items: Any) -> List[Dict[str, Any]]:
    """
    Normalize model-returned items into the schema expected by ReceiptExtraction.

    Your Pydantic schema expects items like:
      {"description": str, "price": float|None, "qty": float|None}

    But the model may return:
      {"name": "...", "price": "...", "qty": "..."}
    """
    if not isinstance(items, list):
        return []

    out: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue

        desc = it.get("description") or it.get("name") or it.get("item") or ""
        desc = str(desc).strip()
        if not desc:
            continue

        price = _to_float(it.get("price"))
        qty = _to_float(it.get("qty"))

        out.append(
            {
                "description": desc[:120],
                "price": price,
                "qty": qty,
            }
        )

    return out


class VisionFallbackExtractor:
    """
    Vision-based extractor that reads the receipt image directly.

    Env vars:
    - OPENAI_API_KEY (required)
    - RECEIPT_VISION_MODEL (optional, default: gpt-4.1-mini)
    """

    def __init__(self) -> None:
        self.model = os.getenv("RECEIPT_VISION_MODEL", "gpt-4.1-mini")

    def extract(
        self, image_bytes: bytes, mime_type: str = "image/png", hint_text: Optional[str] = None
    ) -> ReceiptExtraction:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        # Lazy import so app can still run without openai installed
        from openai import OpenAI

        client = OpenAI(api_key=api_key)

        b64 = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        prompt = """
You are a receipt parser. Read the receipt image and return ONLY a JSON object with this schema:

{
  "merchant": string,
  "date": "YYYY-MM-DD" or null,
  "currency": "USD"|"CAD"|"EUR"|"GBP" or null,
  "subtotal": number or null,
  "tax": number or null,
  "tip": number or null,
  "total": number or null,
  "items": [{"description": string, "price": number|null, "qty": number|null}] (can be []),
  "raw_text": string (short explanation / key evidence lines),
  "category": string or null
}

Rules:
- totals must be realistic; tax should not equal the total unless explicitly shown.
- if unsure, set field to null.
- DO NOT include markdown. DO NOT include code fences. JSON only.
"""

        if hint_text:
            hint = hint_text[:1200]
            prompt += f"\n\nOCR_HINT_TEXT (may be noisy):\n{hint}\n"

        resp = client.responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
        )

        text = getattr(resp, "output_text", None) or ""
        data = _extract_json_object(text)

        # ---- normalize values to match ReceiptExtraction schema ----
        merchant = (data.get("merchant") or "UNKNOWN").strip()[:80]

        date_iso = _to_iso_date(data.get("date"))
        currency = _normalize_currency(data.get("currency")) or "USD"

        subtotal = _to_float(data.get("subtotal"))
        tax = _to_float(data.get("tax"))
        tip = _to_float(data.get("tip"))
        total = _to_float(data.get("total"))

        # ✅ Normalize items so they match schema (description/price/qty)
        items = _normalize_items(data.get("items"))

        raw = (data.get("raw_text") or "").strip()
        raw_text = ("[vision_fallback]\n" + raw)[:8000] if raw else "[vision_fallback]"

        category = (data.get("category") or "Other")

        total_out = float(total) if total is not None else 0.0

        out = ReceiptExtraction(
            merchant=merchant,
            date=date_iso,
            currency=currency,
            subtotal=subtotal,
            tax=tax,
            tip=tip,
            total=total_out,
            items=items,
            raw_text=raw_text,
            category=category,
        )
        return out
