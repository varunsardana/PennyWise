import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from rapidfuzz import fuzz, process

# Name Suggestion Index (OSM) - huge list of brands/merchants.
# We'll fetch once, cache locally, then use it as our merchant universe.
#
# You can pin to a specific version for stability by setting NSI_URL env var.
# Example default uses jsdelivr npm CDN dist files.
DEFAULT_NSI_URL = (
    "https://cdn.jsdelivr.net/npm/name-suggestion-index/dist/nsi.min.json"
)

CACHE_DIR = Path(os.getenv("RECEIPT_STORY_CACHE_DIR", ".cache")) / "merchant_index"
CACHE_FILE = CACHE_DIR / "nsi.min.json"

# If you want: limit memory/CPU by restricting to certain preset types
# (e.g., only brands likely to appear on receipts). For MVP, keep broad.
ALLOWED_TAG_KEYS = {"brand", "name"}  # prioritize these if present


@dataclass(frozen=True)
class MerchantMatch:
    canonical: str
    score: float
    evidence: str  # the matched candidate string
    tags: Dict[str, str]


_nsi_loaded = False
_candidates: List[str] = []               # normalized candidate strings
_candidate_to_record: Dict[str, MerchantMatch] = {}  # normalized -> record
_bucket_index: Dict[str, List[str]] = {} # first-char bucket -> candidates


def _normalize(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^A-Z0-9 ]+", " ", s)  # remove punctuation
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _download_nsi(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


def _load_nsi_json() -> dict:
    url = os.getenv("NSI_URL", DEFAULT_NSI_URL)

    # Cache strategy:
    # - if cached file exists, use it
    # - else download it
    if not CACHE_FILE.exists():
        _download_nsi(url, CACHE_FILE)

    return json.loads(CACHE_FILE.read_text(encoding="utf-8"))


def _index_candidates(nsi_data: dict) -> None:
    """
    Build a normalized candidate list and a quick bucket index.
    NSI format: { "presets": { "<id>": { "name": "...", "tags": {...}, "terms": [...] } } }
    """
    global _candidates, _candidate_to_record, _bucket_index

    presets = nsi_data.get("presets", {}) or {}

    seen = set()

    for _, preset in presets.items():
        name = preset.get("name") or ""
        tags = preset.get("tags", {}) or {}
        terms = preset.get("terms", []) or []

        # Canonical name choice:
        # - If tags contain brand, use that
        # - else use preset name
        canonical = tags.get("brand") or name
        canonical_norm = _normalize(canonical)
        if not canonical_norm:
            continue

        # Candidate strings:
        # include canonical, preset name, and any terms
        raw_candidates = [canonical, name, *terms]
        for raw in raw_candidates:
            norm = _normalize(raw)
            if not norm:
                continue
            if norm in seen:
                continue
            seen.add(norm)

            # store record under this candidate
            rec = MerchantMatch(
                canonical=canonical_norm,
                score=0.0,  # placeholder; real score decided at match time
                evidence=norm,
                tags=tags,
            )
            _candidate_to_record[norm] = rec

    _candidates = list(_candidate_to_record.keys())

    # Bucket by first character (simple but very effective)
    buckets: Dict[str, List[str]] = {}
    for c in _candidates:
        first = c[0]
        buckets.setdefault(first, []).append(c)

    _bucket_index = buckets


def ensure_loaded() -> None:
    global _nsi_loaded
    if _nsi_loaded:
        return
    nsi = _load_nsi_json()
    _index_candidates(nsi)
    _nsi_loaded = True


def resolve_merchant(
    header_text: str,
    *,
    min_score: float = 85.0,
) -> Optional[MerchantMatch]:
    """
    Resolve merchant from OCR header text using:
      1) substring check against candidates (fast win)
      2) fuzzy match inside a bucket (fast)
      3) fuzzy match full set (fallback)

    Returns MerchantMatch or None.
    """
    ensure_loaded()

    q = _normalize(header_text)
    if not q:
        return None

    # 1) Fast substring pass:
    # If a candidate appears as a full word substring, trust it.
    # This helps for cases like "UBER" or "COSTCO WHOLESALE".
    for token in q.split():
        # very short tokens are noisy
        if len(token) < 3:
            continue
        # check direct candidates by token bucket
        bucket = _bucket_index.get(token[0], [])
        # exact token match
        if token in _candidate_to_record:
            rec = _candidate_to_record[token]
            return MerchantMatch(
                canonical=rec.canonical,
                score=100.0,
                evidence=token,
                tags=rec.tags,
            )
        # substring inside candidates (cheap but useful)
        for cand in bucket:
            if token == cand:
                rec = _candidate_to_record[cand]
                return MerchantMatch(
                    canonical=rec.canonical,
                    score=100.0,
                    evidence=cand,
                    tags=rec.tags,
                )

    # 2) Bucketed fuzzy match (by first char of query)
    bucket = _bucket_index.get(q[0], [])
    if bucket:
        match = process.extractOne(q, bucket, scorer=fuzz.WRatio)
        if match and match[1] >= min_score:
            evidence = match[0]
            base = _candidate_to_record[evidence]
            return MerchantMatch(
                canonical=base.canonical,
                score=float(match[1]),
                evidence=evidence,
                tags=base.tags,
            )

    # 3) Full fuzzy match fallback
    match = process.extractOne(q, _candidates, scorer=fuzz.WRatio)
    if match and match[1] >= min_score:
        evidence = match[0]
        base = _candidate_to_record[evidence]
        return MerchantMatch(
            canonical=base.canonical,
            score=float(match[1]),
            evidence=evidence,
            tags=base.tags,
        )

    return None
