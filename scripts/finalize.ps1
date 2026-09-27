$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$report = [ordered]@{
    started_at = (Get-Date).ToString("o")
    python_quality = "pending"
    live_source = "pending"
    fastapi = "pending"
    streamlit = "pending"
    mcp = "pending"
    docker = "not_checked"
    kubernetes = "not_checked"
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Command,
        [Parameter(Mandatory = $true)][string]$Label
    )

    # Windows PowerShell 5.1 converts native stderr output into PowerShell
    # error records. Docker legitimately writes progress/warnings to stderr
    # even when the command succeeds, so judge native commands by exit code.
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "Continue"
        & $Command
        $nativeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }

    if ($nativeExitCode -ne 0) {
        throw "$Label failed with exit code $nativeExitCode"
    }
}

function Test-DockerDaemon {
    $oldPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = "SilentlyContinue"
        docker info *> $null
        $dockerExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $oldPreference
    }
    return ($dockerExitCode -eq 0)
}

function Try-StartDockerDesktop {
    if (Test-DockerDaemon) { return $true }

    $candidates = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            Write-Host "Docker CLI is installed but the daemon is not running. Starting Docker Desktop..."
            Start-Process $candidate | Out-Null
            for ($i = 0; $i -lt 24; $i++) {
                Start-Sleep -Seconds 5
                if (Test-DockerDaemon) { return $true }
            }
            break
        }
    }
    return (Test-DockerDaemon)
}

try {
    Write-Host "=== AgentOps final quality gate ==="
    Invoke-NativeChecked { python -m pip install -r requirements-dev.txt } "Dependency installation"
    Invoke-NativeChecked { pytest -q } "Pytest"
    Invoke-NativeChecked { ruff check backend tests frontend } "Ruff"
    Invoke-NativeChecked { python -m backend.evaluation.run_policy_evaluation } "Policy evaluation"
    $report.python_quality = "pass"

    Write-Host "=== Live public source ==="
    Invoke-NativeChecked { python -m backend.evaluation.run_live_source_check } "Live-source verification"
    $report.live_source = "pass"

    Write-Host "=== FastAPI smoke test ==="
    $api = Start-Process python -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000" -PassThru -WindowStyle Hidden
    try {
        Start-Sleep -Seconds 5
        $health = Invoke-RestMethod http://127.0.0.1:8000/health
        if ($health.status -ne "ok") { throw "FastAPI health failed" }
        $source = Invoke-RestMethod http://127.0.0.1:8000/source-health
        if (-not $source.ok) { throw "Source health failed through FastAPI" }
        $report.fastapi = "pass"

        Write-Host "=== Streamlit smoke test ==="
        $ui = Start-Process python -ArgumentList "-m", "streamlit", "run", "frontend/app.py", "--server.headless", "true", "--server.port", "8501" -PassThru -WindowStyle Hidden
        try {
            Start-Sleep -Seconds 7
            $uiHealth = Invoke-WebRequest http://127.0.0.1:8501/_stcore/health -UseBasicParsing
            if ($uiHealth.StatusCode -ne 200) { throw "Streamlit health failed" }
            $report.streamlit = "pass"
        }
        finally {
            if ($ui -and -not $ui.HasExited) { Stop-Process -Id $ui.Id -Force }
        }
    }
    finally {
        if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force }
    }

    Write-Host "=== MCP import/discovery smoke test ==="
    Invoke-NativeChecked { python -c "from backend.mcp_server import mcp; print('MCP server ready:', type(mcp).__name__)" } "MCP smoke test"
    $report.mcp = "pass"

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        Write-Host "=== Docker build/config smoke test ==="
        if (Try-StartDockerDesktop) {
            Invoke-NativeChecked { docker compose config | Out-Null } "Docker Compose config"
            Invoke-NativeChecked { docker build -t agentops-local-backend:final . } "Backend Docker build"
            Invoke-NativeChecked { docker build -f Dockerfile.streamlit -t agentops-local-ui:final . } "Streamlit Docker build"
            $report.docker = "pass"
        }
        else {
            $report.docker = "blocked_docker_daemon_not_running"
            Write-Warning "Docker is installed, but the Docker daemon is unavailable. Docker validation was not marked as passed."
        }
    }
    else {
        $report.docker = "skipped_docker_not_installed"
    }

    if ((Get-Command kind -ErrorAction SilentlyContinue) -and (Get-Command kubectl -ErrorAction SilentlyContinue) -and ($report.docker -eq "pass")) {
        Write-Host "=== Kubernetes local deployment demo ==="

        $oldPreference = $ErrorActionPreference
        try {
            # Docker/WSL may emit harmless warnings to stderr while kind is running.
            $ErrorActionPreference = "Continue"
            & "$PSScriptRoot\k8s_demo.ps1"
            $kubernetesExitCode = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $oldPreference
        }

        if ($kubernetesExitCode -ne 0) {
            throw "Kubernetes demo failed with exit code $kubernetesExitCode"
        }

        $report.kubernetes = "deployment_pass"
    }
    elseif (Get-Command kubectl -ErrorAction SilentlyContinue) {
        Write-Host "=== Kubernetes manifest validation ==="
        Invoke-NativeChecked { kubectl apply --dry-run=client --validate=false -f k8s/namespace.yaml | Out-Null } "Kubernetes namespace validation"
        Invoke-NativeChecked { kubectl apply --dry-run=client --validate=false -f k8s/configmap.yaml | Out-Null } "Kubernetes ConfigMap validation"
        Invoke-NativeChecked { kubectl apply --dry-run=client --validate=false -f k8s/postgres.yaml | Out-Null } "Kubernetes PostgreSQL validation"
        Invoke-NativeChecked { kubectl apply --dry-run=client --validate=false -f k8s/backend.yaml | Out-Null } "Kubernetes backend validation"
        Invoke-NativeChecked { kubectl apply --dry-run=client --validate=false -f k8s/ui.yaml | Out-Null } "Kubernetes UI validation"
        $report.kubernetes = "manifest_pass_deployment_not_run"
    }
    else {
        $report.kubernetes = "skipped_kubernetes_tools_not_installed"
    }
}
catch {
    $report["failure"] = $_.Exception.Message
    Write-Error $_
}
finally {
    $report.finished_at = (Get-Date).ToString("o")
    New-Item -ItemType Directory -Force reports | Out-Null
    $report | ConvertTo-Json -Depth 6 | Set-Content reports/final_validation.json
    $report | Format-List
    Write-Host "Final report: reports/final_validation.json"
}

if ($report.Contains("failure")) {
    exit 1
}

