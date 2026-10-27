# 拉取 project_proxy2d 的私有商用资源到 project_proxy2d/assets/
# 本地用法：
#   ./scripts/fetch_assets.ps1
#   ./scripts/fetch_assets.ps1 -Repo "https://x-access-token:<TOKEN>@github.com/<you>/project_proxy2d-assets.git"
param(
    [string]$Repo = "https://github.com/coder210/project_proxy2d-assets.git"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root "project_proxy2d/assets"

if (Test-Path (Join-Path $dest ".git")) {
    Write-Host "资源已存在，执行 pull：$dest"
    git -C $dest pull --ff-only
    exit $LASTEXITCODE
}

if (Test-Path $dest) {
    Write-Error "目标已存在且不是 git 仓库：$dest`n请先把它移走（可能含你本地未提交的资源），再重试。"
    exit 1
}

Write-Host "克隆私有资源到：$dest"
git clone $Repo $dest
exit $LASTEXITCODE
