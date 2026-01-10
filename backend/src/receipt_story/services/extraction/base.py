# src/receipt_story/services/extraction/base.py

from typing import Protocol
from receipt_story.models.schemas import ReceiptExtraction


class Extractor(Protocol):
    """
    Interface (contract) for receipt extractors.
    Any extractor must implement:
      extract(image_bytes: bytes, mime_type: str) -> ReceiptExtraction
    """

    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        ...
