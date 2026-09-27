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
        "docs/screenshots/01_agentops_hero.png",
        "docs/screenshots/02_real_investigation_query.png",
        "docs/screenshots/03_execution_trace.png",
        "docs/screenshots/04_live_github_evidence.png",
        "docs/screenshots/05_validated_answer.png",
        "docs/screenshots/06_observability_llm_runtime.png",
        "docs/screenshots/07_system_architecture.png",
        "docs/screenshots/08_validation_results.png",
    ]
    assert all((ROOT / relative).exists() for relative in required)
