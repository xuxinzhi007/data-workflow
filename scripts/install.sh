#!/usr/bin/env bash
# install.sh —— 把 skills/data-workflow 复制进各 agent 工具的原生技能目录。
#
# 复制，不是软链。装完后项目里的技能和技能仓库互不依赖，和旁边那些单独的技能一样。
# 再跑一次会更新副本，但不覆盖已经写过的 config.yaml。
# 多个工具目录的技能正文各有一份；config.yaml 只留一份实体，其余指过去。
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
  dest="$sd/data-workflow"
  if [ "$unlink" = 1 ]; then
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
      rm "$dest"
      printf 'UNLINK %s\n' "$dest"
    elif [ -d "$dest" ] && [ ! -L "$dest" ]; then
      find "$dest" -mindepth 1 -maxdepth 1 ! -name config.yaml -exec rm -rf {} +
      rmdir "$dest" 2>/dev/null || true
      printf 'UNLINK %s\n' "$dest"
    fi
    continue
  fi
  if [ -L "$dest" ]; then
    rm "$dest"
  fi
  mkdir -p "$dest"
  rsync -a --delete --exclude config.yaml "$src/" "$dest/"
  printf 'COPY   %s\n' "$dest"
done

if [ "$unlink" = 0 ]; then
  legacy="$base/.data-workflow/config.yaml"
  primary=""
  for sd in "${dirs[@]}"; do
    dest="$sd/data-workflow"
    [ -d "$dest" ] && [ ! -L "$dest" ] || continue
    if [ -z "$primary" ]; then
      primary="$dest/config.yaml"
      if [ -L "$primary" ]; then
        rm "$primary"
      fi
      if [ ! -f "$primary" ]; then
        if [ -f "$legacy" ]; then
          mv "$legacy" "$primary"
          rmdir "$base/.data-workflow" 2>/dev/null || true
          printf 'CONFIG %s\n' "$primary"
        else
          cp "$repo_root/config.example.yaml" "$primary"
          printf 'CONFIG %s\n' "$primary"
        fi
      else
        printf 'CONFIG %s 已存在，不覆盖\n' "$primary"
      fi
    elif [ ! -e "$dest/config.yaml" ] || [ -L "$dest/config.yaml" ]; then
      ln -sfn "$primary" "$dest/config.yaml"
      printf 'CONFIG %s\n' "$dest/config.yaml"
    fi
  done
  if [ -n "$primary" ] && [ -f "$legacy" ]; then
    rm -f "$legacy"
    rmdir "$base/.data-workflow" 2>/dev/null || true
  fi
  printf '\nDONE 复制到 %s 个工具目录。项目里的副本不依赖技能仓库。\n' "${#dirs[@]}"
  printf '     配置在 %s。要更新技能正文，再跑一次本脚本，config.yaml 不会被盖掉。\n' "$primary"
fi
