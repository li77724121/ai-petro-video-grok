#!/bin/bash
# 一键发布到 GitHub 公开仓库
# 用法: ./publish.sh [token]    （token 省略时读取 ~/.hermes/github_token.txt）
set -euo pipefail

REPO="ai-petro-video-grok"
DESC="🐱 本地零 API 费用的宠物短视频生成器（Pillow 逐帧绘制 + ffmpeg）"
DIR="$(cd "$(dirname "$0")" && pwd)"
TOKEN="${1:-}"
if [ -z "$TOKEN" ] && [ -f "$HOME/.hermes/github_token.txt" ]; then
  TOKEN="$(cat "$HOME/.hermes/github_token.txt")"
fi
if [ -z "$TOKEN" ]; then
  echo "❌ 缺少 token：./publish.sh <token> 或写入 ~/.hermes/github_token.txt" >&2
  exit 1
fi

OWNER=$(curl -sS -H "Authorization: token $TOKEN" https://api.github.com/user \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['login'])")
echo "✅ 认证用户: $OWNER"

# 已存在则跳过创建
CODE=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: token $TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO")
if [ "$CODE" = "404" ]; then
  curl -sS -X POST https://api.github.com/user/repos \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -d "{\"name\":\"$REPO\",\"description\":\"$DESC\",\"private\":false,\"has_issues\":true}" \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('✅ 仓库已创建:', d.get('html_url') or d)"
else
  echo "ℹ️  仓库已存在，直接推送"
fi

cd "$DIR"
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:$TOKEN@github.com/$OWNER/$REPO.git"
git branch -M main
git push -u origin main
git remote set-url origin "https://github.com/$OWNER/$REPO.git"
echo "🎉 已发布: https://github.com/$OWNER/$REPO"
