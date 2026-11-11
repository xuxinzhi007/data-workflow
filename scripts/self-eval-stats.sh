#!/usr/bin/env bash
# 从 specs/ 历史运行里取自评分布。不调用模型，不花钱。
# 用来决定 C3/C9 的对照实验值不值得做——见 docs/dev/c3-c9-experiment.md。
set -uo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$repo/skills/data-workflow/scripts/find_python.sh"
if ! py="$(dw_python)"; then
  printf '找不到可用的 python\n'
  exit 2
fi
cd "$repo"
# shellcheck disable=SC2086
exec $py "$repo/scripts/honesty_stats.py" "${1:-specs}" "${@:2}"
