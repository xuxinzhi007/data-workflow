#!/usr/bin/env bash
# install.sh —— 把本仓 skills/ 铺进各 agent 工具的原生技能目录（软链，改完即生效）。
#
# 为什么：技能本体是 agentskills 标准（SKILL.md + references/ + scripts/），Claude Code / Cursor /
# Qoder / Codex 都读；但每个工具只认自己的目录。v1 靠手工软链，换工具就断。
# 本脚本探测目标位置已存在哪些 .<tool> 目录，只铺存在的，不凭空造目录污染机器。
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

if [ "${#dirs[@]}" = 0 ]; then
  printf 'NOTHING %s 下没有 .claude/.cursor/.qoder/.codex/.agents 任何一个。\n' "$base"
  printf '        先初始化目标工具，或显式传 target_dir / --global。\n'
  exit 0
fi

for sd in "${dirs[@]}"; do
  mkdir -p "$sd"
  for skill in "$repo_root"/skills/*/; do
    name="$(basename "$skill")"
    link="$sd/$name"
    if [ "$unlink" = 1 ]; then
      if [ -L "$link" ] && [ "$(readlink "$link")" = "$repo_root/skills/$name" ]; then
        rm "$link"
        printf 'UNLINK %s\n' "$link"
      fi
      continue
    fi
    ln -sfn "$repo_root/skills/$name" "$link"
    printf 'LINK   %s -> skills/%s\n' "$link" "$name"
  done
done

if [ "$unlink" = 0 ]; then
  printf '\nDONE 铺到 %s 个工具目录。技能之间用命名空间名互引，换机器不断。\n' "${#dirs[@]}"
  printf '     知识源配置见本仓 config.yaml（不存在时复制 config.example.yaml）。\n'
fi
