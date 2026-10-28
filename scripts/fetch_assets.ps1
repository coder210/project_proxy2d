# Fetch the private commercial assets for project_proxy2d into assets/ (private repo restructured to root, no project_proxy2d/ wrapper)
# Usage:
#   ./scripts/fetch_assets.ps1
#   ./scripts/fetch_assets.ps1 -Repo "https://x-access-token:<TOKEN>@github.com/<you>/project_proxy2d-assets.git"
param(
    [string]$Repo = "https://github.com/coder210/project_proxy2d-assets.git"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "assets"

if (Test-Path (Join-Path $dest ".git")) {
    Write-Host "Assets already present, pulling: $dest"
    git -C $dest pull --ff-only
    exit $LASTEXITCODE
}

if (Test-Path $dest) {
    Write-Error "Destination exists but is not a git repo: $dest . Move it away first."
    exit 1
}

Write-Host "Cloning private assets into: $dest"
git clone $Repo $dest
exit $LASTEXITCODE
