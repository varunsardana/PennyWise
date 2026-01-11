#!/usr/bin/env python3
import argparse
import random
import sqlite3
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Your app categories (must match categorize.py)
CATEGORIES = ["Coffee", "Groceries", "Dining", "Gas", "Shopping", "Health", "Other"]

# Use merchants that your categorize.py recognizes (including your new Dining rules)
MERCHANTS = [
    # Coffee
    ("STARBUCKS", "Coffee", 4.25, 9.50, 4),
    ("PEETS", "Coffee", 4.00, 9.00, 2),

    # Dining (you said you added these)
    ("CHIPOTLE", "Dining", 12.50, 24.00, 2),
    ("MCDONALD", "Dining", 6.50, 14.00, 1),
    ("SUBWAY", "Dining", 8.00, 16.00, 1),

    # Groceries
    ("TRADER JOE", "Groceries", 35.00, 95.00, 1),
    ("SAFEWAY", "Groceries", 45.00, 120.00, 1),
    ("COSTCO", "Groceries", 60.00, 180.00, 1),

    # Gas
    ("CHEVRON", "Gas", 30.00, 78.00, 1),
    ("SHELL", "Gas", 28.00, 75.00, 1),

    # Shopping
    ("TARGET", "Shopping", 12.00, 90.00, 1),
    ("WALMART", "Shopping", 10.00, 85.00, 1),

    # Health
    ("CVS", "Health", 6.00, 45.00, 1),
    ("WALGREENS", "Health", 6.00, 45.00, 1),
]

def money(x: float) -> float:
    return round(x + 1e-9, 2)

def iso_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def iso_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def pick_total(min_v: float, max_v: float, week_index: int, category: str, trend: bool) -> float:
    base = random.uniform(min_v, max_v)

    # Make Dining/Coffee trend upward over time to produce a rising baseline line
    if trend and category in {"Dining", "Coffee"}:
        # ~ +2% per week
        base *= (1.02 ** week_index)

    return money(base)

def seed(db_path: Path, weeks: int, seed_value: int, tax_rate: float, reset: bool, trend: bool, mult: float):
    random.seed(seed_value)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")

        # Ensure table exists
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='receipts';"
        ).fetchone()
        if not row:
            raise RuntimeError("receipts table not found")

        if reset:
            print("Resetting receipts table (DELETE FROM receipts)...")
            conn.execute("DELETE FROM receipts;")
            conn.commit()

        now = datetime.now()
        start = now - timedelta(weeks=weeks)

        insert_sql = """
        INSERT INTO receipts (id, merchant, date, total, tax, category, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """

        inserted = 0

        for w in range(weeks):
            week_start = start + timedelta(weeks=w)

            for merchant, category, min_v, max_v, weekly_freq in MERCHANTS:
                freq = max(0, int(round(weekly_freq * mult)))
                for _ in range(freq):
                    # pick day in week
                    day_offset = random.randint(0, 6)

                    # Bias coffee/dining to weekdays
                    if category in {"Coffee", "Dining"}:
                        day_offset = random.choice([0, 1, 2, 3, 4, 5])

                    dt = week_start + timedelta(
                        days=day_offset,
                        hours=random.randint(8, 20),
                        minutes=random.randint(0, 59),
                    )

                    total = pick_total(min_v, max_v, w, category, trend)
                    tax = money(total * tax_rate)
                    rid = str(uuid.uuid4())

                    conn.execute(
                        insert_sql,
                        (
                            rid,
                            merchant,
                            iso_date(dt),
                            total,
                            tax,
                            category,
                            iso_datetime(dt),
                        ),
                    )
                    inserted += 1

        conn.commit()
        print(f"✅ Seeded {inserted} receipts into {db_path}")

    finally:
        conn.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/receipts.db")
    ap.add_argument("--weeks", type=int, default=10)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tax", type=float, default=0.0875)
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--no-trend", action="store_true")
    ap.add_argument("--mult", type=float, default=1.0, help="Increase for more receipts (e.g. 1.5)")
    args = ap.parse_args()

    seed(
        db_path=Path(args.db).resolve(),
        weeks=args.weeks,
        seed_value=args.seed,
        tax_rate=args.tax,
        reset=args.reset,
        trend=not args.no_trend,
        mult=args.mult,
    )

if __name__ == "__main__":
    main()

