from backend.tools.sql_tool import query_orders, query_orders_from_text


def test_parameterized_failed_order_filter():
    result = query_orders(status="failed")
    assert result["matching_order_count"] == 3
    assert all(row["status"] == "failed" for row in result["orders"])


def test_specific_order_query_from_text():
    result = query_orders_from_text("show order 1002")
    assert result["matching_order_count"] == 1
    assert result["orders"][0]["id"] == 1002


def test_sql_filter_rejects_unknown_status():
    try:
        query_orders(status="deleted")
    except ValueError as error:
        assert "status" in str(error)
    else:
        raise AssertionError("Expected ValueError")
