from rapidfuzz import process, fuzz

MERCHANT_RULES = {
    "STARBUCKS": "Coffee",
    "PEETS": "Coffee",
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
    for ch in [",", ".", "#", "@"]:
        n = n.replace(ch, " ")
    return " ".join(n.split())

def categorize(merchant: str) -> str:
    m = normalize_merchant(merchant)

    for key, cat in MERCHANT_RULES.items():
        if key in m:
            return cat

    match = process.extractOne(m, list(MERCHANT_RULES.keys()), scorer=fuzz.WRatio)
    if match and match[1] >= 85:
        return MERCHANT_RULES[match[0]]

    return "Other"
