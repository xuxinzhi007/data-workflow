#!/usr/bin/env bash
# install.sh —— 只把 skills/data-workflow 铺进各 agent 工具的原生技能目录（软链，改完即生效）。
#
# 阶段文件在 data-workflow/stages/ 里，不是独立技能。再跑一次会卸掉以前按阶段拆开的软链。
#
# 用法:
#   install.sh                 # 铺到当前目录（目标项目根）下已存在的 .claude/.cursor/.qoder/.codex/.agents
#   install.sh --global        # 铺到 $HOME 下已存在的同名目录（个人级）
#   install.sh <target_dir>    # 显式指定目标根
#   install.sh --unlink [...]  # 只删除指向本仓的软链，不动其他东西
set -uo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
global=0
unlink=0
target=""
for a in "$@"; do
  case "$a" in
    --global) global=1 ;;
    --unlink) unlink=1 ;;
    *) target="$a" ;;
  esac
done

base="$target"
[ -z "$base" ] && base="$(pwd)"
[ "$global" = 1 ] && base="$HOME"

dirs=()
for d in .claude .cursor .qoder .codex .agents; do
  [ -d "$base/$d" ] && dirs+=("$base/$d/skills")
done

if [ "${#dirs[@]}" -eq 0 ]; then
  printf 'NOTHING %s 下没有 .claude/.cursor/.qoder/.codex/.agents 任何一个。\n' "$base"
  printf '        先初始化目标工具，或显式传 target_dir / --global。\n'
  exit 0
fi

src="$repo_root/skills/data-workflow"

for sd in "${dirs[@]}"; do
  mkdir -p "$sd"
  for link in "$sd"/*; do
    [ -L "$link" ] || continue
    target_path="$(readlink "$link")"
    case "$target_path" in
      "$repo_root/skills"/*)
        if [ "$target_path" != "$src" ]; then
          rm "$link"
          printf 'UNLINK %s\n' "$link"
        fi
        ;;
    esac
  done
  link="$sd/data-workflow"
  if [ "$unlink" = 1 ]; then
    if [ -L "$link" ] && [ "$(readlink "$link")" = "$src" ]; then
      rm "$link"
      printf 'UNLINK %s\n' "$link"
    fi
    continue
  fi
  ln -sfn "$src" "$link"
  printf 'LINK   %s -> skills/data-workflow\n' "$link"
done

if [ "$unlink" = 0 ]; then
  printf '\nDONE 铺到 %s 个工具目录。每个目录里只有 data-workflow；阶段在它的 stages/ 里。\n' "${#dirs[@]}"
  printf '     知识源配置见本仓 config.yaml（不存在时复制 config.example.yaml）。\n'
fi
