from .scoring import parse_weights, score_counts


def empty_counts() -> dict[str, int]:
    return {"Easy": 0, "Medium": 0, "Hard": 0}


def aggregate_rows(rows) -> dict[int, dict[str, int]]:
    agg: dict[int, dict[str, int]] = {}
    for row in rows:
        user_id = row["user_id"] if hasattr(row, "keys") else row[0]
        difficulty = row["difficulty"] if hasattr(row, "keys") else row[1]
        count = row["c"] if hasattr(row, "keys") else row[2]
        agg.setdefault(user_id, empty_counts())
        agg[user_id][difficulty] = count
    return agg


def rank_rows(rows, scoring: str):
    weights = parse_weights(scoring)
    agg = aggregate_rows(rows)
    scored = []
    for user_id, counts in agg.items():
        total = score_counts(counts, weights)
        scored.append(
            {
                "user_id": user_id,
                "total": total,
                "counts": counts,
            }
        )
    scored.sort(
        key=lambda item: (
            -item["total"],
            -item["counts"]["Hard"],
            -item["counts"]["Medium"],
        )
    )
    return scored, weights
