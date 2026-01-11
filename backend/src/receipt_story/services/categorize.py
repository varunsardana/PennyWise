import re
from rapidfuzz import process, fuzz

CATEGORIES = ["Coffee", "Groceries", "Dining", "Gas", "Shopping", "Health", "Other"]

MERCHANT_RULES = {
    "STARBUCKS": "Coffee",
    "PEETS": "Coffee",
    "TRADER JOE": "Groceries",
    "WHOLE FOODS": "Groceries",
    "SAFEWAY": "Groceries",
    "COSTCO": "Groceries",
    "CHEVRON": "Gas",
    "SHELL": "Gas",
    "TARGET": "Shopping",
    "WALMART": "Shopping",
    "CVS": "Health",
    "WALGREENS": "Health",
    "CHIPOTLE": "Dining",
    "MCDONALD": "Dining",
    "SUBWAY": "Dining",
}

def normalize_merchant(name: str) -> str:
    n = (name or "").upper()

    # collapse common variants
    n = n.replace("COSTCO WHOLESALE", "COSTCO")

    # strip punctuation
    n = re.sub(r"[^A-Z0-9 ]+", " ", n)

    # remove store numbers like "#0482" (optional)
    n = re.sub(r"#\s*\d+", " ", n)

    # normalize spaces
    n = re.sub(r"\s+", " ", n).strip()
    return n

def categorize(merchant: str) -> str:
    m = normalize_merchant(merchant)

    # direct contains rules first (most grounded)
    for key, cat in MERCHANT_RULES.items():
        if key in m:
            return cat

    # fuzzy match if merchant is noisy
    match = process.extractOne(m, list(MERCHANT_RULES.keys()), scorer=fuzz.WRatio)
    if match and match[1] >= 90:
        return MERCHANT_RULES[match[0]]

    return "Other"
