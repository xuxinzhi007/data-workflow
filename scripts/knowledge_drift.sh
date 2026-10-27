#!/usr/bin/env bash
# knowledge_drift.sh —— 知识新鲜度门禁
#
# 用法:
#   knowledge_drift.sh <doc.md> [...]     # 检查指定文档
#   knowledge_drift.sh                    # 扫 Obsidian knowledge/（含 排查卡片/）+ CONTEXT.md
#
# 从 YAML frontmatter 读 verified_commit 与 watches，在 data-service 仓库内比对 HEAD：
#   1. git rev-list --count <commit>..HEAD          → 落后多少 commit
#   2. git diff --name-only <commit>..HEAD -- <watches> → 被盯文件是否动过
#   3. 逐文件 git diff --shortstat                  → 变动量级
# 每份文档输出一行 FRESH / STALE / MISSING。
#
# 门禁永不阻塞：正常恒 exit 0。exit 2 仅用于「文件读不了 / frontmatter 未闭合」这类无法解析的情况。
# 缺 frontmatter 或缺 verified_commit 按 STALE 处理 —— 这让未纳管的文档自我暴露，而不是靠制度。
#
# 注意: Obsidian vault 路径含空格，所有路径必须引号包裹。

set -uo pipefail

VAULT_KNOWLEDGE="/Users/xuxinzhi/Documents/Obsidian Vault/xxz_obsidian/knowledge"
DEFAULT_REPO="$HOME/Documents/gowork/data-service"

# 本脚本现在住在独立插件仓库里，不再靠自身位置推断被测仓库。
# 优先级: $DS_REPO > 当前目录所在仓库 > 默认 data-service 路径。
is_ds_repo() { [ -n "${1:-}" ] && [ -d "$1/internal/biz" ]; }
repo_dir="${DS_REPO:-}"
if ! is_ds_repo "$repo_dir"; then
  repo_dir="$(git -C "$(pwd)" rev-parse --show-toplevel 2>/dev/null || true)"
fi
if ! is_ds_repo "$repo_dir"; then
  repo_dir="$(git -C "$DEFAULT_REPO" rev-parse --show-toplevel 2>/dev/null || true)"
fi

if ! is_ds_repo "$repo_dir"; then
  printf 'UNPARSEABLE 找不到 data-service 仓库（试过 $DS_REPO、当前目录、%s）\n' "$DEFAULT_REPO"
  exit 2
fi

# --- frontmatter 解析 -------------------------------------------------------

# 只在前置 frontmatter 块（首个 --- 到下一个 ---）内取值
fm_field() { # fm_field <file> <key>
  awk -v key="$2" '
    !started && $0 ~ /^---[[:space:]]*$/ { started=1; infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { exit }
    infm && $0 ~ "^" key ":" {
      sub("^" key ":[[:space:]]*", "")
      sub("[[:space:]]*$", "")
      print
      exit
    }
  ' "$1"
}

fm_list() { # fm_list <file> <key>  → 每行一个列表项
  awk -v key="$2" '
    !started && $0 ~ /^---[[:space:]]*$/ { started=1; infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/ { exit }
    infm && $0 ~ "^" key ":" { inlist=1; next }
    inlist && $0 ~ /^[[:space:]]*-[[:space:]]*/ {
      sub("^[[:space:]]*-[[:space:]]*", "")
      sub("[[:space:]]*$", "")
      gsub(/^["'\'']|["'\'']$/, "")
      if ($0 != "") print
      next
    }
    inlist { exit }
  ' "$1"
}

fm_terminated() { # 有开始的 --- 且有结束的 --- 才算闭合
  awk '
    /^---[[:space:]]*$/ { n++ }
    END { exit (n >= 2 ? 0 : 1) }
  ' "$1"
}

# --- 单文档判级 -------------------------------------------------------------

grade() {
  local doc="$1" commit behind watches changed detail f ins del

  if [ ! -f "$doc" ]; then
    printf 'MISSING %s\n' "$doc"
    return 0
  fi
  if [ ! -r "$doc" ]; then
    printf 'UNPARSEABLE %s（不可读）\n' "$doc"
    return 2
  fi
  # 索引/说明文件不是知识文档，不参与判级
  if [ "$(basename -- "$doc")" = "README.md" ]; then
    printf 'SKIP %s（索引/说明，不是知识文档）\n' "$doc"
    return 0
  fi

  # 没有 frontmatter 是常态（例如整个 Obsidian 知识库），按 STALE 自我暴露即可
  if head -n 20 "$doc" | grep -q '^---[[:space:]]*$'; then
    if ! fm_terminated "$doc"; then
      printf 'UNPARSEABLE %s（frontmatter 未闭合）\n' "$doc"
      return 2
    fi
  fi

  commit="$(fm_field "$doc" verified_commit)"
  if [ -z "$commit" ]; then
    printf 'STALE %s: 无 verified_commit（未纳管，按过期处理，只可当线索）\n' "$doc"
    return 0
  fi
  if ! git -C "$repo_dir" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    printf 'STALE %s: verified_commit %s 在本仓库不可解析\n' "$doc" "$commit"
    return 0
  fi

  behind="$(git -C "$repo_dir" rev-list --count "${commit}..HEAD" 2>/dev/null)"
  [ -z "$behind" ] && behind='?'

  watches=()
  while IFS= read -r line; do
    [ -n "$line" ] && watches+=("$line")
  done < <(fm_list "$doc" watches)

  if [ "${#watches[@]}" -eq 0 ]; then
    if [ "$behind" = "0" ]; then
      printf 'FRESH %s（无 watches，仅凭 commit 相同判定）\n' "$doc"
    else
      printf 'STALE %s: 落后 %s commit；无 watches，无法判定相关文件是否变动\n' "$doc" "$behind"
    fi
    return 0
  fi

  changed="$(git -C "$repo_dir" diff --name-only "${commit}..HEAD" -- "${watches[@]}" 2>/dev/null)"
  if [ -z "$changed" ]; then
    printf 'FRESH %s（落后 %s commit，但 watches 未变动）\n' "$doc" "$behind"
    return 0
  fi

  detail=''
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    ins=''; del=''
    read -r ins del _ < <(git -C "$repo_dir" diff --numstat "${commit}..HEAD" -- "$f" 2>/dev/null)
    if [ "$ins" = "-" ] || [ "$del" = "-" ]; then
      detail="${detail}${f} (binary); "
    else
      detail="${detail}${f} (+${ins:-0}/-${del:-0}); "
    fi
  done <<< "$changed"

  printf 'STALE %s: 落后 %s commit；watches 变动: %s\n' "$doc" "$behind" "${detail%; }"
  return 0
}

# --- 目标收集 ---------------------------------------------------------------

targets=()
if [ "$#" -gt 0 ]; then
  for a in "$@"; do targets+=("$a"); done
else
  if [ -d "$VAULT_KNOWLEDGE" ]; then
    while IFS= read -r f; do targets+=("$f"); done < <(find "$VAULT_KNOWLEDGE" -type f -name '*.md' 2>/dev/null | sort)
  fi
  [ -f "$repo_dir/CONTEXT.md" ] && targets+=("$repo_dir/CONTEXT.md")
fi

if [ "${#targets[@]}" -eq 0 ]; then
  printf 'MISSING 没有可检查的文档（vault 路径: %s）\n' "$VAULT_KNOWLEDGE"
  exit 0
fi

rc=0
for t in "${targets[@]}"; do
  grade "$t"
  s=$?
  [ "$s" -gt "$rc" ] && rc="$s"
done

exit "$rc"
