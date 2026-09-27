import re
import sqlite3
from pathlib import Path

DB_PATH = Path("data/agentops.db")


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL
            )
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if count == 0:
            connection.executemany(
                "INSERT INTO orders (id, status) VALUES (?, ?)",
                [
                    (1001, "failed"),
                    (1002, "failed"),
                    (1003, "failed"),
                    (1004, "success"),
                    (1005, "success"),
                    (1006, "success"),
                ],
            )
        connection.commit()


def get_order_stats() -> dict:
    initialize_database()

    with sqlite3.connect(DB_PATH) as connection:
        total_orders = connection.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]
        failed_orders = connection.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?", ("failed",)
        ).fetchone()[0]

    return {
        "total_orders": total_orders,
        "failed_orders": failed_orders,
    }


def query_orders(
    *,
    status: str | None = None,
    order_id: int | None = None,
    limit: int = 50,
) -> dict:
    """Run a safe read-only, parameterized query over the fixture orders table."""
    initialize_database()

    if status is not None and status not in {"failed", "success"}:
        raise ValueError("status must be 'failed' or 'success'")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    where: list[str] = []
    params: list[object] = []

    if status:
        where.append("status = ?")
        params.append(status)
    if order_id is not None:
        where.append("id = ?")
        params.append(order_id)

    clause = f" WHERE {' AND '.join(where)}" if where else ""
    sql = f"SELECT id, status FROM orders{clause} ORDER BY id LIMIT ?"
    params.append(limit)

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(sql, params).fetchall()

    return {
        "filters": {"status": status, "order_id": order_id, "limit": limit},
        "matching_order_count": len(rows),
        "orders": [{"id": row[0], "status": row[1]} for row in rows],
        "stats": get_order_stats(),
    }


def query_orders_from_text(tool_input: str) -> dict:
    """Translate a constrained natural-language request into safe SQL filters."""
    text = (tool_input or "").lower()
    status = None
    if "failed" in text:
        status = "failed"
    elif "success" in text or "successful" in text:
        status = "success"

    order_match = re.search(r"(?:order(?:_id)?\s*[=:]?\s*)(\d{3,})", text)
    order_id = int(order_match.group(1)) if order_match else None

    # If the request is only for aggregate counts, preserve the original compact shape.
    if order_id is None and any(
        phrase in text
        for phrase in (
            "how many total",
            "total order count",
            "how many failed",
            "failed order count",
        )
    ):
        return get_order_stats()

    return query_orders(status=status, order_id=order_id)
