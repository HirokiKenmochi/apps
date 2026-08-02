#!/usr/bin/env bash
# TanIn を公開版（Streamlit Community Cloud）へ反映するスクリプト。
#
#   ./scripts/deploy.sh "コミットメッセージ"
#   DRY_RUN=1 ./scripts/deploy.sh "お試し"   # コミット・push・監視をせずに動作だけ確認
#
# やること
#   1. テストと Lint を実行（こわれていたら止まる）
#   2. static/version.txt に「いつのビルドか」を書き込む
#   3. コミットして push
#   4. 公開版が新しい version.txt を返すまで見張る
#   5. 数分待っても変わらなければ、Reboot のしかたを表示する
#
# 注意: macOS の bash 3.2 では、変数の直後に全角文字が続くと変数名の一部と
#       解釈されてしまう。参照は必ず ${name} の形で書くこと。
set -euo pipefail

APP_URL="${APP_URL:-https://tanin-app.streamlit.app}"
# Streamlit Community Cloud はアプリを /~/+/ の下で配信する。
# 自前で streamlit run しているときは /app/static/... なので、両方を見に行く。
VERSION_URL="${APP_URL}/~/+/app/static/version.txt"
VERSION_URL_ALT="${APP_URL}/app/static/version.txt"
WAIT_SECONDS="${WAIT_SECONDS:-300}"
DRY_RUN="${DRY_RUN:-}"

cd "$(dirname "$0")/.."
PY=".venv/bin/python"
[ -x "${PY}" ] || PY="python3"

message="${1:-Update TanIn}"
build="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "▶ テストと Lint"
"${PY}" -m pytest -q
"${PY}" -m ruff check .

echo "▶ バージョンを書き込む build=${build}"
printf 'build=%s\n' "${build}" > static/version.txt

if [ -n "${DRY_RUN}" ]; then
    echo "▶ DRY_RUN のため、コミット・push・反映確認はしません"
    git checkout -- static/version.txt 2>/dev/null || true
    echo "✅ スクリプトはここまで正常に動きます"
    exit 0
fi

echo "▶ コミットして push"
git add -A
git commit -q -m "${message}" || echo "  コミットする変更はありませんでした"
commit="$(git rev-parse --short HEAD)"
git push origin main

echo "▶ 公開版に反映されるのを待ちます 最大 $((WAIT_SECONDS / 60)) 分"
echo "  ${VERSION_URL}"
deadline=$(( $(date +%s) + WAIT_SECONDS ))
while [ "$(date +%s)" -lt "${deadline}" ]; do
    live="$(curl -fsS --max-time 10 "${VERSION_URL}" 2>/dev/null | grep '^build=' || true)"
    if [ -z "${live}" ]; then
        live="$(curl -fsS --max-time 10 "${VERSION_URL_ALT}" 2>/dev/null | grep '^build=' || true)"
    fi
    if [ "${live}" = "build=${build}" ]; then
        echo ""
        echo "✅ 反映されました  ${APP_URL}  コミット ${commit}"
        exit 0
    fi
    printf '.'
    sleep 10
done

echo ""
echo "⏳ まだ反映されていません（Streamlit 側で処理が滞ることがあります）"
echo "   つぎの手順ですぐ反映できます:"
echo "     1. ${APP_URL} を開く"
echo "     2. 右下の Manage app → 右上の ⋮ → Reboot app"
echo "   1〜2 分で最新版 ${commit} になります。"
exit 1
