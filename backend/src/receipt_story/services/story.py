def generate_story(insights: dict) -> tuple[list[str], str]:
    spend_by_category = insights.get("spend_by_category", {})
    receipt_count = insights.get("receipt_count", 0)
    total_spend = insights.get("total_spend", 0.0)

    if receipt_count == 0:
        return (["No receipts yet — upload a few to unlock insights."],
                "Start by scanning 2–3 receipts from different places this week.")

    biggest_cat, biggest_amt = None, 0.0
    for cat, amt in spend_by_category.items():
        if amt > biggest_amt:
            biggest_cat, biggest_amt = cat, amt

    insights_list = [
        f"You tracked {receipt_count} receipt(s) with total spend ${total_spend:.2f}.",
    ]
    if biggest_cat:
        pct = (biggest_amt / total_spend * 100) if total_spend > 0 else 0
        insights_list.append(f"Your biggest category is {biggest_cat} at ${biggest_amt:.2f} ({pct:.0f}%).")

    if biggest_cat and biggest_cat != "Other":
        rec = f"Try cutting {biggest_cat} by 10% next week — that’s about ${biggest_amt*0.10:.2f} saved."
    else:
        rec = "Try tagging a few more receipts this week to get clearer category trends."

    return (insights_list[:2], rec)
