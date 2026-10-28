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

# Cursor 项目钩子。--global 不写：用户级 hook 会拦到所有仓库。
merge_cursor_hooks() {
  local mode="$1"
  local hooks_file="$base/.cursor/hooks.json"
  [ "$global" = 1 ] && return 0
  [ -d "$base/.cursor" ] || return 0
  python3 - "$hooks_file" "$mode" << 'PY'
import json, os, sys
path, mode = sys.argv[1], sys.argv[2]
session = ".cursor/skills/data-workflow/hooks/session-start"
gate = ".cursor/skills/data-workflow/hooks/gate-edit"
ours = {session, gate}

def load():
    if not os.path.isfile(path):
        return {"version": 1, "hooks": {}}
    with open(path, encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError:
            return {"version": 1, "hooks": {}}
    if not isinstance(data, dict):
        return {"version": 1, "hooks": {}}
    data.setdefault("version", 1)
    if not isinstance(data.get("hooks"), dict):
        data["hooks"] = {}
    return data

data = load()
hooks = data["hooks"]

def entries(event):
    raw = hooks.get(event, [])
    return [e for e in raw if isinstance(e, dict)] if isinstance(raw, list) else []

def is_ours(entry):
    return entry.get("command") in ours

if mode == "remove":
    for event in list(hooks):
        kept = [e for e in entries(event) if not is_ours(e)]
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if not hooks and set(data) <= {"version", "hooks"}:
        if os.path.isfile(path):
            os.remove(path)
        print("HOOKS removed %s" % path)
        raise SystemExit(0)
else:
    session_hooks = entries("sessionStart")
    if not any(e.get("command") == session for e in session_hooks):
        session_hooks.append({"command": session})
    hooks["sessionStart"] = session_hooks
    for event in ("preToolUse", "beforeShellExecution"):
        event_hooks = entries(event)
        if not any(e.get("command") == gate for e in event_hooks):
            event_hooks.append({"command": gate, "failClosed": True})
        hooks[event] = event_hooks

os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, indent=2, ensure_ascii=False)
    fh.write("\n")
print("HOOKS %s %s" % (mode, path))
PY
}

if [ "$unlink" = 1 ]; then
  merge_cursor_hooks remove
fi

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
  if [ "$global" = 1 ]; then
    printf 'HOOKS --global 不写 Cursor hook。强制绑定只在装进某个项目的 .cursor 时生效。\n'
  else
    merge_cursor_hooks add
  fi
  printf '\nDONE 复制到 %s 个工具目录。项目里的副本不依赖技能仓库。\n' "${#dirs[@]}"
  printf '     配置在 %s。要更新技能正文，再跑一次本脚本，config.yaml 不会被盖掉。\n' "$primary"
fi
