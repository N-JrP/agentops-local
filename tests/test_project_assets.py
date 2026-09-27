from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_and_observability_assets_exist():
    required = [
        "Dockerfile",
        "Dockerfile.streamlit",
        "docker-compose.yml",
        ".github/workflows/ci.yml",
        "observability/prometheus.yml",
        "observability/grafana/provisioning/datasources/prometheus.yml",
        "observability/grafana/provisioning/dashboards/agentops.yml",
        "observability/grafana/dashboards/agentops-overview.json",
        "k8s/namespace.yaml",
        "k8s/configmap.yaml",
        "k8s/postgres.yaml",
        "k8s/backend.yaml",
        "k8s/ui.yaml",
        "scripts/finalize.ps1",
        "scripts/k8s_demo.ps1",
    ]
    assert all((ROOT / relative).exists() for relative in required)


def test_portfolio_documentation_assets_exist():
    required = [
        "README.md",
        "docs/architecture.md",
        "docs/agent-flow.md",
        "docs/evaluation.md",
        "docs/failure-recovery.md",
        "docs/observability.md",
        "docs/security.md",
        "docs/kubernetes.md",
        "docs/demo.md",
        "docs/limitations.md",
        "docs/future-work.md",
        "docs/resume-bullets.md",
        "docs/native-tool-calling.md",
        "docs/screenshots/live-verification.png",
        "docs/screenshots/architecture-overview.png",
        "docs/screenshots/observability-dashboard.png",
    ]
    assert all((ROOT / relative).exists() for relative in required)
