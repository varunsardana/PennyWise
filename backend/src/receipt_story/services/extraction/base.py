from abc import ABC, abstractmethod
from receipt_story.models.schemas import ReceiptExtraction

class ReceiptExtractor(ABC):
    @abstractmethod
    def extract(self, image_bytes: bytes, mime_type: str) -> ReceiptExtraction:
        raise NotImplementedError
