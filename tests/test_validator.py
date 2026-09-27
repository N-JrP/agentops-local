from backend.agent.nodes import validate_answer


def test_rejects_unsupported_percent_symbol():
    evidence = {
        "metrics": {"payment_error_rate": 8.7},
        "sql": {},
        "logs": [],
        "knowledge": "",
    }
    valid, issues = validate_answer("Payment error rate was 8.7%", evidence)
    assert valid is False
    assert issues


def test_accepts_exact_identifier():
    evidence = {
        "metrics": {},
        "sql": {},
        "logs": [
            "ERROR PaymentGatewayTimeout order_id=1001 provider=payment-service"
        ],
        "knowledge": "",
    }
    valid, issues = validate_answer(
        "PaymentGatewayTimeout order_id=1001 provider=payment-service",
        evidence,
    )
    assert valid is True
    assert issues == []


def test_accepts_identifier_paraphrase():
    evidence = {
        "metrics": {},
        "sql": {},
        "logs": [
            "ERROR PaymentGatewayTimeout order_id=1001 provider=payment-service"
        ],
        "knowledge": "",
    }
    valid, issues = validate_answer(
        "PaymentGatewayTimeout affected order 1001 from payment-service.",
        evidence,
    )
    assert valid is True
    assert issues == []


def test_rejects_unsupported_canonical_identifier():
    evidence = {
        "metrics": {},
        "sql": {},
        "logs": [
            "ERROR PaymentGatewayTimeout order_id=1001 provider=payment-service"
        ],
        "knowledge": "",
    }
    valid, issues = validate_answer(
        "PaymentGatewayTimeout affected order_id=9999.",
        evidence,
    )
    assert valid is False
    assert "Unsupported identifier in answer: order_id=9999" in issues


def test_rejects_broader_unsupported_numeric_claim():
    evidence = {
        "metrics": {"payment_error_rate": 8.7},
        "sql": {},
        "logs": [],
        "knowledge": "",
        "incidents": [],
    }
    valid, issues = validate_answer("Payment error rate was 8.7 and latency was 9999.", evidence)
    assert valid is False
    assert "Unsupported numeric claim in answer: 9999" in issues


def test_rejects_invented_source_url():
    evidence = {
        "status": {
            "source_url": "https://www.githubstatus.com/api/v2/summary.json",
        },
        "incidents": [],
        "metrics": {},
        "sql": {},
        "logs": [],
        "knowledge": "",
    }
    valid, issues = validate_answer("Source: https://example.invalid/fake", evidence)
    assert valid is False
    assert issues
