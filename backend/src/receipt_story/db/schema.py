"""Database schema description optimized for LLM understanding"""

SCHEMA_DESCRIPTION = """
Table: receipts
  - id: TEXT (Primary Key, UUID)
  - merchant: TEXT (Store/merchant name, NOT NULL)
  - date: TEXT (ISO date string YYYY-MM-DD, may be NULL if not found on receipt)
  - total: REAL (Total amount paid, NOT NULL)
  - tax: REAL (Tax amount, may be NULL)
  - category: TEXT (e.g., Coffee, Groceries, Restaurants, Dining, Transportation, NOT NULL)
  - created_at: TEXT (UTC ISO timestamp when receipt was scanned, NOT NULL)

Important notes for querying:
- All dates are stored as ISO strings (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
- Use date() function for date comparisons: date >= date('now', '-30 days')
- Use strftime() for date formatting: strftime('%Y-%m', date) for monthly grouping
- Categories are user-assigned spending categories
- created_at is when the receipt was added to the system
- date is the actual purchase date from the receipt (may be NULL)
- For time-based queries, prefer using 'date' field when available, fallback to 'created_at'

Common query patterns:
- Spending by category: SELECT category, SUM(total) FROM receipts GROUP BY category
- Monthly spending: SELECT strftime('%Y-%m', date) as month, SUM(total) FROM receipts GROUP BY month
- Top merchants: SELECT merchant, COUNT(*) as visits, SUM(total) as spent FROM receipts GROUP BY merchant ORDER BY spent DESC
- Recent receipts: SELECT * FROM receipts WHERE date >= date('now', '-7 days') OR created_at >= date('now', '-7 days')
"""

def get_schema_for_llm() -> str:
    """Returns the database schema description for LLM context"""
    return SCHEMA_DESCRIPTION