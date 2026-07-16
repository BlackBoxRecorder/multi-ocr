#!/usr/bin/env bash
set -euo pipefail

PART="${1:-minor}"  # major / minor / patch

echo "🚀 multi-ocr 发布流程开始"
echo ""

# ── 1. 检查 git 状态 ──────────────────────────────────────────
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ 工作区有未提交的变更，请先提交或暂存"
    exit 1
fi

# ── 2. 升级版本号 ──────────────────────────────────────────────
echo "📦 升级版本（$PART）..."
hatch version "$PART"
NEW_VERSION="$(hatch version)"
echo "   新版本: $NEW_VERSION"
echo ""

# ── 3. 构建 ────────────────────────────────────────────────────
echo "🔨 构建包..."
hatch build
echo ""

# ── 4. 发布到 PyPI ─────────────────────────────────────────────
echo "📤 发布到 PyPI..."
hatch publish
echo ""

# ── 5. Git 提交 + Tag ──────────────────────────────────────────
echo "🏷️  Git 提交 & 打标签..."
git add -A
git commit -m "chore: release v${NEW_VERSION}"
git tag "v${NEW_VERSION}"
git push
git push --tags
echo ""

echo "✅ v${NEW_VERSION} 发布完成！"
