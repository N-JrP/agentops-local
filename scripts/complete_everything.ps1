$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Resolve-PortableCommand {
    param(
        [Parameter(Mandatory = $true)][string]$CommandName
    )

    $existing = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($existing) {
        return $existing.Source
    }

    $exe = "$CommandName.exe"
    $candidates = @()

    $directPaths = @(
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\$exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\$exe"),
        (Join-Path $env:USERPROFILE "AppData\Local\Microsoft\WinGet\Links\$exe")
    )

    foreach ($path in $directPaths) {
        if (Test-Path $path) {
            $candidates += Get-Item $path
        }
    }

    $packageRoot = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $packageRoot) {
        $found = Get-ChildItem $packageRoot -Recurse -Filter $exe -File -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($found) {
            $candidates += $found
        }
    }

    if ($candidates.Count -gt 0) {
        $selected = $candidates | Select-Object -First 1
        $dir = Split-Path -Parent $selected.FullName
        if ($env:Path -notlike "*$dir*") {
            $env:Path = "$dir;$env:Path"
        }
        return $selected.FullName
    }

    return $null
}

function Install-WithWingetIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$CommandName,
        [Parameter(Mandatory = $true)][string]$PackageId
    )

    $resolved = Resolve-PortableCommand -CommandName $CommandName
    if ($resolved) {
        Write-Host "$CommandName ready: $resolved"
        return
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "$CommandName is missing and winget is unavailable. Install $PackageId, then rerun this script."
    }

    Write-Host "Installing $PackageId..."
    & winget install --id $PackageId --exact --accept-package-agreements --accept-source-agreements
    $wingetExit = $LASTEXITCODE

    # WinGet may return a non-zero status when the package is already installed.
    # Resolve the executable first; only fail if it is still genuinely unavailable.
    $resolved = Resolve-PortableCommand -CommandName $CommandName
    if ($resolved) {
        Write-Host "$CommandName ready: $resolved"
        return
    }

    throw "Unable to locate $CommandName after WinGet attempted $PackageId (exit code $wingetExit)."
}

Install-WithWingetIfMissing -CommandName "kubectl" -PackageId "Kubernetes.kubectl"
Install-WithWingetIfMissing -CommandName "kind" -PackageId "Kubernetes.kind"

Write-Host "Resolved Kubernetes tools:"
Get-Command kubectl, kind | Select-Object Name, Source | Format-Table -AutoSize

Write-Host "Running full AgentOps finalizer..."
& "$PSScriptRoot\finalize.ps1"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
