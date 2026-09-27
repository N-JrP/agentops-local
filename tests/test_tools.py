from backend.tools.knowledge_tool import search_knowledge
from backend.tools.log_tool import search_logs
from backend.tools.metrics_tool import get_checkout_metrics
from backend.tools.sql_tool import get_order_stats


def test_metrics_shape():
    metrics = get_checkout_metrics()
    assert metrics["payment_error_rate"] == 8.7
    assert metrics["average_api_latency_ms"] == 1450


def test_sql_stats():
    stats = get_order_stats()
    assert stats == {"total_orders": 6, "failed_orders": 3}


def test_log_search_is_specific():
    rows = search_logs("PaymentGatewayTimeout")
    assert len(rows) == 2
    assert all("PaymentGatewayTimeout" in row for row in rows)
    assert all("ConnectionTimeout" not in row for row in rows)


def test_knowledge_retrieval():
    section = search_knowledge("PaymentGatewayTimeout troubleshooting")
    assert "PAYMENT GATEWAY TIMEOUT" in section
    assert "Check payment API latency" in section
