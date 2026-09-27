EVALUATION_CASES = [
    {
        "name": "payment_gateway_multi_tool",
        "question": (
            "Investigate the PaymentGatewayTimeout incident. "
            "What errors occurred, what operational metrics changed, "
            "and what should an engineer do?"
        ),
        "expected_tools": ["metrics", "logs", "knowledge"],
        "expected_answer_contains": [
            "PaymentGatewayTimeout",
            "2.1",
            "8.7",
            "1450",
            "Check payment API latency",
        ],
    },
    {
        "name": "metrics_only",
        "question": "What operational metrics changed compared with the previous day?",
        "expected_tools": ["metrics"],
        "expected_answer_contains": ["2.1", "3.8", "8.7", "1.2", "1450", "320"],
    },
    {
        "name": "logs_only",
        "question": "What PaymentGatewayTimeout errors occurred in the logs?",
        "expected_tools": ["logs"],
        "expected_answer_contains": ["PaymentGatewayTimeout", "1001", "1002"],
    },
    {
        "name": "knowledge_only",
        "question": "What should an engineer do when investigating PaymentGatewayTimeout?",
        "expected_tools": ["knowledge"],
        "expected_answer_contains": ["Check payment API latency", "Check payment error rate"],
    },
    {
        "name": "sql_total_orders",
        "question": "How many total orders are in the local orders database?",
        "expected_tools": ["sql"],
        "expected_answer_contains": ["6"],
    },
    {
        "name": "sql_failed_orders",
        "question": "How many failed orders are in the local orders database?",
        "expected_tools": ["sql"],
        "expected_answer_contains": ["3"],
    },
    {
        "name": "metrics_and_logs",
        "question": "Show the operational changes and the PaymentGatewayTimeout log errors.",
        "expected_tools": ["metrics", "logs"],
        "expected_answer_contains": ["8.7", "PaymentGatewayTimeout"],
    },
    {
        "name": "logs_and_knowledge",
        "question": "What PaymentGatewayTimeout errors occurred and what should an engineer do?",
        "expected_tools": ["logs", "knowledge"],
        "expected_answer_contains": ["PaymentGatewayTimeout", "Check payment API latency"],
    },
    {
        "name": "unsupported_weather",
        "question": "What is the weather in Berlin today?",
        "expected_tools": [],
        "expected_answer_contains": ["outside the capabilities"],
    },
]
