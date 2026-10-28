#!/usr/bin/env bash
# 拉取 project_proxy2d 的私有商用资源到 assets/（私有仓已上移根目录，无 project_proxy2d/ 包裹）
# 用法：
#   ./scripts/fetch_assets.sh
#   ./scripts/fetch_assets.sh "https://x-access-token:<TOKEN>@github.com/<you>/project_proxy2d-assets.git"
set -euo pipefail

REPO="${1:-https://github.com/coder210/project_proxy2d-assets.git}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$ROOT/assets"

if [ -d "$DEST/.git" ]; then
    echo "资源已存在，执行 pull：$DEST"
    git -C "$DEST" pull --ff-only
    exit $?
fi

if [ -e "$DEST" ]; then
    echo "目标已存在且不是 git 仓库：$DEST（请先移走）" >&2
    exit 1
fi

echo "克隆私有资源到：$DEST"
git clone "$REPO" "$DEST"
