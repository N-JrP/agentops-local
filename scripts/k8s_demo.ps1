$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Invoke-NativeChecked {
    param(
        [Parameter(Mandatory = $true)][scriptblock]$Command,
        [Parameter(Mandatory = $true)][string]$Label
    )

    # Windows PowerShell 5.1 turns native stderr into PowerShell error records.
    # Docker/WSL may emit harmless warnings even when the command succeeds,
    # so native commands are judged by their exit code instead.
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
Require-Command docker
Require-Command kind
Require-Command kubectl

Invoke-NativeChecked { docker info *> $null } "Docker daemon check"

$cluster = "agentops-local"
$clusters = & kind get clusters
if ($LASTEXITCODE -ne 0) { throw "kind get clusters failed with exit code $LASTEXITCODE" }
if (-not ($clusters | Select-String -SimpleMatch $cluster)) {
    Invoke-NativeChecked { kind create cluster --name $cluster } "kind cluster creation"
}

Write-Host "Building AgentOps images..."
Invoke-NativeChecked { docker build -t agentops-local-backend:latest . } "Backend Docker build"
Invoke-NativeChecked { docker build -f Dockerfile.streamlit -t agentops-local-ui:latest . } "Streamlit Docker build"

Invoke-NativeChecked { kind load docker-image agentops-local-backend:latest --name $cluster } "Load backend image into kind"
Invoke-NativeChecked { kind load docker-image agentops-local-ui:latest --name $cluster } "Load UI image into kind"

Invoke-NativeChecked { kubectl apply -f k8s/namespace.yaml } "Apply namespace"
Invoke-NativeChecked { kubectl apply -f k8s/configmap.yaml } "Apply ConfigMap"
Invoke-NativeChecked { kubectl apply -f k8s/postgres.yaml } "Apply PostgreSQL"
Invoke-NativeChecked { kubectl apply -f k8s/backend.yaml } "Apply backend"
Invoke-NativeChecked { kubectl apply -f k8s/ui.yaml } "Apply UI"

Invoke-NativeChecked { kubectl -n agentops rollout status deployment/postgres --timeout=120s } "PostgreSQL rollout"
Invoke-NativeChecked { kubectl -n agentops rollout status deployment/agentops-backend --timeout=180s } "Backend rollout"
Invoke-NativeChecked { kubectl -n agentops rollout status deployment/agentops-ui --timeout=120s } "UI rollout"

Invoke-NativeChecked { kubectl -n agentops get pods,svc } "Kubernetes status check"
Write-Host "Kubernetes demo deployed successfully."
Write-Host "To view the UI locally: kubectl -n agentops port-forward svc/agentops-ui 8501:8501"

